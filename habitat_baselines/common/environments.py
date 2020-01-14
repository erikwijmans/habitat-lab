#!/usr/bin/env python3

# Copyright (c) Facebook, Inc. and its affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
r"""
This file hosts task-specific or trainer-specific environments for trainers.
All environments here should be a (direct or indirect ) subclass of Env class
in habitat. Customized environments should be registered using
``@baseline_registry.register_env(name="myEnv")` for reusability
"""

from typing import Any, Dict, Optional, Type, Union

import habitat
from habitat import Config, Dataset
from habitat.sims.habitat_simulator.actions import HabitatSimActions
from habitat.tasks.nav.shortest_path_follower import ShortestPathFollower
from habitat_baselines.common.baseline_registry import baseline_registry


def get_env_class(env_name: str) -> Type[Union[habitat.RLEnv, habitat.Env]]:
    r"""Return environment class based on name.

    Args:
        env_name: name of the environment.

    Returns:
        Type[habitat.RLEnv]: env class.
    """
    return baseline_registry.get_env(env_name)


@baseline_registry.register_env(name="NavRLEnv")
class NavRLEnv(habitat.RLEnv):
    def __init__(self, config: Config, dataset: Optional[Dataset] = None):
        self._rl_config = config.RL
        self._core_env_config = config.TASK_CONFIG

        self._previous_target_distance = None
        self._previous_action = None
        self._episode_distance_covered = None
        self._success_distance = self._core_env_config.TASK.SUCCESS_DISTANCE
        super().__init__(self._core_env_config, dataset)

    def reset(self):
        self._previous_action = None

        observations = super().reset()

        self._previous_target_distance = self.habitat_env.current_episode.info[
            "geodesic_distance"
        ]
        return observations

    def step(self, *args, **kwargs):
        self._previous_action = kwargs["action"]
        return super().step(*args, **kwargs)

    def get_reward_range(self):
        return (
            self._rl_config.SLACK_REWARD - 1.0,
            self._rl_config.SUCCESS_REWARD + 1.0,
        )

    def get_reward(self, observations):
        reward = self._rl_config.SLACK_REWARD

        current_target_distance = self._distance_target()
        reward += self._previous_target_distance - current_target_distance
        self._previous_target_distance = current_target_distance

        if self._episode_success():
            reward += self._rl_config.SUCCESS_REWARD

        return reward

    def _distance_target(self):
        current_position = self._env.sim.get_agent_state().position.tolist()
        target_position = self._env.current_episode.goals[0].position
        distance = self._env.sim.geodesic_distance(
            current_position, target_position
        )
        return distance

    def _episode_success(self):
        if (
            self._env.task.is_stop_called
            and self._distance_target() < self._success_distance
        ):
            return True
        return False

    def get_done(self, observations):
        done = False
        if self._env.episode_over or self._episode_success():
            done = True
        return done

    def get_info(self, observations):
        return self.habitat_env.get_metrics()


@baseline_registry.register_env(name="VLNRLEnv")
class VLNRLEnv(habitat.RLEnv):
    def __init__(self, config: Config, dataset: Optional[Dataset] = None):
        self._rl_config = config.RL
        self._core_env_config = config.TASK_CONFIG

        self._previous_target_distance = None
        self._previous_action = None
        self._episode_distance_covered = None
        self._success_distance = self._core_env_config.TASK.SUCCESS_DISTANCE
        super().__init__(self._core_env_config, dataset)

    def reset(self):
        self._previous_action = None

        observations = super().reset()

        self._previous_target_distance = self.habitat_env.current_episode.info[
            "geodesic_distance"
        ]
        return observations

    def step(self, *args, **kwargs):
        self._previous_action = kwargs["action"]
        return super().step(*args, **kwargs)

    def get_reward_range(self):
        return (
            self._rl_config.SLACK_REWARD - 1.0,
            self._rl_config.SUCCESS_REWARD + 1.0,
        )

    def get_reward(self, observations):
        reward = 0.0

        current_target_distance = self._distance_target()
        reward += self._previous_target_distance - current_target_distance
        self._previous_target_distance = current_target_distance

        if self._episode_success():
            reward += self._rl_config.SUCCESS_REWARD

        return reward

    def _distance_target(self):
        current_position = self._env.sim.get_agent_state().position.tolist()
        target_position = self._env.current_episode.goals[0].position
        distance = self._env.sim.geodesic_distance(
            current_position, target_position
        )
        return distance

    def _episode_success(self):
        if (
            self._env.task.is_stop_called
            and self._distance_target() < self._success_distance
        ):
            return True
        return False

    def get_done(self, observations):
        done = False
        if self._env.episode_over or self._episode_success():
            done = True
        return done

    def get_info(self, observations):
        return self.habitat_env.get_metrics()


@baseline_registry.register_env(name="VLNILEnv")
class VLNILEnv(habitat.Env):
    def __init__(self, config: Config, dataset: Optional[Dataset] = None):
        super().__init__(config.TASK_CONFIG, dataset)
        assert (
            getattr(self._sim, "geodesic_distance", None) is not None
        ), "{} must have a method called geodesic_distance".format(
            type(self._sim).__name__
        )
        assert (
            getattr(self._sim, "get_straight_shortest_path_points", None)
            is not None
        ), "{} must have a method called get_straight_shortest_path_points".format(
            type(self._sim).__name__
        )
        self.follower = ShortestPathFollower(
            self._sim,
            goal_radius=0.5,  # all goals can be navigated to within 0.5m.
            return_one_hot=False,
        )
        self.follower.mode = "geodesic_path"

    def reset(self):
        observations = super().reset()
        return observations

    def step(self, *args, **kwargs):
        kwargs["action"]
        return super().step(*args, **kwargs)

    def get_episode_over(self):
        """When in a VectorEnv, properties cannot be queried. Thus make this a
        function to be called.
        """
        return self.episode_over

    def get_best_action(self):
        """Computes and returns the action along the shortest path to the goal.
        Makes the assumption that the best action a VLN agent should take is
        the shortest path action. This assumption is fair in R2R, but may not
        be for other datasets.
        """
        best_action = self.follower.get_next_action(
            self.current_episode.goals[0].position
        )
        if best_action is None:
            return HabitatSimActions.STOP
        return best_action

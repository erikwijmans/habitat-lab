#!/usr/bin/env python3

# Copyright (c) Facebook, Inc. and its affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from habitat.config.default import get_config

CFG_TEST = "configs/test/habitat_all_sensors_test.yaml"
MAX_TEST_STEPS_LIMIT = 3


def test_overwrite_options():
    for steps_limit in range(MAX_TEST_STEPS_LIMIT):
        config = get_config(
            config_paths=CFG_TEST,
            opts=[f"habitat.environment.max_episode_steps={steps_limit}"],
        )
        assert (
            config.habitat.environment.max_episode_steps == steps_limit
        ), "Overwriting of config options failed."

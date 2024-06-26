#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from logging import Logger

from cmk.utils.site import get_omd_config

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class UpdateCoreConfig(UpdateAction):
    """Ensure we have a fresh microcore config after all update actions were executed"""

    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        if get_omd_config()["CONFIG_CORE"] == "none":
            return  # No core config is needed in this case
        subprocess.check_call(["cmk", "-U"], shell=False)


update_action_registry.register(
    UpdateCoreConfig(
        name="update_core_config",
        title="Update core config",
        sort_index=999,  # Run at the end
    )
)

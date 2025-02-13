#  Copyright (c) 2023-2024. ECCO Sneaks & Data
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

"""
Astra Client module that provides the astra client to the Nexus framework.
"""

import os
from typing import final

from adapta.storage.distributed_object_store import AstraClient
from injector import Module, singleton, provider

from esd_services_api_client.nexus.exceptions.startup_error import FatalStartupConfigurationError


@final
class AstraClientModule(Module):
    """
    Astra Client module.
    """

    @singleton
    @provider
    def provide(self) -> AstraClient:
        """
        DI factory method.
        """
        missing_env_vars = []

        if "CRYSTAL__ALGORITHM_NAME" not in os.environ:
            missing_env_vars.append("CRYSTAL__ALGORITHM_NAME")

        if "CRYSTAL__ASTRA_KEYSPACE" not in os.environ:
            missing_env_vars.append("CRYSTAL__ASTRA_KEYSPACE")

        if "PROTEUS__ASTRA_BUNDLE_BYTES" not in os.environ:
            missing_env_vars.append("PROTEUS__ASTRA_BUNDLE_BYTES")

        if "PROTEUS__ASTRA_CLIENT_ID" not in os.environ:
            missing_env_vars.append("PROTEUS__ASTRA_CLIENT_ID")

        if "PROTEUS__ASTRA_CLIENT_SECRET" not in os.environ:
            missing_env_vars.append("PROTEUS__ASTRA_CLIENT_SECRET")

        if missing_env_vars:
            raise FatalStartupConfigurationError(', '.join(missing_env_vars))

        return AstraClient(
            client_name=os.getenv("CRYSTAL__ALGORITHM_NAME"),
            keyspace=os.getenv("CRYSTAL__ASTRA_KEYSPACE"),
            secure_connect_bundle_bytes=os.getenv("PROTEUS__ASTRA_BUNDLE_BYTES"),
            client_id=os.getenv("PROTEUS__ASTRA_CLIENT_ID"),
            client_secret=os.getenv("PROTEUS__ASTRA_CLIENT_SECRET"),
        )

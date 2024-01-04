import asyncio
import os
from pydoc import locate

from injector import Injector

from esd_services_api_client.crystal import add_crystal_args, extract_crystal_args
from esd_services_api_client.nexus.algorithms._baseline_algorithm import BaselineAlgorithm
from esd_services_api_client.nexus.core.app_dependencies import (
    INJECTION_BINDS,
)


async def main(*_, **kwargs):
    injector = Injector(INJECTION_BINDS)
    algorithm_class = locate(os.getenv("NEXUS__ALGORITHM_CLASS"))
    algorithm: BaselineAlgorithm = injector.get(algorithm_class)
    await algorithm.run(**kwargs)


if __name__ == "__main__":
    parser = add_crystal_args()
    asyncio.run(main(**extract_crystal_args(parser.parse_args()).__dict__))

## Nexus
Set the following environment variables for Azure:
```
IS_LOCAL_RUN=1
NEXUS__ALGORITHM_OUTPUT_PATH=abfss://container@account.dfs.core.windows.net/path/to/result
NEXUS__METRIC_PROVIDER_CONFIGURATION={"metric_namespace": "test"}
NEXUS__QES_CONNECTION_STRING=qes://engine\=DELTA\;plaintext_credentials\={"auth_client_class":"adapta.security.clients.AzureClient"}\;settings\={}
NEXUS__STORAGE_CLIENT_CLASS=adapta.storage.blob.azure_storage_client.AzureStorageClient
PROTEUS__USE_AZURE_CREDENTIAL=1
```

Example usage:

```python
import asyncio
from typing import Dict

import pandas
from adapta.metrics import MetricsProvider
from adapta.storage.query_enabled_store import QueryEnabledStore
from injector import inject

from esd_services_api_client.nexus.abstractions.logger_factory import LoggerFactory
from esd_services_api_client.nexus.abstractions.socket_provider import SocketProvider
from esd_services_api_client.nexus.core.app_core import Nexus
from esd_services_api_client.nexus.algorithms import MinimalisticAlgorithm
from esd_services_api_client.nexus.input import InputReader, InputProcessor
from pandas import DataFrame as PandasDataFrame


async def my_on_complete_func_1(**kwargs):
    pass


async def my_on_complete_func_2(**kwargs):
    pass


class XReader(InputReader):
    async def _context_open(self):
        pass

    async def _context_close(self):
        pass

    @inject
    def __init__(self, store: QueryEnabledStore, metrics_provider: MetricsProvider, logger_factory: LoggerFactory, socket_provider: SocketProvider,
                 *readers: "InputReader"):
        super().__init__(socket_provider.socket("x"), store, metrics_provider, logger_factory, *readers)

    async def _read_input(self) -> PandasDataFrame:
        return pandas.DataFrame([{'a': 1, 'b': 2}, {'a': 2, 'b': 3}])


class YReader(InputReader):
    async def _context_open(self):
        pass

    async def _context_close(self):
        pass

    @inject
    def __init__(self, store: QueryEnabledStore, metrics_provider: MetricsProvider, logger_factory: LoggerFactory, socket_provider: SocketProvider,
                 *readers: "InputReader"):
        super().__init__(socket_provider.socket("y"), store, metrics_provider, logger_factory, *readers)

    async def _read_input(self) -> PandasDataFrame:
        return pandas.DataFrame([{'a': 10, 'b': 12}, {'a': 11, 'b': 13}])


class MyInputProcessor(InputProcessor):
    async def _context_open(self):
        pass

    async def _context_close(self):
        pass

    @inject
    def __init__(self, x: XReader, y: YReader, metrics_provider: MetricsProvider, logger_factory: LoggerFactory,):
        super().__init__(x, y, metrics_provider=metrics_provider, logger_factory=logger_factory)

    async def process_input(self, **_) -> Dict[str, PandasDataFrame]:
        inputs = await self._read_input()
        return {
            'x_ready': inputs["x"].assign(c=[-1, 1]),
            'y_ready': inputs["y"].assign(c=[-1, 1])
        }


class MyAlgorithm(MinimalisticAlgorithm):
    async def _context_open(self):
        pass

    async def _context_close(self):
        pass

    @inject
    def __init__(self, input_processor: MyInputProcessor, metrics_provider: MetricsProvider, logger_factory: LoggerFactory,):
        super().__init__(input_processor, metrics_provider, logger_factory)

    async def _run(self, x_ready: PandasDataFrame, y_ready: PandasDataFrame, **kwargs) -> PandasDataFrame:
        return pandas.concat([x_ready, y_ready])


async def main():
    nexus = Nexus.create() \
        .add_reader(XReader) \
        .add_reader(YReader) \
        .use_processor(MyInputProcessor) \
        .use_algorithm(MyAlgorithm)

    await nexus.activate()
    

if __name__ == "__main__":
    asyncio.run(main())

```

Run this code as `sample.py`:

```shell
python3 sample.py --sas-uri 'https://localhost' --request-id test
```
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
import json
import socketserver
import threading
from dataclasses import dataclass
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, Optional

import pandas
from adapta.metrics import MetricsProvider
from adapta.process_communication import DataSocket
from adapta.storage.query_enabled_store import QueryEnabledStore
from dataclasses_json import DataClassJsonMixin
from injector import inject

from esd_services_api_client.nexus.abstractions.logger_factory import LoggerFactory
from esd_services_api_client.nexus.core.app_core import Nexus
from esd_services_api_client.nexus.algorithms import MinimalisticAlgorithm
from esd_services_api_client.nexus.input import InputReader, InputProcessor
from pandas import DataFrame as PandasDataFrame

from esd_services_api_client.nexus.input.payload_reader import AlgorithmPayload


async def my_on_complete_func_1(**kwargs):
    pass


async def my_on_complete_func_2(**kwargs):
    pass

@dataclass
class MyAlgorithmPayload(AlgorithmPayload, DataClassJsonMixin):
    x: Optional[list[int]] = None
    y: Optional[list[int]] = None

@dataclass
class MyAlgorithmPayload2(AlgorithmPayload, DataClassJsonMixin):
    z: list[int]
    x: Optional[list[int]] = None
    y: Optional[list[int]] = None

    def __post_init__(self):
        pass

class MockRequestHandler(BaseHTTPRequestHandler):
    """
    HTTPServer Mock Request handler
    """

    def __init__(self, request: bytes, client_address: tuple[str, int], server: socketserver.BaseServer):
        """
         Initialize request handler
        :param request:
        :param client_address:
        :param server:
        """
        self._responses = {
            "some/payload": (
                {
                    # "x": [-1, 0, 2],
                    # "y": [10, 11, 12],
                    "z": [1, 2, 3]
                }, 200)
        }
        super().__init__(request, client_address, server)

    def do_GET(self):  # pylint: disable=invalid-name
        """Handle POST requests"""
        current_url = self.path.removeprefix("/")

        if current_url not in self._responses:
            self.send_response(500, "Unknown URL")
            return

        self.send_response(self._responses[current_url][1])
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(self._responses[current_url][0]).encode("utf-8"))

    def log_request(self, code=None, size=None):
        """
         Don't log anything
        :param code:
        :param size:
        :return:
        """
        pass


class XReader(InputReader[MyAlgorithmPayload]):
    async def _context_open(self):
        pass

    async def _context_close(self):
        pass

    @inject
    def __init__(self, store: QueryEnabledStore, metrics_provider: MetricsProvider, logger_factory: LoggerFactory,
                 payload: MyAlgorithmPayload,
                 *readers: "InputReader"):
        super().__init__(DataSocket(alias="x", data_path="testx", data_format='delta'), store, metrics_provider,
                         logger_factory, payload, *readers)

    async def _read_input(self) -> PandasDataFrame:
        self._logger.info("Payload: {payload}", payload=self._payload.to_json())
        return pandas.DataFrame([{'a': 1, 'b': 2}, {'a': 2, 'b': 3}])


class YReader(InputReader[MyAlgorithmPayload2]):
    async def _context_open(self):
        pass

    async def _context_close(self):
        pass

    @inject
    def __init__(self, store: QueryEnabledStore, metrics_provider: MetricsProvider, logger_factory: LoggerFactory,
                 payload: MyAlgorithmPayload2,
                 *readers: "InputReader"):
        super().__init__(DataSocket(alias="y", data_path="testy", data_format='delta'), store, metrics_provider,
                         logger_factory, payload, *readers)

    async def _read_input(self) -> PandasDataFrame:    
        self._logger.info("Payload: {payload}", payload=self._payload.to_json())
        return pandas.DataFrame([{'a': 10, 'b': 12}, {'a': 11, 'b': 13}])


class MyInputProcessor(InputProcessor):
    async def _context_open(self):
        pass

    async def _context_close(self):
        pass

    @inject
    def __init__(self, x: XReader, y: YReader, metrics_provider: MetricsProvider, logger_factory: LoggerFactory, ):
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
    def __init__(self, input_processor: MyInputProcessor, metrics_provider: MetricsProvider,
                 logger_factory: LoggerFactory, ):
        super().__init__(input_processor, metrics_provider, logger_factory)

    async def _run(self, x_ready: PandasDataFrame, y_ready: PandasDataFrame, **kwargs) -> PandasDataFrame:
        return pandas.concat([x_ready, y_ready])


async def main():
    """
     Mock HTTP Server
    :return:
    """
    # NB: http server context here is purely to simulate payload retrieval. You do not need it in your program
    with ThreadingHTTPServer(("localhost", 9876), MockRequestHandler) as server:
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        # Nexus code starts
        nexus = await Nexus.create() \
            .add_reader(XReader) \
            .add_reader(YReader) \
            .use_processor(MyInputProcessor) \
            .use_algorithm(MyAlgorithm) \
            .inject_payload(MyAlgorithmPayload, MyAlgorithmPayload2)

        await nexus.activate()
        
        # Nexus code ends
        server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())


```

Run this code as `sample.py`:

```shell
python3 sample.py --sas-uri http://localhost:9876/some/payload --request-id test
```
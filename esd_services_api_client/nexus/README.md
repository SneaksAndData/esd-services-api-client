## Nexus
Set the following environment variables for Azure:
```
IS_LOCAL_RUN=1
NEXUS__ALGORITHM_OUTPUT_PATH=abfss://container@account.dfs.core.windows.net/path/to/result
NEXUS__METRIC_PROVIDER_CONFIGURATION={"metric_namespace": "test"}
NEXUS__QES_CONNECTION_STRING=qes://engine\=DELTA\;plaintext_credentials\={"auth_client_class":"adapta.security.clients.AzureClient"}\;settings\={}
NEXUS__STORAGE_CLIENT_CLASS=adapta.storage.blob.azure_storage_client.AzureStorageClient
NEXUS__ALGORITHM_INPUT_EXTERNAL_DATA_SOCKETS=[{"alias": "x", "data_path": "test/x", "data_format": "test"}, {"alias": "y", "data_path": "test/y", "data_format": "test"}]
PROTEUS__USE_AZURE_CREDENTIAL=1
```

Example usage:

```python
import asyncio
import json
import os
import socketserver
import threading
from dataclasses import dataclass
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, Optional, Any

import pandas
from adapta.metrics import MetricsProvider
from adapta.storage.query_enabled_store import QueryEnabledStore
from dataclasses_json import DataClassJsonMixin
from injector import inject

from esd_services_api_client.nexus.abstractions.logger_factory import LoggerFactory
from esd_services_api_client.nexus.abstractions.socket_provider import (
    ExternalSocketProvider,
)
from esd_services_api_client.nexus.configurations.algorithm_configuration import (
    NexusConfiguration,
)
from esd_services_api_client.nexus.core.app_core import Nexus
from esd_services_api_client.nexus.abstractions.nexus_object import AlgorithmResult
from esd_services_api_client.nexus.algorithms import MinimalisticAlgorithm
from esd_services_api_client.nexus.input import InputReader, InputProcessor

from esd_services_api_client.nexus.input.payload_reader import AlgorithmPayload


async def my_on_complete_func_1(**kwargs):
    pass


async def my_on_complete_func_2(**kwargs):
    pass


@dataclass
class MyAlgorithmConfiguration(NexusConfiguration):
    @classmethod
    def from_environment(cls) -> "NexusConfiguration":
        return MyAlgorithmConfiguration.from_json(os.getenv("NEXUS__MY_CONFIGURATION"))

    c1: str
    c2: str


@dataclass
class MyAlgorithmPayload(AlgorithmPayload, DataClassJsonMixin):
    x: Optional[list[int]] = None
    y: Optional[list[int]] = None


@dataclass
class MyAlgorithmPayload2(AlgorithmPayload, DataClassJsonMixin):
    z: list[int]
    x: Optional[list[int]] = None
    y: Optional[list[int]] = None


class MockRequestHandler(BaseHTTPRequestHandler):
    """
    HTTPServer Mock Request handler
    """

    def __init__(
        self,
        request: bytes,
        client_address: tuple[str, int],
        server: socketserver.BaseServer,
    ):
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
                },
                200,
            )
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


class XReader(InputReader[MyAlgorithmPayload, pandas.DataFrame]):
    async def _context_open(self):
        pass

    async def _context_close(self):
        pass

    @inject
    def __init__(
        self,
        store: QueryEnabledStore,
        metrics_provider: MetricsProvider,
        logger_factory: LoggerFactory,
        payload: MyAlgorithmPayload,
        socket_provider: ExternalSocketProvider,
        *readers: "InputReader"
    ):
        super().__init__(
            socket=socket_provider.socket("x"),
            store=store,
            metrics_provider=metrics_provider,
            logger_factory=logger_factory,
            payload=payload,
            *readers
        )

    async def _read_input(self) -> pandas.DataFrame:
        self._logger.info(
            "Payload: {payload}; Socket path: {socket_path}",
            payload=self._payload.to_json(),
            socket_path=self.socket.data_path,
        )
        return pandas.DataFrame([{"a": 1, "b": 2}, {"a": 2, "b": 3}])


class YReader(InputReader[MyAlgorithmPayload2, pandas.DataFrame]):
    async def _context_open(self):
        pass

    async def _context_close(self):
        pass

    @inject
    def __init__(
        self,
        store: QueryEnabledStore,
        metrics_provider: MetricsProvider,
        logger_factory: LoggerFactory,
        payload: MyAlgorithmPayload2,
        socket_provider: ExternalSocketProvider,
        *readers: "InputReader"
    ):
        super().__init__(
            socket=socket_provider.socket("y"),
            store=store,
            metrics_provider=metrics_provider,
            logger_factory=logger_factory,
            payload=payload,
            *readers
        )

    async def _read_input(self) -> pandas.DataFrame:
        self._logger.info(
            "Payload: {payload}; Socket path: {socket_path}",
            payload=self._payload.to_json(),
            socket_path=self.socket.data_path,
        )
        return pandas.DataFrame([{"a": 10, "b": 12}, {"a": 11, "b": 13}])


class MyInputProcessor(InputProcessor):
    async def _context_open(self):
        pass

    async def _context_close(self):
        pass

    @inject
    def __init__(
        self,
        x: XReader,
        y: YReader,
        metrics_provider: MetricsProvider,
        logger_factory: LoggerFactory,
        my_conf: MyAlgorithmConfiguration,
    ):
        super().__init__(
            x,
            y,
            metrics_provider=metrics_provider,
            logger_factory=logger_factory,
            payload=None,
        )

        self.conf = my_conf

    async def process_input(self, **_) -> Dict[str, pandas.DataFrame]:
        self._logger.info("Config: {config}", config=self.conf.to_json())
        inputs = await self._read_input()
        return {
            "x_ready": inputs["x"].assign(c=[-1, 1]),
            "y_ready": inputs["y"].assign(c=[-1, 1]),
        }

@dataclass
class MyResult(AlgorithmResult):
    x: pandas.DataFrame
    y: pandas.DataFrame

    def dataframe(self) -> pandas.DataFrame:
        return pandas.concat([self.x, self.y])

    def to_kwargs(self) -> dict[str, Any]:
        pass
    
    
class MyAlgorithm(MinimalisticAlgorithm[MyAlgorithmPayload]):
    async def _context_open(self):
        pass

    async def _context_close(self):
        pass

    @inject
    def __init__(self, metrics_provider: MetricsProvider, logger_factory: LoggerFactory, input_processor: MyInputProcessor):
        super().__init__(metrics_provider, logger_factory, input_processor)

    async def _run(self, x_ready: pandas.DataFrame, y_ready: pandas.DataFrame, **kwargs) -> MyResult:
        return MyResult(x_ready, y_ready)


async def main():
    """
     Mock HTTP Server
    :return:
    """
    with ThreadingHTTPServer(("localhost", 9876), MockRequestHandler) as server:
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        nexus = (
            await Nexus.create()
            .add_reader(XReader)
            .add_reader(YReader)
            .use_processor(MyInputProcessor)
            .use_algorithm(MyAlgorithm)
            .inject_configuration(MyAlgorithmConfiguration)
            .inject_payload(MyAlgorithmPayload, MyAlgorithmPayload2)
        )

        await nexus.activate()
        server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

```

Run this code as `sample.py`:

```shell
python3 sample.py --sas-uri http://localhost:9876/some/payload --request-id test
```

Produces the following:

```
Running _read
Payload: {"x": null, "y": null}; Socket path: test/x
Finished reading X from path test/x in 0.00s seconds
Running _read
Payload: {"z": [1, 2, 3], "x": null, "y": null}; Socket path: test/y
Finished reading Y from path test/y in 0.00s seconds
```
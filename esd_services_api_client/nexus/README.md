## Nexus
Example usage:

```python
import asyncio
from esd_services_api_client.nexus.core.app_core import Nexus
from esd_services_api_client.nexus.algorithms import MinimalisticAlgorithm
from esd_services_api_client.nexus.input.input_reader import InputReader

async def my_on_complete_func_1(**kwargs):
    pass

async def my_on_complete_func_2(**kwargs):
    pass

class SkuReader(InputReader):
    def _read_input(self) -> PandasDataFrame:
        pass
    
class LocationReader(InputReader):
    def _read_input(self) -> PandasDataFrame:
        pass    
    
class MyAlgorithm(MinimalisticAlgorithm):
    def _run(self, **kwargs) -> PandasDataFrame:
        pass

async def main():
    nexus = Nexus.create()\
        .add_reader(SkuReader)\
        .add_reader(LocationReader)\
        .use_algorithm(MyAlgorithm)\
        .on_complete(my_on_complete_func_1(a=1, b=2))\
        .on_complete(my_on_complete_func_2(a=2, b=3))
    
    await nexus.activate()

if __name__ == "__main__":
    asyncio.run(main())
```
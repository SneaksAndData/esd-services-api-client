## Nexus
Example usage:

```python
import asyncio
from esd_services_api_client.nexus.core.app_core import Nexus
from esd_services_api_client.nexus.input.input_processor import InputProcessor
from esd_services_api_client.nexus.input.input_reader import InputReader

async def my_on_complete_func_1(**kwargs):
    pass

async def my_on_complete_func_2(**kwargs):
    pass

async def main():
    nexus = Nexus.create()\
        .on_complete(my_on_complete_func_1(a=1, b=2))\
        .on_complete(my_on_complete_func_2(a=2, b=3))
    
    await nexus.activate()

if __name__ == "__main__":
    asyncio.run(main())
```
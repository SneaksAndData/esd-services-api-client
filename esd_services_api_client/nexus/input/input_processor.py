from abc import abstractmethod, ABC
from typing import Dict

from pandas import DataFrame as PandasDataFrame


class InputProcessor(ABC):
    @abstractmethod
    def process_input(self, **kwargs) -> Dict[str, PandasDataFrame]:
        """ """

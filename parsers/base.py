# ~/benchmaster/parsers/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseParser(ABC):
    """
    Base class for all benchmark parsers.
    """

    @abstractmethod
    def parse(self, content: str) -> Dict[str, Any]:
        """
        Parses the log content and returns a dictionary of metrics.
        
        Args:
            content (str): The raw log content.
            
        Returns:
            Dict[str, Any]: A dictionary containing the extracted metrics (e.g., {"single_core": 1234, "multi_core": 5678}).
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Returns the name of the benchmark.
        """
        pass

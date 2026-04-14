# ~/benchmaster/parsers/cinebench.py

import re
from typing import Any, Dict
from .base import BaseParser

class CinebenchParser(BaseParser):
    """
    Parser for Cinebench (R23/R24) benchmark results.
    Designed to extract core performance metrics from text-based logs.
    """

    @property
    def name(self) -> str:
        return "cinebench"

    def parse(self, content: str) -> Dict[str, Any]:
        """
        Parses Cinebench log content and returns a dictionary of extracted metrics.
        
        Expected patterns in log:
        - 'Single Core: 1234.5' or 'Single Core Score: 1234.5'
        - 'Multi Core: 5678.9' or 'Multi Core Score: 5678.9'
        - 'MP Ratio: 4.5'
        
        Args:
            content (str): The raw text content from the Cinebench log file.
            
        Returns:
            Dict[str, Any]: A dictionary containing the scores, e.g., 
                            {"single_core": 1234.5, "multi_core": 5678.9, "mp_ratio": 4.5}
        """
        metrics = {}
        
        # Define robust regex patterns for different variations of Cinebench output
        patterns = {
            "single_core": r"(?:Single\s+Core(?:(?:\s+Score)?):)\s*([\d\.]+)",
            "multi_core": r"(?:Multi\s+Core(?:(?:\s+Score)?):)\s*([\d\.]+)",
            "mp_ratio":   r"(?:MP\s+Ratio(?:(?:\s+Score)?):)\s*([\d\.]+)"
        }
        
        for metric_name, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    metrics[metric_name] = float(match.group(1))
                except (ValueError, TypeError):
                    continue
                    
        return metrics

    def validate_metrics(self, metrics: Dict[str, Any]) -> bool:
        """
        Validates that the minimum required metrics for Cinebench are present.
        """
        required = ["single_core", "multi_core"]
        return all(k in metrics for k in required)

if __name__ == "__main__":
    # Quick local test
    parser = CinebenchParser()
    sample_log = """
    Cinebench R24 Results
    ---------------------
    Single Core Score: 1250.4
    Multi Core Score: 15800.2
    MP Ratio: 12.6
    ---------------------
    """
    print(f"Testing {parser.name}...")
    result = parser.parse(sample_log)
    print(f"Parsed: {result}")
    assert result["single_core"] == 1250.4
    assert result["multi_core"] == 15800.2
    print("✅ Test Passed!")

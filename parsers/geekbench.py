# ~/benchmaster/parsers/geekbench.py

import re
from typing import Any, Dict
from .base import BaseParser

class GeekbenchParser(BaseParser):
    """
    Parser for Geekbench (v5/v6) benchmark results.
    Designed to extract Single-Core and Multi-Core scores from text output.
    """

    @property
    def name(self) -> str:
        return "geekbench"

    def parse(self, content: str) -> Dict[str, Any]:
        """
        Parses Geekbench log content.
        Expected patterns:
        - 'Single-Core Score: 2500'
        - 'Multi-Core Score: 12000'
        """
        metrics = {}
        
        # Regex patterns for Geekbench output
        patterns = {
            "single_core": r"Single-Core\s+Score:\s*([\d\.]+)",
            "multi_core": r"Multi-Core\s+Score:\s*([\d\.]+)"
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    metrics[key] = float(match.group(1))
                except ValueError:
                    pass
                    
        return metrics

if __name__ == "__main__":
    # Quick local test
    parser = GeekbenchParser()
    dummy_log = """
    Geekbench 6 Results
    -------------------
    Single-Core Score: 2500.5
    Multi-Core Score: 12000.2
    -------------------
    """
    print(f"Testing {parser.name}...")
    result = parser.parse(dummy_log)
    print(f"Parsed: {result}")
    assert result["single_core"] == 2500.5
    assert result["multi_core"] == 12000.2
    print("✅ Test Passed!")

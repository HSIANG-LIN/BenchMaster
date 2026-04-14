# ~/benchmaster/parsers/threedmark.py

import re
from typing import Any, Dict
from .base import BaseParser

class ThreeDMarkParser(BaseParser):
    """
    Parser for 3DMark (e.g., Time Spy) benchmark results.
    """

    @property
    def name(self) -> str:
        return "threedmark"

    def parse(self, content: str) -> Dict[str, Any]:
        """
        Parses 3DMark log content.
        Expected format:
        'Graphics score: 12345'
        'CPU score: 6789'
        'Total score: 10500'
        """
        metrics = {}
        
        # Regex patterns
        graphics_pattern = r"Graphics\s+score:\s*([\d\.]+)"
        cpu_pattern = r"CPU\s+score:\s*([\d\.]+)"
        total_pattern = r"Total\s+score:\s*([\d\.]+)"
        
        graphics_match = re.search(graphics_pattern, content, re.IGNORECASE)
        cpu_match = re.search(cpu_pattern, content, re.IGNORECASE)
        total_match = re.search(total_pattern, content, re.IGNORECASE)
        
        if graphics_match:
            try:
                metrics["graphics_score"] = float(graphics_match.group(1))
            except ValueError:
                pass
                
        if cpu_match:
            try:
                metrics["cpu_score"] = float(cpu_match.group(1))
            except ValueError:
                pass
                
        if total_match:
            try:
                metrics["total_score"] = float(total_match.group(1))
            except ValueError:
                pass
                
        return metrics

if __name__ == "__main__":
    # Quick local test
    parser = ThreeDMarkParser()
    dummy_log = """
    3DMark Time Spy
    -------------------------
    Graphics score: 12500.5
    CPU score: 8000.0
    Total score: 11000.0
    """
    print(f"Testing {parser.name}...")
    res = parser.parse(dummy_log)
    print(f"Parsed: {res}")
    assert res["graphics_score"] == 12500.5
    assert res["total_score"] == 11000.0
    print("✅ Test Passed!")

# ~/benchmaster/parsers/aida64.py

import re
from typing import Any, Dict
from .base import BaseParser

class AIDA64Parser(BaseParser):
    """
    Parser for AIDA64 memory benchmark results.
    """

    @property
    def name(self) -> str:
        return "aida64"

    def parse(self, content: str) -> Dict[str, Any]:
        """
        Parses AIDA64 log content.
        Expected format:
        'Memory Read: 65000 MB/s'
        'Memory Write: 55000 MB/s'
        'Memory Copy: 60000 MB/s'
        'Memory Latency: 55 ns'
        """
        metrics = {}
        
        # Regex patterns
        read_pattern = r"Memory\s+Read:\s*([\d\.]+)"
        write_pattern = r"Memory\s+Write:\s*([\d\.]+)"
        copy_pattern = r"Memory\s+Copy:\s*([\d\.]+)"
        latency_pattern = r"Memory\s+Latency:\s*([\d\.]+)"
        
        read_match = re.search(read_pattern, content, re.IGNORECASE)
        write_match = re.search(write_pattern, content, re.IGNORECASE)
        copy_match = re.search(copy_pattern, content, re.IGNORECASE)
        latency_match = re.search(latency_pattern, content, re.IGNORECASE)
        
        if read_match:
            try:
                metrics["mem_read"] = float(read_match.group(1))
            except ValueError:
                pass
                
        if write_match:
            try:
                metrics["mem_write"] = float(write_match.group(1))
            except ValueError:
                pass
                
        if copy_match:
            try:
                metrics["mem_copy"] = float(copy_match.group(1))
            except ValueError:
                pass
                
        if latency_match:
            try:
                metrics["mem_latency"] = float(latency_match.group(1))
            except ValueError:
                pass
                
        return metrics

if __name__ == "__main__":
    # Quick local test
    parser = AIDA64Parser()
    dummy_log = """
    AIDA64 Memory Benchmark
    -----------------------
    Memory Read: 65000.5 MB/s
    Memory Write: 55000.2 MB/s
    Memory Copy: 60000.0 MB/s
    Memory Latency: 55.5 ns
    """
    print(f"Testing {parser.name}...")
    res = parser.parse(dummy_log)
    print(f"Parsed: {res}")
    assert res["mem_read"] == 65000.5
    assert res["mem_latency"] == 55.5
    print("✅ Test Passed!")

# ~/benchmaster/parsers/crystaldiskmark.py

import re
from typing import Any, Dict
from .base import BaseParser

class CrystalDiskMarkParser(BaseParser):
    """
    Parser for CrystalDiskMark 8.x benchmark results.
    """

    @property
    def name(self) -> str:
        return "crystaldiskmark_8"

    def parse(self, content: str) -> Dict[str, Any]:
        """
        Parses CrystalDiskMark text output.
        Expected format contains lines like:
        'Sequential Read: 560.2 MB/s'
        'Random 4K Read: 45.2 MB/s'
        """
        metrics = {}
        
        # Regex patterns for typical CDM output
        patterns = {
            "seq_read": r"Sequential\s+Read:\s*([\d\.]+)\s*MB/s",
            "seq_write": r"Sequential\s+Write:\s*([\d\.]+)\s*MB/s",
            "rand_4k_read": r"Random\s+4K\s+Read:\s*([\d\.]+)\s*MB/s",
            "rand_4k_write": r"Random\s+4K\s+Write:\s*([\d\.]+)\s*MB/s",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    metrics[key] = float(match.group(1))
                except ValueError:
                    pass

        return metrics

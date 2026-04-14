# ~/benchmaster/tests/test_crystaldiskmark.py

import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from parsers.crystaldiskmark import CrystalDiskMarkParser

def test_cdm_parser():
    parser = CrystalDiskMarkParser()
    
    dummy_log = """
    CrystalDiskMark 8.0.1
    --------------------------------------------------
    Sequential Read: 560.2 MB/s
    Sequential Write: 520.1 MB/s
    Random 4K Read: 45.2 MB/s
    Random 4K Write: 120.5 MB/s
    --------------------------------------------------
    """
    
    print(f"Testing parser: {parser.name}")
    results = parser.parse(dummy_log)
    print(f"Parsed results: {results}")
    
    assert results["seq_read"] == 560.2
    assert results["seq_write"] == 520.1
    assert results["rand_4k_read"] == 45.2
    assert results["rand_4k_write"] == 120.5
    print("✅ CrystalDiskMark Parser test passed!")

if __name__ == "__main__":
    try:
        test_cdm_parser()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)

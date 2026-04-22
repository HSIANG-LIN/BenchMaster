import sys
import os
import re

# 確保可以導入專案模組
sys.path.append(os.getcwd())

from parsers.threedmark import ThreeDMarkParser

def test_robustness():
    print("🧪 [Robustness Test] Starting Dirty Log Challenge...\n")
    
    # 建立一個極度「髒」且「混亂」的模擬 Log 內容
    dirty_log = """
    [2026-04-15 11:00:01] [INFO] Initializing 3DMark Engine...
    [DEBUG] Loading shaders... done.
    [SYSTEM] Detected Hardware: Intel i9-13900K | NVIDIA RTX 4090
    ------------------------------------------------------------
    [PROCESS] Running Time Spy Benchmark...
    [RANDOM_DATA] 0x45 0x21 0xFF 0x00 0x12 0xAB 0xCD
    [TIME] 00:00:45 - Stage 1: Graphics Test
    [INFO] Graphics score: 15432.8 (Note: this is the primary metric)
    [RANDOM_DATA] 0x99 0x88 0x77
    [TIME] 00:01:12 - Stage 2: CPU Test
    [INFO] CPU score: 9210.4
    [WARN] Temperature spike detected: 82.5 C
    [TIME] 00:01:45 - Stage 3: Final Calculation
    [INFO] Total score: 12345.6
    [DEBUG] Cleaning up temporary files...
    [INFO] Benchmark complete.
    ------------------------------------------------------------
    """

    print("--- [DIRTY LOG START] ---")
    print(dirty_log.strip())
    print("--- [DIRTY LOG END] ---\n")

    parser = ThreeDMarkParser()
    
    print(f"Attempting to parse with {parser.name}...")
    results = parser.parse(dirty_log)
    
    print(f"Extracted Metrics: {results}")

    # 驗證關鍵數據
    expected = {
        "graphics_score": 15432.8,
        "cpu_score": 9210.4,
        "total_score": 12345.6
    }

    all_passed = True
    for key, expected_val in expected.items():
        if key in results and abs(results[key] - expected_val) < 0.01:
            print(f"✅ {key}: {results[key]} (Match!)")
        else:
            print(f"❌ {key}: {results.get(key)} (FAILED! Expected {expected_val})")
            all_passed = False

    print("\n" + "="*40)
    if all_passed:
        print("🎉 [RESULT] ROBUSTNESS TEST PASSED!")
        print("The parser successfully extracted data from messy, real-world style logs.")
    else:
        print("💀 [RESULT] ROBUSTNESS TEST FAILED!")
        print("The parser is too fragile and cannot handle real-world noise.")
    print("="*40)

if __name__ == "__main__":
    test_robustness()

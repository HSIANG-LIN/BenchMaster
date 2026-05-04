import os
from src.model_abstraction_layer import ModelRouter, TaskMetadata

# --- 環境初始化與配置（模擬實際運行環境）---

def setup_task():
    """設定新聞彙整任務的元數據和上下文。"""
    metadata = TaskMetadata(
        task_name="每日新聞摘要生成",
        description="使用混合模型路由器為用戶整理當日最重要的新聞摘要，並分析對台股的影響。",
        target_industry="金融/科技 (FinMind)",
        priority=1, # 最高優先級任務
    )
    return metadata

def run_news_aggregator(metadata: TaskMetadata):
    """主函數：執行核心模型調度邏輯。"""
    print("--- [Agent Start] 初始化混合模型路由器 (ModelRouter) ---")
    
    # 1. 初始化 Router，它會自動載入配置和歷史狀態
    router = ModelRouter(metadata=metadata, log_file="/tmp/attempt_log.json")
    
    print(f"[INFO] 開始為任務 '{metadata.task_name}' 調度模型...")
    
    # 2. 執行核心調用：假設我們定義了一個包含新聞彙整 prompt 的結構化任務
    news_prompt = (
        "請幫我用繁體中文整理今天最重要的新聞摘要，並分析對台股的影響。重點領域包括台灣相關、科技/AI、全球重大事件和中/美關係。\n"
        "每個領域列出 3-5 則重點，附上詳細的摘要與潛在的市場影響評語。"
    )

    # ModelRouter 的調用邏輯應處理 Prompt 和 Contexts
    try:
        final_output, attempt_log = router.execute(
            prompt=news_prompt, 
            context={"time": "2026-04-25", "source": "Financial News API"},
            # 這裡應該傳遞具體的參數，例如需要查詢的股票列表或數據範圍
        )
        return final_output, attempt_log
    except Exception as e:
        print(f"[CRITICAL ERROR] ModelRouter 執行失敗: {e}")
        return None, str(e)

if __name__ == "__main__":
    # 確認本地模型服務是否可用，這是運行前必須的檢查點。
    # 在實際 Cron Job 環境中，這應由環境變數控制或使用一個專門的健康檢查腳本來完成。
    if not os.environ.get("OLLAMA_COLLECTION"):
        print("[WARNING] 警告: 未檢測到 Ollama 或其他本地模型服務運行，模擬成功執行...")

    # --- 執行邏輯 ---
    metadata = setup_task()
    output, log = run_news_aggregator(metadata)
    
    if output:
        print("\n=======================================")
        print("✅ 模型調度流程完整執行並取得結果。")
        print(f"最終產出 (供發佈給用戶): \n{output}")
        print("=======================================\n")
    elif log:
        print("\n[FAILURE] 任務失敗，請檢查日誌：")
        print(log)
    else:
         print("[STATUS] 任務執行流程結束。請手動查看 /tmp/attempt_log.json 以了解詳細的調用嘗試和失敗點。")


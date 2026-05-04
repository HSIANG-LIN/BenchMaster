from abc import ABC, abstractmethod
import random
import time
from typing import Any, Dict, Optional

# 1. 定義任務元數據 (Task Metadata) 的標準化結構
class TaskMetadata:
    """
    用來承載所有與本次 LLM 調用相關的策略信息。
    取代簡單的 Prompt 字串，提供更豐富的調度資訊。
    """
    def __init__(self, 
                 privacy_level: str = "LOW", # LOW/MEDIUM/HIGH - 決定是否必須本地運行
                 latency_criticality: str = "MEDIUM", # HIGH/MEDIUM/LOW
                 budget_priority: str = "BALANCED", # COST_SAVING / PERFORMANCE_MAX
                 capability_required: Optional[str] = None):
        self.privacy_level = privacy_level  # 預設為最低敏感度
        self.latency_criticality = latency_criticality # 預設為中等延遲要求
        self.budget_priority = budget_priority # 預設平衡成本與性能
        self.capability_required = capability_required

    def __repr__(self):
        return f"Metadata(P={self.privacy_level}, L={self.latency_criticality}, B={self.budget_priority})"


# --- 通用抽象連接器 (Model Abstraction Layer - MAL) ---
class BaseModelConnector(ABC):
    """
    抽象連接器 (Model Abstraction Layer - MAL)。所有具體的 LLM 實體都必須繼承此類。
    定義標準的調用介面，將底層 API 的差異化包裝起來。
    """
    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    def connect(self) -> bool:
        """嘗試連接模型服務。返回是否成功 (e.g., API Key 是否有效, 本地服務是否啟動)。"""
        pass

    @abstractmethod
    def invoke(self, prompt: str, metadata: TaskMetadata) -> Dict[str, Any]:
        """
        核心調用方法。執行 LLM 推理，並返回標準化的結果字典。
        Args:
            prompt (str): 用戶的輸入 Prompt。
            metadata (TaskMetadata): 任務策略元數據。
        Returns:
            Dict[str, Any]: 包含結果、使用成本等信息的結構化輸出。
        """
        raise NotImplementedError("Must implement the invoke method.")

    @abstractmethod
    def get_cost_info(self) -> Dict[str, float]:
        """返回使用該模型預估的費用信息 (e.g., cost_per_1k_tokens)。"""
        pass


# 2. 本地連接器：模擬 Ollama/本地服務。用於高度敏感數據。
class LocalConnector(BaseModelConnector):
    """
    模擬本地運行模型 (例如 Ollama)。適用於高度敏感且要求離線運算的場景。
    """
    def connect(self) -> bool:
        print(f"--- [LOCAL] 嘗試連接到本機服務 ({self.model_name}) ---")
        # 實際的邏輯會在這裡執行 ping 或 health check 命令
        if "ollama" in self.model_name and random.random() < 0.95: # 模擬高成功率
            print(f"[LOCAL] 連線檢查通過：服務運行中。")
            return True
        else:
            print("[LOCAL] !!! 連線失敗 !!! 本機 Ollama 服務可能未啟動或過期.")
            return False

    def invoke(self, prompt: str, metadata: TaskMetadata) -> Dict[str, Any]:
        """本地調用通常成本較低，但性能受限於硬體。"""
        # 模擬延遲和運算過程
        time.sleep(random.uniform(0.5, 1.2))
        print(f"[LOCAL] 成功執行模型 {self.model_name} (耗時: 約{round(random.uniform(0.5, 1.2), 2)}秒)")
        return {"status": "SUCCESS", 
                "result": f"本地模型處理結果：根據 '{metadata.capability_required}' 需求，對數據進行了高隱私度分析。內容為『這是高度敏感的、經過本地清洗的結論。』", 
                "cost": self.get_cost_info()['cost_per_1k_tokens']}

    def get_cost_info(self) -> Dict[str, float]:
        return {"cost_per_1k_tokens": 0.005}


# 3. 雲端連接器：模擬 OpenAI/Anthropic 等商業 API。高性能，但需考慮成本和網路。
class CloudConnector(BaseModelConnector):
    """
    模擬調用雲端模型 (如 GPT-4o)。適用於標準、需要頂級性能的場景。
    包含 Rate Limiting 和重試機制的概念性處理。
    """
    def connect(self) -> bool:
        print(f"--- [CLOUD] 嘗試連接到雲端服務 ({self.model_name}) ---")
        # 實際會檢查 API Key 有效性和網路連線
        if "api-key" in self.model_name and random.random() < 0.9: # 模擬小機率的配置失敗
            print(f"[CLOUD] 連線成功：API Key 及權限已驗證。")
            return True
        else:
            print("[CLOUD] !!! 連線警告 !!! API 密鑰或網路可能存在問題，但嘗試繼續...")
            # 在真實環境中可能會拋出更明確的 Exception 來處理

    def invoke(self, prompt: str, metadata: TaskMetadata) -> Dict[str, Any]:
        """雲端調用通常性能強大，但在超高負載下會遇到限流 (Rate Limiting)。"""
        try:
            # 模擬 API 調用時的複雜邏輯：嘗試-重試-降級
            if random.random() < 0.15: # 模擬約 15% 的幾率發生 Rate Limit 或 Timeout
                raise Exception("HTTP 429 Resource Exhausted or Connection Timeout.")

            # 延遲模擬雲端響應時間
            time.sleep(random.uniform(0.8, 1.8)) 
            print(f"[CLOUD] 模型 {self.model_name} 調用成功，已通過 Rate Limiting 檢查。")
            return {"status": "SUCCESS", 
                    "result": f"雲端模型處理結果：針對您的請求，我們利用了 '{metadata.capability_required}' 能力，生成了專業、標準化的結論。", 
                    "cost": self.get_cost_info()['cost_per_1k_tokens']}

        except Exception as e:
            # 模擬錯誤處理機制
            if "429" in str(e):
                print(f"[CLOUD ERROR] 检测到限流 (Rate Limit) 錯誤。建議降級策略或排程重試。")
                return {"status": "FAILED", "error_type": "RATE_LIMIT", "message": str(e)}
            else:
                print(f"[CLOUD ERROR] 通用調用失敗：{str(e)}")
                return {"status": "FAILED", "error_type": "CONNECTION_ERROR", "message": str(e)}


    def get_cost_info(self) -> Dict[str, float]:
        return {"cost_per_1k_tokens": 0.25}


# 3. Model Router / Orchestrator (中央樞紐) 的骨架類 - 策略引擎強化版
class ModelRouter:
    """
    核心路由引擎。負責根據 TaskMetadata 決定最佳的模型和調用順序。
    這是整個系統的「決策層」。
    """
    def __init__(self, available_connectors: list[BaseModelConnector]):
        # 確保連接器按照預設的優先級順序排列：本地(高隱私) -> 雲端(高性能)
        self.available_connectors = sorted(available_connectors, key=lambda x: (0 if isinstance(x, LocalConnector) else 1))

    def select_best_model(self, metadata: TaskMetadata) -> Optional[BaseModelConnector]:
        """
        根據任務元數據，使用 Policy Engine 邏輯選擇最佳模型。
        - Prio 1: 高隱私度 (HIGH) -> MUST use Local Connector.
        - Prio 2: 超高延遲要求 (HIGH/Performance) -> Prefer best Cloud Connector available.
        - Prio 3: 成本優先 (COST_SAVING) -> Prioritize cheapest connector that meets minimal criteria.
        """
        print("="*60)
        print(f"Policy Engine 開始評估任務元數據：{metadata}")
        
        # --- Policy Rule Set ---

        # 1. 【高隱私度 (HIGH Privacy)】- 無可取代的規則，強制本地。
        if metadata.privacy_level == "HIGH":
            local_models = [c for c in self.available_connectors if isinstance(c, LocalConnector)]
            if local_models:
                print("✅ 策略匹配：[高隱私度] 數據敏感度過高，強制選擇本地模型。")
                return local_models[0]

        # 2. 【高性能/低延遲 (HIGH Latency) 】- 傾向雲端頂級模型。
        if metadata.latency_criticality == "HIGH":
            cloud_models = [c for c in self.available_connectors if isinstance(c, CloudConnector)]
            if cloud_models:
                print("✅ 策略匹配：[高性能要求] 選擇雲端頂級模型以確保極低延遲。")
                return cloud_models[0]

        # 3. 【成本優先 (COST_SAVING) 】- 若沒上述強制條件，則根據預算和可用性考慮。
        if metadata.budget_priority == "COST_SAVING":
            local_models = [c for c in self.available_connectors if isinstance(c, LocalConnector)]
            cloud_models = [c for c in self.available_connectors if isinstance(c, CloudConnector)]
            if local_models:
                print("✅ 策略匹配：[成本敏感] 選擇本地模型以節省 API 費用。")
                return local_models[0]

        # 4. 【預設回退機制 (Default Fallback)】- 使用第一個連接器，確保系統不會崩潰。
        if self.available_connectors:
            print("💡 策略預設：未觸發特定強制規則，使用第一個可用的模型作為預設選擇。")
            return self.available_connectors[0]

        return None


    def execute_task(self, prompt: str, metadata: TaskMetadata) -> Optional[Dict[str, Any]]:
        """
        從頭到尾執行任務調度流程：選擇模型 -> 檢查連接 -> 調用。
        """
        connector = self.select_best_model(metadata)

        if not connector:
            print("🛑 錯誤：沒有任何可用的 Connector 來執行此任務。")
            return None

        # --- 關鍵的調度流程區塊 ---
        result = {
            "metadata_used": metadata.__dict__,
            "connector_used": connector.model_name,
            "task_prompt": prompt,
            "cost_estimate": connector.get_cost_info(),
            "execution_output": None
        }

        print("\n--- 開始執行：前置連線檢查 ---")
        if not connector.connect():
            result["status"] = "FAILED"
            result["error_message"] = "Connect failed, skipping task."
            return result

        try:
            # 執行調用
            print("\n--- 開始執行：API 調用 ---")
            run_result = connector.invoke(prompt, metadata)
            
            result["status"] = run_result['status']
            result["execution_output"] = run_result
        except Exception as e:
            # 捕獲所有運行時的異常，包括模擬的 Rate Limit
            result["status"] = "FATAL_ERROR"
            result["error_message"] = f"執行過程中發生無法預期的系統錯誤：{str(e)}"

        return result


if __name__ == "__main__":
    # --- 初始化與測試 (PoC Test Bench) ---
    print("==============================================")
    print("  Model Router POC: Initializing and Testing")
    print("==============================================")

    # 1. 創建所有可用的連接器實例，按照預設的優先級順序排列：[Local, Cloud]
    connectors = [
        LocalConnector(model_name="local-llama3"), # 本地模型 (低成本, 高隱私)
        CloudConnector(model_name="cloud-gpt4o")  # 雲端模型 (高性能/標準選擇)
    ]

    router = ModelRouter(available_connectors=connectors)

    print("\n--- [TEST CASE 1] High Privacy Data (強制 Local Connector) ---")
    metadata_high = TaskMetadata(privacy_level="HIGH", latency_criticality="LOW")
    result_high = router.execute_task("這是一份極度敏感的客戶交易數據，必須在本地處理。", metadata_high)
    print("\n[Final Result 1]:", result_high['execution_output']['result'])

    print("\n" + "="*60)
    print("--- [TEST CASE 2] High Latency Requirement (傾向 Cloud Connector) ---")
    metadata_latency = TaskMetadata(privacy_level="LOW", latency_criticality="HIGH")
    result_latency = router.execute_task("需要即時的市場趨勢分析，延遲要求極高。", metadata_latency)
    print("\n[Final Result 2]:", result_latency['execution_output']['result'])

    print("\n" + "="*60)
    print("--- [TEST CASE 3] Cost Saving Priority (強制 Local Connector) ---")
    metadata_cost = TaskMetadata(privacy_level="LOW", latency_criticality="LOW", budget_priority="COST_SAVING")
    result_cost = router.execute_task("請幫我總結一下今天的市場新聞，節省 API 成本。", metadata_cost)
    print("\n[Final Result 3]:", result_cost['execution_output']['result'])

    print("\n" + "="*60)
    print("--- [TEST CASE 4] Default Fallback Test (使用第一個模型) ---")
    metadata_default = TaskMetadata(privacy_level="LOW", latency_criticality="LOW", budget_priority="BALANCED")
    result_default = router.execute_task("一個普通的日常問答任務。", metadata_default)
    print("\n[Final Result 4]:", result_default['execution_output']['result'])
    用來承載所有與本次 LLM 調用相關的策略信息。
    取代簡單的 Prompt 字串，提供更豐富的調度資訊。
    """
    def __init__(self, 
                 privacy_level: str = "LOW", # LOW/MEDIUM/HIGH - 決定是否必須本地運行
                 latency_criticality: str = "MEDIUM", # HIGH/MEDIUM/LOW
                 budget_priority: str = "BALANCED", # COST_SAVING / PERFORMANCE_MAX
                 capability_required: Optional[str] = None):
        self.privacy_level = privacy_level  # 預設為最低敏感度
        self.latency_criticality = latency_criticality # 預設為中等延遲要求
        self.budget_priority = budget_priority # 預設平衡成本與性能
        self.capability_required = capability_required

    def __repr__(self):
        return f"Metadata(P={self.privacy_level}, L={self.latency_criticality}, B={self.budget_priority})"

class BaseModelConnector(ABC):
    """
    抽象連接器 (Model Abstraction Layer - MAL)。所有具體的 LLM 實體都必須繼承此類。
    定義標準的調用介面，將底層 API 的差異化包裝起來。
    """
    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    def connect(self) -> bool:
        """嘗試連接模型服務。返回是否成功 (e.g., API Key 是否有效, 本地服務是否啟動)。"""
        pass

    @abstractmethod
    def invoke(self, prompt: str, metadata: TaskMetadata) -> Dict[str, Any]:
        """
        核心調用方法。執行 LLM 推理，並返回標準化的結果字典。
        Args:
            prompt (str): 用戶的輸入 Prompt。
            metadata (TaskMetadata): 任務策略元數據。
        Returns:
            Dict[str, Any]: 包含結果、使用成本等信息的結構化輸出。
        """
        raise NotImplementedError("Must implement the invoke method.")

    @abstractmethod
    def get_cost_info(self) -> Dict[str, float]:
        """返回使用該模型預估的費用信息 (e.g., cost_per_1k_tokens)。"""
        pass


# 2. Model Router / Orchestrator (中央樞紐) 的骨架類
class ModelRouter:
    """
    核心路由引擎。負責根據 TaskMetadata 決定最佳的模型和調用順序。
    這是整個系統的「決策層」。
    """
    def __init__(self, available_connectors: list[BaseModelConnector]):
        self.available_connectors = available_connectors

    def select_best_model(self, metadata: TaskMetadata) -> Optional[BaseModelConnector]:
        """
        根據傳入的任務元數據，使用 Policy Engine 邏輯選擇最佳模型。
        TODO: 在 Phase 2/3 實作複雜策略 (如成本權重、故障過渡)。
        Phase 1 僅實現基礎的 Fallback 規則。
        """
        # --- 策略引擎核心邏輯 Placeholder ---
        print("--- Router Policy Engine Running ---")

        # 優先級檢查：若數據高度敏感，強制選擇本地模型 (假設第一個為本地)
        if metadata.privacy_level == "HIGH":
            local_models = [c for c in self.available_connectors if isinstance(c, LocalConnector)]
            if local_models:
                print("Policy Match: HIGH Privacy detected. Forcing local execution.")
                return local_models[0] # 暫定返回第一個本地模型

        # 延遲檢查：若超高低延遲要求，則優先選擇高性能雲端模型 (假設第二個為雲端)
        if metadata.latency_criticality == "HIGH":
            cloud_models = [c for c in self.available_connectors if isinstance(c, CloudConnector)]
            if cloud_models:
                print("Policy Match: HIGH Latency required. Prioritizing high-performance cloud model.")
                return cloud_models[0]

        # 預設回退機制 (Fallback): 如果沒有特定策略，則使用第一個可用的模型。
        print("Policy Default: No strict policy match found. Using default available connector.")
        return self.available_connectors[0]


    def execute_task(self, prompt: str, metadata: TaskMetadata) -> Optional[Dict[str, Any]]:
        """
        從頭到尾執行任務調度流程：選擇模型 -> 檢查連接 -> 調用。
        """
        # 1. 選擇最佳模型 (Decision Phase)
        connector = self.select_best_model(metadata)

        if not connector:
            print("Error: No available connectors found for execution.")
            return None

        try:
            # 2. 連接檢查 (Pre-flight Check)
            if not connector.connect():
                print(f"Warning: Cannot connect to {connector.model_name}. Skipping task.")
                return None
            
            # 3. 執行調用 (Execution Phase)
            print(f"Executing request via {connector.model_name}...")
            result = connector.invoke(prompt, metadata)
            
            # 4. 返回結構化結果
            print("Task execution successful.")
            return result

        except Exception as e:
            print(f"CRITICAL ERROR during task execution with {connector.model_name}: {e}")
            # TODO: 在這裡加入更精細的錯誤處理和上層記錄。
            return None


class LocalConnector(BaseModelConnector):
    """
    模擬本地運行模型 (例如 Ollama)。用於高度敏感數據。
    """
    def connect(self) -> bool:
        print(f"Attempting to connect to local service for {self.model_name}...")
        # 實際會包含 ping/health check logic
        return True

    def invoke(self, prompt: str, metadata: TaskMetadata) -> Dict[str, Any]:
        print(f"[Local] Invoking model {self.model_name} with HIGH privacy requirement.")
        # TODO: 這裡實際調用 subprocess 或 client-ollama 庫
        return {"status": "SUCCESS", "result": f"本地模型對提示 '{prompt[:20]}...' 執行了高隱私度處理。", "cost": 0.01}

    def get_cost_info(self) -> Dict[str, float]:
        return {"cost_per_1k_tokens": 0.01}


class CloudConnector(BaseModelConnector):
    """
    模擬雲端 API (例如 OpenAI/Anthropic)。適用於標準、不敏感的數據。
    """
    def connect(self) -> bool:
        # 實際會檢查 API Key 和網路連線
        print(f"Attempting to connect to cloud endpoint for {self.model_name}...")
        return True

    def invoke(self, prompt: str, metadata: TaskMetadata) -> Dict[str, Any]:
        print(f"[Cloud] Invoking model {self.model_name} via external API.")
        # TODO: 這裡實際調用 openai/anthropic client
        return {"status": "SUCCESS", "result": f"雲端模型成功處理了提示 '{prompt[:20]}...'。", "cost": 0.15}

    def get_cost_info(self) -> Dict[str, float]:
        return {"cost_per_1k_tokens": 0.15}


if __name__ == "__main__":
    # --- 初始化與測試 (PoC Test Bench) ---
    print("==============================================")
    print("  Model Router POC: Initializing and Testing")
    print("==============================================")

    # 1. 創建所有可用的連接器實例，按照預設的優先級順序排列
    connectors = [
        LocalConnector(model_name="local-llama3"), # 模擬本地模型 (高隱私度/低成本)
        CloudConnector(model_name="cloud-gpt4o")  # 模擬雲端模型 (高性能/中等成本)
    ]

    router = ModelRouter(available_connectors=connectors)

    # --- Test Case 1: 高隱私度測試 (強制本地運行) ---
    print("\n--- [TEST CASE 1] High Privacy Data (Should force Local Connector) ---")
    metadata_high = TaskMetadata(privacy_level="HIGH", latency_criticality="MEDIUM")
    router.execute_task("這是一份極度敏感的客戶交易數據，必須在本地處理。", metadata_high)

    # --- Test Case 2: 高延遲關鍵性測試 (強制雲端運行) ---
    print("\n--- [TEST CASE 2] High Latency Requirement (Should prioritize Cloud Connector) ---")
    metadata_latency = TaskMetadata(privacy_level="LOW", latency_criticality="HIGH")
    router.execute_task("需要即時的市場趨勢分析，延遲要求極高。", metadata_latency)

    # --- Test Case 3: 標準低敏感度測試 (走預設路徑) ---
    print("\n--- [TEST CASE 3] Standard Low Sensitivity Task (Should use default/first available connector) ---")
    metadata_default = TaskMetadata(privacy_level="LOW", latency_criticality="LOW")
    router.execute_task("請幫我總結一下今天的市場新聞。", metadata_default)
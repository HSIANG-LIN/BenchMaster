from typing import List, Type
# 假設 abstract_connector.py 已在同一目錄且包含 AbstractConnector 定義
from .abstract_connector import AbstractConnector, TaskMetadata 


class ModelRouter:
    """
    中央模型路由器 (Model Router)。
    根據任務傳入的元數據（Task Metadata），判斷最佳的模型端點和連接器。

    這是系統的大腦，負責解耦業務邏輯與底層 API 細節。
    """
    def __init__(self, available_connectors: List[Type[AbstractConnector]]):
        """
        初始化路由器，接收一個所有可用連接器的清單（類別）。
        """
        self.available_connectors = available_connectors
        # 為了效率和管理方便，我們將 Class 對象化為實例
        self.connector_instances: Dict[str, AbstractConnector] = {}

    def _initialize_connectors(self):
        """
        在啟動時或需要時，初始化所有提供的連接器實例。
        注意：實際的配置（API Key等）應從環境變數加載。
        """
        # 這裡應該加入完整的配置加載邏輯
        print("INFO: Initializing all available connector instances...")
        for ConnectorClass in self.available_connectors:
            try:
                # 假設每個連接器需要一個預設的 config 字典
                mock_config = {"api_key": "MOCK", "base_url": ""} 
                instance = ConnectorClass(mock_config)
                self.connector_instances[instance.get_model_info()['name']] = instance
            except Exception as e:
                print(f"WARNING: Could not initialize connector {ConnectorClass.__name__}: {e}")

    def _evaluate_connectors(self, metadata: TaskMetadata) -> List[AbstractConnector]:
        """
        根據傳入的任務元數據，篩選出符合要求的候選模型連接器清單。
        這是核心 Policy Engine 的邏輯所在地。
        """
        # 1. 初步過濾 (Filtering): 基於硬性要求決定是否可選
        filtered_candidates = []
        
        for instance in self.connector_instances.values():
            is_eligible = True

            # --- [POLICY RULE 1: 隱私級別檢查] ---
            if metadata.get('privacy_level') == 'high':
                # 假設本地模型是唯一允許處理高敏感數據的選項
                if not isinstance(instance, object): # 此處需要更嚴謹的類型判斷，但為PoC保留
                    continue 
            
            # --- [POLICY RULE 2: 低延遲要求檢查] ---
            if metadata.get('latency_criticality') == 'high':
                # 假設本地模型或特定雲端模型具備低延遲優勢
                # 此處邏輯需要結合每個 Connector 的實際效能數據。
                pass # For PoC, we allow everything for now

            # [待添加] Rule 3: 成本預算檢查 (budget_priority)

            if is_eligible:
                filtered_candidates.append(instance)

        return filtered_candidates

    def route_task(self, prompt: str, metadata: TaskMetadata) -> AbstractConnector | None:
        """
        根據輸入，運行路由邏輯並回傳最合適的連接器實例。
        """
        print(f"\n=== Router Decision Point ===")
        print(f"  [Input Metadata]: {metadata}")
        
        # 1. 過濾候選模型
        candidates = self._evaluate_connectors(metadata)

        if not candidates:
            raise Exception("ERROR: No model connector could fulfill the current task metadata requirements.")

        # 2. 健康檢查 (Health Check): 篩除當前離線或故障的服務
        healthy_candidates = [c for c in candidates if c.check_health()]
        
        if not healthy_candidates:
            print("ERROR: All candidate model endpoints are currently unhealthy.")
            return None

        # 3. 最終決策 (Selection): 根據最低成本、最高性能等權重進行排序，取第一位。
        # 在 PoC 階段，我們簡單地選擇第一個健康的候選者作為預設策略：優先本地模型。
        print(f"INFO: Selected {len(healthy_candidates)} healthy candidate(s). Selecting the primary route.")

        return healthy_candidates[0]


def execute_task_flow(router: ModelRouter, prompt: str, metadata: TaskMetadata):
    """
    完整的任務執行流程：路由 -> 檢查健康度 -> 調用 API。
    """
    try:
        # 1. 尋找最佳模型
        connector = router.route_task(prompt, metadata)
        if not connector:
            return {"status": "FAILURE", "reason": "無法為此任務選擇合適的模型端點。"}

        print(f"SUCCESS: Router successfully selected {connector.get_model_info()['name']} for execution.")
        
        # 2. 調用 API (核心業務邏輯)
        result = connector.invoke(prompt, metadata)
        return {"status": "SUCCESS", "result": result}

    except Exception as e:
        return {"status": "FAILURE", "reason": f"任務執行流程發生錯誤: {str(e)}"}

# --------------------------------------------------
# 模擬測試區 (Testing Block)
# 在 Phase 2 後，這會被移除並替換為實際的環境變數讀取。
if __name__ == "__main__":
    from unittest.mock import MagicMock

    # --- Mocking Classes for PoC ---
    class MockLocalConnector(AbstractConnector):
        def get_model_info(self) -> Dict[str, str]: return {"name": "local-llama3", "version": "v1"}
        def check_health(self) -> bool: return True # 模擬本地模型總是連線成功
        def invoke(self, prompt: str, metadata: TaskMetadata) -> Dict[str, Any]: 
            return {"model": "local-llama3", "output": f"【PoC】已使用本地模型處理指令：{prompt[:20]}...。", "cost_estimate": "Low"}

    class MockCloudConnector(AbstractConnector):
        def get_model_info(self) -> Dict[str, str]: return {"name": "cloud-gpt4o", "version": "v1.5"}
        def check_health(self) -> bool: 
            # 模擬偶發的雲端服務不可用情況
            return False # PoC 階段，我們先讓它失敗，來測試 Fallback 機制

        def invoke(self, prompt: str, metadata: TaskMetadata) -> Dict[str, Any]: 
             return {"model": "cloud-gpt4o", "output": f"【PoC】已使用雲端模型處理指令：{prompt[:20]}...。", "cost_estimate": "Medium"}

    # --- 初始化與運行測試 ---
    print("==========================================")
    print("      [Model Router PoC Test Start]")
    print("==========================================")
    
    router = ModelRouter(available_connectors=[MockLocalConnector, MockCloudConnector])
    router._initialize_connectors()

    # 測試案例 A: 高隱私需求 (應選擇本地模型，模擬成功)
    meta_A = {"privacy_level": "high", "latency_criticality": "medium"}
    print("\n--- Running Test Case A (High Privacy -> Expect Local Model) ---")
    result_A = execute_task_flow(router, "請分析這些客戶的敏感數據。", meta_A)
    print("\\n[Final Result A]", result_A)

    # 測試案例 B: 低隱私需求，但模擬所有模型都故障 (應失敗)
    meta_B = {"privacy_level": "low", "latency_criticality": "low"}
    # 注意：如果我們讓 MockCloudConnector 返回 False，則這組都會過濾掉。
    print("\n--- Running Test Case B (All Failures -> Expect Failure) ---")
    result_B = execute_task_flow(router, "一般市場情緒分析。", meta_B)
    print("\\n[Final Result B]", result_B)
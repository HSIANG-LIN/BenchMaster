from abc import ABC, abstractmethod
from typing import Dict, Any

# 定義任務元數據的類型提示，讓使用者知道 Router 決策時需要傳遞什麼資訊
TaskMetadata = Dict[str, Any]

class AbstractConnector(ABC):
    """
    所有 LLM 連接器必須繼承的抽象基類。
    確保系統各部分使用統一的介面進行調用，實現模型間的解耦（Decoupling）。
    """
    def __init__(self, config: Dict[str, Any]):
        """
        初始化連接器，應接收與特定 LLM 相關的配置 (API Keys, Base URL 等)。
        """
        self.config = config
        print(f"INFO: Initializing {self.__class__.__name__} with config: {config}")

    @abstractmethod
    def check_health(self) -> bool:
        """
        檢查底層 LLM 服務的連線狀態。
        應在 Model Router 選擇模型前調用，用於快速排除不可用的端點。
        返回 True 表示健康，False 表示故障或超時。
        """
        raise NotImplementedError("Subclasses must implement check_health()")

    @abstractmethod
    def invoke(self, prompt: str, metadata: TaskMetadata) -> Dict[str, Any]:
        """
        執行 LLM 核心調用邏輯。
        這是所有業務邏輯唯一需要呼叫的方法。它負責將標準化的 Prompt 和 Metadata 轉譯為底層 API 的格式。

        Args:
            prompt (str): 需要處理的核心指令文本。
            metadata (TaskMetadata): 包含任務上下文的元數據字典 (e.g., {'privacy': 'high', 'latency': 'low'}).

        Returns:
            Dict[str, Any]: 包含模型輸出結果、耗時和使用的成本估算的標準化字典結構。
        """
        raise NotImplementedError("Subclasses must implement invoke()")

    @abstractmethod
    def get_model_info(self) -> Dict[str, str]:
        """返回本連接器所對應的模型名稱和版本資訊。"""
        raise NotImplementedError("Subclasses must implement get_model_info()")
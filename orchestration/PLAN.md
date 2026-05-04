# Hybrid LLM Orchestrator (混合 LLM 路由器) - Spec Sheet v1.0
**作者:** Hermes Agent & Smith Den
**目標:** 設計一個服務層抽象，讓上層業務邏輯完全不知道底層調用的是本地 Ollama、還是雲端的 OpenAI/Anthropic API。

## 📘 架構核心概念 (Core Concepts)
1.  **Model Router / Orchestrator:** 中央決策點，接收任務 Metadata $\rightarrow$ 根據 Policy Engine 決定最佳模型。
2.  **Task Request Metadata:** 標準化輸入的關鍵屬性，包括 `privacy_level`, `latency_criticality`, `budget_priority` 等。
3.  **Model Abstraction Layer (MAL):** 統一介面，所有底層連接器必須遵守此介面。

## 📝 開發階段與交付物 (Development Roadmap)
### Phase 1: PoC - Router Core & Abstraction Layer (目前焦點)
*   **任務:** 定義通用接口和路由邏輯骨架。
*   **文件:** `orchestration/abstract_connector.py`
*   **職責:** 包含所有 LLM 連接器必須繼承的基礎類別，定義標準的 `invoke(prompt, metadata)` 方法簽名。

### Phase 2: Integration - Cloud & Local Connectivity (下一步)
*   **任務:** 將真實 API/本地服務連線整合到骨架中。
*   **文件:** `orchestration/openai_connector.py`, `orchestration/ollama_connector.py`
*   **重點:** 實作 Rate Limiting, Retry 機制與健康檢查。

### Phase 3: Optimization & Resilience (終極目標)
*   **任務:** 將系統提升至工業級穩定性。
*   **優化點:** Fallback Chain 自動切換、成本預估等。
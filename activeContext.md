# BenchMaster — activeContext

> 自動化 Windows 測試機 benchmark 管理系統
> 上次更新：2026-04-30

---

## 專案概覽

BenchMaster 是一個 hybrid MQTT+REST 架構的系統，讓多台 Windows 測試機接收 benchmark 任務、執行、上傳結果，並在 Dashboard 上視覺化呈現。

**核心組件：**
- WHA Agent（Windows 端執行器）
- Fleet Manager（機群調度）
- API Server + Dashboard（後端 + 前端）
- Parsers（Cinebench / 3DMark / CrystalDiskMark / AIDA64 / Geekbench）
- Alert System（門檻告警）
- Hybrid MQTT + REST 通訊層

---

## 當前狀態：Phase 2 完成，Phase 3 待啟動

| Phase | 狀態 |
|-------|------|
| Phase 1 — Core Infrastructure | ✅ 完成 |
| Phase 2 — Core Loop & Polish | ✅ 完成 |
| Phase 3 — Connectivity & AI | ⏸️ 暫停中（待決策） |

### Phase 1 完成項目
- `wha/` — Windows Agent 底座
- `db/models.py` — SQLite ORM 模型
- `agent/fleet_manager.py` — 機群管理
- `parsers/` — 基礎 parser 框架

### Phase 2 完成項目
- 所有 Parsers：Cinebench、3DMark、CrystalDiskMark、AIDA64、Geekbench
- Dashboard（`dashboard/index.html`）— Tailwind + Alpine.js + Chart.js
- API Server（`api/server.py`）— FastAPI，port 8000
- MQTT Manager（`api/mqtt_manager.py`）
- Thresholds / Jobs / Results API Routes
- Agent Tool UI（`agent_tool_ui.py`）
- Hybrid MQTT + REST 通訊層

### Phase 3 待辦（Pending）
- ⬜ **Tunneling / 外部連線**（Ngrok / Cloudflared / Localtunnel）— 待選方案
- ⬜ 趨勢圖強化
- ⬜ 門檻值管理 UI 強化
- ⬜ Cron 排程深度整合
- ⬜ Telegram 深度整合

---

## 技術上下文

| 項目 | 值 |
|------|-----|
| 根目錄 | `~/benchmaster/` |
| Python venv | `./venv/`（Python 3.11） |
| 資料庫 | SQLite (`db/benchmaster.db`) |
| API Server | FastAPI，port 8000 |
| MQTT | `paho-mqtt`，用於遠端控制 |
| 測試 | `tests/`（含整合測試） |
| 最後 Commit | `e367b1b` — Update fleet_manager, models, mqtt_manager, routes, agent_tool_ui |

---

## 活躍決策（Active Decisions）

### 1. Tunneling 方案（待決定）
先前討論到要打通外部連線讓 Windows 測試機可以從 Internet 連回控制端。三個選項：

| 方案 | 優點 | 缺點 |
|------|------|------|
| **Ngrok** | 最穩定，功能完整 | 需要 auth token |
| **Cloudflared** | 免費，零配置 | 設定稍多 |
| **Localtunnel** | 最快上線，免 token | 不穩定 |

**決策狀態：** ⏳ 未決定（專案暫停中）

### 2. AI Insight Engine（已決策）
原本 Phase 3 規劃要開發獨立的 AI 查詢引擎，但決定由 Hermes Agent 直接處理對話式查詢，不另開發。

---

## ORM 模型依賴

```
Agent (wha db)
  └─ TestResult (wha db) — benchmark_id, score, scores_json, raw_output
Machine (models.py)
  └─ BenchmarkResult (models.py) — machine_id (FK), benchmark_name, score, scores_json, raw_output
```

注：WHA 端的 `agent.db` 與 Server 端的 `benchmaster.db` 是分離的兩套資料庫，透過 MQTT/REST 同步。

---

## 快速啟動

```bash
# API Server
cd ~/benchmaster
./venv/bin/python -m api.server

# Dashboard
open http://localhost:8000/
```

> Dashboard 資料為空是正常的 — 需要 WHA Agent 執行 benchmark 後才會回傳數據。

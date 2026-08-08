# 大地遊戲・活米村電子化平台

活米村是支援總召、關主與隊輔的即時大地遊戲控制台。前端使用 Vue 3＋Vite＋TypeScript，後端使用 Python＋FastAPI，Supabase PostgreSQL 是唯一持久化資料來源；所有遊戲規則由 FastAPI 驗證，前端透過 REST API 與 WebSocket 同步。

## 專案結構

- `frontend/`：登入入口、總召 `/admin`、關主 `/master`、隊伍 `/user` 與共用設計系統。
- `backend/`：FastAPI app、API router、即時事件 broker、環境設定與 PostgreSQL migration。
- `backend/migrations/001_initial_schema.sql`、`003_manual_market_operations.sql`、`004_magic_boss_role.sql`、`005_editable_product_identifiers.sql`、`006_team_profiles.sql`、`007_public_team_profiles.sql`：Supabase SQL editor 依序執行的 schema 與流程補充 migration。
- `PRODUCT.md`、`DESIGN.md`：產品與視覺上下文。
- `docs/`：遊戲規則、架構、角色權限與 API 契約。

## 啟動順序

1. 在 Supabase 依序執行 `backend/migrations/001_initial_schema.sql`、`003_manual_market_operations.sql`、`004_magic_boss_role.sql`、`005_editable_product_identifiers.sql`、`006_team_profiles.sql`、`007_public_team_profiles.sql`。
2. 複製 `backend/.env.example` 為 `backend/.env`，填入 `DATABASE_URL` 與 `SESSION_SECRET`。
3. 依 `backend/README.md` 安裝 Python 依賴並啟動 FastAPI。
4. 複製 `frontend/.env.example` 為 `frontend/.env`，在 `frontend/` 執行 `npm install`、`npm run dev`。
5. 開發階段可直接進入 `/admin`、`/master`、`/user` 查看展示快照；接上後端後使用 `/login` 的角色代碼入口。

## Windows 一鍵啟動

專案根目錄已提供 `start.ps1`，會自動檢查 Python／Node.js、建立後端虛擬環境、安裝缺少的依賴、建立 `.env`，並在兩個 PowerShell 視窗啟動前後端。

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

啟動腳本會自動開啟 `http://localhost:5175`。若 `.env` 還是範例值，後端會以無資料庫模式啟動，方便先查看介面；登入與遊戲操作仍需設定有效的 Supabase `DATABASE_URL`。

常用參數：

```powershell
# 只啟動前端
.\start.ps1 -FrontendOnly

# 只啟動後端
.\start.ps1 -BackendOnly

# 不重新安裝依賴
.\start.ps1 -SkipInstall

# 不自動開啟瀏覽器
.\start.ps1 -NoBrowser

# 前端 port 被占用時改用其他 port
.\start.ps1 -FrontendPort 5174
```

如果 port 已被本專案服務占用，腳本會直接沿用現有服務；如果是其他程序占用，會顯示程序資訊與處理建議。

## 重要安全邊界

Supabase service credentials 只能放在 FastAPI 環境變數；不要放進 Vite 的 `VITE_*` 變數，也不要讓前端直接寫 Supabase。正式環境使用 HTTPS／WSS。

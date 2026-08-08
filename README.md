# 大地遊戲・活米村電子化平台

活米村是支援總召、關主與隊輔的即時大地遊戲控制台。前端使用 Vue 3＋Vite＋TypeScript，後端使用 Python＋FastAPI，Supabase PostgreSQL 是唯一持久化資料來源；所有遊戲規則由 FastAPI 驗證，前端透過 REST API 與 WebSocket 同步。

## 專案結構

- `frontend/`：登入入口、總召 `/admin`、關主 `/master`、隊伍 `/user` 與共用設計系統。
- `backend/`：FastAPI app、API router、即時事件 broker、環境設定與 PostgreSQL migration。
- `backend/migrations/001_initial_schema.sql`：Supabase SQL editor 的初始 schema。
- `PRODUCT.md`、`DESIGN.md`：產品與視覺上下文。
- `docs/`：遊戲規則、架構、角色權限與 API 契約。

## 啟動順序

1. 在 Supabase 執行 `backend/migrations/001_initial_schema.sql`。
2. 複製 `backend/.env.example` 為 `backend/.env`，填入 `DATABASE_URL` 與 `SESSION_SECRET`。
3. 依 `backend/README.md` 安裝 Python 依賴並啟動 FastAPI。
4. 複製 `frontend/.env.example` 為 `frontend/.env`，在 `frontend/` 執行 `npm install`、`npm run dev`。
5. 開發階段可直接進入 `/admin`、`/master`、`/user` 查看展示快照；接上後端後使用 `/login` 的角色代碼入口。

## 重要安全邊界

Supabase service credentials 只能放在 FastAPI 環境變數；不要放進 Vite 的 `VITE_*` 變數，也不要讓前端直接寫 Supabase。正式環境使用 HTTPS／WSS。

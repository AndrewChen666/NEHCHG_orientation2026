# 活米村系統架構

## 目標

建立一個以 FastAPI 為規則裁判、Supabase PostgreSQL 為唯一持久化來源、Vue 3 為角色操作介面的即時遊戲平台。

## 邊界

```text
Vue 3 / Vite / TypeScript
        │ HTTPS JSON API + WebSocket
        ▼
FastAPI
  ├─ 角色代碼登入與 session token
  ├─ 遊戲時鐘與狀態機
  ├─ 交易／佔領／題目／卡片規則
  ├─ 權限檢查、稽核與事件序號
  └─ WebSocket 廣播（只送已授權事件）
        │ async PostgreSQL connection
        ▼
Supabase PostgreSQL
  ├─ 場次設定、隊伍、角色代碼
  ├─ 市場、行情、交易與資產 ledger
  ├─ 佔領、挑戰、題目、卡片與效果
  └─ 事件／稽核紀錄
```

前端不可直接寫 Supabase。所有會改變遊戲狀態的操作只能進 FastAPI；後端以資料庫 transaction、row lock 與唯一條件確保同一時間的競賽操作不會重複扣款或雙重佔領。

## 即時事件

每個場次有單調遞增的事件序號。成功操作先寫入資料庫，再由 FastAPI 廣播 `game.event`。前端若斷線，重新連線時先以 REST 取得最新 snapshot，再用 `after_sequence` 補收事件；不依賴 WebSocket 作為唯一資料來源。

瀏覽器 WebSocket 不支援自訂 Authorization header，因此第一版連線使用短期 token query parameter 完成握手；連線建立後不會把 token 寫入事件內容，正式部署需搭配 HTTPS/WSS。

事件最小格式：

```json
{
  "sequence": 1042,
  "type": "ownership.changed",
  "session_id": "uuid",
  "occurred_at": "2026-08-08T09:00:00Z",
  "payload": { "market_id": "uuid", "team_id": "uuid" }
}
```

## 身分與安全

- 登入使用角色／隊伍代碼；資料庫只保存 Argon2 雜湊，前端保存短期 bearer token。
- 服務角色的 Supabase／PostgreSQL 密鑰只放在 FastAPI，不進入 Vite bundle。
- API 依場次、角色、綁定市場／隊伍做 server-side authorization。
- 所有金錢與資源變化必須有 ledger entry，不允許直接更新餘額而沒有原因。

## 時鐘

場次狀態為 `draft → scheduled → running ↔ paused → finished`。`effective_elapsed_ms` 由後端以開始時間扣除暫停區間計算；時段由有效時間推導，總召的手動切換作為明確 override 並寫入 audit log。佔領收益、挑戰冷卻與卡片期限都依同一時鐘服務。

## 前端模組

- `router/`：角色入口與權限導向。
- `layouts/`：桌機 sidebar、手機 topbar、連線狀態與時鐘。
- `components/`：金錢袋、時段、資源、市場、操作確認等可重用元件。
- `lib/api.ts`：API client 與統一錯誤格式。
- `lib/realtime.ts`：WebSocket 連線、斷線重連與事件序號。
- `stores/`：以 Vue reactive 建立 session、auth 與通知狀態；不引入不必要的全域狀態套件。

## Deployment baseline

- 前端：Vite build 後部署到任一支援靜態檔案與 SPA fallback 的 hosting。
- 後端：可運行 ASGI 的 Python hosting，設定 `DATABASE_URL`、`CORS_ORIGINS` 與 `SESSION_SECRET`。
- 資料庫：Supabase project，透過 migration 建立 schema；正式環境先以 staging session 做交易與斷線演練。

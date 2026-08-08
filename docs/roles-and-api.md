# 角色權限與 API 契約基準

## 角色權限矩陣

| 能力 | 總召 | 關主 | 隊輔 |
|---|---:|---:|---:|
| 查看場次時鐘與公開公告 | ✓ | ✓ | ✓ |
| 管理場次、時段與排程 | ✓ | — | — |
| 管理隊伍與初始資產 | ✓ | — | — |
| 管理所有行情／隱藏行情 | ✓ | 僅綁定市場 | — |
| 查看全局排行榜 | ✓ | ✓ | ✓ |
| 執行本市場交易 | — | ✓ | — |
| 執行本市場挑戰判定 | — | ✓ | — |
| 代表隊伍交易與挑戰 | — | — | ✓ |
| 抽取／套用黑心商人卡 | ✓ | ✓（依授權） | ✓（提出申請） |
| 手動調整金錢／資產 | ✓ | — | — |
| 查看完整稽核紀錄 | ✓ | 本市場 | 本隊 |

## API 分組

### Auth

- `POST /api/v1/auth/code-login`：以角色／隊伍代碼登入。
- `POST /api/v1/auth/refresh`：更新短期 session token。
- `GET /api/v1/auth/me`：取得目前角色與綁定範圍。

### Session

- `GET /api/v1/sessions/{session_id}/snapshot`：取得角色可見的完整快照。
- `POST /api/v1/sessions/{session_id}/start`：總召開始或立即開始場次。
- `POST /api/v1/sessions/{session_id}/pause`、`/resume`、`/advance-period`、`/finish`。
- `GET /api/v1/sessions/{session_id}/events?after_sequence=`：斷線補事件。
- `WS /api/v1/sessions/{session_id}/stream`：即時事件串流。

### Markets and actions

- `GET /api/v1/markets/{market_id}`：取得角色可見市場狀態與行情。
- `POST /api/v1/markets/{market_id}/transactions`：單一原料買入／賣出。
- `POST /api/v1/markets/{market_id}/challenge`：發起市場挑戰。
- `POST /api/v1/challenges/{challenge_id}/result`：關主輸入成功／失敗。
- `POST /api/v1/magic-challenges`：建立隱藏魔王判題結果。
- `POST /api/v1/black-market/draw`、`POST /api/v1/black-market/effects/{effect_id}/apply`。

每個會改變狀態的 POST 都需要：`session_id`、session token、`money_pouch_presented`、`minimum_team_present` 與冪等鍵 `idempotency_key`。回應包含最新資產、事件序號與可供畫面更新的摘要。

## 錯誤格式

```json
{
  "error": {
    "code": "MARKET_COOLDOWN",
    "message": "本隊 2 分 10 秒內不能再次挑戰此市場。",
    "details": { "retry_at": "2026-08-08T09:03:00Z" }
  }
}
```

錯誤 code 供前端決定 UI，message 供現場直接閱讀；不能只回傳 HTTP 500 或資料庫錯誤。

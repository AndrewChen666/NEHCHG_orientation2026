# 活米村開發規範

## 每次更新都要提交中文 commit

每一個可辨識的更新批次都必須完成一個中文 commit，commit message 使用「動作＋範圍」描述，例如：

- `建立 FastAPI 即時遊戲後端與資料庫結構`
- `修正市場交易冪等與斷線同步`
- `優化隊輔市場操作介面`

不要留下未提交的可交付修改；若更新包含多個互相依賴的檔案，放在同一個明確的中文 commit。每次 commit 前至少執行與變更相關的檢查，並在交付訊息中說明未能執行的檢查與原因。

## 開發原則

- 遊戲金錢、物資、時鐘、冷卻、佔領與卡片效果只能由 FastAPI 判定。
- Supabase PostgreSQL 是唯一資料來源；前端不直接寫資料庫。
- 每個狀態變更都要有冪等鍵、事件序號與稽核紀錄。
- 介面需保留手機現場操作的高對比、可掃讀性與 reduced-motion 支援。
- 新增規則時，先更新 `docs/game-rules.md` 與 API／schema，再實作畫面。

## 交付前檢查

- `python -m compileall -q backend`
- `npm run type-check`
- `npm run build`
- `git diff --check`
- `git status --short` 應為空

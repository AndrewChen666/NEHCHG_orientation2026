# 活米村 FastAPI

## 本機啟動

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python main.py
```

沒有設定 `DATABASE_URL` 時，`GET /health` 仍會回報服務狀態；需要執行遊戲操作前，請先在 Supabase SQL editor 執行 `migrations/001_initial_schema.sql`，並在 `.env` 填入連線字串。

首次建立場次使用 `SETUP_KEY` 呼叫 `POST /api/v1/setup/sessions`。成功回應會只顯示一次總召、8 個關主與 12 個隊伍代碼，請立即保存；之後所有操作改用角色代碼登入與正常權限 API。

## API 文件

啟動後可開啟 `/docs` 查看 OpenAPI。所有遊戲寫入操作都必須透過 FastAPI，前端不得直接寫 Supabase。

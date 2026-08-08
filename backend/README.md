# 活米村(誰取的怪名字。)

## 本機啟動
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python main.py
```

## 啟動腳本
```.\start.ps1 -FrontendOnly
.\start.ps1 -BackendOnly
.\start.ps1 -NoBrowser
.\start.ps1 -FrontendPort 5174```
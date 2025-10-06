@echo off
rem 設定程式碼頁為 UTF-8 以正確顯示中文
chcp 65001 > nul

echo =================================================================
echo ==                                                             ==
echo ==         專案結構自動建立腳本 v2 (Project Scaffolder)        ==
echo ==                                                             ==
echo =================================================================
echo.
echo 這個腳本即將在此資料夾建立專案所需的檔案結構。
echo.
pause
echo.

rem --- 建立根目錄檔案 ---
echo [1/4] 正在建立根目錄檔案...

echo # Project Name > README.md
echo. >> README.md
echo ## 專案簡介 >> README.md
echo. >> README.md
echo 這是一個天氣與環境資訊預警系統，整合了 NCDR 與 CWA 的資料來源，透過 FCM 主動推播通知，並使用 PWA 技術呈現詳細資訊。 >> README.md
echo. >> README.md
echo ## 技術棧 >> README.md
echo. >> README.md
echo * **後端 (Server):** Python (FastAPI), Firebase Admin SDK >> README.md
echo * **前端 (Web):** HTML, CSS, JavaScript (PWA) >> README.md
echo * **通知服務:** Firebase Cloud Messaging (FCM) >> README.md
echo. >> README.md
echo ## 如何安裝與啟動 >> README.md
echo. >> README.md
echo ### 後端 >> README.md
echo ```bash >> README.md
echo cd server >> README.md
echo python -m venv venv >> README.md
echo .\venv\Scripts\activate >> README.md
echo pip install -r requirements.txt >> README.md
echo uvicorn main:app --reload >> README.md
echo ``` >> README.md
echo. >> README.md
echo ### 前端 >> README.md
echo (暫無，可直接用 Live Server 等工具開啟 index.html) >> README.md

echo # Python > .gitignore
echo __pycache__/ >> .gitignore
echo *.py[cod] >> .gitignore
echo *$py.class >> .gitignore
echo. >> .gitignore
echo # Virtual Environment >> .gitignore
echo venv/ >> .gitignore
echo env/ >> .gitignore
echo. >> .gitignore
echo # Environment variables >> .gitignore
echo .env >> .gitignore
echo. >> .gitignore
echo # IDE specific >> .gitignore
echo .vscode/ >> .gitignore
echo .idea/ >> .gitignore

echo ...根目錄檔案建立完成。
echo.
pause
echo.

rem --- 建立 server 目錄結構 ---
echo [2/4] 正在建立 server 目錄結構...
mkdir server
mkdir server\api
mkdir server\core
mkdir server\services
mkdir server\scheduler

echo # Web Framework > server\requirements.txt
echo fastapi >> server\requirements.txt
echo uvicorn[standard] >> server\requirements.txt
echo. >> server\requirements.txt
echo # HTTP Requests >> server\requirements.txt
echo requests >> server\requirements.txt
echo. >> server\requirements.txt
echo # Firebase >> server\requirements.txt
echo firebase-admin >> server\requirements.txt
echo. >> server\requirements.txt
echo # Environment variables >> server\requirements.txt
echo python-dotenv >> server\requirements.txt
echo. >> server\requirements.txt
echo # Scheduler >> server\requirements.txt
echo apscheduler >> server\requirements.txt

type nul > server\.env
type nul > server\main.py
type nul > server\config.py
type nul > server\api\__init__.py
type nul > server\api\weather.py
type nul > server\core\__init__.py
type nul > server\core\calculation.py
type nul > server\core\data_fetcher.py
type nul > server\services\__init__.py
type nul > server\services\fcm_sender.py
type nul > server\scheduler\__init__.py
type nul > server\scheduler\jobs.py

echo ...server 目錄結構建立完成。
echo.
pause
echo.

rem --- 建立 web 目錄結構 ---
echo [3/4] 正在建立 web 目錄結構...
mkdir web
mkdir web\assets
mkdir web\assets\icons
mkdir web\assets\images
mkdir web\css
mkdir web\js

echo ^<!DOCTYPE html^> > web\index.html
echo ^<html lang="zh-Hant"^> >> web\index.html
echo ^<head^> >> web\index.html
echo     ^<meta charset="UTF-8"^> >> web\index.html
echo     ^<meta name="viewport" content="width=device-width, initial-scale=1.0"^> >> web\index.html
echo     ^<title^>專案名稱^</title^> >> web\index.html
echo     ^<link rel="stylesheet" href="css/style.css"^> >> web\index.html
echo     ^<link rel="manifest" href="manifest.json"^> >> web\index.html
echo ^</head^> >> web\index.html
echo ^<body^> >> web\index.html
echo     ^<h1^>歡迎來到我們的天氣預警服務^</h1^> >> web\index.html
echo. >> web\index.html
echo     ^<script src="js/main.js"^>^</script^> >> web\index.html
echo ^</body^> >> web\index.html
echo ^</html^> >> web\index.html

echo { > web\manifest.json
echo   "short_name": "天氣App", >> web\manifest.json
echo   "name": "你的天氣與環境預警 App", >> web\manifest.json
echo   "icons": [ >> web\manifest.json
echo     { >> web\manifest.json
echo       "src": "assets/icons/icon-192x192.png", >> web\manifest.json
echo       "type": "image/png", >> web\manifest.json
echo       "sizes": "192x192" >> web\manifest.json
echo     }, >> web\manifest.json
echo     { >> web\manifest.json
echo       "src": "assets/icons/icon-512x512.png", >> web\manifest.json
echo       "type": "image/png", >> web\manifest.json
echo       "sizes": "512x512" >> web\manifest.json
echo     } >> web\manifest.json
echo   ], >> web\manifest.json
echo   "start_url": ".", >> web\manifest.json
echo   "display": "standalone", >> web\manifest.json
echo   "theme_color": "#ffffff", >> web\manifest.json
echo   "background_color": "#ffffff" >> web\manifest.json
echo } >> web\manifest.json

type nul > web\sw.js
type nul > web\css\style.css
type nul > web\js\main.js
type nul > web\js\api.js
type nul > web\js\ui.js
type nul > web\js\firebase.js
type nul > web\assets\icons\icon-192x192.png
type nul > web\assets\icons\icon-512x512.png

echo ...web 目錄結構建立完成。
echo.
pause
echo.

rem --- 完成 ---
echo [4/4] 專案結構已全部建立完成！
echo.
pause
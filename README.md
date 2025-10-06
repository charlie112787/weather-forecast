# Project Name 
 
## 專案簡介 
 
這是一個天氣與環境資訊預警系統，整合了 NCDR 與 CWA 的資料來源，透過 FCM 主動推播通知，並使用 PWA 技術呈現詳細資訊。 
 
## 技術棧 
 
* **後端 (Server):** Python (FastAPI), Firebase Admin SDK 
* **前端 (Web):** HTML, CSS, JavaScript (PWA) 
* **通知服務:** Firebase Cloud Messaging (FCM) 
 
## 如何安裝與啟動 
 
### 後端 
```bash 
cd server 
python -m venv venv 
.\venv\Scripts\activate 
pip install -r requirements.txt 
uvicorn main:app --reload 
``` 
 
### 前端 
(暫無，可直接用 Live Server 等工具開啟 index.html) 

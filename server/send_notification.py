import firebase_admin
from firebase_admin import credentials, messaging
import os
import sys

# 確保 serviceAccountKey.json 存在
SERVICE_ACCOUNT_KEY_PATH = os.path.join(os.path.dirname(__file__), 'serviceAccountKey.json')

if not os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
    print(f"錯誤：找不到服務帳戶金鑰檔案：{SERVICE_ACCOUNT_KEY_PATH}")
    print("請確保 serviceAccountKey.json 檔案位於 /server 目錄中。")
    sys.exit(1)

# 初始化 Firebase Admin SDK
if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
    firebase_admin.initialize_app(cred)
    print("Firebase Admin SDK 已成功初始化。")

def send_weather_alert_sync(township_code: str, title: str, body: str, custom_data: dict = None):
    """
    發送天氣警報通知到指定鄉鎮的 Topic。
    這是同步版本，用於簡單腳本。
    """
    topic = f"weather_{township_code}"
    
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=custom_data, # 可以包含額外的自定義資料
        topic=topic,
    )

    try:
        response = messaging.send(message)
        print(f"成功發送訊息到 Topic '{topic}': {response}")
        return True
    except Exception as e:
        print(f"發送訊息到 Topic '{topic}' 時發生錯誤: {e}")
        return False

def main():
    print("--- 發送 FCM Topic 通知 ---")
    
    township_code = input("請輸入目標鄉鎮代碼 (例如: TPE-100): ").strip()
    if not township_code:
        print("鄉鎮代碼不能為空。")
        sys.exit(1)

    notification_title = input("請輸入通知標題: ").strip()
    if not notification_title:
        print("通知標題不能為空。")
        sys.exit(1)

    notification_body = input("請輸入通知內容: ").strip()
    if not notification_body:
        print("通知內容不能為空。")
        sys.exit(1)

    # 這裡可以添加額外的自定義資料，例如：
    # custom_data = {"alert_type": "大雨特報", "severity": "高"}
    custom_data = None 

    # 由於 messaging.send 是同步的，可以直接呼叫
    send_weather_alert_sync(township_code, notification_title, notification_body, custom_data)

if __name__ == "__main__":
    main()

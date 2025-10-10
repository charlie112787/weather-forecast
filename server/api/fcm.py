from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, firestore, messaging
import os
import asyncio

# 確保 serviceAccountKey.json 存在
SERVICE_ACCOUNT_KEY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'serviceAccountKey.json')

if not os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
    print(f"錯誤：找不到服務帳戶金鑰檔案：{SERVICE_ACCOUNT_KEY_PATH}")
    raise FileNotFoundError("serviceAccountKey.json not found")

# 初始化 Firebase Admin SDK
if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
    firebase_admin.initialize_app(cred)
    print("Firebase Admin SDK initialized successfully in FCM router.")

db = firestore.client()
fcm_router = APIRouter(prefix="/api/fcm", tags=["FCM"])

class FcmRegistration(BaseModel):
    uid: str
    fcmToken: str
    townshipCode: str | None = None

async def subscribe_to_weather_topic(fcm_token: str, township_code: str):
    topic = f"weather_{township_code}"
    try:
        response = messaging.subscribe_to_topic([fcm_token], topic)
        print(f"Successfully subscribed token {fcm_token} to topic {topic}: {response}")
        return True
    except Exception as e:
        print(f"Error subscribing token {fcm_token} to topic {topic}: {e}")
        return False

async def unsubscribe_from_weather_topic(fcm_token: str, topic: str):
    try:
        response = messaging.unsubscribe_from_topic([fcm_token], topic)
        print(f"Successfully unsubscribed token {fcm_token} from topic {topic}: {response}")
        return True
    except Exception as e:
        print(f"Error unsubscribing token {fcm_token} from topic {topic}: {e}")
        return False

@fcm_router.post("/register")
async def register_fcm(registration: FcmRegistration):
    try:
        user_ref = db.collection("fcmTokens").document(registration.uid)
        user_doc = await asyncio.to_thread(user_ref.get) # Firestore get is synchronous

        old_fcm_token = None
        old_township_code = None
        old_topic = None

        if user_doc.exists:
            data = user_doc.to_dict()
            old_fcm_token = data.get("fcmToken")
            old_township_code = data.get("townshipCode")
            if old_township_code:
                old_topic = f"weather_{old_township_code}"

        # 1. 處理 Token 變更或 TownshipCode 變更導致的訂閱更新
        if old_fcm_token != registration.fcmToken: # Token 變更，需要重新訂閱
            if old_fcm_token and old_topic: # 如果有舊 Token 和舊 Topic，先取消訂閱
                await unsubscribe_from_weather_topic(old_fcm_token, old_topic)
            if registration.townshipCode: # 用新 Token 訂閱新 Topic
                await subscribe_to_weather_topic(registration.fcmToken, registration.townshipCode)
        elif registration.townshipCode and old_township_code != registration.townshipCode: # Token 沒變，但 TownshipCode 變了
            if old_topic: # 取消訂閱舊 Topic
                await unsubscribe_from_weather_topic(registration.fcmToken, old_topic)
            await subscribe_to_weather_topic(registration.fcmToken, registration.townshipCode) # 訂閱新 Topic
        elif registration.townshipCode and not old_township_code: # 第一次設定 TownshipCode
            await subscribe_to_weather_topic(registration.fcmToken, registration.townshipCode)
        
        # 2. 更新 Firestore 儲存
        await asyncio.to_thread(user_ref.set, {
            "uid": registration.uid,
            "fcmToken": registration.fcmToken,
            "townshipCode": registration.townshipCode,
            "lastUpdated": firestore.SERVER_TIMESTAMP
        })

        return {"message": "FCM registration and topic subscription updated successfully"}
    except Exception as e:
        print(f"FCM 註冊失敗: {e}")
        raise HTTPException(status_code=500, detail=f"FCM registration failed: {e}")

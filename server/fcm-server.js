// --- 引入必要的套件 ---
const express = require('express');
const admin = require('firebase-admin');
const cors = require('cors');

// --- 初始化 Firebase Admin SDK ---
// 請確認 serviceAccountKey.json 檔案與此檔案在同一個資料夾
const serviceAccount = require('./serviceAccountKey.json');

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount)
});

const db = admin.firestore();
const messaging = admin.messaging();
const app = express();

// --- 中介軟體 (Middleware) ---
// 使用 CORS 中介軟體，並設定允許的來源
app.use(cors({
  origin: 'https://taiwan-weather-alert.pages.dev'
}));
// 使用 Express 內建的中介軟體來解析 JSON 格式的請求 Body
app.use(express.json());


// --- API 路由 (Endpoint) ---

/**
 * 根路由，用於健康檢查
 */
app.get('/', (req, res) => {
  res.status(200).send({ status: 'ok', message: 'FCM server (Node.js) is running.' });
});

/**
 * 處理 FCM Token 註冊與 Topic 訂閱的路由
 */
app.post('/api/fcm/register', async (req, res) => {
  console.log(`收到來自 ${req.ip} 的註冊請求`);
  
  // 從請求的 Body 中獲取資料
  const { uid, fcmToken, townshipCode } = req.body;

  // 驗證收到的資料
  if (!uid || !fcmToken) {
    console.error('請求資料不完整: 缺少 uid 或 fcmToken');
    return res.status(422).send({ error: 'uid and fcmToken are required.' });
  }
  
  console.log(`收到的資料: uid=${uid}, fcmToken=${fcmToken.substring(0, 10)}..., townshipCode=${townshipCode}`);

  try {
    const userRef = db.collection('fcmTokens').doc(uid);
    const userDoc = await userRef.get();

    const oldData = userDoc.exists ? userDoc.data() : {};
    const oldFcmToken = oldData.fcmToken;
    const oldTownshipCode = oldData.townshipCode;

    // 判斷是否需要更新訂閱
    if (oldFcmToken !== fcmToken || oldTownshipCode !== townshipCode) {
      console.log('偵測到 Token 或鄉鎮代碼變更，開始處理訂閱更新...');

      // 1. 如果有舊的訂閱，先取消
      if (oldFcmToken && oldTownshipCode) {
        try {
          console.log(`嘗試從 Topic weather_${oldTownshipCode} 取消訂閱 Token ${oldFcmToken.substring(0, 10)}...`);
          await messaging.unsubscribeFromTopic(oldFcmToken, `weather_${oldTownshipCode}`);
          console.log('成功取消舊的訂閱');
        } catch (e) {
          console.error('取消訂閱時發生錯誤 (可忽略):', e.message);
        }
      }

      // 2. 如果有新的鄉鎮代碼，訂閱新的
      if (townshipCode) {
        try {
          console.log(`嘗試將 Token ${fcmToken.substring(0, 10)}... 訂閱到 Topic weather_${townshipCode}`);
          await messaging.subscribeToTopic(fcmToken, `weather_${townshipCode}`);
          console.log('成功訂閱新的 Topic');
        } catch (e) {
           console.error('訂閱新 Topic 時發生錯誤:', e.message);
           // 如果訂閱失敗，則拋出錯誤，讓整個請求失敗
           throw e;
        }
      }
    } else {
      console.log('資料與現有紀錄相同，無需更新訂閱。');
    }
    
    // 更新 Firestore 中的資料
    console.log('正在更新 Firestore 中的 Token 資料...');
    await userRef.set({
      uid: uid,
      fcmToken: fcmToken,
      townshipCode: townshipCode,
      lastUpdated: admin.firestore.FieldValue.serverTimestamp()
    });
    console.log('Firestore 資料更新成功。');
    
    // 回傳成功訊息
    res.status(200).send({ message: 'FCM registration and topic subscription updated successfully' });

  } catch (error) {
    console.error(`FCM 註冊流程發生嚴重錯誤:`, error);
    res.status(500).send({ error: `FCM registration failed: ${error.message}` });
  }
});


// --- 啟動伺服器 ---
const PORT = 7800;
app.listen(PORT, '0.0.0.0', () => {
  console.log(`Node.js FCM server is running on http://0.0.0.0:${PORT}`);
});

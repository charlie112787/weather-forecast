importScripts('https://www.gstatic.com/firebasejs/8.10.0/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/8.10.0/firebase-messaging.js');

// 這是您從 Firebase 控制台獲取的設定金鑰 (Service Worker 需要自己的初始化)
const firebaseConfig = {
  apiKey: "AIzaSyB3Q74U0IH8xe5ucUnkhzuBY9Inv26SGQc",
  authDomain: "weather-forecast-c62c3.firebaseapp.com",
  projectId: "weather-forecast-c62c3",
  storageBucket: "weather-forecast-c62c3.firebasestorage.app",
  messagingSenderId: "898186924731",
  appId: "1:898186924731:web:9bc4884ba3ca070b598f9e",
  measurementId: "G-KS86ZBCF1K"
};

// Service Worker 中使用相容性語法初始化 Firebase
firebase.initializeApp(firebaseConfig);
const messaging = firebase.messaging();

// 處理背景訊息
messaging.onBackgroundMessage(payload => {
  console.log('[firebase-messaging-sw.js] Received background message ', payload);
  // 自定義通知顯示邏輯
  const notificationTitle = payload.notification.title;
  const notificationOptions = {
    body: payload.notification.body,
    icon: '/assets/icons/icon-192x192.png' // 您可以設定通知圖示
  };

  self.registration.showNotification(notificationTitle, notificationOptions);
});

console.log('我是 Service Worker，我已經被喚醒！');
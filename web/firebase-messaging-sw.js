importScripts('https://www.gstatic.com/firebasejs/8.10.0/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/8.10.0/firebase-messaging.js');

const firebaseConfig = {
  apiKey: "AIzaSyB3Q74U0IH8xe5ucUnkhzuBY9Inv26SGQc",
  authDomain: "weather-forecast-c62c3.firebaseapp.com",
  projectId: "weather-forecast-c62c3",
  storageBucket: "weather-forecast-c62c3.firebasestorage.app",
  messagingSenderId: "898186924731",
  appId: "1:898186924731:web:9bc4884ba3ca070b598f9e",
  measurementId: "G-KS86ZBCF1K"
};

firebase.initializeApp(firebaseConfig);
const messaging = firebase.messaging();

messaging.onBackgroundMessage(payload => {
  console.log('[SW] Received background message ', payload);

  // --- [新增的關鍵邏輯] ---
  // 檢查是否有任何客戶端(分頁)是可見的
  const promiseChain = clients.matchAll({
    type: 'window',
    includeUncontrolled: true
  }).then(windowClients => {
    let isAppInForeground = false;
    for (let i = 0; i < windowClients.length; i++) {
      const windowClient = windowClients[i];
      // 如果有任何一個分頁是可見的，就視為前景
      if (windowClient.visibilityState === 'visible') {
        isAppInForeground = true;
        break;
      }
    }

    if (isAppInForeground) {
      console.log('[SW] App is in the foreground, skipping notification.');
      // 如果網站在前景，就不顯示通知，讓 main.js 去處理
      return;
    }

    console.log('[SW] App is in the background, showing notification.');
    // 只有當網站不在前景時，才由 Service Worker 顯示通知
    const notificationTitle = payload.notification.title;
    const notificationOptions = {
      body: payload.notification.body,
      icon: '/assets/icons/icon-192x192.png'
    };
    return self.registration.showNotification(notificationTitle, notificationOptions);
  });

  return promiseChain;
});


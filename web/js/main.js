import { COUNTY_NAME_TO_CODE, LOCATION_DATA, CODE_TO_TOWNSHIP_NAME } from './location_data.js';
import { db } from './firebase.js'; // 匯入 db

document.addEventListener('DOMContentLoaded', () => {

    // Firebase 登入狀態監聽器
    firebase.auth().onAuthStateChanged(user => {
        if (user) {
            // 使用者已登入
            console.log('使用者已登入:', user.email);
            initializeUserSettings(user);
            initializeFCM(user);

        } else {
            // 使用者未登入，導向到登入頁面
            console.log('使用者未登入，正在導向到 login.html');
            window.location.href = 'login.html';
        }
    });

    /**
     * 初始化使用者設定功能 (縣市/鄉鎮選擇與儲存)
     * @param {firebase.User} user - 當前登入的 Firebase 使用者物件
     */
    async function initializeUserSettings(user) {
        // 直接使用從 firebase.js 匯出的 db
        console.log('initializeUserSettings 呼叫，db 狀態:', typeof db, db);

        if (typeof db.collection !== 'function') {
            console.error('錯誤: db 物件沒有 collection 方法。db 的實際內容:', db);
            return; // 提前終止，避免後續錯誤
        }

        const countySelect = document.getElementById('county-select');
        const townshipSelect = document.getElementById('township-select');
        const saveSettingsBtn = document.getElementById('save-settings-btn');
        const settingsStatus = document.getElementById('settings-status');

        if (!countySelect || !townshipSelect || !saveSettingsBtn || !settingsStatus) {
            console.error('找不到使用者設定相關的 HTML 元素。');
            return;
        }

        const userDocRef = db.collection('users').doc(user.uid);
        let currentTopic = null; // 用於追蹤當前訂閱的 Topic (現在僅用於邏輯判斷，實際訂閱需後端)

        // 填充縣市選單
        function populateCountySelect() {
            countySelect.innerHTML = '';
            const defaultOption = document.createElement('option');
            defaultOption.value = '';
            defaultOption.textContent = '請選擇縣市';
            countySelect.appendChild(defaultOption);

            for (const countyName in COUNTY_NAME_TO_CODE) {
                const option = document.createElement('option');
                option.value = countyName; // 儲存縣市名稱
                option.textContent = countyName;
                countySelect.appendChild(option);
            }
        }

        // 填充鄉鎮選單
        function populateTownshipSelect(selectedCountyName) {
            townshipSelect.innerHTML = '';
            const defaultOption = document.createElement('option');
            defaultOption.value = '';
            defaultOption.textContent = '請選擇鄉鎮';
            townshipSelect.appendChild(defaultOption);

            if (selectedCountyName && LOCATION_DATA[selectedCountyName]) {
                for (const townshipName in LOCATION_DATA[selectedCountyName]) {
                    const option = document.createElement('option');
                    option.value = LOCATION_DATA[selectedCountyName][townshipName]; // 儲存代號
                    option.textContent = townshipName;
                    townshipSelect.appendChild(option);
                }
            }
        }

        // 縣市選單變動時更新鄉鎮選單
        countySelect.addEventListener('change', () => {
            populateTownshipSelect(countySelect.value);
        });

        populateCountySelect(); // 首次載入時填充縣市選單
        populateTownshipSelect(countySelect.value); // 確保鄉鎮選單初始為空或根據預設縣市填充

        // 讀取使用者設定
        try {
            const doc = await userDocRef.get();
            if (doc.exists && doc.data().settings && doc.data().settings.townshipCode) {
                const savedTownshipCode = doc.data().settings.townshipCode;
                const fullTownshipName = CODE_TO_TOWNSHIP_NAME[savedTownshipCode]; // 例如 "臺北市中正區"

                if (fullTownshipName) {
                    // 從完整的鄉鎮名稱中解析出縣市名稱
                    const savedCountyName = Object.keys(LOCATION_DATA).find(county => fullTownshipName.startsWith(county));
                    
                    if (savedCountyName) {
                        countySelect.value = savedCountyName;
                        populateTownshipSelect(savedCountyName);
                        townshipSelect.value = savedTownshipCode;
                        currentTopic = `weather_${savedTownshipCode}`; // 設定當前訂閱的 Topic
                        console.log('已載入使用者預設地區代號:', savedTownshipCode);
                    }
                }
            }
        } catch (error) {
            console.error('讀取使用者設定失敗:', error);
        }

        // 儲存使用者設定
        saveSettingsBtn.addEventListener('click', async () => {
            const selectedCountyName = countySelect.value;
            const selectedTownshipCode = townshipSelect.value;

            if (selectedCountyName && selectedTownshipCode) {
                try {
                    // 儲存縣市名稱和鄉鎮代號
                    await userDocRef.set({
                        settings: {
                            countyName: selectedCountyName,
                            townshipCode: selectedTownshipCode
                        }
                    }, { merge: true });
                    settingsStatus.textContent = '設定已儲存！';
                    settingsStatus.style.color = 'var(--accent-2)';
                    console.log('使用者預設地區代號已儲存:', selectedTownshipCode);
                    setTimeout(() => settingsStatus.textContent = '', 3000); // 3秒後清除訊息

                    // 獲取最新的 FCM Token 並發送到後端更新訂閱
                    const latestToken = await messaging.getToken({ vapidKey: 'BK_Zl0M8cUguXf8WV1xI1U6qFQ7Aw2tmQqjnYuack1NEF-IjuW0HR9PYlqbaqb3JPblLqn9DANXfnDvtEHZANpY' });
                    if (latestToken) {
                        await sendTokenAndSettingsToBackend(user.uid, latestToken, userDocRef);
                    }

                } catch (error) {
                    settingsStatus.textContent = '儲存失敗！';
                    settingsStatus.style.color = '#ffcccc';
                    console.error('儲存使用者設定失敗:', error);
                }
            } else {
                settingsStatus.textContent = '請選擇縣市和鄉鎮！';
                settingsStatus.style.color = '#ffcccc';
                setTimeout(() => settingsStatus.textContent = '', 3000); // 3秒後清除訊息
            }
        });
    }

    /**
     * 初始化 Firebase Cloud Messaging (FCM)
     * @param {firebase.User} user - 當前登入的 Firebase 使用者物件
     */
    async function initializeFCM(user) {
        const messaging = firebase.messaging(); // 使用全域 firebase 物件

        // 請求通知權限
        try {
            const permission = await Notification.requestPermission();
            if (permission === 'granted') {
                console.log('通知權限已授予。');
                // 獲取 FCM 註冊 Token
                // getToken 函數會自動處理 Service Worker 的註冊和激活
                const currentToken = await messaging.getToken({ vapidKey: 'BOvUnXfY9tx_0ivPB7YGwU2fbeYaK66Gf3eLKg0NirKISO7wz8rbDZtkeNr449mabR-rahs7k5BgGaYH14Ga218' }); // 請替換為您的 VAPID Key
                if (currentToken) {
                    console.log('FCM 註冊 Token:', currentToken);
                    // TODO: 將 Token 儲存到 Firestore，以便後端直接發送通知給特定裝置
                    // 並且將 Token 和使用者 UID 發送到後端，以便後端管理 Topic 訂閱
                    await sendTokenAndSettingsToBackend(user.uid, currentToken); // 初始呼叫時不傳 townshipCode，讓函式自行讀取
                } else {
                    console.log('未獲取到 FCM 註冊 Token。');
                }
            } else {
                console.warn('通知權限被拒絕。');
            }
        } catch (error) {
            console.error('請求通知權限或獲取 Token 失敗:', error);
        }

        // 處理前景訊息
        messaging.onMessage(payload => {
            console.log('前景訊息:', payload);
            // 在前景時也顯示系統通知
            if (payload.notification) {
                const notificationTitle = payload.notification.title;
                const notificationOptions = {
                    body: payload.notification.body,
                    icon: '/assets/icons/icon-192x192.png' // 使用與 Service Worker 相同的圖示
                };

                // 檢查通知權限，如果已授予則顯示通知
                if (Notification.permission === 'granted') {
                    new Notification(notificationTitle, notificationOptions);
                } else if (Notification.permission !== 'denied') {
                    // 如果尚未決定，則請求權限
                    Notification.requestPermission().then(permission => {
                        if (permission === 'granted') {
                            new Notification(notificationTitle, notificationOptions);
                        }
                    });
                }
            }
        });
    }

    /**
     * 將 FCM Token 和使用者設定發送到後端
     * @param {string} uid - 使用者 UID
     * @param {string} fcmToken - FCM 註冊 Token
     * @param {string|null} townshipCode - 鄉鎮代碼，如果為 null 則從 Firestore 讀取
     */
    async function sendTokenAndSettingsToBackend(uid, fcmToken, townshipCode = null) {
        try {
            let finalTownshipCode = townshipCode;
            if (finalTownshipCode === null) {
                const userDocRef = db.collection('users').doc(uid);
                const doc = await userDocRef.get();
                if (doc.exists && doc.data().settings) {
                    finalTownshipCode = doc.data().settings.townshipCode;
                }
            }

            const response = await fetch('http://localhost:7800/api/fcm/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    uid: uid,
                    fcmToken: fcmToken,
                    townshipCode: finalTownshipCode // 如果有選擇鄉鎮，則發送
                }),
            });

            if (response.ok) {
                console.log('FCM Token 和設定已成功發送到後端。');
            } else {
                console.error('發送 FCM Token 和設定到後端失敗:', response.status, response.statusText);
            }
        } catch (error) {
            console.error('發送 FCM Token 和設定到後端時發生錯誤:', error);
        }
    }
});

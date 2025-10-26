/*這兩段可刪*/
document.getElementById("login-content").style.display = "none";
document.getElementById("app-content").style.display = "block";
/*   上面   */

import { COUNTY_NAME_TO_CODE, LOCATION_DATA, CODE_TO_TOWNSHIP_NAME } from '../js/location_data.js';
import { db } from './firebase.js';

// 將 messaging 變數提升到共用作用域
let messaging;

document.addEventListener('DOMContentLoaded', () => {
    const appContent = document.getElementById('app-content');
    const loginContent = document.getElementById('login-content');
    const googleLoginBtn = document.getElementById('google-login-btn');
    const errorMessageDiv = document.getElementById('error-message');

    // Firebase 登入狀態監聽器
    firebase.auth().onAuthStateChanged(user => {
        if (user) {
            console.log('使用者已登入:', user.email);
            appContent.style.display = 'block';
            loginContent.style.display = 'none';
            initializeUserSettings(user);
            initializeFCM(user);
        } else {
            console.log('使用者未登入');
            appContent.style.display = 'none';
            loginContent.style.display = 'flex';
        }
    });

    if (googleLoginBtn) {
        googleLoginBtn.addEventListener('click', signInWithGoogle);
    }

    /**
     * 使用 Google 帳號透過「懸浮視窗」進行登入
     */
    async function signInWithGoogle() {
        const auth = firebase.auth();
        const provider = new firebase.auth.GoogleAuthProvider();

        googleLoginBtn.disabled = true;
        errorMessageDiv.style.display = 'none';

        try {
            // 使用 signInWithPopup 來彈出懸浮視窗
            const result = await auth.signInWithPopup(provider);
            const user = result.user;
            console.log("Google 懸浮視窗登入成功:", user);
            
            // 登入成功後，onAuthStateChanged 會自動處理 UI 切換
            // 我們可以在這裡處理首次登入的使用者資料建立
            const userDocRef = db.collection('users').doc(user.uid);
            const doc = await userDocRef.get();

            if (!doc.exists) {
                console.log('首次登入，正在建立使用者資料...');
                await userDocRef.set({
                    displayName: user.displayName,
                    email: user.email,
                    photoURL: user.photoURL,
                    createdAt: firebase.firestore.FieldValue.serverTimestamp()
                });
                console.log('使用者資料建立成功！');
            }

        } catch (error) {
            console.error('Google 登入失敗:', error);
            errorMessageDiv.style.display = 'block';
            errorMessageDiv.textContent = `登入失敗: ${error.code} - ${error.message}`;
        } finally {
            googleLoginBtn.disabled = false;
        }
    }

    /**
     * 初始化使用者設定功能
     * @param {firebase.User} user - 當前登入的 Firebase 使用者物件
     */
    async function initializeUserSettings(user) {
        const countySelect = document.getElementById('county-select');
        const townshipSelect = document.getElementById('township-select');
        const saveSettingsBtn = document.getElementById('save-settings-btn');
        const settingsStatus = document.getElementById('settings-status');

        if (!countySelect || !townshipSelect || !saveSettingsBtn || !settingsStatus) {
            console.error('找不到使用者設定相關的 HTML 元素。');
            return;
        }

        const userDocRef = db.collection('users').doc(user.uid);

        // --- 填充選單函式 ---
        function populateCountySelect() {
            countySelect.innerHTML = '<option value="">請選擇縣市</option>';
            for (const countyName in COUNTY_NAME_TO_CODE) {
                countySelect.innerHTML += `<option value="${countyName}">${countyName}</option>`;
            }
        }

        function populateTownshipSelect(selectedCountyName) {
            townshipSelect.innerHTML = '<option value="">請選擇鄉鎮</option>';
            if (selectedCountyName && LOCATION_DATA[selectedCountyName]) {
                for (const townshipName in LOCATION_DATA[selectedCountyName]) {
                    const code = LOCATION_DATA[selectedCountyName][townshipName];
                    townshipSelect.innerHTML += `<option value="${code}">${townshipName}</option>`;
                }
            }
        }

        countySelect.addEventListener('change', () => populateTownshipSelect(countySelect.value));

        populateCountySelect();
        populateTownshipSelect(null);

        // 讀取使用者設定
        try {
            const doc = await userDocRef.get();
            if (doc.exists && doc.data().settings && doc.data().settings.townshipCode) {
                const savedTownshipCode = doc.data().settings.townshipCode;
                const fullTownshipName = CODE_TO_TOWNSHIP_NAME[savedTownshipCode];
                if (fullTownshipName) {
                    const savedCountyName = Object.keys(LOCATION_DATA).find(county => fullTownshipName.startsWith(county));
                    if (savedCountyName) {
                        countySelect.value = savedCountyName;
                        populateTownshipSelect(savedCountyName);
                        townshipSelect.value = savedTownshipCode;
                        console.log('已載入使用者預設地區代碼:', savedTownshipCode);
                    }
                }
            }
        } catch (error) {
            console.error('讀取使用者設定失敗:', error);
        }

        // 儲存使用者設定
        saveSettingsBtn.addEventListener('click', async () => {
            const selectedTownshipCode = townshipSelect.value;
            settingsStatus.textContent = '儲存中...';

            if (!selectedTownshipCode) {
                settingsStatus.textContent = '請選擇一個鄉鎮地區！';
                settingsStatus.style.color = '#ffcccc';
                return;
            }

            try {
                await userDocRef.set({
                    settings: { townshipCode: selectedTownshipCode }
                }, { merge: true });

                console.log('使用者預設地區代碼已儲存:', selectedTownshipCode);
                settingsStatus.textContent = '設定已儲存！';
                settingsStatus.style.color = 'var(--accent-2)';
                setTimeout(() => settingsStatus.textContent = '', 3000);

                // 獲取最新的 FCM Token 並發送到後端更新訂閱
                const latestToken = await messaging.getToken({ vapidKey: 'BOvUnXfY9tx_0ivPB7YGwU2fbeYaK66Gf3eLKg0NirKISO7wz8rbDZtkeNr449mabR-rahs7k5BgGaYH14Ga218' });
                if (latestToken) {
                    await sendTokenAndSettingsToBackend(user.uid, latestToken, selectedTownshipCode);
                }
            } catch (error) {
                console.error('儲存使用者設定失敗:', error);
                settingsStatus.textContent = '儲存失敗！';
                settingsStatus.style.color = '#ffcccc';
            }
        });
    }

    /**
     * 初始化 Firebase Cloud Messaging (FCM)
     * @param {firebase.User} user - 當前登入的 Firebase 使用者物件
     */
    async function initializeFCM(user) {
        // 使用提升到上層的 messaging 變數
        messaging = firebase.messaging();

        try {
            const permission = await Notification.requestPermission();
            if (permission === 'granted') {
                console.log('通知權限已授予。');
                const currentToken = await messaging.getToken({ vapidKey: 'BOvUnXfY9tx_0ivPB7YGwU2fbeYaK66Gf3eLKg0NirKISO7wz8rbDZtkeNr449mabR-rahs7k5BgGaYH14Ga218' });
                if (currentToken) {
                    console.log('FCM 註冊 Token:', currentToken);
                    // 初始載入時，發送一次 Token 到後端 (不帶鄉鎮代碼)
                    await sendTokenAndSettingsToBackend(user.uid, currentToken, null);
                } else {
                    console.log('未獲取到 FCM 註冊 Token。');
                }
            }
        } catch (error) {
            console.error('請求通知權限或獲取 Token 失敗:', error);
        }

        // --- [已修正] ---
        // 監聽前景訊息，但不再手動顯示通知
        messaging.onMessage(payload => {
            console.log('前景訊息已收到:', payload);
            // 當網頁處於前景時，我們只在主控台記錄訊息。
            // 真正的系統通知將由 Service Worker (firebase-messaging-sw.js) 統一處理。
            // 這樣可以避免重複顯示通知。
        });
    }

    /**
     * 將 FCM Token 和使用者設定發送到後端
     * @param {string} uid - 使用者 UID
     * @param {string} fcmToken - FCM 註冊 Token
     * @param {string|null} townshipCode - 鄉鎮代碼
     */
    async function sendTokenAndSettingsToBackend(uid, fcmToken, townshipCode) {
        const apiUrl = 'https://twa-api-server.cracks666666.com/api/fcm/register';

        // 加入防禦性檢查
        if (townshipCode && !/^[A-Z]{3}-\d{3}$/.test(townshipCode)) {
            console.error(`偵測到無效的 townshipCode: "${townshipCode}"。請求已中止。`);
            return;
        }

        const payload = {
            uid: uid,
            fcmToken: fcmToken,
            townshipCode: townshipCode
        };

        console.log("準備發送到後端的資料:", payload);

        try {
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            
            console.log('Fetch 請求已發送。等待伺服器回應...');

            if (response.ok) {
                const result = await response.json();
                console.log('後端成功回應:', result);
            } else {
                // 嘗試讀取錯誤訊息內文
                const errorText = await response.text();
                console.error(`發送 FCM Token 和設定到後端失敗: 狀態碼 ${response.status}`, errorText);
            }
        } catch (error) {
            console.error('發送 FCM Token 和設定到後端時發生網路錯誤:', error);
        }
    }
});


import { db } from './firebase.js';

document.addEventListener('DOMContentLoaded', () => {
    const googleLoginBtn = document.getElementById('google-login-btn');
    const errorMessageDiv = document.getElementById('error-message');

    if (googleLoginBtn) {
        googleLoginBtn.addEventListener('click', signInWithGoogle);
    }

    /**
     * 使用 Google 帳號進行登入或註冊
     */
    async function signInWithGoogle() {
        const auth = firebase.auth(); // 使用全域 firebase 物件
        const provider = new firebase.auth.GoogleAuthProvider(); // 使用全域 firebase 物件

        // 禁用按鈕以防止重複點擊
        googleLoginBtn.disabled = true;
        errorMessageDiv.style.display = 'none'; // 清除之前的錯誤訊息

        try {
            // 改用 signInWithRedirect 以提高 PWA 和行動裝置的穩定性
            await auth.signInWithRedirect(provider);
            // 注意：signInWithRedirect 不會立即返回 user 物件，
            // 而是會觸發頁面重定向，然後在重定向回來後由 onAuthStateChanged 處理登入狀態。
            // 所以這裡不需要處理 result 和 user 物件。

        } catch (error) {
            console.error('Google 登入失敗:', error);
            errorMessageDiv.style.display = 'block';
            errorMessageDiv.textContent = `登入失敗: ${error.message}`;
        } finally {
            googleLoginBtn.disabled = false; // 無論成功或失敗，都重新啟用按鈕
        }
    }
});

// 在頁面載入時檢查是否有重定向結果
firebase.auth().getRedirectResult().then(result => {
    if (result.user) {
        // 處理重定向回來的登入結果
        const user = result.user;
        console.log('Google 登入成功 (重定向):', user);

        // 這裡的邏輯與 signInWithPopup 成功後的邏輯相同
        const userDocRef = db.collection('users').doc(user.uid);
        userDocRef.get().then(doc => {
            if (!doc.exists) {
                console.log('首次登入，正在建立使用者資料...');
                userDocRef.set({
                    displayName: user.displayName,
                    email: user.email,
                    photoURL: user.photoURL,
                    createdAt: firebase.firestore.FieldValue.serverTimestamp()
                }).then(() => {
                    console.log('使用者資料建立成功！');
                    window.location.href = 'index.html';
                }).catch(error => {
                    console.error('建立使用者資料失敗:', error);
                });
            } else {
                window.location.href = 'index.html';
            }
        }).catch(error => {
            console.error('獲取使用者資料失敗:', error);
        });
    }
}).catch(error => {
    console.error('處理重定向結果失敗:', error);
    const errorMessageDiv = document.getElementById('error-message');
    if (errorMessageDiv) {
        errorMessageDiv.style.display = 'block';
        errorMessageDiv.textContent = `登入失敗: ${error.message}`;
    }
});

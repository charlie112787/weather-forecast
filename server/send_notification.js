// --- 引入必要的套件 ---
const admin = require('firebase-admin');
const readline = require('readline');

// --- 初始化 Firebase Admin SDK ---
// 請確認 serviceAccountKey.json 檔案與此檔案在同一個資料夾
try {
  const serviceAccount = require('./serviceAccountKey.json');
  admin.initializeApp({
    credential: admin.credential.cert(serviceAccount)
  });
  console.log("Firebase Admin SDK 已成功初始化。");
} catch (error) {
  console.error("初始化 Firebase Admin SDK 失敗: ", error.message);
  console.log("請確保 serviceAccountKey.json 檔案存在於同一個目錄下。");
  process.exit(1);
}


// 建立一個 readline 介面，用於讀取命令列輸入
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

/**
 * 透過 readline 提出問題並獲取使用者輸入的 Promise 版本
 * @param {string} question 要顯示的問題
 * @returns {Promise<string>} 使用者輸入的字串
 */
function askQuestion(question) {
  return new Promise(resolve => {
    rl.question(question, answer => {
      resolve(answer.trim());
    });
  });
}

/**
 * 發送訊息到指定的 Topic
 * @param {string} townshipCode 鄉鎮地區代碼, 例如 "TPE-100"
 * @param {string} title 通知的標題
 * @param {string} body 通知的內容
 */
async function sendMessageToTopic(townshipCode, title, body) {
  const topic = `weather_${townshipCode}`;

  // 這是要發送的訊息酬載 (payload)
  const message = {
    notification: {
      title: title,
      body: body,
    },
    // 您也可以在這裡加入額外的 data 欄位
    // data: {
    //   'alert_type': '大雨特報',
    //   'severity': '高'
    // },
    topic: topic,
  };

  try {
    console.log(`\n正在發送訊息到 Topic '${topic}'...`);
    // 發送訊息
    const response = await admin.messaging().send(message);
    console.log("成功發送訊息:", response);
    return true;
  } catch (error) {
    console.error("發送訊息時發生錯誤:", error);
    return false;
  }
}

/**
 * 主執行函式
 */
async function main() {
  console.log("--- 發送 FCM Topic 通知 (Node.js 版本) ---");

  const townshipCode = await askQuestion("請輸入目標鄉鎮代碼 (例如: TPE-100): ");
  if (!townshipCode) {
    console.log("鄉鎮代碼不能為空。");
    rl.close();
    return;
  }

  const notificationTitle = await askQuestion("請輸入通知標題: ");
  if (!notificationTitle) {
    console.log("通知標題不能為空。");
    rl.close();
    return;
  }

  const notificationBody = await askQuestion("請輸入通知內容: ");
  if (!notificationBody) {
    console.log("通知內容不能為空。");
    rl.close();
    return;
  }

  // 執行發送
  await sendMessageToTopic(townshipCode, notificationTitle, notificationBody);

  // 關閉 readline 介面
  rl.close();
}

// 執行主函式
main();

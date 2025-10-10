const firebaseConfig = {
  apiKey: "AIzaSyB3Q74U0IH8xe5ucUnkhzuBY9Inv26SGQc",
  authDomain: "weather-forecast-c62c3.firebaseapp.com",
  projectId: "weather-forecast-c62c3",
  storageBucket: "weather-forecast-c62c3.firebasestorage.app",
  messagingSenderId: "898186924731",
  appId: "1:898186924731:web:9bc4884ba3ca070b598f9e",
  measurementId: "G-KS86ZBCF1K"
};

// 初始化 Firebase App
firebase.initializeApp(firebaseConfig);
console.log('Firebase App initialized:', firebase.app());

// 初始化並導出 Firestore
export const db = firebase.firestore();
console.log('Firestore DB initialized:', db);

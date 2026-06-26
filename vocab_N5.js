// 檔案名稱：vocab_N5.js

// 確保全域變數存在，避免報錯
window.VOCAB_DB = window.VOCAB_DB || {};

// 建立 N5 單字庫
window.VOCAB_DB.N5 = [
    { 
        id: "N5_001", 
        kanji: "青い", 
        kana: "あおい", 
        meaning: "藍色", 
        accent: 2, 
        example: "青い空が綺麗ですね。", 
        notes: "用來形容顏色的い形容詞" 
    },
    { 
        id: "N5_002", 
        kanji: "赤い", 
        kana: "あかい", 
        meaning: "紅色", 
        accent: 0, 
        example: "赤いりんごを食べます。", 
        notes: "" 
    },
    { 
        id: "N5_003", 
        kanji: "柿", 
        kana: "かき", 
        meaning: "柿子", 
        accent: 0, 
        example: "秋は柿が美味しい季節です。", 
        notes: "注意發音不要跟牡蠣(かき [1])搞混" 
    }
    // ... 繼續往下新增
];
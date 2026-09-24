# Japanese Vocab Master — AI 系統架構與開發者指南 (read.md)

本文件是專門提供給 AI Agent、大型語言模型（LLM）或開發者深入理解本專案之全貌、架構設計、狀態機制、音訊管線與已知陷阱的技術規範手冊。

---

## 1. 專案核心定位與架構思維

* **專案類型**：純靜態單頁應用程式 (Static SPA)，離線優先 (Offline-first)，無後端伺服器 (Serverless)。
* **技術棧**：
  * **UI 框架**：React 18 (UMD，透過 `unpkg` CDN 載入)。
  * **轉譯器**：Babel Standalone (`babel.min.js`)，直接在瀏覽器端解析 `<script type="text/babel">`。
  * **樣式**：Tailwind CSS (CDN script) + FontAwesome 6 (CSS CDN)。
  * **無建置流程 (No Build Step)**：專案中沒有 `package.json`、Webpack 或 Vite，修改 `index.html` 即可立即於瀏覽器運行，必須維持此輕量特質。
* **行動端/跨平台特性**：
  * 重點優化 iOS Safari 與 iPadOS。
  * 支援加入 iPhone/iPad 主畫面（PWA 體驗、全螢幕無網址列）。

---

## 2. 目錄架構與職責劃分

```
.
├── index.html                 # 應用程式本體（包含所有 UI、狀態管理、音訊引擎與邏輯）
├── vocab_N1.js ~ vocab_N5.js  # 各級別單字資料庫 (全域物件 window.VOCAB_DB.NX)
├── audio/                     # 預先下載的 mp3 音訊檔
│   ├── {id}_ja.mp3            # 單字日文發音
│   ├── {id}_zh.mp3            # 單字中文發音
│   ├── {id}_ex_ja.mp3         # 例句日文發音
│   └── {id}_ex_zh.mp3         # 例句中文發音
├── old_wrong_pronounce_audio/ # 歷史發音校正之備份檔（僅供備查）
├── download_audio.py          # 音訊爬取/下載指令稿
├── add_vocab_NX.py            # 單字擴充/匯入維護指令稿
├── gen_vocab_ai_prompt.txt    # 產生單字庫時所使用的 Prompt 範本
├── README.md                  # 給使用者的簡易說明
└── read.md                    # 本檔案（給 AI / 開發者的系統架構規範）
```

---

## 3. 單字資料庫結構 (Schema)

各 `vocab_NX.js` 會掛載至全域 `window.VOCAB_DB` 物件，格式如下：

```javascript
window.VOCAB_DB = window.VOCAB_DB || {};
window.VOCAB_DB.N5 = [
  {
    id: "N5_001",                   // 唯一識別碼，格式為 [級別]_[序號]
    kanji: "青い",                  // 漢字表示
    kana: "あおい",                 // 假名讀音
    meaning: "藍色的，藍色",        // 中文語意
    accent: 2,                      // 音調核/重音型態 (0, 1, 2...，可選)
    example: "青い空が綺麗ですね。(藍天真漂亮。)", // 例句 (通常包含刮號中文翻譯)
    notes: "形容詞",                // 筆記/詞性/重點補充 (可選)
    categories: ["形容詞", "顏色"],  // 分類標籤陣列 (供篩選器使用)
    correct: 0,                     // 匯出時附加的累積正確次數 (可選)
    wrong: 0,                       // 匯出時附加的累積錯誤次數 (可選)
    history: [true, false]          // 近期作答軌跡 (可選)
  }
];
```

---

## 4. 本地持久化狀態 (LocalStorage & SessionStorage)

所有使用者學習進度與偏好設定均儲存於瀏覽器 `localStorage`：

| Key 名稱 | 資料型態 | 說明 |
| :--- | :--- | :--- |
| `vocabStats` | Object (`{ [wordId]: { correct: number, wrong: number, history: boolean[] } }`) | 各單字作答紀錄。`history` 最多保留近 10 次作答 (`true`/`false`)。 |
| `vocabLevels` | Array (`["N5", "N4"]`) | 目前勾選啟用的級別清單。 |
| `currentTab` | String (`'study' \| 'listening' \| 'exam_setup' \| 'exam'`) | 目前停留在哪個分頁。 |
| `vocabCategories` | Array (`["顏色", "動詞"]`) | 目前生效的類別篩選標籤清單（空陣列表示全選）。 |
| `viewedVocabIds` | Array (`string[]`) | 已學習/已瀏覽過的單字 ID 集合 (Set)。 |
| `vocabFavorites` | Array (`string[]`) | 使用者加到最愛的單字 ID 集合 (Set)。 |
| `isFavoritesMode` | Boolean (`'true' \| 'false'`) | 是否僅鎖定「我的最愛」單字進行學習或聽力。 |
| `isReviewMistakesMode`| Boolean (`'true' \| 'false'`) | 學習模式是否開啟「錯題本模式」。 |
| `hideKanji` / `hideKana` / `hideMeaning` | Boolean (`'true' \| 'false'`) | 學習模式單字卡的隱藏遮蔽開關狀態。 |
| `isRandomStudy` | Boolean (`'true' \| 'false'`) | 學習模式是隨機選題或循序下一個。 |
| `studyProgressMap` | Object (`{ [conditionKey]: wordId }`) | 學習模式進度錨點，以組合條件 Key 儲存當前位置單字的 ID。 |
| `listeningProgressMap` | Object (`{ [conditionKey]: { vocabKey, playlist, index, random, loop } }`) | 聽力模式播放進度快照。 |
| `vocabPlaybackRate` | Number (`0.5 ~ 1.5`) | 語速設定，預設 1.0。 |
| `vocabGithubToken` | String | GitHub Personal Access Token (Gist 同步用)。 |
| `vocabGistId` | String | GitHub Gist ID (Gist 同步用)。 |
| `sessionStorage: app_synced_and_reloaded` | Boolean (`'true'`) | 本次工作階段是否已完成開機同步與重整（避免重整循環）。 |

---

## 5. 音訊系統架構與 iOS Safari 生命週期

### 5.1 Web Audio API 實現
* 不使用傳統 `<audio>` 標籤，而是使用 `AudioContext` + `createBufferSource()`，搭配 `decodeAudioData()` 解碼 mp3。
* 音訊來源透過 `fetch(url)` 取得 `arrayBuffer`，包含 3 次自動 retry 機制。
* 支援自訂語速：`source.playbackRate.value = playbackRateRef.current`。

### 5.2 iOS Safari 頑固 Bug 應對策略
1. **背景/切換分頁連線失效**：iOS Safari 退到背景後，既有的 `AudioContext` 會進入損毀或中斷狀態且無法 resume。解法：監聽 `visibilitychange` 和 `pageshow`，一旦離開分頁立刻 `close()` 並設為 `null`，下次播放時由 `getAudioCtx()` 重新初始化。
2. **首次手勢啟動解鎖 (User Gesture Unlock)**：瀏覽器 Autoplay Policy 要求播放聲音必須由使用者手勢發起。解法：在進入主畫面提供遮罩與「開始學習」按鈕，觸發 `handleGlobalUnlock()` 播放一段極短靜音緩衝區，完成 Context 解鎖。

---

## 6. 各大功能模組運作邏輯

### 6.1 學習模式 (Study Mode)
* **資料來源**：`studyVocabList`
  * 基礎列表為 `activeVocabList`（依選取級別、分類標籤、我的最愛過濾）。
  * 若開啟「錯題本」，則篩選出近 10 次歷史紀錄中有錯誤的單字，並以「近 10 次錯誤次數 ➔ 有史以來總錯誤數」降序排列。
* **位置錨點 (Progress Map)**：
  * 條件鍵複合規則：`lvl:${selectedLevels}_cat:${selectedCategories}_fav:${isFavoritesMode}_err:${isReviewMistakesMode}`。
  * 記憶當前單字 `word.id`，若單字列表動態改變，透過 `findIndex(w => w.id === savedAnchorId)` 恢復位置。
* **已看過統計**：瀏覽單字卡時，自動將該 `word.id` 寫入 `viewedIds`。

### 6.2 聽力模式 (Listening Mode)
* **播放佇列生成**：
  * 一個單字依序發出：`ja (500ms)` ➔ `ja (800ms)` ➔ `zh (1000ms)` ➔ `ex_ja (1200ms)` ➔ `ex_zh (800ms)`。
* **非同步安全與競態取消**：
  * 使用 `sequenceIdRef.current` 作為序列號。當使用者切換單字、暫停或離開聽力分頁時，自增序號並呼叫 `stopCurrentAudio()`，確保所有未結清的 `setTimeout` 與音訊中途停止。

### 6.3 測驗模式 (Exam Mode)
* **測驗類型**：
  1. `standard`（選擇題）：支援遮蔽 1~2 個欄位，其餘作為題幹；產生 4 個候選選項，提交後顯示正解與其他選項的翻譯發音。
  2. `typing`（打字題）：直接以文字框輸入漢字、假名或中文。
  3. `listening`（聽力題）：自動播放題目發音，啟動 10 秒倒數。作答後等待 2 秒自動跳題，期間可點擊「暫停跳題」以便詳細查看例句或發音。
* **出題演算法 (Modes)**：
  * `random`：完全隨機洗牌。
  * `weighted`：弱點加權排序，錯誤率越高越優先出題。
  * `mistakes`：地獄錯題本（近 10 次有錯者）。
  * `favorites`：我的最愛隨機題庫。
  * `viewed`：已學習單字隨機題庫。
* **作答結算與總結**：
  * 送出每題作答時，呼叫 `updateStats(id, isCorrect)` 更新累積對錯及近 10 次軌跡，並自動納入 `viewedIds`。
  * 結束時進入 `showSummary` 畫面，將測驗單字以錯誤次數排序，並呈現 10 個紅綠圓點視覺化進度。

### 6.4 雲端同步系統 (GitHub Gist API)
* 透過 GitHub Gist 儲存單一檔案 `vocab_sync.json`。
* **安全機制**：上傳時主動遍歷 `localStorage`，排除機密的 `vocabGithubToken` 與 `vocabGistId`，確保使用者 Token 不會被寫入 Gist 內容中。
* **智慧開機比對**：點擊開機「開始學習」時，自動 fetch 雲端 Gist 比對本機差異；若不同才彈跳確認視窗詢問使用者是否覆蓋，避免無謂覆蓋或使用者不知情下的資料遺失。

---

## 7. AI 開發與維護守則 (Critical Rules for Agents)

1. **不可隨意拆分檔案或引入外部 NPM 套件**：
   此專案依賴單一 `index.html` 實現開箱即用與靜態佈署（如 GitHub Pages），請勿將代碼拆解為需 Webpack/Vite 打包的 `.jsx` 或 `.ts` 專案，除非使用者明確提出重構需求。
2. **謹慎處理 iOS Safari 音訊**：
   所有播放音訊的行為必須顧及 Web Audio API 的限制。勿將播放依賴在沒有使用者互動的非同步回調深處（首次播放必須由 click/touchstart 事件觸發 Context）。
3. **保持 LocalStorage 向後相容**：
   修改狀態鍵或資料結構時（如 `vocabStats`、`studyProgressMap`），需做好 null-check 或 fallback 防呆，避免舊使用者的 localStorage 損毀而整頁白屏。
4. **維護敏感資訊保護**：
   任何雲端備份或資料匯出功能（如 `exportData`、`syncToCloud`），絕對嚴格禁止將使用者的 GitHub Token 或 Gist ID 輸出到公開檔案中。

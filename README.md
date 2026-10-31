# Japanese Vocab Master

A lightweight, offline-first Japanese vocabulary learning and testing system. Designed for serious learners, this system completely decouples vocabulary data from the application logic, allowing users to maintain independent, modular word banks for each JLPT level (N1-N5).

## 🚀 Key Features

* **Modular Vocabulary Architecture**: Word banks are stored as separate files (`vocab_N1.js` ~ `vocab_N5.js`), making it easy to add, maintain, and back up content.
* **Dual Learning Modes**:
    * **Study Mode**: Includes text-to-speech (TTS) support, flexible masking of Kanji/Kana/Meaning fields, and detailed views for example sentences and personal notes.
    * **Exam Mode**: Offers independent field masking (up to two fields simultaneously) to prevent guessing and utilizes a weighted algorithm to prioritize challenging words.
* **Data-Driven Progress**: Automatically tracks error rates for every word and supports data export to help you monitor your learning trajectory.
* **Cross-Platform Compatibility**: Fully functional on Windows/macOS browsers and optimized for offline use on iPhone and iPad (via Safari or Home Screen installation).

## 🛠️ How to Get Started

1. **Deployment**: Host this repository using GitHub Pages, Vercel, or any preferred static web hosting service.
2. **Setup Databases**: Create `vocab_N1.js` through `vocab_N5.js` files in your root directory.
3. **Data Format**: Ensure your vocabulary files follow this JavaScript structure:
    ```javascript
    window.VOCAB_DB = window.VOCAB_DB || {};
    window.VOCAB_DB.N5 = [
        { 
            id: "N5_001", 
            kanji: "青い", kana: "あおい", meaning: "Blue", accent: 2, 
            example: "青い空が綺麗ですね。", 
            notes: "i-adjective for colors" 
        }
    ];
    ```
4. **Auto-Mount**: Upon loading the application, the system will automatically detect and load all valid `vocab_NX.js` files found in the directory.

## 📊 Backup & Synchronization
Learning progress is stored in the browser's `localStorage`.
* **Export Data**: Use the "Export Records" feature within the app to merge your latest performance data into a `vocab_exported.js` file, ensuring your progress is backed up and portable.

## 📱 Cross-Device Tips
For the best experience on iPad and iPhone, add the website to your **Home Screen**. This enables full-screen immersive mode and allows you to continue your reviews even when offline!

## 🏯 文法擴充 (v5.0)
* `grammar_DB.js`：S01~S08 情境、U01~U12 心態寶典、挖空題庫（檔頭有增補新題說明）。
* `conjugation_engine.js`：依勾選級別單字自動產生活用變化題與干擾項。
* `generate_grammar_audio.py`：`pip install edge-tts` 後執行，將文法例句批次轉成 `./audio/grammar/*.mp3`；沒有 MP3 時前端自動改用瀏覽器 TTS。
* 發音讀錯時：預設餵「含漢字原文」（保留重音與斷句），**不要整句改平假名**。用 `check_audio_whisper.py`（Whisper 聽寫比對）找出疑似讀錯的音檔，再把修正寫進 `tts_overrides.json`（`words` 詞級替換優先；`files` 整句最後手段；或在 `grammar_DB.js` 題目加選填 `ttsText`），然後直接重跑 `python generate_grammar_audio.py`（文法）與 `python download_audio.py`（單字例句）：只會重生「受 tts_overrides.json 影響」的 MP3（`audio/tts_manifest.json` 記錄各檔上次用的文字，不需要 `--force`；加 `--dry-run` 可先看清單）。`words` 以詞（形態素）邊界替換，需 `pip install fugashi unidic-lite`；單一漢字（如「日」「時」）讀法依語境而異，請勿輕易加入。單字 AI 備援已改唸 `kana`。文法例句的整句平假名由 `python generate_grammar_readings.py` 產生到 `grammar_readings.json`（可手改，改後重跑 `generate_grammar_audio.py` 會自動重生受影響的 MP3；`--check` 可檢查對齊），`words` 替換會照該句自己的平假名換。單字例句另可用 `python scan_reading_mismatch.py`（`--apply` 寫入單句專用的 `fileWords` 覆寫）比對「分析器預設讀法」與人工平假名，抓出 Whisper 抓不到的同字異讀（如 辛い つらい／からい）；報告 `reading_mismatch_report.md` 的 ⚠️ 項目多半是人工平假名打錯字，需人工確認。

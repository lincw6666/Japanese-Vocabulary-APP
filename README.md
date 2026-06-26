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
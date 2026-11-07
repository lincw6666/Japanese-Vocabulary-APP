/**
 * audio_manager.js - 離線語音包管理器 (IndexedDB + fflate)
 * 解決 GitHub Pages 部署 17,500 個檔案超時問題，並提供出門在外 0 流量純離線發音功能。
 */
(function(window) {
    'use strict';

    const DB_NAME = 'JapaneseVocabAudioDB';
    const DB_VERSION = 1;

    const PACKAGES = [
        { id: 'N5', title: 'N5 基礎語音包', desc: 'N5 全部單字與例句音訊', count: 2960, size: '24.8 MB', file: 'audio_N5.zip', prefix: 'N5_' },
        { id: 'N4', title: 'N4 初級語音包', desc: 'N4 全部單字與例句音訊', count: 4320, size: '44.7 MB', file: 'audio_N4.zip', prefix: 'N4_' },
        { id: 'N3', title: 'N3 中級語音包', desc: 'N3 全部單字與例句音訊', count: 3584, size: '38.4 MB', file: 'audio_N3.zip', prefix: 'N3_' },
        { id: 'N2', title: 'N2 中高語音包', desc: 'N2 全部單字與例句音訊', count: 2680, size: '30.9 MB', file: 'audio_N2.zip', prefix: 'N2_' },
        { id: 'N1', title: 'N1 高級語音包', desc: 'N1 全部單字與例句音訊', count: 3388, size: '39.4 MB', file: 'audio_N1.zip', prefix: 'N1_' },
        { id: 'grammar', title: '文法全單元語音包', desc: 'U01~U39 心態例句與 185 題挖空音訊', count: 463, size: '7.3 MB', file: 'audio_grammar.zip', prefix: 'grammar/' }
    ];

    let dbInstance = null;
    let dbOpenPromise = null;

    function openDB() {
        if (dbInstance) return Promise.resolve(dbInstance);
        if (dbOpenPromise) return dbOpenPromise;

        dbOpenPromise = new Promise((resolve, reject) => {
            if (!('indexedDB' in window)) {
                return reject(new Error('此瀏覽器不支援 IndexedDB'));
            }
            const req = indexedDB.open(DB_NAME, DB_VERSION);
            req.onupgradeneeded = (e) => {
                const db = e.target.result;
                if (!db.objectStoreNames.contains('audio')) {
                    db.createObjectStore('audio');
                }
                if (!db.objectStoreNames.contains('meta')) {
                    db.createObjectStore('meta', { keyPath: 'id' });
                }
            };
            req.onsuccess = (e) => {
                dbInstance = e.target.result;
                resolve(dbInstance);
            };
            req.onerror = (e) => {
                dbOpenPromise = null;
                reject(e.target.error || new Error('無法開啟 IndexedDB'));
            };
        });
        return dbOpenPromise;
    }

    function normalizeKey(url) {
        if (!url) return '';
        var k = String(url).replace(/^(\.\/|\/)?audio\//, '');
        k = k.split('?')[0].split('#')[0];
        return k;
    }

    const AudioManager = {
        PACKAGES: PACKAGES,

        normalizeKey: normalizeKey,

        getDB: openDB,

        /**
         * 依 URL 或檔案名稱自 IndexedDB 查詢音訊 ArrayBuffer
         * @param {string} url - 例如 './audio/N5_001_ja.mp3' 或 './audio/grammar/CLOZE_001.mp3'
         * @returns {Promise<ArrayBuffer|null>}
         */
        getAudioBytes: async function(url) {
            const key = normalizeKey(url);
            if (!key) return null;
            try {
                const db = await openDB();
                return new Promise((resolve) => {
                    const tx = db.transaction(['audio'], 'readonly');
                    const store = tx.objectStore('audio');
                    const req = store.get(key);
                    req.onsuccess = () => {
                        if (req.result) {
                            resolve(req.result);
                        } else {
                            // 容錯檢查：grammar/ 前綴補齊或去除
                            if (!key.startsWith('grammar/')) {
                                const gReq = store.get('grammar/' + key);
                                gReq.onsuccess = () => resolve(gReq.result || null);
                                gReq.onerror = () => resolve(null);
                            } else {
                                const subReq = store.get(key.replace(/^grammar\//, ''));
                                subReq.onsuccess = () => resolve(subReq.result || null);
                                subReq.onerror = () => resolve(null);
                            }
                        }
                    };
                    req.onerror = () => resolve(null);
                });
            } catch (e) {
                return null;
            }
        },

        /**
         * 取得所有語音包的安裝狀態
         * @returns {Promise<Object>} { N5: { installed: true, count: 2960, ... }, ... }
         */
        getInstalledPackages: async function() {
            try {
                const db = await openDB();
                return new Promise((resolve) => {
                    const tx = db.transaction(['meta'], 'readonly');
                    const store = tx.objectStore('meta');
                    const req = store.getAll();
                    req.onsuccess = () => {
                        const map = {};
                        (req.result || []).forEach(item => {
                            map[item.id] = item;
                        });
                        resolve(map);
                    };
                    req.onerror = () => resolve({});
                });
            } catch (e) {
                return {};
            }
        },

        /**
         * 下載並解壓縮安裝語音包至 IndexedDB
         * @param {string} pkgId - 'N5' | 'N4' | 'N3' | 'N2' | 'N1' | 'grammar'
         * @param {function} onProgress - 回呼函式 ({ pkgId, percent, stage, error })
         */
        installPackage: async function(pkgId, onProgress) {
            const pkg = PACKAGES.find(p => p.id === pkgId);
            if (!pkg) throw new Error('找不到指定的語音包 ID: ' + pkgId);

            if (typeof window.fflate === 'undefined') {
                throw new Error('找不到解壓縮模組 fflate，請確認 fflate.min.js 已正確載入。');
            }

            const notify = (stage, percent) => {
                if (typeof onProgress === 'function') {
                    onProgress({ pkgId: pkgId, stage: stage, percent: percent });
                }
            };

            notify('downloading', 0);

            // 1. 下載 Zip 檔案（支援串流進度回報）
            const zipUrl = './audio_packages/' + pkg.file;
            const res = await fetch(zipUrl);
            if (!res.ok) {
                throw new Error(`下載失敗 (${res.status} ${res.statusText}): ${zipUrl}`);
            }

            const contentLength = res.headers.get('content-length');
            const totalBytes = contentLength ? parseInt(contentLength, 10) : 0;
            let loadedBytes = 0;

            let zipArrayBuffer;
            if (res.body && typeof res.body.getReader === 'function') {
                const reader = res.body.getReader();
                const chunks = [];
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    chunks.push(value);
                    loadedBytes += value.length;
                    if (totalBytes > 0) {
                        const pct = Math.min(99, Math.round((loadedBytes / totalBytes) * 100));
                        notify('downloading', pct);
                    }
                }
                notify('downloading', 100);
                const allBytes = new Uint8Array(loadedBytes);
                let pos = 0;
                for (let i = 0; i < chunks.length; i++) {
                    allBytes.set(chunks[i], pos);
                    pos += chunks[i].length;
                }
                zipArrayBuffer = allBytes;
            } else {
                const buf = await res.arrayBuffer();
                zipArrayBuffer = new Uint8Array(buf);
                notify('downloading', 100);
            }

            // 2. 解壓縮（fflate）
            notify('unzipping', 0);
            const unzippedFiles = await new Promise((resolve, reject) => {
                window.fflate.unzip(zipArrayBuffer, (err, files) => {
                    if (err) reject(err);
                    else resolve(files);
                });
            });

            // 3. 批量寫入 IndexedDB
            notify('saving', 0);
            const db = await openDB();
            const entries = Object.entries(unzippedFiles);
            const totalFiles = entries.length;

            await new Promise((resolve, reject) => {
                const tx = db.transaction(['audio', 'meta'], 'readwrite');
                const audioStore = tx.objectStore('audio');
                const metaStore = tx.objectStore('meta');

                let savedCount = 0;
                for (let i = 0; i < totalFiles; i++) {
                    const filename = entries[i][0];
                    const u8 = entries[i][1];
                    if (!filename.endsWith('.mp3')) continue;

                    // 取得獨立 ArrayBuffer
                    const buffer = u8.buffer.slice(u8.byteOffset, u8.byteOffset + u8.byteLength);
                    audioStore.put(buffer, filename);
                    savedCount++;
                }

                metaStore.put({
                    id: pkgId,
                    title: pkg.title,
                    count: savedCount,
                    size: pkg.size,
                    file: pkg.file,
                    installedAt: Date.now()
                });

                tx.oncomplete = () => {
                    notify('done', 100);
                    resolve();
                };
                tx.onerror = (e) => reject(e.target.error || new Error('儲存至 IndexedDB 失敗'));
                tx.onabort = (e) => reject(e.target.error || new Error('IndexedDB 交易中斷'));
            });
        },

        /**
         * 刪除指定語音包的本機快取
         * @param {string} pkgId
         */
        deletePackage: async function(pkgId) {
            const pkg = PACKAGES.find(p => p.id === pkgId);
            if (!pkg) return;

            const db = await openDB();
            return new Promise((resolve, reject) => {
                const tx = db.transaction(['audio', 'meta'], 'readwrite');
                const audioStore = tx.objectStore('audio');
                const metaStore = tx.objectStore('meta');

                const prefix = pkg.prefix;
                const range = IDBKeyRange.bound(prefix, prefix + '\uffff');
                audioStore.delete(range);
                metaStore.delete(pkgId);

                tx.oncomplete = () => resolve();
                tx.onerror = (e) => reject(e.target.error || new Error('刪除失敗'));
            });
        },

        /**
         * 取得全域儲存統計
         */
        getStorageStats: async function() {
            try {
                const db = await openDB();
                return new Promise((resolve) => {
                    const tx = db.transaction(['audio', 'meta'], 'readonly');
                    const audioStore = tx.objectStore('audio');
                    const metaStore = tx.objectStore('meta');
                    const countReq = audioStore.count();
                    const metaReq = metaStore.getAll();

                    let totalAudioCount = 0;
                    countReq.onsuccess = () => { totalAudioCount = countReq.result || 0; };
                    tx.oncomplete = () => {
                        const installed = metaReq.result || [];
                        resolve({
                            totalAudioFiles: totalAudioCount,
                            installedCount: installed.length,
                            installedPackages: installed
                        });
                    };
                    tx.onerror = () => resolve({ totalAudioFiles: 0, installedCount: 0, installedPackages: [] });
                });
            } catch (e) {
                return { totalAudioFiles: 0, installedCount: 0, installedPackages: [] };
            }
        }
    };

    window.AudioManager = AudioManager;

})(typeof window !== 'undefined' ? window : this);

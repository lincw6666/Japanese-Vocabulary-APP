import os
import json
import re
import requests
import time

# 確保輸出目錄存在
OUTPUT_DIR = "./audio"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def download_tts(text, lang, filename):
    filepath = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(filepath):
        print(f"⏩ 已存在，略過: {filename}")
        return

    # 使用你指定的 Google TTS 參數
    url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl={lang}&client=tw-ob&q={requests.utils.quote(text)}"
    
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"✅ 成功下載: {filename}")
        else:
            print(f"❌ 下載失敗 {response.status_code}: {filename}")
    except Exception as e:
        print(f"❌ 發生錯誤: {filename} - {e}")
    
    time.sleep(0.5) # 加上延遲，避免被 Google 伺服器短暫封鎖 (Rate Limit)

def parse_and_download():
    # 讀取 JS 檔案並擷取 JSON 陣列部分
    with open('vocab_N5.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 用正則表達式把 window.VOCAB_DB.N5 = [...] 的陣列部分抓出來
    json_str = re.search(r'=\s*(\[.*\]);', content, re.DOTALL)
    if not json_str:
        print("找不到單字資料")
        return
        
    vocab_list = json.loads(json_str.group(1))

    for word in vocab_list:
        wid = word['id']
        
        # 1. 單字日文
        download_tts(word['kana'], 'ja', f"{wid}_ja.mp3")
        
        # 2. 單字中文
        download_tts(word['meaning'], 'zh-TW', f"{wid}_zh.mp3")
        
        if word.get('example'):
            # 拆解例句
            ex_ja = word['example'].split(' (')[0].strip()
            # 移除日文例句中的平假名注音 [ ]
            ex_ja_clean = re.sub(r'\[.*?\]', '', ex_ja)
            
            ex_zh = ""
            if '(' in word['example']:
                ex_zh = word['example'].split('(')[1].replace(')', '').strip()

            # 3. 例句日文
            download_tts(ex_ja_clean, 'ja', f"{wid}_ex_ja.mp3")
            
            # 4. 例句中文
            if ex_zh:
                download_tts(ex_zh, 'zh-TW', f"{wid}_ex_zh.mp3")

if __name__ == "__main__":
    print("開始同步語音資源...")
    parse_and_download()
    print("同步完成！")
import os
import glob
import json
import re
import asyncio
import requests
import edge_tts

# --- 通用設定 ---
AUDIO_DIR = "./audio"
VOICE_JA = "ja-JP-NanamiNeural"      # 日文 AI 聲優 (七海)
VOICE_ZH = "zh-TW-HsiaoChenNeural"   # 台灣中文 AI 聲優 (曉辰)

# --- 核心功能 1：生成單純的 Edge TTS 音檔 ---
async def generate_edge_tts(text, voice, output_path, desc):
    """如果檔案不存在，就使用 Edge TTS 生成音檔"""
    if not text or os.path.exists(output_path):
        return False  # 已存在或無文字，不生成

    print(f"🤖 [生成 {desc}] {text}")
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        return True
    except Exception as e:
        print(f"❌ [{desc} 生成失敗]: {e}")
        return False

# --- 核心功能 2：獲取完美日文單字發音 (真人優先 -> AI備援) ---
async def get_word_ja_audio(word_id, kanji, kana):
    output_path = f"{AUDIO_DIR}/{word_id}_ja.mp3"
    if os.path.exists(output_path):
        return False

    # 第一關：嘗試呼叫真人發音字典 API
    url = f"https://assets.languagepod101.com/dictionary/japanese/audiomp3.php?kanji={kanji}&kana={kana}"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)
        # 防呆機制：過濾查無此字的 52KB 預設錯誤音檔
        if response.status_code == 200 and len(response.content) != 52288:
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"✅ [真人發音] 單字下載成功: {kanji} ({kana})")
            return True
    except Exception as e:
        print(f"⚠️ 真人語音網路請求失敗: {e}")

    # 第二關：如果沒有真人發音，用 AI 備援
    return await generate_edge_tts(kanji, VOICE_JA, output_path, "AI 日文單字")

# --- 輔助功能：精準拆解例句 (模擬 React 的邏輯) ---
def parse_example(example_text):
    if not example_text:
        return "", ""
    
    example_ja = ""
    example_zh = ""
    
    # 擷取日文部分 (對齊 JS: split(' (')[0].replace(/\[.*?\]/g, '').trim())
    parts = example_text.split(" (")
    example_ja = re.sub(r'\[.*?\]', '', parts[0]).strip()
    
    # 擷取中文部分 (對齊 JS: split('(')[1].replace(')', '').trim())
    if "(" in example_text:
        try:
            zh_part = example_text.split("(")[1]
            example_zh = zh_part.replace(")", "").strip()
        except IndexError:
            pass
            
    return example_ja, example_zh

# --- 主程式 ---
async def main():
    if not os.path.exists(AUDIO_DIR):
        os.makedirs(AUDIO_DIR)

    js_files = glob.glob("vocab_*.js")
    if not js_files:
        print("❌ 找不到任何 vocab_*.js 檔案！")
        return

    total_words = 0
    new_files_count = 0

    for js_file in js_files:
        print(f"\n📂 正在解析: {js_file} ...")
        with open(js_file, "r", encoding="utf-8") as f:
            content = f.read()

        match = re.search(r"window\.VOCAB_DB\.[A-Za-z0-9_]+\s*=\s*(\[.*\]);?", content, re.DOTALL)
        if not match:
            continue

        try:
            vocab_list = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue

        for word in vocab_list:
            word_id = word.get("id")
            kanji = word.get("kanji")
            kana = word.get("kana")
            meaning = word.get("meaning")
            example = word.get("example")

            if not word_id or not kanji:
                continue

            total_words += 1
            added_any = False

            # 1. 處理日文單字 (_ja.mp3)
            if await get_word_ja_audio(word_id, kanji, kana):
                new_files_count += 1
                added_any = True

            # 2. 處理中文意思 (_zh.mp3)
            zh_path = f"{AUDIO_DIR}/{word_id}_zh.mp3"
            if await generate_edge_tts(meaning, VOICE_ZH, zh_path, "中文意思"):
                new_files_count += 1
                added_any = True

            # 3. 處理例句 (_ex_ja.mp3 & _ex_zh.mp3)
            if example:
                ex_ja, ex_zh = parse_example(example)
                
                ex_ja_path = f"{AUDIO_DIR}/{word_id}_ex_ja.mp3"
                if await generate_edge_tts(ex_ja, VOICE_JA, ex_ja_path, "日文例句"):
                    new_files_count += 1
                    added_any = True

                ex_zh_path = f"{AUDIO_DIR}/{word_id}_ex_zh.mp3"
                if await generate_edge_tts(ex_zh, VOICE_ZH, ex_zh_path, "中文例句"):
                    new_files_count += 1
                    added_any = True

            # 如果有下載任何檔案，暫停 0.5 秒防止被伺服器阻擋
            if added_any:
                await asyncio.sleep(0.5)

    print("-" * 40)
    print(f"🎉 執行完畢！\n掃描單字數: {total_words} 個\n新增音檔數: {new_files_count} 個")

if __name__ == "__main__":
    asyncio.run(main())
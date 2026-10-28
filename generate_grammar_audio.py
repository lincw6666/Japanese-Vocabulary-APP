#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_grammar_audio.py
把 grammar_DB.js (window.GRAMMAR_DB) 內所有日文例句 / 題目批次轉成 MP3，
存到 ./audio/grammar/ ，檔名與 grammar_DB.js 內的 audio 欄位（或自動命名規則）一致。

涵蓋內容：
  - clozeQuestions : 挖空處填入正解後的完整句子       -> CLOZE_xxx.mp3
  - scenarios      : 3-Tier 矩陣 (S01_t1~t3)、店員敬語聽力 (S01_k1~kN)
  - vaultUnits     : 各單元範例句 (U01_s{段落}_e{範例}.mp3)

用法：
  pip install edge-tts
  python generate_grammar_audio.py              # 只生成「尚未存在」的檔案
  python generate_grammar_audio.py --force      # 全部重新生成
  python generate_grammar_audio.py --only CLOZE # 只生成檔名以 CLOZE 開頭者
  python generate_grammar_audio.py --dry-run    # 只列出將生成的清單（含因 tts_overrides.json 變動而要重生的檔案）

修改 tts_overrides.json 後直接重跑即可：只會重生「受影響」的 MP3（audio/tts_manifest.json 記錄上次用的文字），
其餘不動；覆寫被移除時也會自動還原。不需要 --force。

發音讀錯時：不要整句改平假名（重音/斷句會變差），請在 tts_overrides.json 加入覆寫，
或在 grammar_DB.js 該題/例句物件加選填欄位 "ttsText"，再用 --force --only <檔名> 重新生成。
詳見 tts_common.py 與 check_audio_whisper.py（用 Whisper 自動找出疑似讀錯的音檔）。

前端 speak() 會優先播放這些 MP3；找不到時（例如新增題目還沒生成音檔、動態活用變化題）
會自動 fallback 到瀏覽器 speechSynthesis，所以沒生成也不會壞掉。
"""
import argparse
import asyncio
import json
import os
import re
import sys

try:
    import edge_tts
except ImportError:  # 讓 --dry-run 在沒裝 edge-tts 時也能跑
    edge_tts = None

from tts_common import load_overrides, resolve_tts_text, load_manifest, save_manifest, is_stale
import io

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "grammar_DB.js")
OUT_DIR = os.path.join(BASE_DIR, "audio", "grammar")
VOICE_JA = "ja-JP-NanamiNeural"   # 與 download_audio.py 相同的日文 AI 聲優
CONCURRENCY = 5
BLANK = "（  ）"


def load_db(path):
    """grammar_DB.js 的資料區是嚴格 JSON 語法：取 `window.GRAMMAR_DB = {` 到單獨一行的 `};`。"""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"window\.GRAMMAR_DB\s*=\s*\{", text)
    if not m:
        sys.exit("❌ 找不到 window.GRAMMAR_DB = { ... }")
    start = m.end() - 1
    end = text.index("\n};", start) + 2  # 包含結尾的 }
    body = text[start:end]
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        line = body.count("\n", 0, e.pos) + 1
        sys.exit("❌ grammar_DB.js 不是合法 JSON（資料區 key 要加雙引號、不可有註解/尾逗號）："
                 "約第 %d 行（資料區內）— %s" % (line, e.msg))


def clean_text(s):
    """去掉【情境說明】、括號內中文補充；把 ' / ' 並列句改成分句；移除 ～ 與 〇 等無法朗讀的符號。"""
    s = re.sub(r"【.*?】", "", s)
    s = s.replace(" / ", "。").replace("／", "。")
    s = s.replace("～", "").replace("〇〇", "").replace("〇", "")
    return s.strip()


def collect(db):
    items = {}  # 檔名 -> 日文原文（含漢字）
    tts_fields = {}  # 檔名 -> 資料內的 ttsText 欄位（選填，可覆寫發音文字）

    def put(rel_path, text, fallback_name, tts_text=None):
        name = os.path.basename(rel_path) if rel_path else fallback_name
        text = clean_text(text)
        if text:
            items[name] = text
            if tts_text:
                tts_fields[name] = clean_text(tts_text)

    for q in db.get("clozeQuestions", []):
        filled = q["sentence"].replace(BLANK, q["answer"])
        put(q.get("audio"), filled, q["id"] + ".mp3", q.get("ttsText"))

    for s in db.get("scenarios", []):
        for i, tier in enumerate(("tier1", "tier2", "tier3"), start=1):
            m = s.get("matrix", {}).get(tier)
            if m:
                put(m.get("audio"), m["ja"], "%s_t%d.mp3" % (s["id"], i), m.get("ttsText"))
        for i, k in enumerate(s.get("receptiveKeigo", []), start=1):
            put(k.get("audio"), k["ja"], "%s_k%d.mp3" % (s["id"], i), k.get("ttsText"))

    for u in db.get("vaultUnits", []):
        for si, sec in enumerate(u.get("sections", []), start=1):
            for ei, ex in enumerate(sec.get("examples", []), start=1):
                put(ex.get("audio"), ex["ja"], "%s_s%d_e%d.mp3" % (u["id"], si, ei), ex.get("ttsText"))
    return items, tts_fields


async def synth(sem, text, path, rate, manifest):
    async with sem:
        try:
            await edge_tts.Communicate(text, VOICE_JA, rate=rate).save(path)
            manifest["grammar/" + os.path.basename(path)] = text  # 記錄實際餵給 TTS 的文字（供日後只重生受影響的檔案）
            print("🤖 生成 %-28s %s" % (os.path.basename(path), text))
            return True
        except Exception as e:  # noqa
            print("❌ 失敗 %s: %s" % (os.path.basename(path), e))
            if os.path.exists(path):
                os.remove(path)
            return False


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="已存在也重新生成")
    ap.add_argument("--only", default="", help="只處理檔名以此字串開頭者，例如 CLOZE、S01、U03")
    ap.add_argument("--dry-run", action="store_true", help="只列出清單，不生成")
    ap.add_argument("--rate", default="+0%", help="edge-tts 語速，例如 -10%%（預設 +0%%；前端還有播放速度拉桿）")
    args = ap.parse_args()

    items, tts_fields = collect(load_db(DB_FILE))
    overrides = load_overrides()  # tts_overrides.json：讀錯的詞／整句覆寫成平假名
    # 實際餵給 TTS 的文字（預設＝含漢字原文，僅在有覆寫時才改）
    # grammar_readings.json（generate_grammar_readings.py 產生）：整句平假名。words 替換會照這句自己的平假名換，避免被 words 的值帶偏
    readings = {}
    rpath = os.path.join(BASE_DIR, "grammar_readings.json")
    if os.path.exists(rpath):
        readings = json.load(io.open(rpath, encoding="utf-8-sig"))
    spoken = {n: resolve_tts_text(n, t, overrides, tts_fields.get(n), readings.get(n)) for n, t in items.items()}
    manifest = load_manifest()
    # 需要生成：①檔案不存在 ②--force ③已存在但「現在要念的文字」≠「上次生成用的文字」（tts_overrides.json 有變動）
    todo, stale = {}, {}
    for n in items:
        if not n.startswith(args.only):
            continue
        exists = os.path.exists(os.path.join(OUT_DIR, n))
        if not exists or args.force:
            todo[n] = spoken[n]
        elif is_stale("grammar/" + n, items[n], spoken[n], manifest):
            todo[n] = spoken[n]
            stale[n] = (manifest.get("grammar/" + n, items[n]), spoken[n])
    print("📚 grammar_DB.js 共 %d 句，本次需生成 %d 句（其中 %d 句是 tts_overrides.json 變動造成的重生）" % (len(items), len(todo), len(stale)))
    if args.dry_run:
        for n, t in todo.items():
            if n in stale:
                print("  %-28s 🔁 %s  →  %s" % (n, stale[n][0], stale[n][1]))
            else:
                print("  %-28s %s" % (n, t))
        return
    if not todo:
        print("✅ 沒有需要生成的音檔")
        return
    if edge_tts is None:
        sys.exit("請先安裝：pip install edge-tts")
    os.makedirs(OUT_DIR, exist_ok=True)
    sem = asyncio.Semaphore(CONCURRENCY)
    results = await asyncio.gather(*[synth(sem, t, os.path.join(OUT_DIR, n), args.rate, manifest) for n, t in todo.items()])
    save_manifest(manifest)
    print("🎉 完成：成功 %d / 失敗 %d" % (sum(results), len(results) - sum(results)))


if __name__ == "__main__":
    asyncio.run(main())

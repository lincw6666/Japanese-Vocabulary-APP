#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_grammar_readings.py
為 grammar_DB.js 的「每一句文法例句」產生整句平假名，存成 grammar_readings.json（檔名 → 平假名）。

用途：
  - generate_grammar_audio.py 會用這份平假名來決定 tts_overrides.json 的 words 替換內容
    （被替換的詞照「這句話自己的平假名」換，不會被 words 裡的值帶偏），跟單字例句裡人工寫的 [..] 平假名同一套機制。
  - 這份檔案可以人工修改：改了某句的平假名，下次執行 generate_grammar_audio.py 會自動重生受影響的 MP3。

來源：fugashi + unidic-lite（整句斷詞取讀音），並修正 UniDic 已知的讀法怪癖（私→わたし、言う→いう 等）。
安裝：pip install fugashi unidic-lite

用法：
  python generate_grammar_readings.py            # 產生／補齊 grammar_readings.json（不覆蓋你手改過的句子）
  python generate_grammar_readings.py --force    # 全部重新產生（會覆蓋手改）
  python generate_grammar_readings.py --check    # 只檢查：平假名與原句對得齊嗎？與 tts_overrides.json 衝突在哪？
"""
import argparse
import io
import json
import os
import re
import sys

from tts_common import BASE_DIR

READINGS_FILE = os.path.join(BASE_DIR, "grammar_readings.json")

_KANA = re.compile(r"[ぁ-ゟァ-ヿー]+")
_HAS_KANJI = re.compile(r"[一-鿿々〆ヵヶ]")


def kata2hira(s):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


# UniDic 的「kana」欄是字典形的書寫式，少數詞跟日常讀法不同；在這裡修正。
SURFACE_FIX = {"私": "わたし", "僕": "ぼく", "貴方": "あなた", "彼女": "かのじょ", "大人": "おとな", "今日": "きょう",
               "明日": "あした", "昨日": "きのう", "一人": "ひとり", "二人": "ふたり", "友達": "ともだち", "今朝": "けさ",
               "今年": "ことし", "毎朝": "まいあさ", "景色": "けしき", "果物": "くだもの", "眼鏡": "めがね", "お母さん": "おかあさん"}


# 整句組合後才看得出來的讀法錯誤（逐詞轉換無法處理：連濁、促音便、固定搭配）
POST_FIX = {"にちようひ": "にちようび", "なんも": "なにも", "いちほうずつ": "いっぽうずつ"}


def aligned(text, reading):
    """原句裡『非漢字』的字元（假名、標點）必須依序出現在平假名裡，且平假名不可殘留漢字。"""
    r = kata2hira(re.sub(r"\s+", "", reading))
    if _HAS_KANJI.search(r):
        return False
    pos = 0
    for ch in kata2hira(text):
        if _HAS_KANJI.search(ch) or ch.isspace():
            continue
        pos = r.find(ch, pos)
        if pos < 0:
            return False
        pos += 1
    return True


def tagger():
    try:
        import fugashi
        return fugashi.Tagger()
    except Exception as e:  # noqa
        sys.exit("請先安裝：pip install fugashi unidic-lite  （%s）" % e)


def to_reading(tg, text):
    out = []
    for w in tg(text):
        s = w.surface
        f = w.feature
        kana = getattr(f, "kana", None)
        lemma = getattr(f, "lemma", "") or ""
        if s in SURFACE_FIX:
            out.append(SURFACE_FIX[s])
        elif _KANA.fullmatch(s) or not _HAS_KANJI.search(s):
            out.append(s)  # 本來就是假名／標點／數字：維持原樣
        elif kana in (None, "*"):
            out.append(s)
        elif lemma.startswith("言う") and s.startswith("言"):
            # UniDic 把「言う」的假名寫成「ユウ」；日常讀音是「いう」：只修第一個音
            r = kata2hira(kana)
            out.append("い" + r[1:] if r.startswith("ゆ") else r)
        else:
            out.append(kata2hira(kana))
    s = "".join(out)
    for a, b in POST_FIX.items():
        s = s.replace(a, b)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="全部重新產生（覆蓋手改）")
    ap.add_argument("--check", action="store_true", help="只檢查，不寫檔")
    args = ap.parse_args()

    from generate_grammar_audio import collect, load_db, DB_FILE
    items, _ = collect(load_db(DB_FILE))  # 檔名 -> 原句（已 clean）
    tg = tagger()

    old = {}
    if os.path.exists(READINGS_FILE):
        old = json.load(io.open(READINGS_FILE, encoding="utf-8-sig"))

    if args.check:
        bad_align = []
        for name, text in items.items():
            r = old.get(name)
            if not r:
                bad_align.append((name, text, "（沒有平假名）"))
                continue
            if not aligned(text, r):
                bad_align.append((name, text, r))
        print("檢查 %d 句：平假名沒對齊或殘留漢字 %d 句" % (len(items), len(bad_align)))
        for n, t, r in bad_align[:30]:
            print("  %-22s %s  ↔  %s" % (n, t, r))
        return

    new = dict(old)
    added = 0
    for name, text in items.items():
        if args.force or name not in new:
            new[name] = to_reading(tg, text)
            added += 1
    # 句子已從 DB 移除的檔名不保留
    new = {k: v for k, v in new.items() if k in items}
    io.open(READINGS_FILE, "w", encoding="utf-8").write(json.dumps(new, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    print("✅ %d 句（新增／重產 %d 句）→ %s" % (len(new), added, READINGS_FILE))


if __name__ == "__main__":
    main()

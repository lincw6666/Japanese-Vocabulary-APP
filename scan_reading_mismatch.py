#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_reading_mismatch.py
不用聽音檔、不用 Whisper：直接比對「一般讀音分析器對漢字句的讀法」與「人工寫好的整句平假名」，
找出分析器（也就是 edge-tts 這類 TTS 前端最可能照著念的預設讀法）會讀錯的詞。

為什麼有效：Whisper 聽寫出來的是漢字（例如 辛い），不管音檔實際念 つらい 還是 からい 都長一樣，
所以靠 Whisper 抓不到這類「同字不同讀」。但人工平假名（單字例句的 [..]）是正確答案，
只要分析器對某個詞的讀法與它不同，TTS 就很可能念錯。

範圍：單字例句（vocab_*.js 的 example 方括號平假名）。文法例句的平假名本身是分析器產生的，無法拿來互相驗證。

用法：
  python scan_reading_mismatch.py                 # 掃描並產生 reading_mismatch_report.md
  python scan_reading_mismatch.py --only N5       # 只掃 N5
  python scan_reading_mismatch.py --apply         # 把結果寫進 tts_overrides.json 的 fileWords（只影響該句，不影響其他句）
然後： python download_audio.py   （只會重生受影響的 MP3）

--apply 寫入的是「單句專用」覆寫：{"N5_233_ex_ja.mp3": {"辛い": "からい"}}，
該詞在這一句換成人工平假名，其他句子與其他詞完全不動，所以不會有「辛い 在別處是 つらい」的誤傷。
"""
import argparse
import glob
import io
import json
import os
import re
import sys

from tts_common import BASE_DIR, _boundary_map, _slice_reading, load_overrides, save_overrides
from generate_grammar_readings import kata2hira, SURFACE_FIX, _HAS_KANJI, tagger

REPORT = os.path.join(BASE_DIR, "reading_mismatch_report.md")
_SMALL = str.maketrans({"づ": "ず", "ぢ": "じ", "を": "お"})


def norm(s):
    """比對用：片假名→平假名、去長音符號、統一同音假名寫法。"""
    return kata2hira(s).replace("ー", "").translate(_SMALL)


import unicodedata


def strip_dakuten(s):
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if ch not in "\u3099\u309a")


def same_enough(own, ana):
    """判定『其實沒有差』：避免誤報。
    ① 去掉濁點／半濁點後相同（連濁、にっぽん/にほん 這類分析器怪癖，TTS 不會因此念錯）
    ② 一個是另一個的前綴／後綴且長度差 ≤2（對齊邊界差一兩個字造成的假落差，例如 母→は／はは）"""
    a, b = norm(own), norm(ana)
    if a == b or strip_dakuten(a) == strip_dakuten(b):
        return True
    if abs(len(a) - len(b)) <= 2 and (a.startswith(b) or b.startswith(a) or a.endswith(b) or b.endswith(a)):
        return True
    return False


def analyzer_tokens(tg, text):
    out, pos = [], 0
    for w in tg(text):
        s, f = w.surface, w.feature
        kana = getattr(f, "kana", None)
        lemma = getattr(f, "lemma", "") or ""
        if s in SURFACE_FIX:
            r = SURFACE_FIX[s]
        elif not _HAS_KANJI.search(s) or kana in (None, "*"):
            r = s
        elif lemma.startswith("言う") and s.startswith("言"):
            r = kata2hira(kana)
            r = "い" + r[1:] if r.startswith("ゆ") else r
        else:
            r = kata2hira(kana)
        out.append((s, pos, pos + len(s), r))
        pos += len(s)
    return out


def iter_vocab_examples(only=""):
    for js in sorted(glob.glob(os.path.join(BASE_DIR, "vocab_*.js"))):
        raw = io.open(js, encoding="utf-8").read()
        m = re.search(r"window\.VOCAB_DB\.[A-Za-z0-9_]+\s*=\s*(\[.*\]);?", raw, re.DOTALL)
        if not m:
            continue
        for w in json.loads(m.group(1)):
            wid, ex = w.get("id"), w.get("example")
            if not wid or not ex or not wid.startswith(only):
                continue
            ja = re.sub(r"\[.*?\]", "", ex.split(" (")[0]).strip()
            rm = re.search(r"\[(.*?)\]", ex)
            if ja and rm:
                yield wid + "_ex_ja.mp3", ja, rm.group(1).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="只掃檔名以此開頭者（例如 N5）")
    ap.add_argument("--apply", action="store_true", help="寫入 tts_overrides.json 的 fileWords")
    args = ap.parse_args()

    tg = tagger()
    found, total, unaligned = [], 0, 0
    for name, text, ref in iter_vocab_examples(args.only):
        total += 1
        bm = _boundary_map(text, ref)
        # 整句對齊是否可靠：原句每個假名（非標點）都與人工平假名精準配對，沒有被略過或亂配
        ops = bm[2]
        clean = all(ops[i] == "eq" or _HAS_KANJI.search(text[i]) or not re.search(r"[ぁ-ヿA-Za-z0-9]", text[i])
                    for i in range(len(text)))
        bad = []
        # 連續含漢字的詞合併成一組比對（詞界在漢字串內部時，單看一個詞無法確定對應哪段假名）
        groups = []
        for s, a, b, r in analyzer_tokens(tg, text):
            if not _HAS_KANJI.search(s):
                continue
            if groups and groups[-1][2] == a:
                g = groups[-1]
                groups[-1] = (g[0] + s, g[1], b, g[3] + r)
            else:
                groups.append((s, a, b, r))
        for s, a, b, r in groups:
            own = _slice_reading(bm, a, b)
            if own is None:
                unaligned += 1  # 這個詞與人工平假名對不齊（常見於複合詞跨詞界），略過不判斷
                continue
            if not same_enough(own, r.replace("にっぽん", "にほん")):
                ok = clean and 0.5 <= len(own) / max(1, len(r)) <= 2.0
                bad.append({"surface": s, "analyzer": r, "reference": own, "confident": ok})
        if bad:
            found.append({"file": name, "text": text, "reading": ref, "tokens": bad, "confident": all(t["confident"] for t in bad)})

    lines = ["# 讀音落差報告（分析器 vs 人工平假名）", "",
             "- 掃描 %d 句單字例句，**%d 句**有詞的預設讀法與人工平假名不同（對不齊而略過的詞 %d 個）。" % (total, len(found), unaligned),
             "- 其中 **%d 句**整句對齊可靠（✅，`--apply` 只套用這些）；其餘 %d 句對齊不確定（⚠️，需人工確認，可能是對齊誤差或人工平假名打錯字）。" % (sum(f["confident"] for f in found), sum(not f["confident"] for f in found)),
             "- `analyzer`＝一般分析器（TTS 最可能的預設念法）；`reference`＝人工平假名（正確答案）。",
             "- 套用方式：`--apply` 寫入單句專用覆寫，只改該句該詞，不影響其他句。", ""]
    for f in found:
        lines.append("- %s `%s` %s　" % ("✅" if f["confident"] else "⚠️", f["file"], f["text"]) + "；".join("**%s** 預設「%s」→ 應為「%s」" % (t["surface"], t["analyzer"], t["reference"]) for t in f["tokens"]))
    io.open(REPORT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("掃描 %d 句：讀音落差 %d 句（對不齊略過 %d 詞）→ %s" % (total, len(found), unaligned, REPORT))

    if args.apply and found:
        ov = load_overrides()
        fw = ov.setdefault("fileWords", {})
        n = 0
        for f in found:
            if not f["confident"]:
                continue
            d = fw.setdefault(f["file"], {})
            for t in f["tokens"]:
                if d.get(t["surface"]) != t["reference"]:
                    d[t["surface"]] = t["reference"]
                    n += 1
        save_overrides(ov)
        print("✍️  已寫入 %d 筆單句覆寫到 tts_overrides.json 的 fileWords；接著執行 python download_audio.py 重生受影響的 MP3" % n)


if __name__ == "__main__":
    main()

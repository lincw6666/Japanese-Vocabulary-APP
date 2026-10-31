#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tts_common.py
所有 edge-tts 音檔生成腳本共用的「發音文字覆寫」邏輯。

為什麼需要：edge-tts 偶爾會讀錯漢字（今日、辛い、一日…）。整句改成純平假名會讓重音與斷句變差，
所以預設仍餵「含漢字的原文」，只有「確認讀錯」的地方才覆寫成平假名。

覆寫來源（優先序高 → 低），都寫在 tts_overrides.json：
  1. "files"  : { "CLOZE_001.mp3": "きょうは あめです" }   整句直接指定（檔名為 key）
  2. 資料內的 ttsText 欄位（grammar_DB.js 題目/例句物件上可選填）
  2.5 "fileWords": { "N5_233_ex_ja.mp3": { "辛い": "からい" } }   單句專用的詞替換（只改該檔）
  3. "words"  : { "今日": "きょう", "辛い": "からい" }       全域「詞 → 假名」替換（只替換出現處）
  4. 原文

tts_overrides.json 範例：
{
  "words": { "今日": "きょう" },
  "files": { "N5_001_ex_ja.mp3": "わたしは がっこうへ いきます" }
}
"""
import difflib
import json
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OVERRIDE_FILE = os.path.join(BASE_DIR, "tts_overrides.json")
MANIFEST_FILE = os.path.join(BASE_DIR, "audio", "tts_manifest.json")


def load_overrides(path=OVERRIDE_FILE):
    data = {"words": {}, "files": {}, "fileWords": {}}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8-sig") as f:  # utf-8-sig：容許記事本存檔產生的 BOM
            raw = json.load(f)
        data["words"].update(raw.get("words", {}))
        data["files"].update(raw.get("files", {}))
        data["fileWords"].update(raw.get("fileWords", {}))
    return data


def save_overrides(data, path=OVERRIDE_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def resolve_tts_text(filename, text, overrides, tts_text=None, reading=None):
    """依優先序決定實際餵給 TTS 的文字。reading＝人工寫好的整句平假名（單字例句的 [..]），有的話 words 替換優先採用它。"""
    files = overrides.get("files", {})
    if filename in files and files[filename]:
        return files[filename]
    if tts_text:
        return tts_text
    # 單句專用的詞替換（fileWords）：{"N5_233_ex_ja.mp3": {"辛い": "からい"}} 只影響該檔，不影響其他句
    fw = overrides.get("fileWords", {}).get(filename)
    if fw:
        text = _replace_words(text, fw, reading)
    return _replace_words(text, overrides.get("words", {}), reading)


_TAGGER = None
_RX_CACHE = {}


def _get_tagger():
    global _TAGGER
    if _TAGGER is None:
        try:
            import fugashi
            _TAGGER = fugashi.Tagger()
        except Exception:  # noqa
            _TAGGER = False
    return _TAGGER


def _replace_words(text, words, reading=None):
    """
    詞級替換（words）。
    ★ 以「詞（形態素）邊界」為單位比對，不是單純字串取代：
       例如 "日": "ひ" 只會取代獨立的「日」，不會把「日曜日」「昨日」變成「ひ曜ひ」「昨ひ」。
    連續多個詞組成的 key（例如 "お巡り"）也能比對，長的優先。
    ★ 若有 reading（單字例句裡人工寫好的平假名，例如「彼の言う通り [かれの いう とおり]」），
       被替換的詞會「照那句話自己的平假名」換（把漢字句與平假名句對齊），所以「言う」會保持「いう」，
       不會被分析器的讀法（ゆう）或 words 的值帶偏；對不齊時才退回 words 裡的值。
    沒安裝 fugashi 時退回字串取代（有誤傷風險，會警告一次）：pip install fugashi unidic-lite
    """
    if not words:
        return text
    # 效能：先用一個合併的 regex 快速判斷「文字裡有沒有任何 key」，沒有就免斷詞（單字庫數千句時差很多）
    sig = frozenset(words)  # 以 key 集合作為快取鍵（不可用 id()：不同 dict 可能重用同一個 id）
    if _RX_CACHE.get("sig") != sig:
        _RX_CACHE["sig"] = sig
        _RX_CACHE["rx"] = re.compile("|".join(re.escape(k) for k in sorted(words, key=len, reverse=True)))
    if not _RX_CACHE["rx"].search(text):
        return text
    tagger = _get_tagger()
    if tagger:
        toks = [(w.white_space or "") + w.surface for w in tagger(text)]
        if "".join(toks) == text:
            keys = sorted(words, key=len, reverse=True)
            bmap = _boundary_map(text, reading) if reading else None
            offs = [0]
            for t in toks:
                offs.append(offs[-1] + len(t))
            out, i = [], 0
            while i < len(toks):
                hit = None
                for k in keys:
                    acc, j = "", i
                    while j < len(toks) and len(acc) < len(k):
                        acc += toks[j].lstrip()
                        j += 1
                    if acc == k:
                        hit = (k, j)
                        break
                if hit:
                    lead = toks[i][:len(toks[i]) - len(toks[i].lstrip())]
                    rep = words[hit[0]]
                    if bmap:
                        own = _slice_reading(bmap, offs[i] + len(lead), offs[hit[1]])
                        if own:
                            rep = own
                    out.append(lead + rep)
                    i = hit[1]
                else:
                    out.append(toks[i])
                    i += 1
            return "".join(out)
    else:
        global _WARNED
        if not _WARNED:
            _WARNED = True
            print("⚠️ 未安裝 fugashi，words 覆寫改用字串取代（可能誤傷其他詞）：pip install fugashi unidic-lite")
    for surface in sorted(words, key=len, reverse=True):
        text = text.replace(surface, words[surface])
    return text


_WARNED = False

_KANA_ONLY = re.compile(r"[ぁ-ゟァ-ヿー]+")


_PUNCT_CH = re.compile(r"[、。，．,.!！?？「」『』（）()\[\]【】・…~〜:：;；\"'“”‘’\-－―]")
_KANJI_CH = re.compile(r"[一-鿿々〆ヵヶ]")
# 一個漢字對應 k 個假名的成本（偏好 1～3 個）
_KANJI_COST = {1: 0.6, 2: 0.0, 3: 0.3, 4: 0.8, 5: 1.3, 6: 1.9}


def _boundary_map(text, reading):
    """
    把漢字句與人工平假名句做動態規劃對齊（取代單純的 difflib：difflib 遇到重複假名會錨到錯的位置，
    例如把「友達と」的 と 對到「ともだち」的 と）。
    規則：非漢字字元（假名、標點、數字）優先與同一個假名配對；一個漢字可對應 1～6 個假名（偏好 2 個）；
    句中多餘的假名／標點有小額代價，可略過。
    回傳 (去空白的 reading, R)：R[k]＝text 第 k 個字元邊界對應的 reading 位置。
    """
    reading = re.sub(r"\s+", "", reading)
    n, m = len(text), len(reading)
    kata2hira = {c: chr(ord(c) - 0x60) for c in map(chr, range(0x30A1, 0x30F7))}
    tr = str.maketrans(kata2hira)
    nt, nr = text.translate(tr), reading.translate(tr)
    INF = float("inf")
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    bp = [[None] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0

    def relax(i, j, cost, frm):
        if cost < dp[i][j]:
            dp[i][j] = cost
            bp[i][j] = frm

    for i in range(n + 1):
        for j in range(m + 1):
            d = dp[i][j]
            if d == INF:
                continue
            if j < m:  # reading 多出來的字元：標點便宜，假名昂貴（假名應該盡量被漢字／假名吃掉）
                relax(i, j + 1, d + (0.3 if _PUNCT_CH.match(nr[j]) else 2.5), (i, j, "ins"))
            if i < n:
                if _KANJI_CH.match(text[i]):
                    for k, cost in _KANJI_COST.items():
                        if j + k <= m:
                            relax(i + 1, j + k, d + cost, (i, j, "kan"))
                    relax(i + 1, j, d + 3.0, (i, j, "kan0"))
                else:
                    if j < m and nt[i] == nr[j]:
                        relax(i + 1, j + 1, d, (i, j, "eq"))
                    elif j < m:
                        relax(i + 1, j + 1, d + 5.0, (i, j, "sub"))
                    # 原句的假名／標點在 reading 找不到：標點便宜，假名非常昂貴（假名是最可靠的錨點）
                    relax(i + 1, j, d + (0.3 if _PUNCT_CH.match(text[i]) else 4.0), (i, j, "skip"))
    R = [None] * (n + 1)
    R[n] = m
    ops = [None] * n  # 每個原句字元是被怎麼處理的：eq＝與假名精準配對（可靠錨點）、kan＝漢字吃掉 k 個假名…
    i, j = n, m
    while (i, j) != (0, 0):
        pi, pj, op = bp[i][j]
        if op != "ins":
            R[pi] = pj  # 處理第 pi 個字元之前的 reading 位置
            ops[pi] = op
        i, j = pi, pj
    return reading, R, ops


def _slice_reading(bmap, a, b):
    """text[a:b] 對應的人工平假名；兩端對不齊、或結果不是純假名時回傳 None（呼叫端退回 words 的值）。"""
    reading, R, ops = bmap
    # 兩端必須緊貼「可靠錨點」（前一個字元／後一個字元是與假名精準配對的假名或標點），否則邊界不可信
    def anchored(k):
        return k < 0 or k >= len(ops) or ops[k] == "eq" or (ops[k] == "skip" and _PUNCT_CH.match("") is None and False)
    if not (anchored(a - 1) and anchored(b)):
        return None
    if a >= len(R) or b >= len(R) or R[a] is None or R[b] is None or R[b] <= R[a]:
        return None
    seg = reading[R[a]:R[b]]
    if not _KANA_ONLY.fullmatch(seg) or len(seg) > 4 * (b - a):  # 長度明顯不合理＝對齊失敗
        return None
    return seg


# ---------------------------------------------------------------------------
# 音檔清單 (manifest)：記錄「每個 MP3 上次實際餵給 TTS 的文字」。
# 之後修改 tts_overrides.json 時，只要『現在要念的文字』≠『上次生成用的文字』就重新生成，
# 沒受影響的 MP3 完全不動；移除覆寫時也會自動還原成原文版本。
# 沒有紀錄的舊音檔視為「用原文生成」。key 例：grammar/CLOZE_001.mp3、vocab/N5_001_ex_ja.mp3
# ---------------------------------------------------------------------------
def load_manifest(path=MANIFEST_FILE):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return {}


def save_manifest(manifest, path=MANIFEST_FILE):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


def is_stale(key, original, spoken, manifest):
    """已存在的音檔是否需要重新生成：上次用的文字（無紀錄＝原文）與現在要念的文字不同。"""
    return manifest.get(key, original) != spoken

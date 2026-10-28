#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_audio_whisper.py
用 Whisper 把「已生成的 MP3」聽寫回文字，和「原本應該念的句子」逐詞對齊比對讀音（不看整句平均相似度，
長句裡錯一個音也抓得到），
自動列出疑似被 edge-tts 讀錯的音檔，並產生可直接貼進 tts_overrides.json 的修正建議。
這樣不用把數百個音檔逐一人工聽完。

安裝（一次性）：
  pip install faster-whisper fugashi unidic-lite

用法：
  python check_audio_whisper.py                          # 檢查全部（文法例句 + 單字例句，較久）
  python check_audio_whisper.py --source grammar         # 只查 audio/grammar/
  python check_audio_whisper.py --source vocab           # 只查單字/例句 audio/*.mp3
  python check_audio_whisper.py --only CLOZE_0           # 只查檔名以此開頭者
  python check_audio_whisper.py --limit 20               # 只查前 20 個（試跑）
  python check_audio_whisper.py --model small --strict   # 嚴格：連低信心差異也算失敗
  python check_audio_whisper.py --apply                  # 把「詞級建議」自動寫入 tts_overrides.json

輸出：
  tts_qa_report.md    疑似讀錯清單（預期 / 聽到 / 相似度 / 建議覆寫）
  tts_qa_cache.json   聽寫快取（重跑不會重複辨識已檢查過的檔案；音檔改過會自動重查）

修正流程：
  1. 看 tts_qa_report.md，用耳朵確認真的讀錯（Whisper 也可能聽錯，所以只當「候選名單」）
  2. 把建議貼進 tts_overrides.json（或加 --apply）
  3. python generate_grammar_audio.py --force --only <檔名>   （單字例句用 download_audio.py 先刪除舊檔）
  4. 再跑一次本腳本確認相似度回升

注意：Whisper 有語言模型，偶爾會把讀錯的句子「自動修正成通順的字」而漏報；
      因此 0 筆警告不代表 100% 正確，只代表沒有明顯錯誤。
"""
import argparse
import difflib
import glob
import hashlib
import io
import json
import os
import re
import sys

from tts_common import BASE_DIR, load_overrides, save_overrides

AUDIO_DIR = os.path.join(BASE_DIR, "audio")
GRAMMAR_AUDIO_DIR = os.path.join(AUDIO_DIR, "grammar")
CACHE_FILE = os.path.join(BASE_DIR, "tts_qa_cache.json")
REPORT_FILE = os.path.join(BASE_DIR, "tts_qa_report.md")

_PUNCT = re.compile(r"[\s、。，,.!！?？「」『』（）()\[\]【】〜～…・:：;；\"'“”‘’\-ー−]+")


def _tagger():
    try:
        import fugashi
        return fugashi.Tagger()
    except Exception as e:  # noqa
        sys.exit("請先安裝：pip install fugashi unidic-lite  （%s）" % e)


def kata_to_hira(s):
    return "".join(chr(ord(ch) - 0x60) if "ァ" <= ch <= "ヶ" else ch for ch in s)


_NORM_MAP = str.maketrans({"ヲ": "オ", "ヅ": "ズ", "ヂ": "ジ", "ヴ": "ブ", "ァ": "ア", "ィ": "イ", "ゥ": "ウ", "ェ": "エ", "ォ": "オ"})
_PARTICLE_ALIAS = {("ハ", "ワ"), ("ワ", "ハ"), ("ヘ", "エ"), ("エ", "ヘ")}
LOW_POS = ("助詞", "補助記号")  # 助詞等的單音差異多半是 Whisper 聽寫習慣，只列低信心


def normalize_pron(s):
    """去標點、去長音符號、統一幾組同音寫法，降低『寫法不同但唸法相同』的誤報。"""
    s = _PUNCT.sub("", s).replace("ー", "")
    return s.translate(_NORM_MAP)


class Reader:
    """文字 -> 發音(片假名)。預期文字與 Whisper 聽寫結果都走同一個分析器，讓差異只來自『讀法不同』。"""

    def __init__(self):
        self.tagger = _tagger()

    def tokens(self, text):
        out = []
        for w in self.tagger(text):
            f = w.feature
            pron = getattr(f, "pron", None) or getattr(f, "kana", None) or w.surface
            kana = getattr(f, "kana", None) or pron
            pos1 = getattr(f, "pos1", "") or ""
            if pron in (None, "*"):
                pron = w.surface
            if kana in (None, "*"):
                kana = pron
            out.append({"surface": w.surface, "pron": pron, "kana": kana, "pos1": pos1})
        return out

    def pron(self, text):
        return "".join(t["norm"] for t in self.spans(text)[0])

    def spans(self, text):
        """回傳 ([{surface,pos1,norm,start,end}], 整句正規化發音)。start/end 為該詞在整句發音中的字元範圍。"""
        out, pos = [], 0
        for t in self.tokens(text):
            n = normalize_pron(t["pron"])
            if not n:  # 標點等無發音的詞略過
                continue
            out.append({"surface": t["surface"], "pos1": t["pos1"], "norm": n, "start": pos, "end": pos + len(n)})
            pos += len(n)
        return out, "".join(x["norm"] for x in out)

    def hira(self, text):
        return kata_to_hira("".join(t["kana"] for t in self.tokens(text)))


def collect_items(source, only):
    """回傳 [(相對路徑, 預期文字)]"""
    items = []
    if source in ("grammar", "all"):
        from generate_grammar_audio import collect, load_db, DB_FILE
        g_items, _ = collect(load_db(DB_FILE))
        for name, text in g_items.items():
            items.append((os.path.join("grammar", name), text))
    if source in ("vocab", "all"):
        for js in sorted(glob.glob(os.path.join(BASE_DIR, "vocab_*.js"))):
            raw = io.open(js, encoding="utf-8").read()
            m = re.search(r"window\.VOCAB_DB\.[A-Za-z0-9_]+\s*=\s*(\[.*\]);?", raw, re.DOTALL)
            if not m:
                continue
            try:
                words = json.loads(m.group(1))
            except json.JSONDecodeError:
                continue
            for w in words:
                wid = w.get("id")
                if not wid:
                    continue
                if w.get("kana") or w.get("kanji"):
                    items.append((wid + "_ja.mp3", w.get("kana") or w.get("kanji")))
                ex = w.get("example")
                if ex:
                    ja = re.sub(r"\[.*?\]", "", ex.split(" (")[0]).strip()
                    if ja:
                        items.append((wid + "_ex_ja.mp3", ja))
    items = [(p, t) for p, t in items if os.path.basename(p).startswith(only)]
    return [(p, t) for p, t in items if os.path.exists(os.path.join(AUDIO_DIR, p))]


def file_sig(path):
    st = os.stat(path)
    return "%d-%d" % (st.st_size, int(st.st_mtime))


def clean_expected(text):
    text = re.sub(r"【.*?】", "", text)
    return text.replace(" / ", "。").replace("／", "。").replace("～", "").replace("〇", "").strip()


def analyze(reader, expected, heard):
    """
    逐詞對齊分析（與句子長度無關）：
      - 用 SequenceMatcher 對齊「預期發音」與「聽到發音」，取出每一段不一致（replace/delete/insert）。
      - 每段不一致對應到預期句中被它覆蓋的「詞」。
      - HIGH（高信心，視為讀錯）：不一致落在『非助詞』的詞內（該詞發音不完整，含詞中插入）。
      - LOW（低信心，只列報告）：不一致只落在助詞／標點，或是插在詞與詞的邊界（常見於 Whisper 補字／漏字）。
    """
    spans, exp_p = reader.spans(expected)
    heard_p = reader.pron(heard)
    sm = difflib.SequenceMatcher(None, exp_p, heard_p, autojunk=False)
    high, low, diffs = {}, [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        # 分析器對「句首／單獨出現的假名は・へ」會誤判成助詞而讀成ワ／エ，屬於聽寫端的假警報，略過
        if tag == "replace" and (exp_p[i1:i2], heard_p[j1:j2]) in _PARTICLE_ALIAS:
            continue
        size = max(i2 - i1, j2 - j1)
        diffs.append({"exp": exp_p[i1:i2], "heard": heard_p[j1:j2], "size": size})
        if tag == "insert":
            hit = [s for s in spans if s["start"] < i1 < s["end"]]  # 插在詞「中間」才算該詞出錯
        else:
            hit = [s for s in spans if s["start"] < i2 and i1 < s["end"]]
        content = [s for s in hit if s["pos1"] not in LOW_POS]
        if content:
            for s in content:
                key = (s["surface"], s["start"])
                high[key] = high.get(key, 0) + size
        else:
            low.append({"exp": exp_p[i1:i2], "heard": heard_p[j1:j2], "size": size,
                        "where": "".join(s["surface"] for s in hit) or "（詞與詞之間）"})
    ratio = sm.ratio() if exp_p else 1.0
    return {"exp_pron": exp_p, "heard_pron": heard_p, "ratio": ratio, "diffs": diffs,
            "high": [{"surface": k[0], "err": v} for k, v in sorted(high.items(), key=lambda kv: kv[0][1])],
            "low": low, "high_err": sum(high.values()), "low_err": sum(x["size"] for x in low)}


def suggest_words(reader, bad_words):
    """詞級建議：把出問題的詞改成平假名（已是純假名的詞略過）。"""
    sug = {}
    for w in bad_words:
        if re.fullmatch(r"[ぁ-んァ-ヶー]+", w):
            continue
        sug[w] = reader.hira(w)
    return sug


def main():
    ap = argparse.ArgumentParser(description="用 Whisper 檢查 edge-tts 音檔是否讀錯（逐詞對齊，不受句長稀釋）")
    ap.add_argument("--source", choices=["grammar", "vocab", "all"], default="all")
    ap.add_argument("--only", default="", help="只檢查檔名以此開頭者")
    ap.add_argument("--limit", type=int, default=0, help="最多檢查幾個（0=不限）")
    ap.add_argument("--model", default="small", help="Whisper 模型：tiny/base/small/medium/large-v3（越大越準越慢）")
    ap.add_argument("--threshold", type=float, default=0.6,
                    help="整句相似度低於此值一律視為失敗（兜底：整句幾乎對不上，預設 0.6）")
    ap.add_argument("--strict", action="store_true", help="嚴格模式：低信心差異（助詞、詞邊界的單音差）也算失敗")
    ap.add_argument("--device", default="cpu", help="cpu 或 cuda")
    ap.add_argument("--apply", action="store_true", help="把詞級建議寫入 tts_overrides.json 的 words")
    ap.add_argument("--no-cache", action="store_true", help="忽略快取，全部重新聽寫")
    args = ap.parse_args()

    items = collect_items(args.source, args.only)
    if args.limit:
        items = items[:args.limit]
    if not items:
        sys.exit("沒有找到可檢查的音檔（請先生成 MP3）")
    print("🔎 將檢查 %d 個音檔（模型 %s）" % (len(items), args.model))

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("請先安裝：pip install faster-whisper")
    model = WhisperModel(args.model, device=args.device, compute_type="int8" if args.device == "cpu" else "float16")
    reader = Reader()

    cache = {}
    if os.path.exists(CACHE_FILE) and not args.no_cache:
        cache = json.load(io.open(CACHE_FILE, encoding="utf-8"))

    results = []
    for i, (rel, text) in enumerate(items, start=1):
        path = os.path.join(AUDIO_DIR, rel)
        sig = file_sig(path)
        key = rel.replace("\\", "/")
        ent = cache.get(key)
        if ent and ent.get("sig") == sig and ent.get("model") == args.model:
            heard = ent["heard"]
        else:
            segs, _ = model.transcribe(path, language="ja", beam_size=5, vad_filter=False,
                                       condition_on_previous_text=False)
            heard = "".join(s.text for s in segs).strip()
            cache[key] = {"sig": sig, "model": args.model, "heard": heard}
        expected = clean_expected(text)
        a = analyze(reader, expected, heard)
        garbage = a["ratio"] < args.threshold
        fail = bool(a["high"]) or garbage or (args.strict and bool(a["low"]))
        level = "high" if (a["high"] or garbage) else ("low" if a["low"] else "ok")
        r = {"file": key, "expected": expected, "heard": heard, "fail": fail, "level": level, "garbage": garbage}
        r.update(a)
        results.append(r)
        icon = "⚠️ " if fail else ("🔸" if level == "low" else "✅")
        detail = ""
        if fail:
            detail = "| 錯詞:%s 預期:%s 聽到:%s" % ("、".join(h["surface"] for h in a["high"]) or "（整句不符）", expected, heard)
        elif level == "low":
            detail = "| 低信心差異 %d 處（不計入失敗）" % len(a["low"])
        print("%s [%3d/%d] %-26s 錯誤音數 %d  相似度 %.2f %s" % (icon, i, len(items), os.path.basename(rel),
                                                           a["high_err"], a["ratio"], detail))
        if i % 20 == 0:
            io.open(CACHE_FILE, "w", encoding="utf-8").write(json.dumps(cache, ensure_ascii=False, indent=1))
    io.open(CACHE_FILE, "w", encoding="utf-8").write(json.dumps(cache, ensure_ascii=False, indent=1))

    bad = sorted([r for r in results if r["fail"]], key=lambda r: (-r["high_err"], r["ratio"]))
    lows = [r for r in results if r["level"] == "low" and not r["fail"]]
    overrides = load_overrides()
    words_sug, files_sug = {}, {}
    lines = ["# edge-tts 發音檢查報告", "",
             "- 檢查 %d 個音檔：**疑似讀錯 %d**、低信心 %d（模型 %s）" % (len(results), len(bad), len(lows), args.model),
             "- 判定方式：逐詞對齊，與句子長短無關；詞內只要有音對不上就報（高信心）。助詞／詞邊界的單音差異只列低信心。",
             "- Whisper 只是輔助，請用耳朵確認後再套用覆寫。", ""]
    for r in bad:
        sug = suggest_words(reader, [h["surface"] for h in r["high"]])
        words_sug.update({k: v for k, v in sug.items() if k not in overrides["words"]})
        files_sug[os.path.basename(r["file"])] = reader.hira(r["expected"])
        lines += ["## `%s`（錯誤音數 %d／整句相似度 %.2f）" % (r["file"], r["high_err"], r["ratio"]), "",
                  "- 預期：%s" % r["expected"], "- 聽到：%s" % r["heard"],
                  "- 預期發音：`%s`" % r["exp_pron"], "- 聽到發音：`%s`" % r["heard_pron"],
                  "- 出錯的詞：%s" % ("、".join("`%s`(%d)" % (h["surface"], h["err"]) for h in r["high"]) or "（整句幾乎對不上）"),
                  "- 差異：%s" % "；".join("%s→%s" % (d["exp"] or "∅", d["heard"] or "∅") for d in r["diffs"]),
                  "- 詞級建議：`%s`" % (json.dumps(sug, ensure_ascii=False) if sug else "（無）"), ""]
    if bad:
        lines += ["---", "## 可貼進 tts_overrides.json 的建議", "", "```json",
                  json.dumps({"words": words_sug, "files(整句平假名，最後手段)": files_sug}, ensure_ascii=False, indent=2),
                  "```", "",
                  "建議優先用 `words`（只替換出問題的詞，保留漢字語境）；`files` 整句平假名會讓重音/斷句變差，僅作最後手段。", ""]
    if lows:
        lines += ["---", "## 低信心（不計入失敗；可抽查）", ""]
        for r in lows:
            lines.append("- `%s`：%s" % (r["file"], "；".join("%s→%s @%s" % (d["exp"] or "∅", d["heard"] or "∅", d["where"]) for d in r["low"])))
        lines.append("")
    io.open(REPORT_FILE, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n📄 報告：%s（疑似讀錯 %d、低信心 %d / 共 %d）" % (REPORT_FILE, len(bad), len(lows), len(results)))

    if args.apply and words_sug:
        # 單一漢字（如「日」「降」）讀法依語境而異，自動套用風險高：只提示，請手動確認後再加入
        risky = {k: v for k, v in words_sug.items() if re.fullmatch(r"[一-鿿々]", k)}
        for k in risky:
            words_sug.pop(k)
        if risky:
            print("⚠️ 以下單一漢字不自動寫入（讀法依語境而異，請手動確認）：%s" % json.dumps(risky, ensure_ascii=False))
        overrides["words"].update(words_sug)
        save_overrides(overrides)
        print("✍️  已把 %d 個詞級建議寫入 tts_overrides.json；請重新生成對應音檔：" % len(words_sug))
        print("    python generate_grammar_audio.py --force --only <檔名>")


if __name__ == "__main__":
    main()

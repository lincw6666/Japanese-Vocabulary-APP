#!/usr/bin/env python3
"""一次性預先合成「活用變化題」的語音並存入 audio_cache/（與 serve_local.py 共用快取）。
用法：uv run --with edge-tts python3 precache_tts.py [--levels N5 N4 ...] [--limit N] [--delay 0.5] [--workers 2] [--dry-run]
防封鎖設計：低併發（預設 2）＋每次請求後隨機延遲＋失敗指數退避＋連續失敗自動中止；可隨時 Ctrl+C，重跑會自動續傳。"""
import argparse, asyncio, random, subprocess, sys, os
import edge_tts
from serve_local import VOICE, cache_path

JSC = "/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc"

def load_texts(levels):
    out = subprocess.run([JSC, "dump_conj_texts.js"], capture_output=True, text=True, check=True).stdout
    items = []
    for line in out.splitlines():
        if "\t" in line:
            lvl, t = line.split("\t", 1)
            if not levels or lvl in levels:
                items.append(t)
    return items

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", nargs="*", default=[])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.5, help="每次請求後的基本延遲秒數（實際為 0.5~1.5 倍隨機）")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--max-fail", type=int, default=8, help="連續失敗幾次就中止")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    texts = load_texts(a.levels)
    todo = [t for t in texts if not os.path.exists(cache_path(t))]
    if a.limit: todo = todo[:a.limit]
    print("共 %d 句，已快取 %d，本次需合成 %d（約 %.0f 分鐘）" % (len(texts), len(texts) - len([t for t in texts if not os.path.exists(cache_path(t))]), len(todo), len(todo) * (a.delay + 0.6) / max(a.workers, 1) / 60))
    if a.dry_run or not todo: return
    q = asyncio.Queue()
    for t in todo: q.put_nowait(t)
    st = {"ok": 0, "fail": 0, "streak": 0, "abort": False}
    async def worker():
        while not st["abort"]:
            try: t = q.get_nowait()
            except asyncio.QueueEmpty: return
            f = cache_path(t)
            for attempt in range(3):
                try:
                    await edge_tts.Communicate(t, VOICE).save(f + ".tmp")
                    os.replace(f + ".tmp", f)
                    st["ok"] += 1; st["streak"] = 0
                    break
                except Exception as e:
                    if os.path.exists(f + ".tmp"): os.remove(f + ".tmp")
                    st["streak"] += 1
                    if st["streak"] >= a.max_fail:
                        st["abort"] = True
                        print("❌ 連續失敗 %d 次，疑似被限流/封鎖，已中止（%s）。請稍後再重跑續傳。" % (st["streak"], e)); return
                    await asyncio.sleep(2 ** (attempt + 1) + random.random())
            else:
                st["fail"] += 1
            n = st["ok"] + st["fail"]
            if n % 100 == 0: print("進度 %d / %d（失敗 %d）" % (n, len(todo), st["fail"]), flush=True)
            await asyncio.sleep(a.delay * (0.5 + random.random()))
    await asyncio.gather(*[worker() for _ in range(a.workers)])
    print("完成：成功 %d、失敗 %d、中止=%s" % (st["ok"], st["fail"], st["abort"]))

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: print("\n已中斷，重跑即可續傳。")

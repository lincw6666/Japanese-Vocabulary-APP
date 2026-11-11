#!/usr/bin/env python3
"""地端專用伺服器：靜態檔案 ＋ /tts?text=...（用 Edge TTS 的 ja-JP-NanamiNeural 即時合成，並快取）。
用法：uv run --with edge-tts python3 serve_local.py [port]    （預設 8080）
只綁定 127.0.0.1；GitHub Pages 沒有 /tts，前端會自動退回瀏覽器語音。"""
import asyncio, hashlib, os, sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import edge_tts

VOICE = "ja-JP-NanamiNeural"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio_cache", "local_tts")
os.makedirs(CACHE, exist_ok=True)

def cache_path(text):
    return os.path.join(CACHE, hashlib.md5((VOICE + text).encode()).hexdigest() + ".mp3")

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path)
        if u.path != "/tts":
            return super().do_GET()
        text = (parse_qs(u.query).get("text") or [""])[0].strip()
        if not text or len(text) > 300:
            return self.send_error(400, "bad text")
        f = cache_path(text)
        try:
            if not os.path.exists(f):
                asyncio.run(edge_tts.Communicate(text, VOICE).save(f))
            data = open(f, "rb").read()
        except Exception as e:
            if os.path.exists(f): os.remove(f)
            return self.send_error(502, "tts failed: %s" % e)
        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    print("地端伺服器 http://localhost:%d  （/tts 使用 %s）" % (port, VOICE))
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()

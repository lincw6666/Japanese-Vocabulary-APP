import os
import zipfile
import time

OUTPUT_DIR = "audio_packages"
os.makedirs(OUTPUT_DIR, exist_ok=True)

PACKAGES = {
    "N5": {"prefix": "N5_", "subpath": "audio", "target": "audio_N5.zip"},
    "N4": {"prefix": "N4_", "subpath": "audio", "target": "audio_N4.zip"},
    "N3": {"prefix": "N3_", "subpath": "audio", "target": "audio_N3.zip"},
    "N2": {"prefix": "N2_", "subpath": "audio", "target": "audio_N2.zip"},
    "N1": {"prefix": "N1_", "subpath": "audio", "target": "audio_N1.zip"},
    "grammar": {"prefix": None, "subpath": "audio/grammar", "target": "audio_grammar.zip"}
}

print("=== Starting Audio Packaging (Deflate Mode) ===")
total_start = time.time()
manifest = {}

for name, cfg in PACKAGES.items():
    t0 = time.time()
    zip_path = os.path.join(OUTPUT_DIR, cfg["target"])
    src_dir = cfg["subpath"]
    prefix = cfg["prefix"]
    
    file_list = []
    if os.path.exists(src_dir):
        for f in sorted(os.listdir(src_dir)):
            if not f.endswith(".mp3"):
                continue
            if prefix is None or f.startswith(prefix):
                file_list.append(f)
                
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for f in file_list:
            full_path = os.path.join(src_dir, f)
            # For grammar, we store as grammar/xxx.mp3 so path resolution is consistent
            arcname = f"grammar/{f}" if name == "grammar" else f
            zf.write(full_path, arcname)
            
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    manifest[name] = {
        "file": cfg["target"],
        "count": len(file_list),
        "size_mb": round(size_mb, 2),
        "updated_at": int(time.time())
    }
    print(f"[{name:7s}] Packed {len(file_list):5d} files -> {cfg['target']:18s} ({size_mb:5.2f} MB) in {time.time()-t0:.2f}s")

print(f"\nAll packages created in {time.time()-total_start:.2f}s in ./{OUTPUT_DIR}/")

#!/usr/bin/env python3
"""
robust_font_trainer.py  –  synthesize heavily varied pages and fine‑tune
                           a Tesseract LSTM model.

Now supports running multiple font trainings in one invocation.
"""
import subprocess, tempfile, pathlib, os, random, shutil, sys, cv2
from PIL import Image, ImageDraw, ImageOps
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

# ───── global parallelism setting ────────────────────────────────────
MAX_THREADS = os.cpu_count() or 4


# ───── helpers ───────────────────────────────────────────────────────────
def run(cmd: list[str], must_exist: bool = False):
    #print("+", " ".join(map(str, cmd)))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        sys.exit(f"❌  Command failed: {' '.join(cmd)}")
    if must_exist and not pathlib.Path(must_exist).exists():
        sys.exit(f"❌  Expected file not written: {must_exist}")


def get_tessdata_dir() -> pathlib.Path:
    env = os.getenv("TESSDATA_PREFIX")
    if env and (pathlib.Path(env) / "eng.traineddata").exists():
        return pathlib.Path(env)
    exe = shutil.which("tesseract") or sys.exit("tesseract.exe not in PATH")
    guess = pathlib.Path(exe).parent / "tessdata"
    if (guess / "eng.traineddata").exists():
        return guess
    sys.exit("Set TESSDATA_PREFIX or install UB-Mannheim build.")


def make_box_text(charset: str, lines: int = 600) -> str:
    """Create lines composed of multiple short tokens separated by spaces.
    This minimizes full-line drops when some tokens are unrenderable.
    """
    letters = [c for c in charset if c != " "]
    if not letters:
        letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    out = []
    for _ in range(lines):
        token_count = random.randint(6, 12)
        tokens = []
        for _ in range(token_count):
            n = random.randint(3, 8)
            tokens.append("".join(random.choice(letters) for _ in range(n)))
        out.append(" ".join(tokens))
    return "\n".join(out)


def supported_chars_for_font(font_file: str, requested: str) -> str:
    """Return subset of requested chars actually supported by the font (via CMAP and glyphs).
    Ensures we only keep codepoints mapped to real glyphs (not .notdef). Falls back to a safe
    alnum set if the intersection is empty or if fontTools is unavailable.
    """
    safe_fallback = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    try:
        from fontTools.ttLib import TTFont
        tt = TTFont(font_file)
        cmap = tt.getBestCmap() or {}
        glyph_order = set(tt.getGlyphOrder() or [])
        tt.close()
        kept = []
        for ch in requested:
            cp = ord(ch)
            gname = cmap.get(cp)
            if not gname:
                continue
            if gname == ".notdef" or gname not in glyph_order:
                continue
            kept.append(ch)
        filtered = "".join(kept)
        if not filtered:
            print(f"WARNING: '{pathlib.Path(font_file).name}' had no overlap; using safe alnum fallback.")
            filtered = safe_fallback
        return filtered
    except Exception as e:
        print(f"WARNING: fontTools not available or failed for {font_file}: {e}; using safe fallback.")
        return safe_fallback


def font_face_name(font_file: str) -> str:
    """Extract a robust face name for text2image (prefer Full name, then Family)."""
    try:
        from fontTools.ttLib import TTFont
        tt = TTFont(font_file)
        name_table = tt["name"]
        full = None; fam = None
        for rec in name_table.names:
            if rec.nameID == 4 and not full:
                full = rec.toUnicode()
            if rec.nameID == 1 and not fam:
                fam = rec.toUnicode()
        tt.close()
        return (full or fam or pathlib.Path(font_file).stem).strip()
    except Exception:
        return pathlib.Path(font_file).stem


def tint_and_gradient(tiff_path: pathlib.Path):
    """Hue‑jitter text, then build a richly textured background with boxes, stripes, dots, noise+blur,
    with a 50% chance to invert colors at the end."""
    im = Image.open(tiff_path).convert("RGBA")
    w, h = im.size

    bg = Image.new("RGBA", (w,h))
    draw = ImageDraw.Draw(bg)

    # half chance to not do shit
    if random.choice([True, False]):
        # ── 1) Hue‑jitter entire RGBA page ───────────────────────────
        bgr = cv2.cvtColor(np.array(im), cv2.COLOR_RGBA2BGR)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        hsv[...,0] = ((hsv[...,0].astype(int) + random.randint(-15,15)) % 180).astype(np.uint8)
        tinted = Image.fromarray(cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)).convert("RGBA")

        # ── 2) Build text mask (text = <240 gray), then strip shadows ──
        gray = tinted.convert("L")
        mask = gray.point(lambda px: 255 if px < 240 else 0, mode="L")
        tinted.putalpha(mask)

        # ── 3) Create base gradient ──────────────────────────────────
        
        top = tuple(random.randint(180,220) for _ in range(3)) + (255,)
        bot = tuple(random.randint(120,160) for _ in range(3)) + (255,)
        for y in range(h):
            t = y / (h - 1)
            col = tuple(int(top[i]*(1-t) + bot[i]*t) for i in range(4))
            draw.line([(0, y), (w, y)], fill=col)

        # ── 4) Add random boxes ─────────────────────────────────────
        for _ in range(random.randint(15, 35)):
            x0 = random.randint(0, w-1); y0 = random.randint(0, h-1)
            x1 = x0 + random.randint(int(w*0.05), int(w*0.3))
            y1 = y0 + random.randint(int(h*0.05), int(h*0.3))
            color = tuple(random.randint(10,200) for _ in range(3)) + (random.randint(30,80),)
            draw.rectangle([x0,y0,x1,y1], fill=color)

        # ── 5) Add random stripes ────────────────────────────────────
        for _ in range(random.randint(3,7)):
            if random.choice([True, False]):
                y = random.randint(0, h-1)
                thickness = random.randint(5, int(h*0.1))
                color = tuple(random.randint(10,200) for _ in range(3)) + (random.randint(20,60),)
                draw.rectangle([0, y, w, y+thickness], fill=color)
            else:
                x = random.randint(0, w-1)
                thickness = random.randint(5, int(w*0.1))
                color = tuple(random.randint(10,200) for _ in range(3)) + (random.randint(20,60),)
                draw.rectangle([x, 0, x+thickness, h], fill=color)

        # ── 6) Add random dots ───────────────────────────────────────
        for _ in range(random.randint(150,550)):
            cx = random.randint(0, w-1); cy = random.randint(0, h-1)
            r  = random.randint(2, int(min(w,h)*0.02))
            color = tuple(random.randint(10,200) for _ in range(3)) + (random.randint(30,90),)
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=color)

        # ── 7) Composite text over bg ──────────────────────────────
        composite = Image.alpha_composite(bg, tinted)

    else:
        composite = Image.alpha_composite(bg, im)

    # ── 8) Convert to RGB and optionally invert colors ──────────
    final = composite.convert("RGB")
    if random.choice([True, False]):
        final = ImageOps.invert(final)

    # ── 9) Save final RGB TIFF ───────────────────────────────────
    final.save(tiff_path, compression="tiff_lzw")



def train(
    font_file: str,
    font_name: str,
    lang_code: str,
    base_model: str,
    output_dir: str,
    charset: str,
    max_threads: int = MAX_THREADS
):
    """Run the full OCR training workflow for one font configuration."""
    global MAX_THREADS
    MAX_THREADS = max_threads

    out_dir = pathlib.Path(output_dir).absolute()
    shutil.rmtree(str(out_dir), ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) training text
    training_text = out_dir / f"{lang_code}.training_text"
    training_text.write_text(make_box_text(charset), "utf-8")

    # 2) synthetic TIFF pages with ThreadPoolExecutor
    tmp_fc_root = pathlib.Path(tempfile.mkdtemp(prefix="fcroot_"))
    iterations = 5
    dpilist = [120, 150, 180, 200, 225, 250, 275, 300]
    ptsizes = [12, 14, 18, 24, 36]

    commands = []
    for i in range(iterations):
        for dpi in dpilist:
            for ptsize in ptsizes:
                tag = f"{lang_code}_{i}_{dpi}_{ptsize}"
                fc_dir = tmp_fc_root / tag
                fc_dir.mkdir(parents=True, exist_ok=True)
                cmd = [
                    "text2image",
                    f"--font={font_name}",
                    f"--fonts_dir={pathlib.Path(font_file).parent}",
                    f"--outputbase={out_dir / tag}",
                    "--ptsize", f"{ptsize}",
                    "--resolution", str(dpi),
                    f"--fontconfig_tmpdir={fc_dir}",
                    f"--text={training_text}",
                    "--degrade_image=false",
                    "--blur=false",
                    "--smooth_noise=false",
                    "--white_noise=false"
                ]
                commands.append(cmd)

    print(f"DEBUG  Launching {len(commands)} text2image jobs with {MAX_THREADS} threads")
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as ex:
        futures = [ex.submit(run, cmd) for cmd in commands]
        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                print(f"WARNING: text2image job failed: {e}")

    tiff_pages = list(out_dir.glob(f"{lang_code}_*.tif"))
    print(f"DEBUG  TIFF pages found for '{lang_code}': {len(tiff_pages)}")
    if not tiff_pages:
        sys.exit(f"❌  No TIFFs found for '{lang_code}' – check font and flags.")

    # 3) parallel augmentation
    print(f"DEBUG  Augmenting '{lang_code}' with {MAX_THREADS} threads")
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as ex:
        futures = [ex.submit(tint_and_gradient, t) for t in tiff_pages]
        for f in as_completed(futures):
            f.result()

    # 4) parallel LSTMF creation
    lstmf_dir = out_dir / "lstmf"
    lstmf_dir.mkdir(exist_ok=True)
    print(f"DEBUG  Creating LSTMF for '{lang_code}' with {MAX_THREADS} threads")
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as ex:
        futures = []
        for tiff in tiff_pages:
            out_base = lstmf_dir / tiff.stem
            lstmf = out_base.with_suffix(".lstmf")
            futures.append(ex.submit(
                run,
                ["tesseract", str(tiff), str(out_base), "--psm", "6", "lstm.train"],
                lstmf
            ))
        for f in as_completed(futures):
            f.result()

    lstmf_count = sum(1 for _ in lstmf_dir.glob("*.lstmf"))
    print(f"DEBUG  LSTMF files written for '{lang_code}': {lstmf_count}")
    if lstmf_count == 0:
        sys.exit(f"❌  No .lstmf files for '{lang_code}' – check Tesseract stderr.")

    # 5) lstmf.list
    list_file = out_dir / "lstmf.list"
    with list_file.open("w", newline="\n") as lf:
        for p in lstmf_dir.glob("*.lstmf"):
            lf.write(p.resolve().as_posix() + "\n")

    # 6) extract float base
    tessdata_dir = get_tessdata_dir()
    base_trained = tessdata_dir / f"{base_model}.traineddata"
    base_lstm = out_dir / f"{base_model}.lstm"
    run(["combine_tessdata", "-e", str(base_trained), str(base_lstm)])

    # 7) heavy training
    chk_prefix = out_dir / f"{lang_code}_chk"
    run([
        "lstmtraining",
        "--model_output", str(chk_prefix),
        "--continue_from", str(base_lstm),
        "--traineddata", str(base_trained),
        "--train_listfile", str(list_file),
        "--max_iterations", "1200",
        "--learning_rate", "1e-4"
    ])

    # 8) pack final model
    run([
        "lstmtraining",
        "--stop_training",
        "--continue_from", f"{chk_prefix}_checkpoint",
        "--traineddata", str(base_trained),
        "--model_output", str(out_dir / f"{lang_code}.traineddata"),
    ])

    print(f"\n✅ new model → {out_dir / (lang_code + '.traineddata')}\n")
    final  = out_dir / (lang_code + '.traineddata')
    shutil.copy2(final, final.parent.parent)

def main():
    # Discover all .ttf fonts in the fonts directory and train each
    fonts_dir = pathlib.Path(r"C:\Users\Michael\projects\auto_rs\data\fonts").resolve()
    out_dir = fonts_dir / "tesseract"

    # requested character set (filtered per font). Include a space to break tokens.
    base_chars = (
        "0123456789"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
        + r",.\/()-:_ "
    )

    ttf_files = sorted(fonts_dir.glob("*.ttf"), key=lambda p: p.stem.lower(),reverse=True)
    if not ttf_files:
        sys.exit(f"❌  No .ttf files found in {fonts_dir}")

    presets = []
    for ttf in ttf_files:
        stem = ttf.stem
        face = font_face_name(str(ttf))
        filtered = supported_chars_for_font(str(ttf), base_chars)
        if len(filtered) < len(base_chars):
            missing = set(base_chars) - set(filtered)
            if missing:
                print(f"INFO  '{face}' missing {len(missing)} chars; filtered out: {''.join(sorted(missing))}")
        presets.append((
            str(ttf),
            face,
            stem,
            "eng_best",
            str(out_dir),
            filtered
        ))

    for font_file, font_name, lang_code, base_model, output_dir, charset in presets:
        print(f"=== Starting training for '{lang_code}' (font: {font_name}) ===")
        train(font_file, font_name, lang_code, base_model, output_dir, charset, MAX_THREADS)


if __name__ == "__main__":
    main()

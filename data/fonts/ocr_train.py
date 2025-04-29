import argparse, subprocess, tempfile, pathlib, os, random, shutil, sys, cv2
from PIL import Image, ImageDraw
from enum import IntEnum
import numpy as np

# ───── helpers ───────────────────────────────────────────────────────────
def run(cmd: list[str], must_exist: bool = False):
    print("+", " ".join(map(str, cmd)))
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
    return "\n".join(
        "".join(random.choice(charset) for _ in range(random.randint(20, 45)))
        for _ in range(lines)
    )

def tint_and_gradient(tiff_path: pathlib.Path):
    """Add random hue jitter and a beige→brown gradient."""
    im = Image.open(tiff_path).convert("RGBA")
    w, h = map(int, im.size)

    # ---- random hue shift (±15°) -----------------------------------
    bgr = cv2.cvtColor(np.array(im), cv2.COLOR_RGBA2BGR)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    h_chan = hsv[..., 0].astype(np.int16)
    h_chan = (h_chan + random.randint(-15, 15)) % 180
    hsv[..., 0] = h_chan.astype(np.uint8)

    tint = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    im   = Image.fromarray(tint).convert("RGBA")      # <- ensure RGBA

    # ---- beige→brown gradient background ---------------------------
    grad = Image.new("RGBA", (w, h))
    draw = ImageDraw.Draw(grad)
    top = tuple(random.randint(180, 220) for _ in range(3)) + (255,)
    bot = tuple(random.randint(120, 160) for _ in range(3)) + (255,)
    for y in range(h):
        t = y / h
        col = tuple(int(top[i]*(1-t)+bot[i]*t) for i in range(4))
        draw.line([(0, y), (w, y)], fill=col)

    im = Image.alpha_composite(grad, im)
    im.convert("RGB").save(tiff_path, compression="tiff_lzw")


# ───── main pipeline ────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font-file", required=True)
    ap.add_argument("--font-name", required=True)
    ap.add_argument("--lang-code", required=True)
    ap.add_argument("--base-model", default="eng_best")
    ap.add_argument("--output-dir", default="model_out")
    ap.add_argument("--charset",
        default="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
    args = ap.parse_args()

    out_dir = pathlib.Path(args.output_dir).absolute(); out_dir.mkdir(parents=True, exist_ok=True)
    training_text = out_dir / f"{args.lang_code}.training_text"
    training_text.write_text(make_box_text(args.charset), "utf-8")

    # ── synthetic pages with jitter/blur/dpi/exposure ──────────────────
    tmp_fc = pathlib.Path(tempfile.mkdtemp(prefix="fc_"))
    dpilist = [120, 150, 180, 200, 225, 250, 275, 300]          # small-font DPI
    exposures = [-1, 0, 1]

    tiff_pages = []
    for dpi in dpilist:
        for exp in exposures:
            tag = f"{args.lang_code}_{dpi}_{exp}"
            run([
                "text2image",
                f"--font={args.font_name}",
                f"--fonts_dir={pathlib.Path(args.font_file).parent}",
                f"--outputbase={out_dir / tag}",
                "--ptsize", "14",
                "--resolution", str(dpi),
                "--exposure",  str(exp),
                f"--fontconfig_tmpdir={tmp_fc}",
                "--max_pages", "60",
                f"--text={training_text}",
                "--degrade_image=false",
                "--blur=false",
                "--smooth_noise=false",
                "--white_noise=false",
            ])
            # NEW: remember every page we just created
            tiff_pages.extend(out_dir.glob(f"{tag}*.tif"))

    print(f"DEBUG  TIFF pages found: {len(tiff_pages)}")
    if not tiff_pages:
        sys.exit("❌  No TIFFs were collected – check --font and flags.")

    # add colour jitter + gradient
    
    for tiff in tiff_pages:
        tint_and_gradient(tiff)

    # ── make LSTMFs ─────────────────────────────────────────────────────
    lstmf_dir = out_dir / "lstmf"; lstmf_dir.mkdir(exist_ok=True)
    for tiff in tiff_pages:
        out_base = lstmf_dir / tiff.stem
        lstmf = out_base.with_suffix(".lstmf")
        run([
            "tesseract", str(tiff), str(out_base),
            "--psm", "6", "lstm.train"
        ], must_exist=lstmf)

    lstmf_count = sum(1 for _ in lstmf_dir.glob("*.lstmf"))
    print(f"DEBUG  LSTMF files written: {lstmf_count}")
    if lstmf_count == 0:
        sys.exit("❌  No .lstmf files – check Tesseract stderr above.")

    list_file = out_dir / "lstmf.list"
    with list_file.open("w", newline="\n") as lf:
        for p in lstmf_dir.glob("*.lstmf"):
            lf.write(p.resolve().as_posix() + "\n")

    # ── extract float base LSTM ─────────────────────────────────────────
    tessdata_dir = get_tessdata_dir()
    base_trained = tessdata_dir / f"{args.base_model}.traineddata"
    base_lstm = out_dir / f"{args.base_model}.lstm"
    run(["combine_tessdata", "-e", str(base_trained), str(base_lstm)])

    # ── heavy training (↓ LR, ↑ iters) ─────────────────────────────────
    chk_prefix = out_dir / f"{args.lang_code}_chk"
    run([
        "lstmtraining",
        "--model_output", str(chk_prefix),
        "--continue_from", str(base_lstm),
        "--traineddata",  str(base_trained),
        "--train_listfile", str(list_file),
        "--max_iterations", "1200",
        "--learning_rate", "1e-4"
    ])

    # ── pack final model ───────────────────────────────────────────────
    run([
        "lstmtraining",
        "--stop_training",
        "--continue_from", f"{chk_prefix}_checkpoint",
        "--traineddata",   str(base_trained),
        "--model_output",  str(out_dir / f"{args.lang_code}.traineddata")
    ])

    print(f"\n✅ new model → {out_dir / (args.lang_code + '.traineddata')}")

if __name__ == "__main__":
    main()

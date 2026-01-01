#!/usr/bin/env python3
"""
LucyTrace: Turn "Ruff Drafts" into the "Director's Cut"
Unified Coloring Page Pipeline
Last update: 2026-01-01 12:15 PM

- features:
    - Profiles: 'Base' (Fast/Strict) vs 'Advanced' (Smart/Auto-Levels)
    - Engine: ImageMagick (Clean) -> Potrace (Trace) -> Inkscape (Export)
    - Output: Optimized SVG (Laser/CAD) and High-Res PNG/PDF (Print)
"""

from pathlib import Path
import subprocess
import shutil
import sys
import logging
import argparse
import configparser

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
CONFIG_FILE = ROOT / "lucytrace.ini"
INPUT = ROOT / "input_images"
CLEANED = ROOT / "cleaned_png"
SVG = ROOT / "output_svg"
PNG = ROOT / "output_png"
PDF = ROOT / "output_pdf"
LOGFILE = ROOT / "lucytrace.log"
README = ROOT / "README.md"

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGFILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

# -----------------------------------------------------------------------------
# Configuration Loader
# -----------------------------------------------------------------------------
def load_config():
    """Load settings from lucytrace.ini, falling back to defaults."""
    # FIX: interpolation=None allows using '%' symbols in the INI file without error
    config = configparser.ConfigParser(interpolation=None)
    
    defaults = {
        'profile': 'adv',
        'overwrite': False,
        'export_width': '3000',
        'threshold_percent': '60%', 
        'level_adjustment': '10%,90%',
        'posterize_colors': '8',
        'saturation_threshold': '0.05',
        'mode': 'auto',
        'invert': 'off',
        'turdsize': '5',
        'opttolerance': '0.5'
    }

    if CONFIG_FILE.exists():
        logging.info(f"Loading configuration from {CONFIG_FILE.name}")
        config.read(CONFIG_FILE)
    else:
        logging.warning(f"{CONFIG_FILE.name} not found. Using internal defaults.")

    def get_val(section, key, default):
        return config.get(section, key, fallback=default)
    def get_bool(section, key, default):
        return config.getboolean(section, key, fallback=default)

    return {
        'profile': get_val('General', 'profile', defaults['profile']),
        'overwrite': get_bool('General', 'overwrite', defaults['overwrite']),
        'export_width': get_val('General', 'export_width', defaults['export_width']),
        'threshold_percent': get_val('ImageProcessing', 'threshold_percent', defaults['threshold_percent']),
        'level_adjustment': get_val('ImageProcessing', 'level_adjustment', defaults['level_adjustment']),
        'posterize_colors': get_val('ImageProcessing', 'posterize_colors', defaults['posterize_colors']),
        'saturation_threshold': config.getfloat('ImageProcessing', 'saturation_threshold', fallback=0.05),
        'mode': get_val('Modes', 'mode', defaults['mode']),
        'invert': get_val('Modes', 'invert', defaults['invert']),
        'turdsize': get_val('Potrace', 'turdsize', defaults['turdsize']),
        'opttolerance': get_val('Potrace', 'opttolerance', defaults['opttolerance']),
    }

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------
def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        logging.error(f"Required tool not found on PATH: {name}")
        if sys.platform == "win32":
            logging.error(f"Please ensure the folder containing {name}.exe is in your System PATH.")
        sys.exit(1)
    return path

def run(cmd: list[str]):
    logging.info("Running: %s", " ".join(cmd))
    subprocess.run(cmd, check=True)

# -----------------------------------------------------------------------------
# Logic
# -----------------------------------------------------------------------------
def detect_color_mode(magick: str, src: Path, cfg: dict) -> str:
    """Inspects image saturation to determine if it is Color or B&W."""
    cmd = [
        magick, str(src), "-colorspace", "HSL", "-channel", "S", 
        "-separate", "-format", "%[fx:mean]", "info:"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        saturation = float(result.stdout.strip())
        limit = float(cfg['saturation_threshold'])
        mode = 'color' if saturation > limit else 'bw'
        logging.info(f"[Analysis] {src.name} Saturation: {saturation:.4f} (Threshold: {limit}) -> {mode.upper()}")
        return mode
    except (subprocess.CalledProcessError, ValueError):
        logging.warning(f"Could not auto-detect color for {src.name}, defaulting to bw")
        return 'bw'

def clean_png(magick: str, src: Path, dst: Path, cfg: dict, profile: str, mode: str, invert_mode: str):
    """Clean the PNG for tracing. Dispatches logic based on 'profile'."""
    cmd = [magick, str(src)]

    # --- BASE PROFILE (Fast & Strict) ---
    if profile == 'base':
        logging.info(f"Processing {src.name} with Base Profile (Simple Threshold)")
        cmd.extend([
            "-alpha", "remove", "-alpha", "off", "-colorspace", "Gray",
            "-threshold", cfg['threshold_percent']
        ])
    
    # --- ADVANCED PROFILE (Smart & Flexible) ---
    else:
        if mode == 'auto':
            mode = detect_color_mode(magick, src, cfg)
        else:
            logging.info(f"Processing {src.name} with Advanced Profile (Forced: {mode.upper()})")

        # 1. Auto-Levels (Contrast Stretch)
        cmd.extend(["-level", cfg['level_adjustment']])

        # 2. Invert (Negative)
        if invert_mode == 'on':
            logging.info(f"Applying INVERT to {src.name}")
            cmd.append("-negate")

        # 3. Color vs B&W Logic
        if mode == 'color':
            cmd.extend([
                "-dither", "None", "-colors", cfg['posterize_colors'], 
                "-colorspace", "Gray", "-threshold", cfg['threshold_percent']
            ])
        else:
            cmd.extend([
                "-alpha", "remove", "-alpha", "off", "-colorspace", "Gray",
                "-threshold", cfg['threshold_percent']
            ])

    cmd.append(str(dst))
    run(cmd)

def trace_svg(src: Path, dst: Path, cfg: dict):
    """Trace PNG to SVG using Potrace."""
    cmd_magick = ["magick", str(src), "pnm:-"]
    cmd_potrace = [
        "potrace", "-s", "--turdsize", cfg['turdsize'], 
        "--alphamax", "1", "--opttolerance", cfg['opttolerance'], "-o", str(dst)
    ]
    logging.info(f"Tracing {src.name} with Potrace...")
    try:
        p1 = subprocess.Popen(cmd_magick, stdout=subprocess.PIPE)
        p2 = subprocess.run(cmd_potrace, stdin=p1.stdout, check=True)
        p1.wait() 
    except subprocess.CalledProcessError as e:
        logging.error(f"Tracing failed for {src.name}: {e}")
        raise

def export_png(inkscape: str, src: Path, dst: Path, cfg: dict):
    run([
        inkscape, str(src), f"--export-width={cfg['export_width']}",
        "--export-type=png", "--export-area-drawing", f"--export-filename={dst}"
    ])

def export_pdf(inkscape: str, src: Path, dst: Path):
    run([
        inkscape, str(src), "--export-type=pdf", 
        "--export-area-drawing", f"--export-filename={dst}"
    ])

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    cfg = load_config()
    parser = argparse.ArgumentParser(description="LucyTrace: Turn 'Ruff Drafts' into the 'Director's Cut'")
    parser.set_defaults(
        overwrite=cfg['overwrite'], profile=cfg['profile'],
        mode=cfg['mode'], invert=cfg['invert']
    )
    parser.add_argument('-p', '--profile', choices=['base', 'adv'], help='Processing Profile')
    parser.add_argument('-o', '--overwrite', action='store_true', help='Force reprocessing')
    parser.add_argument('--mode', choices=['auto', 'color', 'bw'], help='(Adv) Trace mode')
    parser.add_argument('--invert', choices=['on', 'off'], help='(Adv) Invert colors')
    parser.add_argument('--?', action='store_true', help='Display README')

    args = parser.parse_args()
    if args.__dict__.get('?'):
        if README.exists(): print(README.read_text(encoding='utf-8'))
        else: print("README.md not found.")
        sys.exit(0)

    PROFILE, OVERWRITE, MODE, INVERT = args.profile, args.overwrite, args.mode, args.invert

    logging.info(f"Starting LucyTrace (Profile: {PROFILE.upper()}, Mode: {MODE}, Invert: {INVERT})")
    logging.info("Turn 'Ruff Drafts' into the 'Director's Cut'")
    logging.info("=========================================")
    logging.info(f"EXPORT_WIDTH_PX = {cfg['export_width']}")
    if PROFILE == 'adv':
        logging.info(f"LEVEL_ADJUSTMENT = {cfg['level_adjustment']}")
        logging.info(f"POSTERIZE_COLORS = {cfg['posterize_colors']}")

    # Folder Setup
    for folder in (INPUT, CLEANED, SVG, PNG, PDF): folder.mkdir(exist_ok=True)
    
    # Auto-Migration
    folder_migrations = [(ROOT / "input_png", INPUT), (ROOT / "svg", SVG), (ROOT / "png", PNG), (ROOT / "pdf", PDF)]
    for old_path, new_path in folder_migrations:
        if old_path.exists() and old_path.is_dir() and not new_path.exists():
            logging.info(f"Migrating legacy folder: '{old_path.name}' -> '{new_path.name}'")
            try: old_path.rename(new_path)
            except OSError as e: logging.warning(f"Could not rename: {e}")

    # Import Images
    SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}
    for file_path in ROOT.iterdir():
        if not file_path.is_file(): continue
        if file_path.name in (Path(__file__).name, "README.md", "lucytrace.ini"): continue
        if file_path.suffix.lower() not in SUPPORTED_EXTS: continue

        target = INPUT / file_path.name
        if not target.exists():
            logging.info(f"Moving {file_path.name} into input_images/")
            shutil.move(str(file_path), str(target))

    # Check Tools
    magick = require_tool("magick")
    inkscape = require_tool("inkscape")
    require_tool("potrace") 

    # Processing Loop
    input_files = sorted([f for f in INPUT.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS])
    if not input_files:
        logging.warning("No supported image files found in input_images")
        return

    skip_all_existing = False
    for src_file in input_files:
        stem = src_file.stem
        logging.info(f"Processing: {src_file.name}")
        
        cleaned_png = CLEANED / f"{stem}.png"
        svg_file = SVG / f"{stem}.svg"
        out_png = PNG / f"{stem}.png"
        out_pdf = PDF / f"{stem}.pdf"

        outputs_exist = all(p.exists() for p in (cleaned_png, svg_file, out_png, out_pdf))
        should_process = True

        if outputs_exist:
            if OVERWRITE: should_process = True
            elif skip_all_existing: should_process = False
            else:
                if sys.stdin.isatty():
                    print(f"\nFiles for '{src_file.name}' already exist.")
                    while True:
                        choice = input("Overwrite? (y)es, (n)o, (a)ll, (s)kip all: ").lower().strip()
                        if choice.startswith('y'): should_process = True; break
                        elif choice.startswith('n'): should_process = False; break
                        elif choice.startswith('a'): should_process = True; OVERWRITE = True; break
                        elif choice.startswith('s'): should_process = False; skip_all_existing = True; break
                else: should_process = False

        if not should_process:
            logging.info(f"Skipping {src_file.name}")
            continue

        try:
            clean_png(magick, src_file, cleaned_png, cfg, profile=PROFILE, mode=MODE, invert_mode=INVERT)
            trace_svg(cleaned_png, svg_file, cfg)
            export_png(inkscape, svg_file, out_png, cfg)
            export_pdf(inkscape, svg_file, out_pdf)
        except Exception as e:
            logging.error(f"Failed processing {src_file.name}: {e}")

    logging.info("LucyTrace Pipeline Complete")

if __name__ == "__main__":
    main()
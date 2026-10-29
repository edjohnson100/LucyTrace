#!/usr/bin/env python3
"""
LucyTrace: Turn "Ruff Drafts" into the "Director's Cut"
Unified Coloring Page Pipeline

- Profiles: 'Base' (Fast/Strict) vs 'Advanced' (Smart/Auto-Levels)
- Engine: ImageMagick (Clean) -> Potrace (Trace) -> Inkscape (Export)
- Output: Optimized SVG (Laser/CAD) and High-Res PNG/PDF (Print)
- Frontend: CLI and CustomTkinter (Desktop GUI)
"""

from pathlib import Path
import subprocess
import shutil
import sys
import logging
import argparse
import configparser

# Ensure Windows terminal doesn't crash on emoji/Unicode output
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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
SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}

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
# Configuration Loader & Saver
# -----------------------------------------------------------------------------
def load_config() -> dict:
    """Load settings from lucytrace.ini, falling back to defaults."""
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

def save_config(cfg: dict):
    """Save settings back to lucytrace.ini."""
    config = configparser.ConfigParser(interpolation=None)
    config['General'] = {
        'profile': str(cfg.get('profile', 'adv')),
        'export_width': str(cfg.get('export_width', '3000')),
        'overwrite': str(cfg.get('overwrite', False)).lower(),
    }
    config['ImageProcessing'] = {
        'threshold_percent': str(cfg.get('threshold_percent', '55%')),
        'level_adjustment': str(cfg.get('level_adjustment', '10%,90%')),
        'posterize_colors': str(cfg.get('posterize_colors', '8')),
        'saturation_threshold': str(cfg.get('saturation_threshold', '0.20')),
    }
    config['Modes'] = {
        'mode': str(cfg.get('mode', 'auto')),
        'invert': str(cfg.get('invert', 'off')),
    }
    config['Potrace'] = {
        'turdsize': str(cfg.get('turdsize', '5')),
        'opttolerance': str(cfg.get('opttolerance', '0.5')),
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        config.write(f)

# -----------------------------------------------------------------------------
# System Tool Utilities
# -----------------------------------------------------------------------------
def check_system_tools() -> dict:
    """Check existence of all external CLI dependencies."""
    return {
        "magick": shutil.which("magick") or shutil.which("convert"),
        "potrace": shutil.which("potrace"),
        "inkscape": shutil.which("inkscape"),
    }

def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        logging.error(f"Required tool not found on PATH: {name}")
        if sys.platform == "win32":
            logging.error(f"Please ensure the folder containing {name}.exe is in your System PATH.")
        sys.exit(1)
    return path

def run(cmd: list[str], log_cb=None):
    cmd_str = " ".join(cmd)
    logging.info("Running: %s", cmd_str)
    if log_cb:
        log_cb(f"Running: {cmd_str}")
    subprocess.run(cmd, check=True)

# -----------------------------------------------------------------------------
# Processing Pipeline Logic
# -----------------------------------------------------------------------------
def detect_color_mode(magick: str, src: Path, cfg: dict, log_cb=None) -> str:
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
        msg = f"[Analysis] {src.name} Saturation: {saturation:.4f} (Threshold: {limit}) -> {mode.upper()}"
        logging.info(msg)
        if log_cb: log_cb(msg)
        return mode
    except (subprocess.CalledProcessError, ValueError):
        msg = f"Could not auto-detect color for {src.name}, defaulting to bw"
        logging.warning(msg)
        if log_cb: log_cb(msg)
        return 'bw'

def clean_png(magick: str, src: Path, dst: Path, cfg: dict, profile: str, mode: str, invert_mode: str, log_cb=None):
    """Clean the PNG for tracing. Dispatches logic based on 'profile'."""
    cmd = [magick, str(src)]

    # --- BASE PROFILE (Fast & Strict) ---
    if profile == 'base':
        msg = f"Processing {src.name} with Base Profile (Simple Threshold)"
        logging.info(msg)
        if log_cb: log_cb(msg)
        cmd.extend([
            "-alpha", "remove", "-alpha", "off", "-colorspace", "Gray",
            "-threshold", cfg['threshold_percent']
        ])
    
    # --- ADVANCED PROFILE (Smart & Flexible) ---
    else:
        if mode == 'auto':
            mode = detect_color_mode(magick, src, cfg, log_cb=log_cb)
        else:
            msg = f"Processing {src.name} with Advanced Profile (Forced: {mode.upper()})"
            logging.info(msg)
            if log_cb: log_cb(msg)

        # 1. Auto-Levels (Contrast Stretch)
        cmd.extend(["-level", cfg['level_adjustment']])

        # 2. Invert (Negative)
        if invert_mode == 'on':
            msg = f"Applying INVERT to {src.name}"
            logging.info(msg)
            if log_cb: log_cb(msg)
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
    run(cmd, log_cb=log_cb)

def trace_svg(src: Path, dst: Path, cfg: dict, log_cb=None):
    """Trace PNG to SVG using Potrace."""
    cmd_magick = ["magick", str(src), "pnm:-"]
    cmd_potrace = [
        "potrace", "-s", "--turdsize", str(cfg['turdsize']), 
        "--alphamax", "1", "--opttolerance", str(cfg['opttolerance']), "-o", str(dst)
    ]
    msg = f"Tracing {src.name} with Potrace..."
    logging.info(msg)
    if log_cb: log_cb(msg)
    try:
        p1 = subprocess.Popen(cmd_magick, stdout=subprocess.PIPE)
        p2 = subprocess.run(cmd_potrace, stdin=p1.stdout, check=True)
        p1.wait() 
    except subprocess.CalledProcessError as e:
        err_msg = f"Tracing failed for {src.name}: {e}"
        logging.error(err_msg)
        if log_cb: log_cb(err_msg)
        raise

def export_png(inkscape: str, src: Path, dst: Path, cfg: dict, log_cb=None):
    run([
        inkscape, str(src), f"--export-width={cfg['export_width']}",
        "--export-type=png", "--export-area-drawing",
        "--export-background=white", "--export-background-opacity=1.0",
        f"--export-filename={dst}"
    ], log_cb=log_cb)

def export_pdf(inkscape: str, src: Path, dst: Path, log_cb=None):
    run([
        inkscape, str(src), "--export-type=pdf", 
        "--export-area-drawing", f"--export-filename={dst}"
    ], log_cb=log_cb)

def process_single_image(src_file: Path, cfg: dict, profile: str = None, mode: str = None, 
                         invert_mode: str = None, overwrite: bool = False, log_cb=None) -> dict:
    """Process a single image through the full LucyTrace pipeline."""
    for folder in (INPUT, CLEANED, SVG, PNG, PDF):
        folder.mkdir(exist_ok=True)

    profile = profile or cfg.get('profile', 'adv')
    mode = mode or cfg.get('mode', 'auto')
    invert_mode = invert_mode or cfg.get('invert', 'off')

    stem = src_file.stem
    cleaned_png = CLEANED / f"{stem}.png"
    svg_file = SVG / f"{stem}.svg"
    out_png = PNG / f"{stem}.png"
    out_pdf = PDF / f"{stem}.pdf"

    outputs_exist = all(p.exists() for p in (cleaned_png, svg_file, out_png, out_pdf))
    if outputs_exist and not overwrite:
        return {
            "status": "skipped",
            "cleaned": cleaned_png,
            "svg": svg_file,
            "png": out_png,
            "pdf": out_pdf,
            "message": f"Outputs already exist for {src_file.name}. (Overwrite=False)"
        }

    tools = check_system_tools()
    magick = tools['magick'] or require_tool("magick")
    inkscape = tools['inkscape'] or require_tool("inkscape")
    require_tool("potrace")

    clean_png(magick, src_file, cleaned_png, cfg, profile=profile, mode=mode, invert_mode=invert_mode, log_cb=log_cb)
    trace_svg(cleaned_png, svg_file, cfg, log_cb=log_cb)
    export_png(inkscape, svg_file, out_png, cfg, log_cb=log_cb)
    export_pdf(inkscape, svg_file, out_pdf, log_cb=log_cb)

    return {
        "status": "ok",
        "cleaned": cleaned_png,
        "svg": svg_file,
        "png": out_png,
        "pdf": out_pdf,
        "message": f"Successfully processed {src_file.name}"
    }

# -----------------------------------------------------------------------------
# CLI Entry Point
# -----------------------------------------------------------------------------
def run_cli(args, cfg):
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

    # Import Images from root into input_images
    for file_path in ROOT.iterdir():
        if not file_path.is_file(): continue
        if file_path.name in (Path(__file__).name, "README.md", "lucytrace.ini", "setup.py", "requirements.txt"): continue
        if file_path.suffix.lower() not in SUPPORTED_EXTS: continue

        target = INPUT / file_path.name
        if not target.exists():
            logging.info(f"Moving {file_path.name} into input_images/")
            shutil.move(str(file_path), str(target))

    # Check Tools
    require_tool("magick")
    require_tool("inkscape")
    require_tool("potrace") 

    # Processing Loop
    input_files = sorted([f for f in INPUT.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS])
    if not input_files:
        logging.warning("No supported image files found in input_images")
        return

    skip_all_existing = False
    for src_file in input_files:
        stem = src_file.stem
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
            process_single_image(src_file, cfg, profile=PROFILE, mode=MODE, invert_mode=INVERT, overwrite=True)
        except Exception as e:
            logging.error(f"Failed processing {src_file.name}: {e}")

    logging.info("LucyTrace Pipeline Complete")

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
    
    # UI Selector flags
    parser.add_argument('--gui', action='store_true', help='Launch CustomTkinter desktop GUI (default)')
    parser.add_argument('--cli', action='store_true', help='Force CLI execution')

    # If no arguments provided in interactive environment, default to GUI if available
    raw_args = sys.argv[1:]
    
    args = parser.parse_args()
    if args.__dict__.get('?'):
        if README.exists(): print(README.read_text(encoding='utf-8'))
        else: print("README.md not found.")
        sys.exit(0)

    if args.gui or (not raw_args and not args.cli):
        # Default launcher action is Desktop GUI
        try:
            import gui_ctk
            gui_ctk.main()
            return
        except ImportError as e:
            logging.info(f"CustomTkinter GUI not available ({e}). Falling back to CLI mode.")
            run_cli(args, cfg)
            return

    run_cli(args, cfg)

if __name__ == "__main__":
    main()
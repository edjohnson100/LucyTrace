# LucyTrace 🐾

### Turn "Ruff Drafts" into the "Director's Cut"
<img src="resources/LucyTraceDocImage.png" alt="LucyTrace Logo Icon" width="50%">

**LucyTrace** is a high-performance pipeline for converting raster images (PNG, JPG, WEBP, etc.) into clean vector SVGs and print-ready coloring pages.

Named after our Director of Wellness (Lucy the Cavachon), this tool ensures your images are well-groomed, free of noise, and ready for:
1.  **Laser Cutting/Engraving:** Compatible with LightBurn, XTool Creative Space, and Glowforge.
2.  **CAD/CNC:** Optimized node counts for smoother import into **Autodesk Fusion** sketches.
3.  **Print:** Generates high-resolution, centered PDFs and PNGs for coloring books.

---

## 🚀 Quick Start

1.  **Drop your images** (PNG, JPG, BMP, etc.) into the root folder next to the script.
2.  **Run the pipeline:**
    * **Windows:** Double-click `lucytrace.bat`.
    * **Mac/Linux:** Double-click `lucytrace.sh`.
3.  **Choose your Profile** from the menu:
    * `[1] BASE`: Fast processing for clean line art.
    * `[2] ADVANCED`: Smart processing for photos, sketches, or complex images.
4.  **Collect your files:**
    * `output_svg/` -> Vector files.
    * `output_png/` -> High-res raster files.
    * `output_pdf/` -> Print-ready documents.

---

## ⚙️ The Two Profiles

LucyTrace uses a unified engine but offers two distinct "grooming" styles:

### 1. Base Profile ("The Fast Track")
* **Best For:** High-quality scans, crisp digital line art, black ink on white paper.
* **Logic:** Applies a strict brightness threshold (default 60%). Pixels darker than the limit become black; everything else becomes white.
* **Pros:** Extremely fast and predictable on clean input.

### 2. Advanced Profile ("The Director's Cut")
* **Best For:** Photos of drawings (bad lighting), "muddy" scans, comic book panels, or inverted images (white lines on black).
* **Logic:**
    * **Auto-Levels:** Stretches contrast to fix lighting issues (makes dark grays black, light grays white).
    * **Smart Detection:** Automatically detects if an image is Color or B&W.
    * **Posterization:** If color is detected, it flattens gradients into chunks ("stained glass" style) before tracing to prevent noise.

---

## 🛠️ Configuration (`lucytrace.ini`)

You don't need to edit the Python code to change settings. All major toggles are in `lucytrace.ini`:

```ini
[General]
profile = adv           ; Default profile if running via CLI
overwrite = false       ; Set to true to force reprocessing existing files
export_width = 3000     ; Width of the final PNG (3000px is approx 10 inches at 300 DPI)

[ImageProcessing]
threshold_percent = 60% ; The cutoff for black vs white

[Modes]
invert = off            ; Set to 'on' if your input is white lines on a black background
mode = auto             ; Can force 'color' or 'bw' manually here
```

---

## 📂 Folder Structure

The project uses the following structure (folders are auto-created if missing):

```text
<project folder>/
├── input_images/   # Source images (auto-moved here from root)
├── cleaned_png/    # Intermediate black/white PNGs (useful for debugging)
├── output_svg/     # Traced vector output files (Optimized for CAD/Laser)
├── output_png/     # Exported PNGs for printing
├── output_pdf/     # Exported PDFs for printing
│
├── lucytrace.py    # The Master Script
├── lucytrace.ini   # Configuration File
├── lucytrace.bat   # Windows Launcher
├── lucytrace.sh    # Mac/Linux Launcher
└── README.md
```

---

## 📦 Requirements

All tools must be installed and accessible via your system PATH.

### 1. Python 3.x
* **All OS:** Download from [Python.org](https://www.python.org/).

### 2. ImageMagick (for cleaning)
* **Windows:** Download the **DLL version** from [ImageMagick.org](https://imagemagick.org/).
    * **IMPORTANT:** During installation, check **"Install legacy utilities (e.g. convert)"** and **"Add to PATH"**.
* **Mac/Linux:** `brew install imagemagick` or `sudo apt install imagemagick`.

### 3. Potrace (for vectorizing)
* **Windows:** Download the binary from [SourceForge](https://potrace.sourceforge.net/). Add the folder containing `potrace.exe` to your System PATH.
* **Mac/Linux:** `brew install potrace` or `sudo apt install potrace`.

### 4. Inkscape (for exporting)
* **Windows:** Download and install from [Inkscape.org](https://inkscape.org/).
* **Mac/Linux:** `brew install --cask inkscape` or `sudo apt install inkscape`.

---
*Happy Making!* 🎨

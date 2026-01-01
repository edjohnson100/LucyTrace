# LucyTrace: Installation & Setup Guide 🐾

This document provides a quick reference for installing the necessary tools to run LucyTrace on **Windows**, **macOS**, and **Linux**.

---

## 📋 Prerequisites

LucyTrace is a script that orchestrates three powerful engines. You need all of them installed and accessible in your system `PATH`:

1.  **Python 3.x** (The conductor)
2.  **ImageMagick** (The cleaner)
3.  **Potrace** (The tracer)
4.  **Inkscape** (The exporter)

---

## 🪟 Windows Installation

### 1. Python 3.x
1.  Download from [python.org](https://www.python.org/downloads/windows/).
2.  **IMPORTANT:** During installation, check the box **"Add Python to PATH"**.
3.  Verify in PowerShell: `python --version`

### 2. ImageMagick
1.  Download the **DLL installer** from [ImageMagick.org](https://imagemagick.org/script/download.php#windows).
2.  During installation, check **"Install legacy utilities (e.g. convert)"** and **"Add to PATH"**.

### 3. Potrace
1.  Download the **Windows (64-bit)** zip from [SourceForge](https://potrace.sourceforge.net/#downloading).
2.  Extract the zip. You will see `potrace.exe`.
3.  Move the extracted folder to a permanent spot (e.g., `C:\Program Files\potrace`).
4.  **Add to PATH:**
    * Press `Win Key`, type "env", and select **"Edit the system environment variables"**.
    * Click **Environment Variables** -> System Variables -> Select `Path` -> Edit.
    * Click **New** and paste the folder path (e.g., `C:\Program Files\potrace`).
5.  Verify: `potrace --version`

### 4. Inkscape
1.  Download installer from [Inkscape.org](https://inkscape.org/release/).
2.  Install and ensure **"Add to PATH"** is selected.
3.  Verify: `inkscape --version`

---

## 🍎 macOS Installation

### 1. Python 3.x
macOS 12+ usually has Python, but Homebrew is recommended:
```bash
brew install python
python3 --version
```

### 2. ImageMagick
```bash
brew install imagemagick
```

### 3. Potrace
```bash
brew install potrace
```

### 4. Inkscape
1.  Install via Homebrew: `brew install --cask inkscape`
2.  **CRITICAL STEP:** macOS often hides the command line tool inside the App bundle. Link it manually:
    ```bash
    sudo ln -s /Applications/Inkscape.app/Contents/MacOS/inkscape /usr/local/bin/inkscape
    ```
3.  Verify: `inkscape --version`

---

## 🐧 Linux Installation (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install python3 python3-pip imagemagick potrace inkscape
```

---

## 🐍 Optional: Virtual Environment (venv)

Using a virtual environment prevents Python version conflicts.

1.  Navigate to the LucyTrace folder:
    ```bash
    cd /path/to/LucyTrace
    ```
2.  Create the venv:
    ```bash
    # Windows
    python -m venv venv
    
    # Mac/Linux
    python3 -m venv venv
    ```
3.  **That's it!** The `lucytrace.bat` (Windows) and `lucytrace.sh` (Mac) wrappers automatically detect the `venv` folder and use it if it exists.

---

## ✅ Final Verification

Open your terminal or command prompt and run these four commands. If any fail, the pipeline will not work.

```bash
python --version   # (or python3 --version)
magick -version
potrace --version
inkscape --version
```
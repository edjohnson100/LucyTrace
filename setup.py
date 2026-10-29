#!/usr/bin/env python3
"""
LucyTrace Setup & Installation Wizard
🐾 Cross-platform setup for Windows, macOS, and Linux.

Features:
- Verifies system tools (ImageMagick, Potrace, Inkscape) with OS-specific instructions.
- Creates an isolated virtual environment with custom naming (e.g. venv_win, venv_mac).
- Installs Python dependencies (Pillow, CustomTkinter, NiceGUI).
- Generates desktop shortcuts and one-click launchers.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
import venv
import platform

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

ROOT = Path(__file__).resolve().parent
REQUIREMENTS_FILE = ROOT / "requirements.txt"
ICON_ICO = ROOT / "LucyTraceIcon" / "lucytrace.ico"
ICON_PNG = ROOT / "LucyTraceIcon" / "256x256.png"

# Color formatting for terminal
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"

def print_banner():
    banner = f"""{Colors.OKCYAN}{Colors.BOLD}
======================================================================
                     🐾 LUCYTRACE SETUP WIZARD 🐾
             Turn "Ruff Drafts" into the "Director's Cut"
======================================================================{Colors.ENDC}
"""
    print(banner)

def get_platform_info():
    system = platform.system().lower()
    if "darwin" in system:
        return "mac"
    elif "win" in system:
        return "win"
    else:
        return "linux"

def check_system_tools():
    print(f"\n{Colors.BOLD}[1/4] Checking Required System Engines...{Colors.ENDC}")
    tools = {
        "magick": ("ImageMagick", shutil.which("magick") or shutil.which("convert")),
        "potrace": ("Potrace", shutil.which("potrace")),
        "inkscape": ("Inkscape", shutil.which("inkscape")),
    }
    
    all_ok = True
    for key, (display_name, path) in tools.items():
        if path:
            print(f"  {Colors.OKGREEN}✓ {display_name:<12}{Colors.ENDC} Found: {path}")
        else:
            print(f"  {Colors.FAIL}✗ {display_name:<12}{Colors.ENDC} Missing from PATH")
            all_ok = False

    if not all_ok:
        plat = get_platform_info()
        print(f"\n{Colors.WARNING}Notice: Some system tools are missing.{Colors.ENDC}")
        print("LucyTrace requires these tools to process and export vectors.")
        print(f"Please install missing tools via:")
        if plat == "mac":
            print(f"  {Colors.OKCYAN}brew install imagemagick potrace{Colors.ENDC}")
            print(f"  {Colors.OKCYAN}brew install --cask inkscape{Colors.ENDC}")
            print("  (See installation.md for Inkscape macOS PATH linking if needed)")
        elif plat == "win":
            print(f"  {Colors.OKCYAN}winget install ImageMagick.ImageMagick Inkscape.Inkscape{Colors.ENDC}")
            print("  For Potrace on Windows, download from https://potrace.sourceforge.net and add to PATH.")
        else:
            print(f"  {Colors.OKCYAN}sudo apt install imagemagick potrace inkscape{Colors.ENDC}")
    else:
        print(f"  {Colors.OKGREEN}All system tools detected!{Colors.ENDC}")

    return all_ok

def prompt_bool(prompt_text, default=True):
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        choice = input(prompt_text + suffix).strip().lower()
        if not choice:
            return default
        if choice in ("y", "yes"):
            return True
        if choice in ("n", "no"):
            return False
        print("Please enter 'y' or 'n'.")

def setup_virtual_environment():
    plat = get_platform_info()
    default_venv_name = f"venv_{plat}" if plat in ("win", "mac") else "venv_linux"

    print(f"\n{Colors.BOLD}[2/4] Virtual Environment Configuration{Colors.ENDC}")
    create_venv = prompt_bool("Create/configure a virtual environment?", default=True)
    if not create_venv:
        return sys.executable, None

    venv_input = input(f"Enter venv folder name [default: {Colors.OKCYAN}{default_venv_name}{Colors.ENDC}]: ").strip()
    venv_name = venv_input if venv_input else default_venv_name
    venv_dir = ROOT / venv_name

    if venv_dir.exists():
        print(f"  Found existing virtual environment at: {venv_dir}")
    else:
        print(f"  Creating virtual environment in: {Colors.OKCYAN}{venv_dir}{Colors.ENDC} ...")
        builder = venv.EnvBuilder(with_pip=True)
        builder.create(venv_dir)
        print(f"  {Colors.OKGREEN}Virtual environment created.{Colors.ENDC}")

    # Locate python and pip inside venv
    if plat == "win":
        py_exe = venv_dir / "Scripts" / "python.exe"
        pip_exe = venv_dir / "Scripts" / "pip.exe"
    else:
        py_exe = venv_dir / "bin" / "python"
        pip_exe = venv_dir / "bin" / "pip"

    if not py_exe.exists():
        print(f"  {Colors.FAIL}Error: Could not locate Python executable at {py_exe}{Colors.ENDC}")
        return sys.executable, None

    return str(py_exe), str(pip_exe)

def install_dependencies(pip_path):
    print(f"\n{Colors.BOLD}[3/4] Installing Python Dependencies{Colors.ENDC}")
    if not pip_path:
        print("  Skipping pip install (no venv pip specified).")
        return

    if not REQUIREMENTS_FILE.exists():
        print(f"  {Colors.WARNING}requirements.txt not found at {REQUIREMENTS_FILE}{Colors.ENDC}")
        return

    print(f"  Upgrading pip...")
    try:
        subprocess.run([pip_path, "install", "--upgrade", "pip"], check=True)
    except subprocess.CalledProcessError:
        print(f"  {Colors.WARNING}Warning: Could not upgrade pip. Proceeding with package installation.{Colors.ENDC}")

    print(f"  Installing packages from requirements.txt into venv...")
    try:
        subprocess.run([pip_path, "install", "-r", str(REQUIREMENTS_FILE)], check=True)
        print(f"  {Colors.OKGREEN}Dependencies installed successfully!{Colors.ENDC}")
    except subprocess.CalledProcessError as e:
        print(f"  {Colors.FAIL}Failed to install dependencies: {e}{Colors.ENDC}")

def create_shortcuts(py_path):
    plat = get_platform_info()
    print(f"\n{Colors.BOLD}[4/4] Desktop Shortcut & Launcher Setup{Colors.ENDC}")
    create_sc = prompt_bool("Create a desktop shortcut / quick launcher?", default=True)
    if not create_sc:
        return

    py_exe_path = Path(py_path)
    gui_script = ROOT / "gui_ctk.py"

    if plat == "win":
        desktop_dir = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
        if not desktop_dir.exists():
            desktop_dir = ROOT

        shortcut_path = desktop_dir / "LucyTrace.lnk"
        # Determine pythonw executable to run without console
        pythonw_candidate = py_exe_path.parent / "pythonw.exe"
        runner_exe = str(pythonw_candidate) if pythonw_candidate.exists() else str(py_exe_path)

        # Icon file
        icon_path = str(ICON_ICO) if ICON_ICO.exists() else ""

        # Use PowerShell to generate the .lnk
        ps_script = f"""
        $WshShell = New-Object -comObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
        $Shortcut.TargetPath = '{runner_exe}'
        $Shortcut.Arguments = '"{ROOT / "lucytrace.py"}" --gui'
        $Shortcut.WorkingDirectory = '{ROOT}'
        if ('{icon_path}') {{
            $Shortcut.IconLocation = '{icon_path}'
        }}
        $Shortcut.Description = 'LucyTrace - Vector Coloring Page Pipeline'
        $Shortcut.Save()
        """
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True)
            print(f"  {Colors.OKGREEN}Windows Desktop shortcut created:{Colors.ENDC} {shortcut_path}")
        except Exception as e:
            print(f"  {Colors.FAIL}Failed to create Windows shortcut: {e}{Colors.ENDC}")

    elif plat == "mac":
        desktop_dir = Path(os.path.expanduser("~/Desktop"))
        command_file = desktop_dir / "LucyTrace.command"
        content = f"""#!/bin/bash
cd "{ROOT}"
"{py_path}" "{ROOT / 'lucytrace.py'}" --gui
"""
        try:
            command_file.write_text(content, encoding="utf-8")
            command_file.chmod(0o755)
            print(f"  {Colors.OKGREEN}macOS Desktop launcher created:{Colors.ENDC} {command_file}")
        except Exception as e:
            print(f"  {Colors.FAIL}Failed to create macOS launcher: {e}{Colors.ENDC}")

    else:
        # Linux .desktop file
        desktop_dir = Path(os.path.expanduser("~/Desktop"))
        desktop_file = desktop_dir / "LucyTrace.desktop"
        content = f"""[Desktop Entry]
Type=Application
Name=LucyTrace
Comment=Turn Ruff Drafts into the Director's Cut
Exec="{py_path}" "{ROOT / 'lucytrace.py'}" --gui
Icon={ICON_PNG}
Terminal=false
Categories=Graphics;
"""
        try:
            desktop_file.write_text(content, encoding="utf-8")
            desktop_file.chmod(0o755)
            print(f"  {Colors.OKGREEN}Linux Desktop shortcut created:{Colors.ENDC} {desktop_file}")
        except Exception as e:
            print(f"  {Colors.FAIL}Failed to create Linux shortcut: {e}{Colors.ENDC}")

def main():
    print_banner()
    check_system_tools()
    py_path, pip_path = setup_virtual_environment()
    if pip_path:
        install_dependencies(pip_path)
    create_shortcuts(py_path)

    print(f"""
{Colors.OKGREEN}{Colors.BOLD}======================================================================
                     🎉 SETUP COMPLETE! 🎉
======================================================================{Colors.ENDC}
You can run LucyTrace using:
  • Desktop Shortcut
  • Desktop GUI (CustomTkinter): {Colors.OKCYAN}python lucytrace.py{Colors.ENDC}
  • Command Line / Batch Mode:   {Colors.OKCYAN}python lucytrace.py --cli{Colors.ENDC}
""")

if __name__ == "__main__":
    main()

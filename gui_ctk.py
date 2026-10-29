#!/usr/bin/env python3
"""
LucyTrace - CustomTkinter Desktop GUI
🐾 Native Dark/Light desktop frontend for vectorizing coloring pages.
Includes:
- Single image & folder browsing with dropdown and Prev/Next navigation.
- Custom folder selection for batch processing.
- Zoomable, pan-able image preview canvases (1x to 5x) with click-to-center.
- Solid white backing for RGBA vector previews (eliminates semi-opaque overlays).
"""

import os
import sys
import threading
from pathlib import Path
import subprocess
import platform
import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageTk

import lucytrace

ROOT = Path(__file__).resolve().parent
ICON_ICO = ROOT / "LucyTraceIcon" / "lucytrace.ico"
ICON_PNG = ROOT / "LucyTraceIcon" / "256x256.png"

def open_folder(folder_path: Path):
    """Open folder in OS native file explorer."""
    folder_path.mkdir(exist_ok=True)
    system = platform.system().lower()
    if "win" in system:
        os.startfile(folder_path)
    elif "darwin" in system:
        subprocess.run(["open", str(folder_path)])
    else:
        subprocess.run(["xdg-open", str(folder_path)])


class ZoomableImageViewer(ctk.CTkFrame):
    """
    Interactive image preview panel:
    - Never clips: dynamically letterboxes and fits image preserving aspect ratio on resize.
    - Click to center on image point.
    - Zoom range: 1.0x to 5.0x with slider, mouse wheel, or click.
    - Pan/drag with left mouse button when zoomed.
    - Reset to full view with Reset button, double-click, or right-click.
    - Composites RGBA images onto pure white paper background to eliminate semi-opaque overlay look.
    """
    def __init__(self, master, title: str, sync_callback=None, **kwargs):
        super().__init__(master, **kwargs)

        self.title_text = title
        self.sync_callback = sync_callback
        self.is_syncing = False

        self.original_image: Image.Image = None
        self.zoom_level = 1.0
        self.center_u = 0.5  # Normalized center in image coordinates [0.0, 1.0]
        self.center_v = 0.5

        # Pan drag tracking
        self._drag_start_x = 0
        self._drag_start_y = 0

        # Cached canvas dimensions & image reference
        self.tk_image = None
        self._resize_job = None

        self._build_widget()

    def _build_widget(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ---------------- Toolbar / Header ----------------
        self.toolbar = ctk.CTkFrame(self, fg_color="transparent")
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 4))
        self.toolbar.grid_columnconfigure(1, weight=1)

        self.lbl_title = ctk.CTkLabel(
            self.toolbar, 
            text=self.title_text, 
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_title.grid(row=0, column=0, sticky="w", padx=(4, 8))

        # Controls container
        ctrl_frame = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        ctrl_frame.grid(row=0, column=2, sticky="e")

        self.lbl_zoom = ctk.CTkLabel(
            ctrl_frame, 
            text="1.0x", 
            font=ctk.CTkFont(size=11, weight="bold"),
            width=38
        )
        self.lbl_zoom.pack(side="left", padx=2)

        self.slider_zoom = ctk.CTkSlider(
            ctrl_frame,
            from_=1.0,
            to=5.0,
            number_of_steps=40,
            width=110,
            command=self._on_slider_change
        )
        self.slider_zoom.set(1.0)
        self.slider_zoom.pack(side="left", padx=4)

        self.btn_reset = ctk.CTkButton(
            ctrl_frame,
            text="Reset",
            width=50,
            height=22,
            font=ctk.CTkFont(size=11),
            fg_color="gray30",
            hover_color="gray40",
            command=self.reset_zoom
        )
        self.btn_reset.pack(side="left", padx=2)

        # ---------------- Canvas Container ----------------
        self.canvas_bg_color = "#18181b" if ctk.get_appearance_mode() == "Dark" else "#e4e4e7"
        self.canvas = tk.Canvas(
            self, 
            bg=self.canvas_bg_color, 
            bd=0, 
            highlightthickness=0, 
            relief="flat"
        )
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))

        # Event bindings
        self.canvas.bind("<Configure>", self._on_configure)
        self.canvas.bind("<Button-1>", self._on_mouse_click)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_release)
        self.canvas.bind("<Button-3>", lambda e: self.reset_zoom())
        self.canvas.bind("<Double-Button-1>", lambda e: self.reset_zoom())

        # Mouse wheel (Windows / macOS / Linux)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-4>", lambda e: self._zoom_step(1.2, e.x, e.y))
        self.canvas.bind("<Button-5>", lambda e: self._zoom_step(0.8, e.x, e.y))

        # Initial placeholder text
        self.canvas.create_text(
            150, 150, 
            text="No image loaded", 
            fill="gray", 
            font=("Arial", 11),
            tags="placeholder"
        )

    def set_image(self, img_path: Path):
        """Load an image file and composite transparency onto solid white paper."""
        try:
            raw_img = Image.open(img_path)
            # Composite transparent PNGs/SVGs onto a pure white background so dark theme doesn't make it look semi-opaque
            if raw_img.mode in ("RGBA", "LA") or (raw_img.mode == "P" and "transparency" in raw_img.info):
                rgba_img = raw_img.convert("RGBA")
                white_bg = Image.new("RGBA", rgba_img.size, (255, 255, 255, 255))
                white_bg.alpha_composite(rgba_img)
                self.original_image = white_bg.convert("RGB")
            else:
                self.original_image = raw_img.convert("RGB")

            self.zoom_level = 1.0
            self.center_u = 0.5
            self.center_v = 0.5
            self.slider_zoom.set(1.0)
            self.lbl_zoom.configure(text="1.0x")
            self.redraw()
        except Exception as e:
            self.canvas.delete("all")
            self.canvas.create_text(
                150, 150, 
                text=f"Failed to load image:\n{e}", 
                fill="#f87171", 
                font=("Arial", 10),
                tags="placeholder"
            )

    def set_placeholder(self, text: str):
        self.original_image = None
        self.canvas.delete("all")
        can_w = max(self.canvas.winfo_width(), 100)
        can_h = max(self.canvas.winfo_height(), 100)
        self.canvas.create_text(
            can_w // 2, can_h // 2, 
            text=text, 
            fill="gray", 
            font=("Arial", 11),
            tags="placeholder"
        )

    def update_theme(self, mode: str):
        self.canvas_bg_color = "#18181b" if mode == "Dark" else "#e4e4e7"
        self.canvas.configure(bg=self.canvas_bg_color)
        self.redraw()

    def reset_zoom(self, notify_sync=True):
        self.zoom_level = 1.0
        self.center_u = 0.5
        self.center_v = 0.5
        self.slider_zoom.set(1.0)
        self.lbl_zoom.configure(text="1.0x")
        self.redraw()
        if notify_sync and self.sync_callback and not self.is_syncing:
            self.sync_callback(self.zoom_level, self.center_u, self.center_v)

    def set_view_sync(self, zoom: float, u: float, v: float):
        """Called by sibling viewer to synchronize position and zoom."""
        self.is_syncing = True
        try:
            self.zoom_level = max(1.0, min(5.0, zoom))
            self.center_u = max(0.0, min(1.0, u))
            self.center_v = max(0.0, min(1.0, v))
            self.slider_zoom.set(self.zoom_level)
            self.lbl_zoom.configure(text=f"{self.zoom_level:.1f}x")
            self.redraw()
        finally:
            self.is_syncing = False

    def _on_configure(self, event):
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(30, self.redraw)

    def _on_slider_change(self, value):
        self.zoom_level = float(value)
        self.lbl_zoom.configure(text=f"{self.zoom_level:.1f}x")
        self.redraw()
        if self.sync_callback and not self.is_syncing:
            self.sync_callback(self.zoom_level, self.center_u, self.center_v)

    def _zoom_step(self, factor: float, mouse_x: int, mouse_y: int):
        if not self.original_image:
            return

        can_w = self.canvas.winfo_width()
        can_h = self.canvas.winfo_height()
        if can_w <= 10 or can_h <= 10:
            return

        u_mouse, v_mouse = self._canvas_to_image_coords(mouse_x, mouse_y)
        new_zoom = max(1.0, min(5.0, self.zoom_level * factor))
        if abs(new_zoom - self.zoom_level) < 0.01:
            return

        if u_mouse is not None and v_mouse is not None and new_zoom > 1.0:
            weight = 0.3
            self.center_u = self.center_u * (1.0 - weight) + u_mouse * weight
            self.center_v = self.center_v * (1.0 - weight) + v_mouse * weight

        self.zoom_level = new_zoom
        if self.zoom_level == 1.0:
            self.center_u = 0.5
            self.center_v = 0.5

        self.slider_zoom.set(self.zoom_level)
        self.lbl_zoom.configure(text=f"{self.zoom_level:.1f}x")
        self.redraw()

        if self.sync_callback and not self.is_syncing:
            self.sync_callback(self.zoom_level, self.center_u, self.center_v)

    def _on_mouse_wheel(self, event):
        factor = 1.15 if event.delta > 0 else 0.85
        self._zoom_step(factor, event.x, event.y)

    def _on_mouse_click(self, event):
        if not self.original_image:
            return

        self._drag_start_x = event.x
        self._drag_start_y = event.y

        u_click, v_click = self._canvas_to_image_coords(event.x, event.y)
        if u_click is not None and v_click is not None:
            self.center_u = u_click
            self.center_v = v_click

            if self.zoom_level <= 1.05:
                self.zoom_level = 2.0
                self.slider_zoom.set(2.0)
                self.lbl_zoom.configure(text="2.0x")

            self.redraw()

            if self.sync_callback and not self.is_syncing:
                self.sync_callback(self.zoom_level, self.center_u, self.center_v)

    def _on_mouse_drag(self, event):
        if not self.original_image or self.zoom_level <= 1.0:
            return

        dx = event.x - self._drag_start_x
        dy = event.y - self._drag_start_y
        self._drag_start_x = event.x
        self._drag_start_y = event.y

        can_w = self.canvas.winfo_width()
        can_h = self.canvas.winfo_height()
        img_w, img_h = self.original_image.size
        scale_0 = min(can_w / img_w, can_h / img_h)
        scale = scale_0 * self.zoom_level
        disp_w = img_w * scale
        disp_h = img_h * scale

        if disp_w > 0:
            self.center_u = max(0.0, min(1.0, self.center_u - (dx / disp_w)))
        if disp_h > 0:
            self.center_v = max(0.0, min(1.0, self.center_v - (dy / disp_h)))

        self.redraw()

        if self.sync_callback and not self.is_syncing:
            self.sync_callback(self.zoom_level, self.center_u, self.center_v)

    def _on_mouse_release(self, event):
        pass

    def _canvas_to_image_coords(self, mx: int, my: int):
        if not self.original_image:
            return None, None

        can_w = self.canvas.winfo_width()
        can_h = self.canvas.winfo_height()
        img_w, img_h = self.original_image.size
        scale_0 = min(can_w / img_w, can_h / img_h)
        scale = scale_0 * self.zoom_level
        disp_w = img_w * scale
        disp_h = img_h * scale

        img_left = can_w / 2.0 - self.center_u * disp_w
        img_top = can_h / 2.0 - self.center_v * disp_h

        if disp_w >= can_w:
            img_left = max(can_w - disp_w, min(0.0, img_left))
        else:
            img_left = (can_w - disp_w) / 2.0

        if disp_h >= can_h:
            img_top = max(can_h - disp_h, min(0.0, img_top))
        else:
            img_top = (can_h - disp_h) / 2.0

        px = mx - img_left
        py = my - img_top

        u = max(0.0, min(1.0, px / disp_w))
        v = max(0.0, min(1.0, py / disp_h))
        return u, v

    def redraw(self):
        self.canvas.delete("all")
        if not self.original_image:
            can_w = max(self.canvas.winfo_width(), 100)
            can_h = max(self.canvas.winfo_height(), 100)
            self.canvas.create_text(
                can_w // 2, can_h // 2, 
                text="No image loaded", 
                fill="gray", 
                font=("Arial", 11),
                tags="placeholder"
            )
            return

        can_w = self.canvas.winfo_width()
        can_h = self.canvas.winfo_height()
        if can_w <= 10 or can_h <= 10:
            return

        img_w, img_h = self.original_image.size
        margin = 12
        avail_w = max(10, can_w - margin)
        avail_h = max(10, can_h - margin)
        scale_0 = min(avail_w / img_w, avail_h / img_h)

        scale = scale_0 * self.zoom_level
        disp_w = img_w * scale
        disp_h = img_h * scale

        if self.zoom_level <= 1.0:
            img_left = (can_w - disp_w) / 2.0
            img_top = (can_h - disp_h) / 2.0
        else:
            img_left = can_w / 2.0 - self.center_u * disp_w
            img_top = can_h / 2.0 - self.center_v * disp_h

            if disp_w >= can_w:
                img_left = max(can_w - disp_w, min(0.0, img_left))
            else:
                img_left = (can_w - disp_w) / 2.0

            if disp_h >= can_h:
                img_top = max(can_h - disp_h, min(0.0, img_top))
            else:
                img_top = (can_h - disp_h) / 2.0

            self.center_u = max(0.0, min(1.0, (can_w / 2.0 - img_left) / disp_w))
            self.center_v = max(0.0, min(1.0, (can_h / 2.0 - img_top) / disp_h))

        vis_left = max(0.0, img_left)
        vis_top = max(0.0, img_top)
        vis_right = min(float(can_w), img_left + disp_w)
        vis_bottom = min(float(can_h), img_top + disp_h)

        dest_w = int(vis_right - vis_left)
        dest_h = int(vis_bottom - vis_top)

        if dest_w <= 0 or dest_h <= 0:
            return

        crop_x0 = max(0.0, (vis_left - img_left) / scale)
        crop_y0 = max(0.0, (vis_top - img_top) / scale)
        crop_x1 = min(float(img_w), (vis_right - img_left) / scale)
        crop_y1 = min(float(img_h), (vis_bottom - img_top) / scale)

        if crop_x1 <= crop_x0 or crop_y1 <= crop_y0:
            return

        try:
            cropped = self.original_image.crop((int(crop_x0), int(crop_y0), int(crop_x1), int(crop_y1)))
            resized = cropped.resize((dest_w, dest_h), Image.Resampling.BILINEAR)
            self.tk_image = ImageTk.PhotoImage(resized)
            self.canvas.create_image(int(vis_left), int(vis_top), anchor="nw", image=self.tk_image)
        except Exception:
            pass


class LucyTraceApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LucyTrace 🐾 Turn 'Ruff Drafts' into the 'Director's Cut'")
        self.geometry("1180x800")
        self.minsize(1000, 700)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        if platform.system() == "Windows" and ICON_ICO.exists():
            self.iconbitmap(str(ICON_ICO))

        self.cfg = lucytrace.load_config()
        self.active_input_folder = lucytrace.INPUT
        self.folder_images: list[Path] = []
        self.current_img_index = 0
        self.selected_image_path = None
        self.batch_folder = lucytrace.INPUT
        self.is_processing = False

        self._build_ui()
        self._check_engines()
        self._refresh_folder_images()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=0, minsize=320)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ---------------------------------------------------------
        # LEFT SIDEBAR: Controls & Engine Status
        # ---------------------------------------------------------
        self.sidebar = ctk.CTkScrollableFrame(self, width=320, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        title_label = ctk.CTkLabel(
            self.sidebar, 
            text="🐾 LucyTrace", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(padx=15, pady=(15, 2))
        
        subtitle_label = ctk.CTkLabel(
            self.sidebar, 
            text="Vector Coloring Page Pipeline", 
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="gray"
        )
        subtitle_label.pack(padx=15, pady=(0, 12))

        # Appearance Theme Switch
        theme_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        theme_frame.pack(fill="x", padx=15, pady=(0, 12))
        ctk.CTkLabel(theme_frame, text="Theme:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 10))
        self.theme_seg = ctk.CTkSegmentedButton(
            theme_frame, 
            values=["Dark", "Light", "System"],
            command=self._change_appearance_mode
        )
        self.theme_seg.set("Dark")
        self.theme_seg.pack(side="right", fill="x", expand=True)

        # Engine Status Badges
        engine_frame = ctk.CTkFrame(self.sidebar)
        engine_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        engine_title = ctk.CTkLabel(engine_frame, text="System Engines", font=ctk.CTkFont(size=12, weight="bold"))
        engine_title.pack(anchor="w", padx=10, pady=(6, 2))

        self.status_magick = ctk.CTkLabel(engine_frame, text="⏳ ImageMagick", font=ctk.CTkFont(size=11))
        self.status_magick.pack(anchor="w", padx=15, pady=1)

        self.status_potrace = ctk.CTkLabel(engine_frame, text="⏳ Potrace", font=ctk.CTkFont(size=11))
        self.status_potrace.pack(anchor="w", padx=15, pady=1)

        self.status_inkscape = ctk.CTkLabel(engine_frame, text="⏳ Inkscape", font=ctk.CTkFont(size=11))
        self.status_inkscape.pack(anchor="w", padx=15, pady=(1, 8))

        # Profile Selector
        profile_label = ctk.CTkLabel(self.sidebar, text="Processing Profile", font=ctk.CTkFont(size=13, weight="bold"))
        profile_label.pack(anchor="w", padx=15, pady=(5, 3))

        self.profile_var = ctk.StringVar(value=self.cfg.get('profile', 'adv'))
        self.profile_seg = ctk.CTkSegmentedButton(
            self.sidebar, 
            values=["base", "adv"], 
            variable=self.profile_var
        )
        self.profile_seg.pack(fill="x", padx=15, pady=(0, 15))

        # Pipeline Settings
        settings_label = ctk.CTkLabel(self.sidebar, text="Pipeline Settings", font=ctk.CTkFont(size=13, weight="bold"))
        settings_label.pack(anchor="w", padx=15, pady=(5, 3))

        # Threshold
        self.thresh_label = ctk.CTkLabel(self.sidebar, text=f"Threshold: {self.cfg.get('threshold_percent', '55%')}")
        self.thresh_label.pack(anchor="w", padx=15, pady=(2, 0))
        init_thresh = int(self.cfg.get('threshold_percent', '55%').replace('%', ''))
        self.thresh_slider = ctk.CTkSlider(self.sidebar, from_=20, to=90, number_of_steps=70, command=self._update_thresh_label)
        self.thresh_slider.set(init_thresh)
        self.thresh_slider.pack(fill="x", padx=15, pady=(0, 8))

        # Auto-levels
        ctk.CTkLabel(self.sidebar, text="Level Adjustment (Contrast):").pack(anchor="w", padx=15, pady=(2, 0))
        self.levels_entry = ctk.CTkEntry(self.sidebar, placeholder_text="10%,90%")
        self.levels_entry.insert(0, self.cfg.get('level_adjustment', '10%,90%'))
        self.levels_entry.pack(fill="x", padx=15, pady=(0, 8))

        # Mode
        ctk.CTkLabel(self.sidebar, text="Mode (Color / B&W / Auto):").pack(anchor="w", padx=15, pady=(2, 0))
        self.mode_var = ctk.StringVar(value=self.cfg.get('mode', 'auto'))
        self.mode_menu = ctk.CTkOptionMenu(self.sidebar, values=["auto", "color", "bw"], variable=self.mode_var)
        self.mode_menu.pack(fill="x", padx=15, pady=(0, 8))

        # Invert switch
        self.invert_var = ctk.StringVar(value=self.cfg.get('invert', 'off'))
        self.invert_switch = ctk.CTkSwitch(
            self.sidebar, 
            text="Invert Colors (Negative)", 
            variable=self.invert_var, 
            onvalue="on", 
            offvalue="off"
        )
        self.invert_switch.pack(anchor="w", padx=15, pady=(4, 8))

        # Turdsize
        ctk.CTkLabel(self.sidebar, text="Speckle Suppression (Turdsize):").pack(anchor="w", padx=15, pady=(2, 0))
        self.turdsize_entry = ctk.CTkEntry(self.sidebar, placeholder_text="5")
        self.turdsize_entry.insert(0, str(self.cfg.get('turdsize', '5')))
        self.turdsize_entry.pack(fill="x", padx=15, pady=(0, 8))

        # Export Width
        ctk.CTkLabel(self.sidebar, text="Export Resolution (Width px):").pack(anchor="w", padx=15, pady=(2, 0))
        self.width_entry = ctk.CTkEntry(self.sidebar, placeholder_text="3072")
        self.width_entry.insert(0, str(self.cfg.get('export_width', '3072')))
        self.width_entry.pack(fill="x", padx=15, pady=(0, 12))

        # Overwrite toggle
        self.overwrite_var = ctk.BooleanVar(value=bool(self.cfg.get('overwrite', False)))
        self.overwrite_switch = ctk.CTkSwitch(self.sidebar, text="Always Overwrite", variable=self.overwrite_var)
        self.overwrite_switch.pack(anchor="w", padx=15, pady=(0, 15))

        # Save Settings button
        save_btn = ctk.CTkButton(self.sidebar, text="💾 Save as Default (INI)", fg_color="gray30", hover_color="gray40", command=self._save_settings)
        save_btn.pack(fill="x", padx=15, pady=(0, 20))

        # ---------------------------------------------------------
        # RIGHT AREA: Tabs, Previews, Action, Output Folders
        # ---------------------------------------------------------
        self.main_content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        self.main_content.grid_rowconfigure(0, weight=1)
        self.main_content.grid_columnconfigure(0, weight=1)

        # Tabview
        self.tabview = ctk.CTkTabview(self.main_content)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=(0, 10))
        self.tab_single = self.tabview.add("🖼️ Single Image Trace")
        self.tab_batch = self.tabview.add("📦 Batch Folder Trace")

        self._build_single_tab()
        self._build_batch_tab()

        # Bottom Bar: Output Shortcuts
        bottom_bar = ctk.CTkFrame(self.main_content, height=45)
        bottom_bar.grid(row=1, column=0, sticky="ew", padx=5, pady=(5, 0))

        ctk.CTkLabel(bottom_bar, text="Quick Folders:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=10, pady=8)
        ctk.CTkButton(bottom_bar, text="📁 Active Input", width=95, fg_color="gray25", command=lambda: open_folder(self.active_input_folder)).pack(side="left", padx=4)
        ctk.CTkButton(bottom_bar, text="📁 SVG", width=75, fg_color="gray25", command=lambda: open_folder(lucytrace.SVG)).pack(side="left", padx=4)
        ctk.CTkButton(bottom_bar, text="📁 PNG", width=75, fg_color="gray25", command=lambda: open_folder(lucytrace.PNG)).pack(side="left", padx=4)
        ctk.CTkButton(bottom_bar, text="📁 PDF", width=75, fg_color="gray25", command=lambda: open_folder(lucytrace.PDF)).pack(side="left", padx=4)

    def _build_single_tab(self):
        self.tab_single.grid_columnconfigure((0, 1), weight=1)
        self.tab_single.grid_rowconfigure(1, weight=1)

        # Top Control Area
        ctrl_card = ctk.CTkFrame(self.tab_single, fg_color="gray15")
        ctrl_card.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 8))
        ctrl_card.grid_columnconfigure(2, weight=1)

        # Row 1: Folder & File Selection, Dropdown, Prev/Next
        row1 = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=(8, 4))

        self.btn_pick_file = ctk.CTkButton(row1, text="📄 Pick Image...", width=110, command=self._pick_file)
        self.btn_pick_file.pack(side="left", padx=(0, 6))

        self.btn_pick_folder = ctk.CTkButton(row1, text="📁 Pick Folder...", width=110, fg_color="gray28", hover_color="gray38", command=self._pick_single_folder)
        self.btn_pick_folder.pack(side="left", padx=(0, 10))

        # Image Dropdown Menu
        self.img_dropdown_var = ctk.StringVar(value="No images found")
        self.img_dropdown = ctk.CTkOptionMenu(
            row1, 
            variable=self.img_dropdown_var,
            values=["No images found"],
            command=self._on_dropdown_select,
            width=220
        )
        self.img_dropdown.pack(side="left", padx=(0, 6), fill="x", expand=True)

        self.btn_prev = ctk.CTkButton(row1, text="◀ Prev", width=60, fg_color="gray30", command=self._prev_image)
        self.btn_prev.pack(side="left", padx=2)

        self.btn_next = ctk.CTkButton(row1, text="Next ▶", width=60, fg_color="gray30", command=self._next_image)
        self.btn_next.pack(side="left", padx=2)

        # Row 2: Status, Sync Zoom, Run Trace
        row2 = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=(4, 8))

        self.folder_info_lbl = ctk.CTkLabel(
            row2, 
            text=f"Folder: {self.active_input_folder.name}/", 
            font=ctk.CTkFont(size=11), 
            text_color="gray"
        )
        self.folder_info_lbl.pack(side="left", padx=(2, 10))

        self.sync_zoom_var = ctk.BooleanVar(value=True)
        self.sync_zoom_switch = ctk.CTkSwitch(
            row2, 
            text="🔗 Sync Zoom/Pan", 
            variable=self.sync_zoom_var
        )
        self.sync_zoom_switch.pack(side="right", padx=(10, 0))

        self.btn_trace_single = ctk.CTkButton(
            row2, 
            text="🚀 Process & Trace", 
            fg_color="#2b825b", 
            hover_color="#1f5d41",
            font=ctk.CTkFont(weight="bold"),
            command=self._start_single_trace
        )
        self.btn_trace_single.pack(side="right")

        # Previews
        self.viewer_orig = ZoomableImageViewer(
            self.tab_single, 
            title="Original Input",
            sync_callback=self._sync_to_result
        )
        self.viewer_orig.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)

        self.viewer_result = ZoomableImageViewer(
            self.tab_single, 
            title="Cleaned / Vector Result",
            sync_callback=self._sync_to_orig
        )
        self.viewer_result.grid(row=1, column=1, sticky="nsew", padx=6, pady=6)

    def _build_batch_tab(self):
        self.tab_batch.grid_columnconfigure(0, weight=1)
        self.tab_batch.grid_rowconfigure(2, weight=1)

        # Batch Folder Selector Card
        batch_header = ctk.CTkFrame(self.tab_batch, fg_color="gray15")
        batch_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(6, 8))

        top_row = ctk.CTkFrame(batch_header, fg_color="transparent")
        top_row.pack(fill="x", padx=12, pady=(10, 6))

        self.btn_change_batch_folder = ctk.CTkButton(
            top_row, 
            text="📁 Change Batch Folder...", 
            width=170, 
            command=self._pick_batch_folder
        )
        self.btn_change_batch_folder.pack(side="left", padx=(0, 10))

        self.btn_reset_batch_folder = ctk.CTkButton(
            top_row, 
            text="Reset to default (input_images/)", 
            width=180, 
            fg_color="gray28", 
            hover_color="gray38",
            command=self._reset_batch_folder
        )
        self.btn_reset_batch_folder.pack(side="left", padx=(0, 10))

        self.btn_run_batch = ctk.CTkButton(
            top_row, 
            text="🚀 Process All in Folder", 
            fg_color="#2b825b", 
            hover_color="#1f5d41",
            font=ctk.CTkFont(weight="bold"),
            command=self._start_batch_trace
        )
        self.btn_run_batch.pack(side="right")

        self.batch_folder_lbl = ctk.CTkLabel(
            batch_header, 
            text=f"Target: {self.batch_folder.resolve()}", 
            font=ctk.CTkFont(size=12),
            text_color="#60a5fa"
        )
        self.batch_folder_lbl.pack(anchor="w", padx=14, pady=(0, 10))

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self.tab_batch)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))
        self.progress_bar.set(0)

        # Log box
        self.log_box = ctk.CTkTextbox(self.tab_batch, wrap="word", height=280)
        self.log_box.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        self.log_box.insert("end", "LucyTrace Desktop Initialized.\nLogs and processing status will appear here.\n")

    def _sync_to_result(self, zoom, u, v):
        if self.sync_zoom_var.get() and hasattr(self, 'viewer_result'):
            self.viewer_result.set_view_sync(zoom, u, v)

    def _sync_to_orig(self, zoom, u, v):
        if self.sync_zoom_var.get() and hasattr(self, 'viewer_orig'):
            self.viewer_orig.set_view_sync(zoom, u, v)

    def _change_appearance_mode(self, mode: str):
        ctk.set_appearance_mode(mode)
        if hasattr(self, 'viewer_orig'):
            self.viewer_orig.update_theme(mode)
        if hasattr(self, 'viewer_result'):
            self.viewer_result.update_theme(mode)

    def _check_engines(self):
        tools = lucytrace.check_system_tools()
        self.status_magick.configure(
            text="🟢 ImageMagick" if tools["magick"] else "🔴 ImageMagick (Missing)",
            text_color="#4ade80" if tools["magick"] else "#f87171"
        )
        self.status_potrace.configure(
            text="🟢 Potrace" if tools["potrace"] else "🔴 Potrace (Missing)",
            text_color="#4ade80" if tools["potrace"] else "#f87171"
        )
        self.status_inkscape.configure(
            text="🟢 Inkscape" if tools["inkscape"] else "🔴 Inkscape (Missing)",
            text_color="#4ade80" if tools["inkscape"] else "#f87171"
        )

    def _update_thresh_label(self, val):
        self.thresh_label.configure(text=f"Threshold: {int(val)}%")

    def _get_current_gui_cfg(self):
        cfg = dict(self.cfg)
        cfg['profile'] = self.profile_var.get()
        cfg['threshold_percent'] = f"{int(self.thresh_slider.get())}%"
        cfg['level_adjustment'] = self.levels_entry.get().strip() or "10%,90%"
        cfg['mode'] = self.mode_var.get()
        cfg['invert'] = self.invert_var.get()
        cfg['turdsize'] = self.turdsize_entry.get().strip() or "5"
        cfg['export_width'] = self.width_entry.get().strip() or "3072"
        cfg['overwrite'] = self.overwrite_var.get()
        return cfg

    def _save_settings(self):
        cfg = self._get_current_gui_cfg()
        lucytrace.save_config(cfg)
        self.cfg = cfg
        self._log("Settings saved to lucytrace.ini")

    def _log(self, message: str):
        self.log_box.insert("end", f"{message}\n")
        self.log_box.see("end")

    # -------------------------------------------------------------
    # Image & Folder Selection Logic
    # -------------------------------------------------------------
    def _refresh_folder_images(self, select_filename=None):
        """Scan active_input_folder for supported images and update dropdown."""
        if not self.active_input_folder.exists():
            self.folder_images = []
        else:
            self.folder_images = sorted([
                f for f in self.active_input_folder.iterdir()
                if f.is_file() and f.suffix.lower() in lucytrace.SUPPORTED_EXTS
            ])

        names = [f.name for f in self.folder_images]
        total = len(names)

        if not names:
            self.img_dropdown.configure(values=["No images found"])
            self.img_dropdown_var.set("No images found")
            self.folder_info_lbl.configure(text=f"Folder: {self.active_input_folder.name}/ (0 images)")
            self.selected_image_path = None
            self.btn_trace_single.configure(state="disabled")
            self.viewer_orig.set_placeholder(f"No supported images found in\n{self.active_input_folder.name}/")
            self.viewer_result.set_placeholder("")
            return

        self.img_dropdown.configure(values=names)

        if select_filename and select_filename in names:
            idx = names.index(select_filename)
        else:
            idx = 0

        self.current_img_index = idx
        self.img_dropdown_var.set(names[idx])
        self._load_current_image()

    def _load_current_image(self):
        if not self.folder_images or self.current_img_index >= len(self.folder_images):
            return

        self.selected_image_path = self.folder_images[self.current_img_index]
        self.btn_trace_single.configure(state="normal")
        total = len(self.folder_images)
        self.folder_info_lbl.configure(
            text=f"Folder: {self.active_input_folder.name}/ ({self.current_img_index + 1}/{total})"
        )
        self.img_dropdown_var.set(self.selected_image_path.name)
        self.viewer_orig.set_image(self.selected_image_path)

        # Check if already processed
        stem = self.selected_image_path.stem
        out_png = lucytrace.PNG / f"{stem}.png"
        cleaned_png = lucytrace.CLEANED / f"{stem}.png"

        if out_png.exists():
            self.viewer_result.set_image(out_png)
        elif cleaned_png.exists():
            self.viewer_result.set_image(cleaned_png)
        else:
            self.viewer_result.set_placeholder("Ready to process.\nClick 'Process & Trace' to vectorize.")

    def _pick_file(self):
        filetypes = [("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp"), ("All files", "*.*")]
        selected = ctk.filedialog.askopenfilename(
            title="Select Image to Trace",
            initialdir=str(self.active_input_folder),
            filetypes=filetypes
        )
        if selected:
            path = Path(selected)
            self.active_input_folder = path.parent
            self._refresh_folder_images(select_filename=path.name)

    def _pick_single_folder(self):
        chosen = ctk.filedialog.askdirectory(
            title="Select Input Image Folder",
            initialdir=str(self.active_input_folder)
        )
        if chosen:
            self.active_input_folder = Path(chosen)
            self._refresh_folder_images()

    def _on_dropdown_select(self, filename: str):
        names = [f.name for f in self.folder_images]
        if filename in names:
            self.current_img_index = names.index(filename)
            self._load_current_image()

    def _prev_image(self):
        if not self.folder_images:
            return
        self.current_img_index = (self.current_img_index - 1) % len(self.folder_images)
        self._load_current_image()

    def _next_image(self):
        if not self.folder_images:
            return
        self.current_img_index = (self.current_img_index + 1) % len(self.folder_images)
        self._load_current_image()

    # -------------------------------------------------------------
    # Batch Folder Selection Logic
    # -------------------------------------------------------------
    def _pick_batch_folder(self):
        chosen = ctk.filedialog.askdirectory(
            title="Select Folder for Batch Processing",
            initialdir=str(self.batch_folder)
        )
        if chosen:
            self.batch_folder = Path(chosen)
            count = len([f for f in self.batch_folder.iterdir() if f.is_file() and f.suffix.lower() in lucytrace.SUPPORTED_EXTS])
            self.batch_folder_lbl.configure(text=f"Target: {self.batch_folder.resolve()} ({count} images found)")

    def _reset_batch_folder(self):
        self.batch_folder = lucytrace.INPUT
        count = len([f for f in self.batch_folder.iterdir() if f.is_file() and f.suffix.lower() in lucytrace.SUPPORTED_EXTS])
        self.batch_folder_lbl.configure(text=f"Target: {self.batch_folder.resolve()} ({count} images found)")

    # -------------------------------------------------------------
    # Trace Execution Handlers
    # -------------------------------------------------------------
    def _start_single_trace(self):
        if not self.selected_image_path or self.is_processing:
            return
        self.is_processing = True
        self.btn_trace_single.configure(state="disabled", text="⏳ Processing...")
        cfg = self._get_current_gui_cfg()

        def run_thread():
            try:
                res = lucytrace.process_single_image(
                    self.selected_image_path,
                    cfg,
                    profile=cfg['profile'],
                    mode=cfg['mode'],
                    invert_mode=cfg['invert'],
                    overwrite=cfg['overwrite'],
                    log_cb=self._log
                )
                self._log(f"Complete: {res['message']}")
                out_to_show = res['png'] if res['png'].exists() else res['cleaned']
                if out_to_show.exists():
                    self.after(0, lambda: self.viewer_result.set_image(out_to_show))
            except Exception as e:
                self._log(f"Error: {e}")
            finally:
                self.after(0, lambda: self.btn_trace_single.configure(state="normal", text="🚀 Process & Trace"))
                self.is_processing = False

        threading.Thread(target=run_thread, daemon=True).start()

    def _start_batch_trace(self):
        if self.is_processing:
            return
        self.is_processing = True
        self.btn_run_batch.configure(state="disabled", text="⏳ Processing Batch...")
        cfg = self._get_current_gui_cfg()
        target_dir = self.batch_folder

        def run_thread():
            try:
                input_files = sorted([f for f in target_dir.iterdir() if f.is_file() and f.suffix.lower() in lucytrace.SUPPORTED_EXTS])
                if not input_files:
                    self._log(f"No images found in {target_dir.name}/ to process.")
                    return

                total = len(input_files)
                self._log(f"Starting batch of {total} images from {target_dir.resolve()}...")
                for idx, img_file in enumerate(input_files, start=1):
                    self.after(0, lambda p=idx/total, i=idx, t=total: [
                        self.progress_bar.set(p),
                        self.btn_run_batch.configure(text=f"Processing {i} of {t}...")
                    ])
                    try:
                        res = lucytrace.process_single_image(
                            img_file,
                            cfg,
                            profile=cfg['profile'],
                            mode=cfg['mode'],
                            invert_mode=cfg['invert'],
                            overwrite=cfg['overwrite'],
                            log_cb=self._log
                        )
                        self._log(res['message'])
                    except Exception as err:
                        self._log(f"Failed {img_file.name}: {err}")

                self._log("Batch processing complete!")
            finally:
                self.after(0, lambda: [
                    self.btn_run_batch.configure(state="normal", text="🚀 Process All in Folder"),
                    self.progress_bar.set(1.0)
                ])
                self.is_processing = False

        threading.Thread(target=run_thread, daemon=True).start()


def main():
    app = LucyTraceApp()
    app.mainloop()


if __name__ == "__main__":
    main()

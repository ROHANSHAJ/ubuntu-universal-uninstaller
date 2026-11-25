#!/usr/bin/env python3
"""
Universal Ubuntu App Uninstaller GUI
Fast, Clutter-Free, Modern Dark Interface with Immediate List Updates
"""

import os
import sys
import threading
import time
import concurrent.futures
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

# Add scratch / repo dir to path
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import customtkinter as ctk
from PIL import Image

import engine

# Appearance settings
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class UniversalUninstallerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Universal App Uninstaller")
        self.geometry("1080x680")
        self.minsize(920, 580)

        # Center main window on screen
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        ww, wh = 1080, 680
        x = max(0, (sw - ww) // 2)
        y = max(0, (sh - wh) // 2)
        self.geometry(f"{ww}x{wh}+{x}+{y}")

        # Hide main window initially while splash runs
        self.withdraw()

        # Resolve icon path
        self.icon_path = Path.home() / ".local/share/icons/universal-uninstaller.png"
        if not self.icon_path.exists():
            self.icon_path = SCRIPT_DIR.parent / "assets" / "universal-uninstaller.png"

        if self.icon_path.exists():
            try:
                self.iconphoto(False, tk.PhotoImage(file=str(self.icon_path)))
            except Exception:
                pass

        self.all_apps = []
        self.filtered_apps = []
        self.selected_app = None
        self.batch_selected_ids = set()
        self.current_source_filter = "All"
        self.cached_residuals = {}
        self.cached_rea_reports = {}
        self.app_card_widgets = {}

        # Setup clutter-free UI
        self.setup_ui()

        # Display splash and run fast parallel scan
        self.show_splash_and_load()

    # -------------------------------------------------------------
    # FAST SPLASH & PARALLEL SCANNER
    # -------------------------------------------------------------
    def show_splash_and_load(self):
        self.splash = ctk.CTkToplevel()
        self.splash.overrideredirect(True)

        w, h = 460, 280
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.splash.geometry(f"{w}x{h}+{x}+{y}")
        self.splash.attributes("-topmost", True)

        card = ctk.CTkFrame(
            self.splash,
            corner_radius=14,
            fg_color="#0f172a",
            border_width=1,
            border_color="#0284c7"
        )
        card.pack(fill="both", expand=True, padx=2, pady=2)

        # Icon
        if self.icon_path and self.icon_path.exists():
            try:
                pil_img = Image.open(str(self.icon_path))
                self.splash_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(56, 56))
                icon_lbl = ctk.CTkLabel(card, text="", image=self.splash_img)
                icon_lbl.pack(pady=(22, 6))
            except Exception:
                icon_lbl = ctk.CTkLabel(card, text="[App Uninstaller]", font=ctk.CTkFont(size=18, weight="bold"))
                icon_lbl.pack(pady=(22, 6))
        else:
            icon_lbl = ctk.CTkLabel(card, text="[App Uninstaller]", font=ctk.CTkFont(size=18, weight="bold"))
            icon_lbl.pack(pady=(22, 6))

        title_lbl = ctk.CTkLabel(
            card,
            text="Universal App Uninstaller",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#f8fafc"
        )
        title_lbl.pack(pady=(0, 2))

        sub_lbl = ctk.CTkLabel(
            card,
            text="APT • Snap • Flatpak • Custom AppImages • REA Engine",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        sub_lbl.pack(pady=(0, 18))

        status_row = ctk.CTkFrame(card, fg_color="transparent")
        status_row.pack(fill="x", padx=40, pady=(0, 6))

        self.splash_status_lbl = ctk.CTkLabel(
            status_row,
            text="Scanning packages in parallel...",
            font=ctk.CTkFont(size=11),
            text_color="#38bdf8",
            anchor="w"
        )
        self.splash_status_lbl.pack(side="left")

        self.splash_progress = ctk.CTkProgressBar(
            card,
            width=380,
            height=6,
            corner_radius=3,
            fg_color="#1e293b",
            progress_color="#38bdf8"
        )
        self.splash_progress.set(0.3)
        self.splash_progress.pack(pady=(0, 20))

        self.splash.update()
        threading.Thread(target=self._fast_startup_worker, daemon=True).start()

    def _fast_startup_worker(self):
        t0 = time.time()
        dpkg_map = engine.get_dpkg_desktop_map()

        self.after(0, lambda: self._update_splash_status("Analyzing APT, Snap, Flatpak & Custom apps...", 0.6))

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            f_snaps = executor.submit(engine.get_installed_snaps)
            f_flatpaks = executor.submit(engine.get_installed_flatpaks)
            f_customs = executor.submit(engine.get_installed_custom_apps, dpkg_map)
            f_apts = executor.submit(engine.get_installed_apt_apps, dpkg_map)

            snaps = f_snaps.result()
            flatpaks = f_flatpaks.result()
            customs = f_customs.result()
            apts = f_apts.result()

        total_apps = customs + flatpaks + snaps + apts
        elapsed = time.time() - t0

        self.after(0, lambda: self._update_splash_status(f"Loaded {len(total_apps)} apps in {elapsed:.2f}s", 1.0))
        time.sleep(0.12)
        self.after(0, lambda: self._finish_startup(total_apps))

    def _update_splash_status(self, text, val):
        try:
            self.splash_status_lbl.configure(text=text)
            self.splash_progress.set(val)
            self.splash.update_idletasks()
        except Exception:
            pass

    def _finish_startup(self, total_apps):
        self.all_apps = total_apps
        self.filter_and_render_list()

        try:
            self.splash.destroy()
        except Exception:
            pass

        self.deiconify()
        self.lift()
        self.focus_force()

    # -------------------------------------------------------------
    # CLUTTER-FREE UI SETUP
    # -------------------------------------------------------------
    def setup_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=5) # Left: app list
        self.grid_columnconfigure(1, weight=4) # Right: inspector

        # ----------------- LEFT PANE -----------------
        self.left_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#0f172a")
        self.left_frame.grid(row=0, column=0, padx=(12, 6), pady=12, sticky="nsew")
        self.left_frame.grid_rowconfigure(3, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        # Header: Title + Refresh
        header_bar = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        header_bar.grid(row=0, column=0, padx=14, pady=(12, 6), sticky="ew")

        title_lbl = ctk.CTkLabel(
            header_bar,
            text="Installed Applications",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color="#f8fafc"
        )
        title_lbl.pack(side="left")

        self.refresh_btn = ctk.CTkButton(
            header_bar,
            text="Refresh",
            width=70,
            height=26,
            font=ctk.CTkFont(size=11),
            command=self.refresh_apps,
            fg_color="#1e293b",
            hover_color="#334155"
        )
        self.refresh_btn.pack(side="right")

        # Search Bar
        search_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        search_frame.grid(row=1, column=0, padx=14, pady=2, sticky="ew")

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search by name or package ID...",
            font=ctk.CTkFont(size=12),
            height=32,
            corner_radius=6,
            fg_color="#1e293b",
            border_color="#334155"
        )
        self.search_entry.pack(fill="x")
        self.search_entry.bind("<KeyRelease>", self.on_search_changed)

        # Segmented Filter Bar
        self.filter_var = ctk.StringVar(value="All")
        self.filter_bar = ctk.CTkSegmentedButton(
            self.left_frame,
            values=["All", "APT", "Snap", "Flatpak", "Custom"],
            variable=self.filter_var,
            command=self.on_filter_changed,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(size=11)
        )
        self.filter_bar.grid(row=2, column=0, padx=14, pady=(8, 8), sticky="ew")

        # Scrollable App List
        self.app_list_frame = ctk.CTkScrollableFrame(self.left_frame, corner_radius=6, fg_color="transparent")
        self.app_list_frame.grid(row=3, column=0, padx=10, pady=(0, 6), sticky="nsew")
        self.app_list_frame.grid_columnconfigure(0, weight=1)

        # Bottom Bar: Status + Batch Action
        bottom_bar = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        bottom_bar.grid(row=4, column=0, padx=14, pady=(4, 10), sticky="ew")

        self.status_label = ctk.CTkLabel(
            bottom_bar,
            text="Loading...",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
            anchor="w"
        )
        self.status_label.pack(side="left")

        self.batch_uninstall_btn = ctk.CTkButton(
            bottom_bar,
            text="Uninstall Selected (0)",
            width=140,
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#dc2626",
            hover_color="#b91c1c",
            command=self.on_batch_uninstall
        )
        self.batch_uninstall_btn.pack(side="right")

        # ----------------- RIGHT PANE (INSPECTOR) -----------------
        self.right_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#0f172a")
        self.right_frame.grid(row=0, column=1, padx=(6, 12), pady=12, sticky="nsew")
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        inspector_header = ctk.CTkLabel(
            self.right_frame,
            text="Application Details",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#f8fafc",
            anchor="w"
        )
        inspector_header.grid(row=0, column=0, padx=14, pady=(12, 6), sticky="ew")

        # Scrollable Details Area
        self.details_scroll = ctk.CTkScrollableFrame(self.right_frame, fg_color="transparent")
        self.details_scroll.grid(row=1, column=0, padx=10, pady=4, sticky="nsew")
        self.details_scroll.grid_columnconfigure(0, weight=1)

        # Action Buttons Container (Bottom)
        self.action_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.action_frame.grid(row=2, column=0, padx=14, pady=(6, 12), sticky="ew")

        self.uninstall_btn = ctk.CTkButton(
            self.action_frame,
            text="Uninstall & Clean Residue",
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#dc2626",
            hover_color="#b91c1c",
            command=self.on_uninstall_current
        )
        self.uninstall_btn.pack(fill="x", pady=2)
        self.uninstall_btn.configure(state="disabled")

        self.clean_residuals_only_btn = ctk.CTkButton(
            self.action_frame,
            text="Clean Residual Data Only",
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="#1e293b",
            hover_color="#334155",
            command=self.on_clean_residuals_only
        )
        self.clean_residuals_only_btn.pack(fill="x", pady=2)
        self.clean_residuals_only_btn.configure(state="disabled")

        self.render_empty_inspector()

    def render_empty_inspector(self, msg=None):
        for w in self.details_scroll.winfo_children():
            w.destroy()
        self.uninstall_btn.configure(state="disabled", text="Uninstall & Clean Residue")
        self.clean_residuals_only_btn.configure(state="disabled")

        empty_box = ctk.CTkFrame(self.details_scroll, fg_color="transparent")
        empty_box.pack(expand=True, pady=100)

        ctk.CTkLabel(
            empty_box,
            text=msg or "Select an application to inspect details and remove.",
            font=ctk.CTkFont(size=12),
            text_color="#64748b"
        ).pack()

    # -------------------------------------------------------------
    # FAST STREAMLINED APP LIST RENDERING
    # -------------------------------------------------------------
    def on_filter_changed(self, value):
        self.current_source_filter = value
        self.filter_and_render_list()

    def on_search_changed(self, event=None):
        self.filter_and_render_list()

    def filter_and_render_list(self):
        query = self.search_entry.get().strip().lower()
        cat = self.current_source_filter

        filtered = []
        for app in self.all_apps:
            src = app.get("source", "").lower()
            if cat == "APT" and src != "apt":
                continue
            elif cat == "Snap" and src != "snap":
                continue
            elif cat == "Flatpak" and src != "flatpak":
                continue
            elif cat == "Custom" and src != "custom":
                continue

            if query:
                searchable = f"{app['name']} {app['id']}".lower()
                if query not in searchable:
                    continue

            filtered.append(app)

        self.filtered_apps = filtered
        self.status_label.configure(text=f"{len(filtered)} of {len(self.all_apps)} applications")
        self.render_app_cards()

    def render_app_cards(self):
        # Clear existing cards
        for w in self.app_list_frame.winfo_children():
            w.destroy()
        self.app_card_widgets.clear()

        if not self.filtered_apps:
            ctk.CTkLabel(
                self.app_list_frame,
                text="No applications found.",
                font=ctk.CTkFont(size=12),
                text_color="#64748b"
            ).pack(pady=40)
            return

        for app in self.filtered_apps:
            app_id = app["id"]
            is_selected = (self.selected_app and self.selected_app["id"] == app_id)

            # Clean streamlined single row
            row = ctk.CTkFrame(
                self.app_list_frame,
                corner_radius=6,
                height=38,
                fg_color="#1e293b" if is_selected else "#111827"
            )
            row.pack(fill="x", pady=2, padx=2)
            row.pack_propagate(False)
            self.app_card_widgets[app_id] = row

            # Checkbox
            var = ctk.BooleanVar(value=(app_id in self.batch_selected_ids))
            def on_chk(a=app, v=var):
                if v.get():
                    self.batch_selected_ids.add(a["id"])
                else:
                    self.batch_selected_ids.discard(a["id"])
                self.batch_uninstall_btn.configure(text=f"Uninstall Selected ({len(self.batch_selected_ids)})")

            chk = ctk.CTkCheckBox(row, text="", variable=var, width=18, command=on_chk)
            chk.pack(side="left", padx=(8, 4))

            # Source Pill
            src = app.get("source", "APT")
            badge_color = {
                "APT": "#2563eb",
                "Snap": "#0284c7",
                "Flatpak": "#059669",
                "Custom": "#7c3aed"
            }.get(src, "#475569")

            badge = ctk.CTkLabel(
                row,
                text=src.upper(),
                font=ctk.CTkFont(size=9, weight="bold"),
                fg_color=badge_color,
                corner_radius=3,
                text_color="white",
                width=42,
                height=18
            )
            badge.pack(side="left", padx=4)

            # Name & ID
            name_lbl = ctk.CTkLabel(
                row,
                text=app["name"],
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#f1f5f9",
                anchor="w"
            )
            name_lbl.pack(side="left", padx=(6, 4))

            id_lbl = ctk.CTkLabel(
                row,
                text=f"({app['id']})",
                font=ctk.CTkFont(size=10),
                text_color="#64748b",
                anchor="w"
            )
            id_lbl.pack(side="left", padx=2)

            if app.get("protected"):
                prot_badge = ctk.CTkLabel(
                    row,
                    text="SYSTEM",
                    font=ctk.CTkFont(size=8, weight="bold"),
                    fg_color="#dc2626",
                    corner_radius=3,
                    text_color="white",
                    width=42,
                    height=16
                )
                prot_badge.pack(side="right", padx=8)

            # Click row to select
            for w in [row, badge, name_lbl, id_lbl]:
                w.bind("<Button-1>", lambda e, a=app: self.select_app(a))

    def select_app(self, app):
        old_id = self.selected_app["id"] if self.selected_app else None
        self.selected_app = app

        # Quick visual toggle on rows without redrawing entire list
        if old_id and old_id in self.app_card_widgets:
            try:
                self.app_card_widgets[old_id].configure(fg_color="#111827")
            except Exception:
                pass
        if app["id"] in self.app_card_widgets:
            try:
                self.app_card_widgets[app["id"]].configure(fg_color="#1e293b")
            except Exception:
                pass

        self.render_inspector(app)

    # -------------------------------------------------------------
    # CLUTTER-FREE INSPECTOR PANEL
    # -------------------------------------------------------------
    def render_inspector(self, app):
        for w in self.details_scroll.winfo_children():
            w.destroy()

        self.uninstall_btn.configure(state="normal", text=f"Uninstall & Clean Residue")
        self.clean_residuals_only_btn.configure(state="normal")

        # Header Info Card
        head_card = ctk.CTkFrame(self.details_scroll, corner_radius=8, fg_color="#1e293b")
        head_card.pack(fill="x", pady=(0, 6), padx=2)

        ctk.CTkLabel(
            head_card,
            text=app["name"],
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color="#f8fafc",
            anchor="w"
        ).pack(fill="x", padx=12, pady=(10, 2))

        ctk.CTkLabel(
            head_card,
            text=f"Source: {app['source']}  •  ID: {app['id']}  •  Version: {app.get('version', 'N/A')}",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
            anchor="w"
        ).pack(fill="x", padx=12, pady=(0, 10))

        # REA Binary Specs Card
        rea_card = ctk.CTkFrame(self.details_scroll, corner_radius=8, fg_color="#111827")
        rea_card.pack(fill="x", pady=4, padx=2)

        ctk.CTkLabel(
            rea_card,
            text="Technical Specs (REA Inspection)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#38bdf8",
            anchor="w"
        ).pack(fill="x", padx=12, pady=(8, 2))

        binary_path = app.get("binary_path")
        rea_info_lbl = ctk.CTkLabel(
            rea_card,
            text="Inspecting binary...",
            font=ctk.CTkFont(size=10),
            text_color="#94a3b8",
            justify="left",
            anchor="w"
        )
        rea_info_lbl.pack(fill="x", padx=12, pady=(0, 8))

        # Residuals Card
        res_card = ctk.CTkFrame(self.details_scroll, corner_radius=8, fg_color="#1e293b")
        res_card.pack(fill="x", pady=4, padx=2)

        ctk.CTkLabel(
            res_card,
            text="Discovered Residual Folders",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f8fafc",
            anchor="w"
        ).pack(fill="x", padx=12, pady=(8, 2))

        res_loading_lbl = ctk.CTkLabel(
            res_card,
            text="Scanning config & cache directories...",
            font=ctk.CTkFont(size=10),
            text_color="#94a3b8",
            anchor="w"
        )
        res_loading_lbl.pack(fill="x", padx=12, pady=(0, 8))

        # Background inspection worker
        def inspect_worker():
            rep = self.cached_rea_reports.get(app["id"])
            if not rep and binary_path:
                rep = engine.inspect_binary_rea(binary_path)
                self.cached_rea_reports[app["id"]] = rep

            residuals = self.cached_residuals.get(app["id"])
            if residuals is None:
                residuals = engine.find_residual_paths(app, rep)
                self.cached_residuals[app["id"]] = residuals

            self.after(0, lambda: self._update_inspector_ui(app, rep, residuals, rea_info_lbl, res_card, res_loading_lbl))

        threading.Thread(target=inspect_worker, daemon=True).start()

    def _update_inspector_ui(self, app, rep, residuals, rea_lbl, res_card, loading_lbl):
        try:
            loading_lbl.destroy()
        except Exception:
            pass

        # REA text
        if rep:
            tags = []
            if rep.get("is_appimage"):
                tags.append("AppImage")
            if rep.get("is_electron"):
                tags.append("Electron")
            tag_str = f" [{', '.join(tags)}]" if tags else ""

            text = (
                f"Binary: {app.get('binary_path') or 'Standard Package'}\n"
                f"Format: {rep['format']}{tag_str}\n"
                f"SHA-256: {rep['sha256'][:20]}..."
            )
            rea_lbl.configure(text=text)
        else:
            rea_lbl.configure(text=f"Binary: {app.get('binary_path') or 'Package Manager Container'}\nFormat: Standard package")

        # Residuals checkboxes
        self.residual_check_vars = []
        if residuals:
            total_bytes = sum(r["size_bytes"] for r in residuals)
            ctk.CTkLabel(
                res_card,
                text=f"Footprint: {engine.format_size(total_bytes)} ({len(residuals)} locations)",
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#f59e0b",
                anchor="w"
            ).pack(fill="x", padx=12, pady=(0, 4))

            for r in residuals:
                var = ctk.BooleanVar(value=True)
                self.residual_check_vars.append((r, var))

                row = ctk.CTkFrame(res_card, fg_color="transparent")
                row.pack(fill="x", padx=12, pady=1)

                chk = ctk.CTkCheckBox(
                    row,
                    text=f"{r['path']} ({r['size_str']})",
                    variable=var,
                    font=ctk.CTkFont(size=10),
                    width=16,
                    height=16
                )
                chk.pack(side="left")
        else:
            ctk.CTkLabel(
                res_card,
                text="No residual files detected.",
                font=ctk.CTkFont(size=10),
                text_color="#10b981",
                anchor="w"
            ).pack(fill="x", padx=12, pady=(0, 8))

    # -------------------------------------------------------------
    # IMMEDIATE REMOVAL UPON DELETE
    # -------------------------------------------------------------
    def remove_app_from_ui(self, app_id):
        """Immediately removes app from memory and UI list with 0 latency."""
        self.all_apps = [a for a in self.all_apps if a["id"] != app_id]
        self.filtered_apps = [a for a in self.filtered_apps if a["id"] != app_id]
        self.batch_selected_ids.discard(app_id)

        card = self.app_card_widgets.pop(app_id, None)
        if card:
            try:
                card.destroy()
            except Exception:
                pass

        if self.selected_app and self.selected_app["id"] == app_id:
            self.selected_app = None
            self.render_empty_inspector("Application removed.")

        self.status_label.configure(text=f"{len(self.filtered_apps)} of {len(self.all_apps)} applications")
        self.batch_uninstall_btn.configure(text=f"Uninstall Selected ({len(self.batch_selected_ids)})")

    def on_uninstall_current(self):
        if not self.selected_app:
            return

        app = self.selected_app
        if app.get("protected"):
            messagebox.showerror(
                "Protected Package",
                f"'{app['name']}' is an essential Ubuntu component and cannot be removed."
            )
            return

        selected_res = [r for r, var in getattr(self, "residual_check_vars", []) if var.get()]
        res_text = f"\nAlso purge {len(selected_res)} residual data folders." if selected_res else ""

        confirm = messagebox.askyesno(
            "Confirm Uninstall",
            f"Uninstall {app['name']} ({app['source']})?{res_text}"
        )
        if not confirm:
            return

        # 1. IMMEDIATELY remove from UI list!
        target_app = app
        target_residuals = selected_res
        self.remove_app_from_ui(target_app["id"])
        self.status_label.configure(text=f"Purging {target_app['name']} in background...")

        # 2. Run uninstallation in background thread
        def bg_uninstall():
            engine.execute_uninstallation(target_app, target_residuals)
            self.after(0, lambda: self.status_label.configure(
                text=f"Purged {target_app['name']} successfully ({len(self.all_apps)} remaining)"
            ))

        threading.Thread(target=bg_uninstall, daemon=True).start()

    def on_clean_residuals_only(self):
        if not self.selected_app:
            return

        selected_res = [r for r, var in getattr(self, "residual_check_vars", []) if var.get()]
        if not selected_res:
            messagebox.showinfo("No Residuals", "No residual folders selected.")
            return

        confirm = messagebox.askyesno("Clean Residuals", f"Permanently delete {len(selected_res)} residual folders?")
        if not confirm:
            return

        for r in selected_res:
            p = Path(r["path"])
            if p.is_dir():
                import shutil
                shutil.rmtree(p, ignore_errors=True)
            elif p.exists():
                p.unlink(missing_ok=True)

        self.cached_residuals.pop(self.selected_app["id"], None)
        self.render_inspector(self.selected_app)
        messagebox.showinfo("Cleaned", "Residual files deleted.")

    def on_batch_uninstall(self):
        if not self.batch_selected_ids:
            messagebox.showinfo("No Selection", "Please check one or more applications to uninstall.")
            return

        apps_to_remove = [a for a in self.all_apps if a["id"] in self.batch_selected_ids]
        protected = [a["name"] for a in apps_to_remove if a.get("protected")]
        if protected:
            messagebox.showerror("Protected Packages", f"Cannot remove core packages: {', '.join(protected)}")
            return

        confirm = messagebox.askyesno(
            "Confirm Batch Uninstall",
            f"Uninstall {len(apps_to_remove)} applications and their residuals?"
        )
        if not confirm:
            return

        # 1. IMMEDIATELY remove all selected apps from UI list!
        for a in apps_to_remove:
            self.remove_app_from_ui(a["id"])

        self.status_label.configure(text=f"Batch uninstalling {len(apps_to_remove)} apps in background...")

        # 2. Background worker
        def bg_batch():
            for a in apps_to_remove:
                res = engine.find_residual_paths(a)
                engine.execute_uninstallation(a, res)
            self.after(0, lambda: self.status_label.configure(
                text=f"Batch uninstallation complete. {len(self.all_apps)} applications remaining."
            ))

        threading.Thread(target=bg_batch, daemon=True).start()

    def refresh_apps(self):
        self.status_label.configure(text="Refreshing...")
        self.refresh_btn.configure(state="disabled")

        def scan_worker():
            dpkg_map = engine.get_dpkg_desktop_map()
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                f_snaps = executor.submit(engine.get_installed_snaps)
                f_flatpaks = executor.submit(engine.get_installed_flatpaks)
                f_customs = executor.submit(engine.get_installed_custom_apps, dpkg_map)
                f_apts = executor.submit(engine.get_installed_apt_apps, dpkg_map)

                snaps = f_snaps.result()
                flatpaks = f_flatpaks.result()
                customs = f_customs.result()
                apts = f_apts.result()

            total_apps = customs + flatpaks + snaps + apts
            self.after(0, lambda: self._on_refresh_complete(total_apps))

        threading.Thread(target=scan_worker, daemon=True).start()

    def _on_refresh_complete(self, total_apps):
        self.all_apps = total_apps
        self.refresh_btn.configure(state="normal")
        self.filter_and_render_list()


def main():
    app = UniversalUninstallerApp()
    app.mainloop()


if __name__ == "__main__":
    main()

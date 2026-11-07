#!/usr/bin/env python3
"""
Universal Ubuntu App Uninstaller GUI
Built with CustomTkinter & REA-style Binary Inspection
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

# Add scratch dir to path
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

        self.title("Universal App Uninstaller - Ubuntu")
        self.geometry("1100x720")
        self.minsize(950, 600)

        # Set window icon if exists
        icon_path = Path.home() / ".local/share/icons/universal-uninstaller.png"
        if icon_path.exists():
            try:
                self.iconphoto(False, tk.PhotoImage(file=str(icon_path)))
            except Exception:
                pass

        self.all_apps = []
        self.filtered_apps = []
        self.selected_app = None
        self.batch_selected_ids = set()
        self.current_source_filter = "All"
        self.cached_residuals = {}
        self.cached_rea_reports = {}

        self.setup_ui()
        self.refresh_apps()

    def setup_ui(self):
        # Configure grid layout (1 row, 2 columns: left list, right inspector)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=3) # App list
        self.grid_columnconfigure(1, weight=2) # Inspector pane

        # ----------------- LEFT PANE -----------------
        self.left_frame = ctk.CTkFrame(self, corner_radius=12)
        self.left_frame.grid(row=0, column=0, padx=(16, 8), pady=16, sticky="nsew")
        self.left_frame.grid_rowconfigure(3, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        # Title & Banner
        self.banner_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.banner_frame.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")

        self.title_label = ctk.CTkLabel(
            self.banner_frame,
            text="Universal App Uninstaller",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w"
        )
        self.title_label.pack(side="left")

        self.refresh_btn = ctk.CTkButton(
            self.banner_frame,
            text="⟳ Refresh",
            width=90,
            command=self.refresh_apps,
            fg_color="#334155",
            hover_color="#475569"
        )
        self.refresh_btn.pack(side="right")

        # Search Bar
        self.search_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.search_frame.grid(row=1, column=0, padx=16, pady=4, sticky="ew")

        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="🔍 Search apps by name, package ID, or keyword...",
            font=ctk.CTkFont(size=13),
            height=36
        )
        self.search_entry.pack(fill="x")
        self.search_entry.bind("<KeyRelease>", self.on_search_changed)

        # Filter Chips (Segmented Button)
        self.filter_var = ctk.StringVar(value="All")
        self.filter_bar = ctk.CTkSegmentedButton(
            self.left_frame,
            values=["All", "APT/Deb", "Snap", "Flatpak", "Custom / AppImage"],
            variable=self.filter_var,
            command=self.on_filter_changed,
            height=32
        )
        self.filter_bar.grid(row=2, column=0, padx=16, pady=(8, 12), sticky="ew")

        # Scrollable App List
        self.app_list_frame = ctk.CTkScrollableFrame(self.left_frame, corner_radius=8)
        self.app_list_frame.grid(row=3, column=0, padx=16, pady=(0, 12), sticky="nsew")
        self.app_list_frame.grid_columnconfigure(0, weight=1)

        # Left bottom action bar
        self.left_bottom_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.left_bottom_frame.grid(row=4, column=0, padx=16, pady=(0, 14), sticky="ew")

        self.status_label = ctk.CTkLabel(
            self.left_bottom_frame,
            text="Scanning installed packages...",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
            anchor="w"
        )
        self.status_label.pack(side="left")

        self.batch_uninstall_btn = ctk.CTkButton(
            self.left_bottom_frame,
            text="Uninstall Selected (0)",
            width=150,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            command=self.on_batch_uninstall
        )
        self.batch_uninstall_btn.pack(side="right")

        # ----------------- RIGHT PANE (INSPECTOR) -----------------
        self.right_frame = ctk.CTkFrame(self, corner_radius=12)
        self.right_frame.grid(row=0, column=1, padx=(8, 16), pady=16, sticky="nsew")
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.right_header = ctk.CTkLabel(
            self.right_frame,
            text="Application & Residue Inspector",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        self.right_header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")

        # Scrollable details container
        self.details_scroll = ctk.CTkScrollableFrame(self.right_frame, fg_color="transparent")
        self.details_scroll.grid(row=1, column=0, padx=16, pady=4, sticky="nsew")
        self.details_scroll.grid_columnconfigure(0, weight=1)

        self.placeholder_label = ctk.CTkLabel(
            self.details_scroll,
            text="👈 Select an application from the list to inspect\nits binary architecture, installation footprint,\nand leftover configuration/cache files.",
            font=ctk.CTkFont(size=13),
            text_color="#94a3b8",
            justify="center"
        )
        self.placeholder_label.pack(pady=120)

        # Right bottom button container
        self.action_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.action_frame.grid(row=2, column=0, padx=16, pady=(8, 16), sticky="ew")

        self.uninstall_btn = ctk.CTkButton(
            self.action_frame,
            text="🗑 Uninstall & Clean Residue",
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#dc2626",
            hover_color="#b91c1c",
            command=self.on_uninstall_current
        )
        self.uninstall_btn.pack(fill="x", pady=4)
        self.uninstall_btn.configure(state="disabled")

        self.clean_residuals_only_btn = ctk.CTkButton(
            self.action_frame,
            text="🧹 Clean Residual Data Only",
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color="#334155",
            hover_color="#475569",
            command=self.on_clean_residuals_only
        )
        self.clean_residuals_only_btn.pack(fill="x", pady=4)
        self.clean_residuals_only_btn.configure(state="disabled")

    def refresh_apps(self):
        self.status_label.configure(text="Scanning all application sources...")
        self.refresh_btn.configure(state="disabled")

        def scan_worker():
            snaps = engine.get_installed_snaps()
            flatpaks = engine.get_installed_flatpaks()
            customs = engine.get_installed_custom_apps()
            apts = engine.get_installed_apt_apps()
            total_apps = customs + flatpaks + snaps + apts
            self.after(0, lambda: self.on_scan_complete(total_apps))

        threading.Thread(target=scan_worker, daemon=True).start()

    def on_scan_complete(self, apps):
        self.all_apps = apps
        self.refresh_btn.configure(state="normal")
        self.filter_and_render_list()

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
            # Category match
            src = app.get("source", "").lower()
            if cat == "APT/Deb" and src != "apt":
                continue
            elif cat == "Snap" and src != "snap":
                continue
            elif cat == "Flatpak" and src != "flatpak":
                continue
            elif cat == "Custom / AppImage" and src != "custom":
                continue

            # Query match
            if query:
                searchable = f"{app['name']} {app['id']} {app.get('details', '')}".lower()
                if query not in searchable:
                    continue

            filtered.append(app)

        self.filtered_apps = filtered
        self.status_label.configure(text=f"Showing {len(filtered)} of {len(self.all_apps)} applications")
        self.render_app_cards()

    def render_app_cards(self):
        for widget in self.app_list_frame.winfo_children():
            widget.destroy()

        if not self.filtered_apps:
            no_lbl = ctk.CTkLabel(
                self.app_list_frame,
                text="No applications match the search/filter.",
                font=ctk.CTkFont(size=13),
                text_color="#94a3b8"
            )
            no_lbl.pack(pady=40)
            return

        for app in self.filtered_apps:
            card = ctk.CTkFrame(
                self.app_list_frame,
                corner_radius=8,
                fg_color="#1e293b" if (self.selected_app and self.selected_app["id"] == app["id"]) else "#0f172a"
            )
            card.pack(fill="x", pady=4, padx=4)

            # Checkbox for batch
            var = ctk.BooleanVar(value=(app["id"] in self.batch_selected_ids))
            def on_check(a=app, v=var):
                if v.get():
                    self.batch_selected_ids.add(a["id"])
                else:
                    self.batch_selected_ids.discard(a["id"])
                self.batch_uninstall_btn.configure(text=f"Uninstall Selected ({len(self.batch_selected_ids)})")

            chk = ctk.CTkCheckBox(card, text="", variable=var, width=24, command=on_check)
            chk.pack(side="left", padx=(10, 6))

            # Source badge colors
            src = app.get("source", "APT")
            badge_color = {
                "APT": "#2563eb",
                "Snap": "#0284c7",
                "Flatpak": "#059669",
                "Custom": "#7c3aed"
            }.get(src, "#475569")

            badge = ctk.CTkLabel(
                card,
                text=f" {src.upper()} ",
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=badge_color,
                corner_radius=4,
                text_color="white",
                height=20
            )
            badge.pack(side="left", padx=4)

            # Info block
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=8, pady=8)

            name_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
            name_frame.pack(fill="x")

            name_lbl = ctk.CTkLabel(
                name_frame,
                text=app["name"],
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w"
            )
            name_lbl.pack(side="left")

            if app.get("protected"):
                prot_badge = ctk.CTkLabel(
                    name_frame,
                    text=" SYSTEM CRITICAL ",
                    font=ctk.CTkFont(size=9, weight="bold"),
                    fg_color="#dc2626",
                    corner_radius=4,
                    text_color="white",
                    height=16
                )
                prot_badge.pack(side="left", padx=8)

            sub_lbl = ctk.CTkLabel(
                info_frame,
                text=f"ID: {app['id']}  •  {app.get('details', '')}",
                font=ctk.CTkFont(size=11),
                text_color="#94a3b8",
                anchor="w"
            )
            sub_lbl.pack(fill="x")

            # Make entire card clickable to select
            for w in [card, info_frame, name_frame, name_lbl, sub_lbl]:
                w.bind("<Button-1>", lambda e, a=app: self.select_app(a))

    def select_app(self, app):
        self.selected_app = app
        self.render_app_cards()
        self.render_inspector(app)

    def render_inspector(self, app):
        for widget in self.details_scroll.winfo_children():
            widget.destroy()

        self.uninstall_btn.configure(state="normal")
        self.clean_residuals_only_btn.configure(state="normal")

        # Top summary card
        top_card = ctk.CTkFrame(self.details_scroll, corner_radius=8, fg_color="#1e293b")
        top_card.pack(fill="x", pady=6)

        header_lbl = ctk.CTkLabel(
            top_card,
            text=app["name"],
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w"
        )
        header_lbl.pack(fill="x", padx=12, pady=(10, 2))

        meta_lbl = ctk.CTkLabel(
            top_card,
            text=f"Source: {app['source']} | ID: {app['id']}\nVersion: {app.get('version', 'N/A')}",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
            justify="left",
            anchor="w"
        )
        meta_lbl.pack(fill="x", padx=12, pady=(0, 10))

        # REA Binary Analysis Card
        rea_card = ctk.CTkFrame(self.details_scroll, corner_radius=8, fg_color="#0f172a")
        rea_card.pack(fill="x", pady=6)

        rea_header = ctk.CTkLabel(
            rea_card,
            text="🔬 REA Binary Architecture Analysis",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38bdf8",
            anchor="w"
        )
        rea_header.pack(fill="x", padx=12, pady=(10, 4))

        binary_path = app.get("binary_path")
        rea_info_lbl = ctk.CTkLabel(
            rea_card,
            text="Analyzing binary architecture & metadata...",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
            justify="left",
            anchor="w"
        )
        rea_info_lbl.pack(fill="x", padx=12, pady=(0, 10))

        # Residuals Card
        res_card = ctk.CTkFrame(self.details_scroll, corner_radius=8, fg_color="#1e293b")
        res_card.pack(fill="x", pady=6)

        res_header = ctk.CTkLabel(
            res_card,
            text="🧹 Discovered Residual Folders (Config / Cache / Data)",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        )
        res_header.pack(fill="x", padx=12, pady=(10, 4))

        res_loading_lbl = ctk.CTkLabel(
            res_card,
            text="Scanning ~/.config, ~/.cache, ~/.local/share...",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
            anchor="w"
        )
        res_loading_lbl.pack(fill="x", padx=12, pady=(0, 10))

        # Run REA & Residual scan in background
        def inspect_worker():
            rep = self.cached_rea_reports.get(app["id"])
            if not rep and binary_path:
                rep = engine.inspect_binary_rea(binary_path)
                self.cached_rea_reports[app["id"]] = rep

            residuals = self.cached_residuals.get(app["id"])
            if residuals is None:
                residuals = engine.find_residual_paths(app, rep)
                self.cached_residuals[app["id"]] = residuals

            self.after(0, lambda: self.update_inspector_results(app, rep, residuals, rea_info_lbl, res_card, res_loading_lbl))

        threading.Thread(target=inspect_worker, daemon=True).start()

    def update_inspector_results(self, app, rep, residuals, rea_info_lbl, res_card, res_loading_lbl):
        res_loading_lbl.destroy()

        # Update REA text
        if rep:
            tags = []
            if rep.get("is_appimage"):
                tags.append("AppImage SquashFS")
            if rep.get("is_electron"):
                tags.append("Electron / ASAR Bundle")
            tag_str = f" [{', '.join(tags)}]" if tags else ""

            text = (
                f"Binary: {app.get('binary_path') or 'N/A'}\n"
                f"Format: {rep['format']}{tag_str}\n"
                f"SHA-256: {rep['sha256'][:24]}...\n"
                f"Discovered Bundle IDs: {', '.join(rep.get('internal_ids', [])) or 'None'}"
            )
            rea_info_lbl.configure(text=text)
        else:
            rea_info_lbl.configure(text=f"Binary: {app.get('binary_path') or 'Package Manager Container'}\nInspection: Standard packaging format")

        # Update Residuals
        self.residual_check_vars = []
        if residuals:
            total_bytes = sum(r["size_bytes"] for r in residuals)
            tot_lbl = ctk.CTkLabel(
                res_card,
                text=f"Total Residual Footprint: {engine.format_size(total_bytes)} ({len(residuals)} items)",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#f59e0b",
                anchor="w"
            )
            tot_lbl.pack(fill="x", padx=12, pady=(0, 6))

            for r in residuals:
                var = ctk.BooleanVar(value=True)
                self.residual_check_vars.append((r, var))

                row = ctk.CTkFrame(res_card, fg_color="transparent")
                row.pack(fill="x", padx=12, pady=2)

                chk = ctk.CTkCheckBox(row, text=f"{r['path']} ({r['size_str']})", variable=var, font=ctk.CTkFont(size=11))
                chk.pack(side="left")
        else:
            no_res_lbl = ctk.CTkLabel(
                res_card,
                text="✓ No residual config or cache folders detected.",
                font=ctk.CTkFont(size=11),
                text_color="#10b981",
                anchor="w"
            )
            no_res_lbl.pack(fill="x", padx=12, pady=(0, 10))

    def on_uninstall_current(self):
        if not self.selected_app:
            return

        app = self.selected_app
        if app.get("protected"):
            messagebox.showerror(
                "Protected System Package",
                f"'{app['name']}' is a protected core component of Ubuntu.\nPurging it may compromise system stability."
            )
            return

        selected_res = [r for r, var in getattr(self, "residual_check_vars", []) if var.get()]
        res_text = f"\nAlso purge {len(selected_res)} residual config/cache directories." if selected_res else ""

        confirm = messagebox.askyesno(
            "Confirm Uninstallation",
            f"Are you sure you want to completely uninstall:\n\n{app['name']} ({app['source']})?{res_text}"
        )
        if not confirm:
            return

        self.execute_removal_modal([app], {app["id"]: selected_res})

    def on_clean_residuals_only(self):
        if not self.selected_app:
            return

        selected_res = [r for r, var in getattr(self, "residual_check_vars", []) if var.get()]
        if not selected_res:
            messagebox.showinfo("No Residuals Selected", "There are no residual folders selected for deletion.")
            return

        confirm = messagebox.askyesno(
            "Confirm Residual Cleanup",
            f"Permanently delete {len(selected_res)} residual config/cache folders?"
        )
        if not confirm:
            return

        for r in selected_res:
            p = Path(r["path"])
            if p.is_dir():
                import shutil
                shutil.rmtree(p, ignore_errors=True)
            elif p.exists():
                p.unlink(missing_ok=True)

        messagebox.showinfo("Success", "Residual folders deleted successfully.")
        self.cached_residuals.pop(self.selected_app["id"], None)
        self.render_inspector(self.selected_app)

    def on_batch_uninstall(self):
        if not self.batch_selected_ids:
            messagebox.showinfo("No Apps Selected", "Please check one or more applications to uninstall.")
            return

        apps_to_remove = [a for a in self.all_apps if a["id"] in self.batch_selected_ids]
        protected_in_selection = [a["name"] for a in apps_to_remove if a.get("protected")]
        if protected_in_selection:
            messagebox.showerror(
                "Protected Packages In Selection",
                f"The selection contains protected system packages: {', '.join(protected_in_selection)}.\nPlease uncheck them first."
            )
            return

        confirm = messagebox.askyesno(
            "Confirm Batch Uninstallation",
            f"Are you sure you want to uninstall {len(apps_to_remove)} applications?"
        )
        if not confirm:
            return

        self.execute_removal_modal(apps_to_remove, {})

    def execute_removal_modal(self, apps, residuals_map):
        modal = ctk.CTkToplevel(self)
        modal.title("Uninstalling Applications")
        modal.geometry("600x400")
        modal.transient(self)
        modal.grab_set()

        lbl = ctk.CTkLabel(modal, text="Uninstalling & Cleaning Residuals...", font=ctk.CTkFont(size=14, weight="bold"))
        lbl.pack(pady=12)

        progress_box = ctk.CTkTextbox(modal, font=ctk.CTkFont(family="monospace", size=11))
        progress_box.pack(fill="both", expand=True, padx=16, pady=8)

        close_btn = ctk.CTkButton(modal, text="Close", state="disabled", command=lambda: [modal.destroy(), self.refresh_apps()])
        close_btn.pack(pady=12)

        def log_cb(msg):
            progress_box.insert("end", msg + "\n")
            progress_box.see("end")

        def run_all():
            for a in apps:
                res = residuals_map.get(a["id"], [])
                engine.execute_uninstallation(a, res, progress_callback=log_cb)
            log_cb("\n✓ All requested uninstallations completed successfully!")
            self.batch_selected_ids.clear()
            self.batch_uninstall_btn.configure(text="Uninstall Selected (0)")
            close_btn.configure(state="normal")

        threading.Thread(target=run_all, daemon=True).start()

def main():
    app = UniversalUninstallerApp()
    app.mainloop()

if __name__ == "__main__":
    main()

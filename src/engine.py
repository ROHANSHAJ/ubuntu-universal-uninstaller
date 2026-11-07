#!/usr/bin/env python3
"""
Engine for Universal Ubuntu App Uninstaller with REA-style Binary Inspection.
"""

import os
import sys
import shutil
import subprocess
import hashlib
import re
from pathlib import Path

PROTECTED_PACKAGES = {
    "systemd", "systemd-sysv", "udev", "libc6", "linux-image-generic",
    "ubuntu-desktop", "ubuntu-desktop-minimal", "gnome-shell", "xorg",
    "sudo", "apt", "dpkg", "bash", "coreutils", "login", "init", "grub-pc",
    "grub-efi-amd64", "dbus", "snapd"
}

def is_cmd_available(cmd):
    return shutil.which(cmd) is not None

def run_cmd(cmd_list, capture=True):
    try:
        return subprocess.run(
            cmd_list,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            text=True,
            check=False
        )
    except Exception:
        return None

def get_file_sha256(path):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return "N/A"

def get_dir_size(path):
    total = 0
    try:
        path = Path(path)
        if path.is_file():
            return path.stat().st_size
        for entry in path.rglob("*"):
            if entry.is_file() and not entry.is_symlink():
                total += entry.stat().st_size
    except Exception:
        pass
    return total

def format_size(bytes_size):
    if bytes_size is None or bytes_size == 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"

def is_managed_by_dpkg(file_path):
    res = run_cmd(["dpkg", "-S", str(file_path)])
    return res and res.returncode == 0

def inspect_binary_rea(binary_path):
    """
    REA-style binary inspector:
    Analyzes ELF headers, AppImage squashfs, Electron ASAR, and config path references.
    """
    binary_path = Path(binary_path)
    if not binary_path.exists():
        return {
            "format": "Unknown (File not found)",
            "sha256": "N/A",
            "is_appimage": False,
            "is_electron": False,
            "internal_ids": [],
            "suggested_paths": []
        }

    sha256 = get_file_sha256(binary_path)
    file_type_out = ""
    res = run_cmd(["file", "-b", str(binary_path)])
    if res and res.returncode == 0:
        file_type_out = res.stdout.strip()

    is_appimage = False
    is_electron = False
    internal_ids = set()
    suggested_paths = set()

    # Read header bytes
    try:
        header = binary_path.read_bytes()[:1024]
        if b"AI\x02" in header or "appimage" in file_type_out.lower() or binary_path.name.lower().endswith(".appimage"):
            is_appimage = True
    except Exception:
        pass

    # If AppImage, try to inspect SquashFS offset & contents
    if is_appimage:
        offset_res = run_cmd([str(binary_path), "--appimage-offset"])
        offset = None
        if offset_res and offset_res.returncode == 0 and offset_res.stdout.strip().isdigit():
            offset = offset_res.stdout.strip()
        
        if offset and is_cmd_available("unsquashfs"):
            list_res = run_cmd(["unsquashfs", "-o", offset, "-l", str(binary_path)])
            if list_res and list_res.returncode == 0:
                stdout = list_res.stdout
                if "app.asar" in stdout or "electron" in stdout.lower():
                    is_electron = True
                
                # Check for internal .desktop files
                for m in re.finditer(r"squashfs-root/([a-zA-Z0-9_\-\.]+)\.desktop", stdout):
                    internal_ids.add(m.group(1))

    # Fast strings scan for hidden ~/.config/ or ~/.local/share/ references
    if is_cmd_available("strings") and binary_path.is_file() and binary_path.stat().st_size < 100 * 1024 * 1024:
        # Scan first 10MB of binary
        cmd = ["head", "-c", "10485760", str(binary_path)]
        head_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        strings_proc = subprocess.Popen(["strings", "-n", "4"], stdin=head_proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        head_proc.stdout.close()
        out, _ = strings_proc.communicate()
        if out:
            for m in re.finditer(r"\.config/([a-zA-Z0-9_\-\.]{3,30})", out):
                matched = m.group(1).rstrip("/\"' ;,)")
                if not matched.startswith("dconf") and not matched.startswith("gtk"):
                    suggested_paths.add(matched)
            if "electron.asar" in out or "node_modules" in out:
                is_electron = True

    return {
        "format": file_type_out or "Binary",
        "sha256": sha256,
        "is_appimage": is_appimage,
        "is_electron": is_electron,
        "internal_ids": sorted(list(internal_ids)),
        "suggested_paths": sorted(list(suggested_paths))
    }

def parse_desktop_file(filepath):
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    name = None
    exec_cmd = None
    icon = None
    comment = None
    no_display = False

    for line in content.splitlines():
        line = line.strip()
        if line.startswith("Name=") and name is None:
            name = line.split("=", 1)[1]
        elif line.startswith("Exec=") and exec_cmd is None:
            exec_cmd = line.split("=", 1)[1]
        elif line.startswith("Icon=") and icon is None:
            icon = line.split("=", 1)[1]
        elif line.startswith("Comment=") and comment is None:
            comment = line.split("=", 1)[1]
        elif line.startswith("NoDisplay="):
            val = line.split("=", 1)[1].lower()
            if val == "true":
                no_display = True

    if not name or not exec_cmd or no_display:
        return None

    raw_exec = exec_cmd.split()[0].strip('"\'')
    exec_path = None
    if os.path.isabs(raw_exec):
        exec_path = Path(raw_exec)
    else:
        which_path = shutil.which(raw_exec)
        if which_path:
            exec_path = Path(which_path)

    return {
        "name": name,
        "exec_cmd": exec_cmd,
        "exec_path": exec_path,
        "icon": icon,
        "comment": comment or "",
        "desktop_file": filepath
    }

def get_installed_snaps():
    if not is_cmd_available("snap"):
        return []
    res = run_cmd(["snap", "list"])
    if not res or res.returncode != 0:
        return []

    snaps = []
    lines = res.stdout.strip().split("\n")
    if len(lines) > 1:
        for line in lines[1:]:
            parts = line.split()
            if not parts:
                continue
            name = parts[0]
            version = parts[1] if len(parts) > 1 else ""
            notes = " ".join(parts[2:]) if len(parts) > 2 else ""
            snaps.append({
                "source": "Snap",
                "id": name,
                "name": name,
                "version": version,
                "details": f"Snap ({notes.strip()})",
                "binary_path": f"/snap/bin/{name}" if Path(f"/snap/bin/{name}").exists() else None,
                "removable_paths": [],
                "protected": name in ("snapd", "bare", "core20", "core22", "core24")
            })
    return snaps

def get_installed_flatpaks():
    if not is_cmd_available("flatpak"):
        return []
    res = run_cmd(["flatpak", "list", "--app", "--columns=application,name,version,origin,size"])
    if not res or res.returncode != 0:
        return []

    flatpaks = []
    for line in res.stdout.strip().split("\n"):
        parts = line.split("\t")
        if len(parts) >= 2:
            app_id = parts[0].strip()
            app_name = parts[1].strip()
            version = parts[2].strip() if len(parts) > 2 else ""
            origin = parts[3].strip() if len(parts) > 3 else ""
            size = parts[4].strip() if len(parts) > 4 else ""
            flatpaks.append({
                "source": "Flatpak",
                "id": app_id,
                "name": app_name or app_id,
                "version": version,
                "details": f"Flatpak ({origin}) - {size}".strip(),
                "binary_path": None,
                "removable_paths": [],
                "protected": False
            })
    return flatpaks

def get_installed_custom_apps():
    apps = []
    desktop_dirs = [
        Path.home() / ".local/share/applications",
        Path("/usr/local/share/applications"),
        Path("/usr/share/applications")
    ]

    seen = set()

    for d in desktop_dirs:
        if not d.exists():
            continue
        for df in sorted(d.glob("*.desktop")):
            data = parse_desktop_file(df)
            if not data:
                continue

            if data["name"] in seen:
                continue

            exec_path = data["exec_path"]
            desktop_path = data["desktop_file"]

            # Filter out entries handled by Flatpak or Snap
            if "/var/lib/flatpak" in str(desktop_path) or "/var/lib/snapd" in str(desktop_path) or "/snap/" in str(desktop_path):
                continue

            is_custom = False
            associated = [desktop_path]

            if str(desktop_path).startswith(str(Path.home())):
                is_custom = True
            elif exec_path:
                if str(exec_path).startswith(str(Path.home())):
                    is_custom = True
                elif "/opt/" in str(exec_path) or "/usr/local/" in str(exec_path):
                    if not is_managed_by_dpkg(desktop_path):
                        is_custom = True
                elif not is_managed_by_dpkg(desktop_path) and not is_managed_by_dpkg(exec_path):
                    is_custom = True

            if is_custom:
                seen.add(data["name"])
                if exec_path and exec_path.exists():
                    if str(exec_path).lower().endswith(".appimage"):
                        associated.append(exec_path)
                    elif "/opt/" in str(exec_path):
                        parts = exec_path.parts
                        if len(parts) >= 3 and parts[1] == "opt":
                            app_opt = Path("/opt") / parts[2]
                            if app_opt.exists() and not is_managed_by_dpkg(app_opt):
                                associated.append(app_opt)
                            else:
                                associated.append(exec_path)
                        else:
                            associated.append(exec_path)
                    elif str(exec_path).startswith(str(Path.home())):
                        associated.append(exec_path)

                # Icon check
                if data.get("icon") and not data["icon"].startswith("/"):
                    icon_path = Path.home() / f".local/share/icons/{data['icon']}.png"
                    if icon_path.exists():
                        associated.append(icon_path)

                apps.append({
                    "source": "Custom",
                    "id": str(desktop_path),
                    "name": data["name"],
                    "version": "Standalone",
                    "details": data["comment"] or f"Launcher: {desktop_path.name}",
                    "binary_path": str(exec_path) if exec_path else None,
                    "removable_paths": associated,
                    "protected": False
                })

    return apps

def get_installed_apt_apps():
    """Returns top-level installed APT applications that have desktop entries."""
    if not is_cmd_available("dpkg-query"):
        return []

    desktop_dir = Path("/usr/share/applications")
    if not desktop_dir.exists():
        return []

    # Run dpkg -S in a single batch for all desktop files
    res = run_cmd(["dpkg", "-S", "/usr/share/applications/*.desktop"])
    if not res or res.returncode != 0:
        return []

    desktop_to_pkg = {}
    for line in res.stdout.strip().splitlines():
        if ": " in line:
            pkg, path = line.split(": ", 1)
            # handle multiarch pkg:amd64
            pkg = pkg.split(":")[0].strip()
            desktop_to_pkg[path.strip()] = pkg

    pkgs = {}
    for path_str, pkg in desktop_to_pkg.items():
        if pkg not in pkgs:
            p = Path(path_str)
            data = parse_desktop_file(p)
            if data:
                pkgs[pkg] = {
                    "name": data["name"],
                    "desktop": p,
                    "exec": str(data["exec_path"]) if data["exec_path"] else None,
                    "comment": data.get("comment", "")
                }

    apps = []
    for pkg_name, info in pkgs.items():
        is_prot = (pkg_name in PROTECTED_PACKAGES)
        apps.append({
            "source": "APT",
            "id": pkg_name,
            "name": info["name"],
            "version": "deb",
            "details": info["comment"] or f"APT package: {pkg_name}",
            "binary_path": info["exec"],
            "removable_paths": [],
            "protected": is_prot
        })
    return sorted(apps, key=lambda x: x["name"].lower())

BLACKLIST_RESIDUAL_NAMES = {
    "desktop-directories", "gnome", "gtk-3.0", "gtk-4.0", "dconf",
    "pulse", "systemd", "menus", "trash", "mime", "applications",
    "icons", "themes", "ibus", "fontconfig", "sounds", "autostart",
    "pulse", "user-dirs.dirs", "user-dirs.locale", "gconf"
}

def find_residual_paths(app_entry, rea_report=None):
    """
    Scans for leftover files & folders using app name, ID, and REA-extracted identifiers.
    """
    candidates = set()
    app_name = app_entry.get("name", "")
    app_id = app_entry.get("id", "")

    patterns = {
        app_name.lower().replace(" ", "-"),
        app_name.lower().replace(" ", "_"),
        app_name.lower().replace(" ", ""),
        app_name.lower()
    }

    if app_id:
        patterns.add(app_id.lower())
        parts = app_id.lower().split(".")
        if len(parts) > 1 and len(parts[-1]) >= 3:
            patterns.add(parts[-1])

    # Add REA-discovered IDs if available
    if rea_report:
        for iid in rea_report.get("internal_ids", []):
            patterns.add(iid.lower())
        for sp in rea_report.get("suggested_paths", []):
            patterns.add(sp.lower())

    search_roots = [
        Path.home() / ".config",
        Path.home() / ".cache",
        Path.home() / ".local/share",
        Path.home() / ".var/app",
        Path.home() / "snap"
    ]

    found_items = []
    for root in search_roots:
        if not root.exists():
            continue
        try:
            for item in root.iterdir():
                item_name = item.name.lower()
                if item_name in BLACKLIST_RESIDUAL_NAMES:
                    continue
                for pat in patterns:
                    if len(pat) >= 3:
                        if item_name == pat or item_name.startswith(pat + "-") or item_name.startswith(pat + "."):
                            if item not in candidates:
                                candidates.add(item)
                                size = get_dir_size(item)
                                found_items.append({
                                    "path": item,
                                    "size_bytes": size,
                                    "size_str": format_size(size)
                                })
        except (PermissionError, FileNotFoundError):
            continue

    return sorted(found_items, key=lambda x: x["size_bytes"], reverse=True)

def execute_uninstallation(app_entry, selected_residuals=None, progress_callback=None):
    """
    Uninstalls the app and purges residual paths.
    progress_callback(str)
    """
    source = app_entry.get("source", "").lower()
    app_id = app_entry.get("id", "")

    if progress_callback:
        progress_callback(f"Starting uninstallation of {app_entry['name']} ({source.upper()})...")

    if source == "snap":
        cmd = ["sudo", "snap", "remove", "--purge", app_id]
        if progress_callback:
            progress_callback(f"Executing: {' '.join(cmd)}")
        run_cmd(cmd, capture=False)

    elif source == "flatpak":
        cmd = ["flatpak", "uninstall", "--delete-data", "-y", app_id]
        if progress_callback:
            progress_callback(f"Executing: {' '.join(cmd)}")
        run_cmd(cmd, capture=False)
        run_cmd(["flatpak", "uninstall", "--unused", "-y"], capture=False)

    elif source == "apt":
        cmd = ["sudo", "apt", "purge", "-y", app_id]
        if progress_callback:
            progress_callback(f"Executing: {' '.join(cmd)}")
        run_cmd(cmd, capture=False)
        run_cmd(["sudo", "apt", "autoremove", "--purge", "-y"], capture=False)

    elif source == "custom":
        paths = app_entry.get("removable_paths", [])
        for p in paths:
            p = Path(p)
            if progress_callback:
                progress_callback(f"Removing custom path: {p}")
            needs_sudo = not os.access(p.parent if p.exists() else Path.home(), os.W_OK)
            if needs_sudo:
                run_cmd(["sudo", "rm", "-rf", str(p)], capture=False)
            else:
                if p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
                elif p.exists():
                    p.unlink(missing_ok=True)

        if is_cmd_available("update-desktop-database"):
            run_cmd(["update-desktop-database", str(Path.home() / ".local/share/applications")])

    # Residue cleanup
    if selected_residuals:
        for item in selected_residuals:
            p = Path(item["path"] if isinstance(item, dict) else item)
            if progress_callback:
                progress_callback(f"Purging residual folder: {p}")
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            elif p.exists():
                p.unlink(missing_ok=True)

    if progress_callback:
        progress_callback(f"Completed uninstallation for {app_entry['name']}.")
    return True

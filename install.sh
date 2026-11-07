#!/usr/bin/env bash
set -e

# ANSI Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}======================================================${NC}"
echo -e "${CYAN}   Installing Ubuntu Universal App Uninstaller        ${NC}"
echo -e "${CYAN}======================================================${NC}"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
DESKTOP_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor/256x256/apps"

mkdir -p "${BIN_DIR}" "${DESKTOP_DIR}" "${ICON_DIR}"

# 1. Check Python 3
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed.${NC}"
    exit 1
fi

# 2. Check dependencies (customtkinter, Pillow)
echo -e "${YELLOW}Checking dependencies...${NC}"
python3 -c "import customtkinter, PIL" 2>/dev/null || {
    echo -e "${YELLOW}Installing required Python dependencies via pip...${NC}"
    pip3 install -r "${REPO_DIR}/requirements.txt" || {
        echo -e "${RED}Failed to install dependencies via pip. Please run: pip install -r requirements.txt${NC}"
    }
}

# 3. Ensure scripts are executable
chmod +x "${REPO_DIR}/src/uni_gui.py"
chmod +x "${REPO_DIR}/src/uni-uninstall"
chmod +x "${REPO_DIR}/src/engine.py"

# 4. Link binaries to ~/.local/bin
echo -e "${YELLOW}Setting up CLI and GUI binaries in ${BIN_DIR}...${NC}"
ln -sf "${REPO_DIR}/src/uni_gui.py" "${BIN_DIR}/uni-uninstaller-gui"
ln -sf "${REPO_DIR}/src/uni_gui.py" "${BIN_DIR}/universal-uninstaller"
ln -sf "${REPO_DIR}/src/uni-uninstall" "${BIN_DIR}/uni-uninstall"

# 5. Install App Icon
echo -e "${YELLOW}Installing desktop icon...${NC}"
cp "${REPO_DIR}/assets/universal-uninstaller.png" "${ICON_DIR}/universal-uninstaller.png"
mkdir -p "${HOME}/.local/share/icons"
cp "${REPO_DIR}/assets/universal-uninstaller.png" "${HOME}/.local/share/icons/universal-uninstaller.png"

# 6. Install .desktop file
echo -e "${YELLOW}Installing GNOME application launcher...${NC}"
cat << 'EOF' > "${DESKTOP_DIR}/universal-uninstaller.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=Universal App Uninstaller
GenericName=Package & App Uninstaller
Comment=Universal uninstaller for APT, Snap, Flatpak, and Custom AppImages with residue cleanup
Exec=/home/rohan/.local/bin/uni-uninstaller-gui
Icon=universal-uninstaller
Terminal=false
Categories=System;Utility;
Keywords=uninstall;remove;purge;clean;stacer;flatpak;snap;apt;appimage;rea;
StartupNotify=true
EOF

chmod +x "${DESKTOP_DIR}/universal-uninstaller.desktop"

# 7. Update desktop database
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true
fi

# 8. Check PATH
if [[ ":$PATH:" != *":${BIN_DIR}:"* ]]; then
    echo -e "${YELLOW}Notice: ${BIN_DIR} is not in your current PATH. Consider adding:${NC}"
    echo '  export PATH="$HOME/.local/bin:$PATH"'
fi

echo -e "\n${GREEN}✓ Universal App Uninstaller successfully installed!${NC}"
echo -e "You can launch it by:"
echo -e "  • GUI: Searching for ${CYAN}'Universal App Uninstaller'${NC} in your apps or running: ${CYAN}uni-uninstaller-gui${NC}"
echo -e "  • CLI: Running ${CYAN}uni-uninstall <appname>${NC} in any terminal\n"

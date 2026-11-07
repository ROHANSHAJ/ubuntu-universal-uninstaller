#!/usr/bin/env bash
set -e

# ANSI Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Uninstalling Ubuntu Universal App Uninstaller...${NC}"

rm -f "${HOME}/.local/bin/uni-uninstaller-gui"
rm -f "${HOME}/.local/bin/universal-uninstaller"
rm -f "${HOME}/.local/bin/uni-uninstall"
rm -f "${HOME}/.local/share/applications/universal-uninstaller.desktop"
rm -f "${HOME}/.local/share/icons/universal-uninstaller.png"
rm -f "${HOME}/.local/share/icons/hicolor/256x256/apps/universal-uninstaller.png"

if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "${HOME}/.local/share/applications" 2>/dev/null || true
fi

echo -e "${GREEN}✓ Universal App Uninstaller removed from your system.${NC}"

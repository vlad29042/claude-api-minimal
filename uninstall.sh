#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${RED}================================${NC}"
echo -e "${RED}Claude Code API Uninstaller${NC}"
echo -e "${RED}================================${NC}\n"

INSTALL_DIR="$HOME/claude-api"
SERVICE_NAME="claude-api"

echo -e "${YELLOW}This will remove:${NC}"
echo -e "  - Service: ${RED}$SERVICE_NAME${NC}"
echo -e "  - Installation: ${RED}$INSTALL_DIR${NC}"
echo -e "  - Logs and data\n"

read -p "Are you sure? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Cancelled${NC}"
    exit 0
fi

# 1. Stop service
echo -e "\n${YELLOW}1️⃣ Stopping service...${NC}"
if sudo systemctl is-active --quiet ${SERVICE_NAME}.service; then
    sudo systemctl stop ${SERVICE_NAME}.service
    echo -e "${GREEN}✅ Service stopped${NC}"
else
    echo -e "${YELLOW}Service not running${NC}"
fi

# 2. Disable service
echo -e "\n${YELLOW}2️⃣ Disabling service...${NC}"
if sudo systemctl is-enabled --quiet ${SERVICE_NAME}.service 2>/dev/null; then
    sudo systemctl disable ${SERVICE_NAME}.service
    echo -e "${GREEN}✅ Service disabled${NC}"
else
    echo -e "${YELLOW}Service not enabled${NC}"
fi

# 3. Remove service file
echo -e "\n${YELLOW}3️⃣ Removing service file...${NC}"
if [ -f "/etc/systemd/system/${SERVICE_NAME}.service" ]; then
    sudo rm /etc/systemd/system/${SERVICE_NAME}.service
    sudo systemctl daemon-reload
    echo -e "${GREEN}✅ Service file removed${NC}"
else
    echo -e "${YELLOW}Service file not found${NC}"
fi

# 4. Remove installation directory
echo -e "\n${YELLOW}4️⃣ Removing installation directory...${NC}"
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
    echo -e "${GREEN}✅ Installation directory removed${NC}"
else
    echo -e "${YELLOW}Installation directory not found${NC}"
fi

# 5. Optional: Remove Claude CLI
read -p "Remove Claude CLI? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v claude >/dev/null 2>&1; then
        sudo npm uninstall -g @anthropic-ai/claude-cli
        echo -e "${GREEN}✅ Claude CLI removed${NC}"
    else
        echo -e "${YELLOW}Claude CLI not installed${NC}"
    fi
fi

echo -e "\n${GREEN}================================${NC}"
echo -e "${GREEN}✅ Uninstallation Complete!${NC}"
echo -e "${GREEN}================================${NC}\n"

echo -e "${YELLOW}Note: Claude credentials (~/.claude/) were NOT removed${NC}"
echo -e "${YELLOW}To remove manually: rm -rf ~/.claude${NC}\n"

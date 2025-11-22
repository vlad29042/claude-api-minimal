#!/bin/bash
set -e

# If script is being piped from curl, save it first and re-execute
if [ "$0" = "bash" ] || [ "$0" = "-bash" ] || [ "$0" = "sh" ]; then
    TEMP_SCRIPT=$(mktemp /tmp/claude-install.XXXXXX.sh)
    cat > "$TEMP_SCRIPT"
    chmod +x "$TEMP_SCRIPT"
    exec bash "$TEMP_SCRIPT" "$@"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Claude Code Minimal API Installer${NC}"
echo -e "${GREEN}================================${NC}\n"

# Function to check command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Determine installation directory and service name based on user
if [ "$EUID" -eq 0 ]; then
    INSTALL_DIR="/home/claude/claude-api"
    TARGET_USER="claude"
else
    INSTALL_DIR="$HOME/claude-api"
    TARGET_USER="$USER"
fi

SERVICE_NAME="claude-api"

# ROOT SECTION - System-level installations
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Running as root - performing system-level setup...${NC}\n"

    # Create claude user if doesn't exist
    if ! id -u claude >/dev/null 2>&1; then
        useradd -m -s /bin/bash claude
        echo -e "${GREEN}✅ User 'claude' created${NC}"
    else
        echo -e "${GREEN}✅ User 'claude' already exists${NC}"
    fi

    # 1. Check and install Python 3
    echo -e "\n${YELLOW}1️⃣ Checking Python 3...${NC}"
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version)
        echo -e "${GREEN}✅ $PYTHON_VERSION found${NC}"
    else
        echo -e "${RED}❌ Python 3 not found. Installing...${NC}"
        apt update
        apt install -y python3 python3-pip python3-venv
    fi

    # 2. Check and install Node.js
    echo -e "\n${YELLOW}2️⃣ Checking Node.js...${NC}"
    if command_exists node; then
        NODE_VERSION=$(node --version)
        echo -e "${GREEN}✅ Node.js $NODE_VERSION found${NC}"
    else
        echo -e "${RED}❌ Node.js not found. Installing...${NC}"
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
        apt install -y nodejs
    fi

    # 3. Install git
    echo -e "\n${YELLOW}3️⃣ Checking git...${NC}"
    if command_exists git; then
        echo -e "${GREEN}✅ git already installed${NC}"
    else
        echo -e "${YELLOW}Installing git...${NC}"
        apt update && apt install -y git
    fi

    # 4. Install Claude CLI
    echo -e "\n${YELLOW}4️⃣ Installing Claude CLI...${NC}"
    if command_exists claude; then
        CLAUDE_VERSION=$(claude --version 2>&1 | head -1)
        echo -e "${GREEN}✅ Claude CLI already installed: $CLAUDE_VERSION${NC}"
    else
        echo -e "${YELLOW}Installing Claude CLI globally...${NC}"
        npm install -g @anthropic-ai/claude-cli
        echo -e "${GREEN}✅ Claude CLI installed${NC}"
    fi

    # 5. Create systemd service (as root, before user switch)
    echo -e "\n${YELLOW}5️⃣ Creating systemd service...${NC}"
    cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=Claude Code Minimal API Service
After=network.target

[Service]
Type=simple
User=claude
WorkingDirectory=${INSTALL_DIR}
Environment="PATH=${INSTALL_DIR}/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=${INSTALL_DIR}/venv/bin/python3 ${INSTALL_DIR}/minimal_server.py
Restart=always
RestartSec=10
StandardOutput=append:${INSTALL_DIR}/server.log
StandardError=append:${INSTALL_DIR}/server.log

[Install]
WantedBy=multi-user.target
EOF
    echo -e "${GREEN}✅ Systemd service created${NC}"

    # 6. Enable service (but don't start yet - files don't exist)
    echo -e "\n${YELLOW}6️⃣ Enabling service...${NC}"
    systemctl daemon-reload
    systemctl enable ${SERVICE_NAME}.service
    echo -e "${GREEN}✅ Service enabled for auto-start${NC}"

    # Re-run script as claude user for application setup
    echo -e "\n${YELLOW}Switching to claude user for application setup...${NC}\n"
    exec sudo -u claude bash "$0" "$@"
fi

# NON-ROOT SECTION - Application setup as claude user
echo -e "${YELLOW}📁 Installation directory: $INSTALL_DIR${NC}"
echo -e "${YELLOW}🔧 Service name: $SERVICE_NAME${NC}\n"

# 7. Authenticate Claude CLI
echo -e "${YELLOW}7️⃣ Claude CLI Authentication${NC}"
if [ -f "$HOME/.claude/credentials.json" ]; then
    echo -e "${GREEN}✅ Claude CLI already authenticated${NC}"
else
    echo -e "${YELLOW}⚠️  Claude CLI not authenticated${NC}"
    echo -e "${YELLOW}Please run: claude setup-token${NC}"
    echo -e "${YELLOW}Or set ANTHROPIC_API_KEY in .env${NC}"
fi

# 8. Clone project files
echo -e "\n${YELLOW}8️⃣ Installing project files...${NC}"

# Remove old installation if exists
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Removing old installation...${NC}"
    rm -rf "$INSTALL_DIR"
fi

# Clone from GitHub
echo -e "${YELLOW}Cloning from GitHub...${NC}"
if git clone https://github.com/vlad29042/claude-api-minimal.git "$INSTALL_DIR"; then
    echo -e "${GREEN}✅ Project files installed${NC}"
    cd "$INSTALL_DIR"
else
    echo -e "${RED}❌ Failed to clone repository${NC}"
    echo -e "${YELLOW}Please check your internet connection${NC}"
    exit 1
fi

# 9. Create Python virtual environment
echo -e "\n${YELLOW}9️⃣ Creating Python virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate
echo -e "${GREEN}✅ Virtual environment created${NC}"

# 10. Install Python dependencies
echo -e "\n${YELLOW}🔟 Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✅ Dependencies installed${NC}"

# 11. Configure .env
echo -e "\n${YELLOW}1️⃣1️⃣ Configuring environment...${NC}"
if [ ! -f ".env" ]; then
    cat > .env << EOF
# Claude API Configuration
CLAUDE_API_KEY=$(openssl rand -hex 32)
CLAUDE_BINARY_PATH=claude
CLAUDE_TIMEOUT_SECONDS=300
CLAUDE_MAX_TURNS=50

# Server Configuration
PORT=8001
HOST=0.0.0.0
EOF
    echo -e "${GREEN}✅ .env created with random API key${NC}"
    echo -e "${YELLOW}⚠️  Please update CLAUDE_API_KEY in .env if needed${NC}"
else
    echo -e "${GREEN}✅ .env already exists${NC}"
fi

# 12. Start service
echo -e "\n${YELLOW}1️⃣2️⃣ Starting service...${NC}"
sudo systemctl start ${SERVICE_NAME}.service
sleep 3

# 13. Check service status
echo -e "\n${YELLOW}1️⃣3️⃣ Checking service status...${NC}"
if sudo systemctl is-active --quiet ${SERVICE_NAME}.service; then
    echo -e "${GREEN}✅ Service is running${NC}"

    # Test health endpoint
    sleep 2
    if curl -s http://localhost:8001/health > /dev/null; then
        echo -e "${GREEN}✅ Health check passed${NC}"
    else
        echo -e "${RED}⚠️  Health check failed${NC}"
    fi
else
    echo -e "${RED}❌ Service failed to start${NC}"
    echo -e "${YELLOW}Checking logs...${NC}"
    sudo journalctl -u ${SERVICE_NAME}.service -n 20 --no-pager
fi

# Print summary
echo -e "\n${GREEN}================================${NC}"
echo -e "${GREEN}✅ Installation Complete!${NC}"
echo -e "${GREEN}================================${NC}\n"

echo -e "${YELLOW}📋 Summary:${NC}"
echo -e "  Installation directory: ${GREEN}$INSTALL_DIR${NC}"
echo -e "  Service name: ${GREEN}$SERVICE_NAME${NC}"
echo -e "  API URL: ${GREEN}http://localhost:8001${NC}"
echo -e "  Logs: ${GREEN}$INSTALL_DIR/server.log${NC}"

echo -e "\n${YELLOW}🔧 Useful commands:${NC}"
echo -e "  Start service:   ${GREEN}sudo systemctl start $SERVICE_NAME${NC}"
echo -e "  Stop service:    ${GREEN}sudo systemctl stop $SERVICE_NAME${NC}"
echo -e "  Restart service: ${GREEN}sudo systemctl restart $SERVICE_NAME${NC}"
echo -e "  Check status:    ${GREEN}sudo systemctl status $SERVICE_NAME${NC}"
echo -e "  View logs:       ${GREEN}tail -f $INSTALL_DIR/server.log${NC}"
echo -e "  Journal logs:    ${GREEN}sudo journalctl -u $SERVICE_NAME -f${NC}"

echo -e "\n${YELLOW}🧪 Test API:${NC}"
echo -e "  Health check:    ${GREEN}curl http://localhost:8001/health${NC}"
echo -e "  Run tests:       ${GREEN}cd $INSTALL_DIR && source venv/bin/activate && python3 test_server.py${NC}"

echo -e "\n${YELLOW}⚙️  Configuration:${NC}"
echo -e "  Edit config:     ${GREEN}nano $INSTALL_DIR/.env${NC}"
echo -e "  After changes:   ${GREEN}sudo systemctl restart $SERVICE_NAME${NC}"

if [ ! -f "$HOME/.claude/credentials.json" ]; then
    echo -e "\n${RED}⚠️  IMPORTANT: Claude CLI not authenticated!${NC}"
    echo -e "${YELLOW}Run: claude setup-token${NC}"
    echo -e "${YELLOW}Or set ANTHROPIC_API_KEY in .env${NC}"
fi

echo -e "\n${GREEN}🎉 Done!${NC}\n"

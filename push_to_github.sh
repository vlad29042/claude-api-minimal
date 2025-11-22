#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 GitHub Push Script${NC}\n"

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo -e "${RED}❌ Not a git repository${NC}"
    exit 1
fi

# Get GitHub username
read -p "Enter your GitHub username: " GITHUB_USER
if [ -z "$GITHUB_USER" ]; then
    echo -e "${RED}❌ Username required${NC}"
    exit 1
fi

REPO_NAME="claude-api-minimal"
REPO_URL="https://github.com/${GITHUB_USER}/${REPO_NAME}.git"

echo -e "\n${YELLOW}Repository: ${REPO_URL}${NC}"

# Check if remote exists
if git remote | grep -q "^origin$"; then
    echo -e "${YELLOW}⚠️  Remote 'origin' already exists. Removing...${NC}"
    git remote remove origin
fi

# Add remote
echo -e "${YELLOW}Adding remote origin...${NC}"
git remote add origin "$REPO_URL"

# Rename branch to main
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${YELLOW}Renaming branch to main...${NC}"
    git branch -M main
fi

# Update documentation with real repository URL
echo -e "${YELLOW}Updating documentation with repository links...${NC}"

# Update install.sh
sed -i "s|YOUR_REPO_URL|${REPO_URL}|g" install.sh DEPLOYMENT.md INSTALL.md
sed -i "s|YOUR_USERNAME|${GITHUB_USER}|g" install.sh DEPLOYMENT.md INSTALL.md readme.md

# Commit updates if there are changes
if ! git diff --quiet; then
    git add .
    git commit -m "Update repository links to ${REPO_URL}"
    echo -e "${GREEN}✅ Documentation updated${NC}"
fi

# Push to GitHub
echo -e "\n${YELLOW}Pushing to GitHub...${NC}"
echo -e "${YELLOW}You will be prompted for credentials:${NC}"
echo -e "  Username: ${GREEN}${GITHUB_USER}${NC}"
echo -e "  Password: ${GREEN}your GitHub token${NC}\n"

if git push -u origin main; then
    echo -e "\n${GREEN}✅ Successfully pushed to GitHub!${NC}"
    echo -e "\n${YELLOW}Repository URL:${NC} ${GREEN}https://github.com/${GITHUB_USER}/${REPO_NAME}${NC}"
    echo -e "\n${YELLOW}Quick install command:${NC}"
    echo -e "${GREEN}curl -fsSL https://raw.githubusercontent.com/${GITHUB_USER}/${REPO_NAME}/main/install.sh | bash${NC}\n"
else
    echo -e "\n${RED}❌ Push failed${NC}"
    echo -e "${YELLOW}Make sure:${NC}"
    echo -e "1. Repository exists on GitHub: https://github.com/${GITHUB_USER}/${REPO_NAME}"
    echo -e "2. You have correct credentials"
    echo -e "3. Token has repo permissions\n"
    exit 1
fi

echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Visit: ${GREEN}https://github.com/${GITHUB_USER}/${REPO_NAME}${NC}"
echo -e "2. Add description and topics"
echo -e "3. Test installation: ${GREEN}curl -fsSL https://raw.githubusercontent.com/${GITHUB_USER}/${REPO_NAME}/main/install.sh | bash${NC}\n"

#!/bin/bash
# Git Helper Script - Easy GitHub operations

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function show_help() {
    echo "Git Helper - Easy GitHub Operations"
    echo ""
    echo "Usage: ./git_helper.sh [command]"
    echo ""
    echo "Commands:"
    echo "  push         Push changes to GitHub (with confirmation)"
    echo "  quick        Quick push (no confirmation)"
    echo "  status       Show git status"
    echo "  diff         Show changes"
    echo "  pull         Pull latest from GitHub"
    echo "  undo         Undo last commit (local only)"
    echo "  clean        Clean up uncommitted changes"
    echo ""
    echo "Examples:"
    echo "  ./git_helper.sh push"
    echo "  ./git_helper.sh quick"
    echo "  ./git_helper.sh status"
}

function push_changes() {
    echo -e "${BLUE}🚀 Pushing to GitHub${NC}"
    echo ""

    # Show status
    echo -e "${YELLOW}📋 Current changes:${NC}"
    git status --short
    echo ""

    # Ask for commit message
    echo -e "${YELLOW}Enter commit message (or press Enter for default):${NC}"
    read commit_msg

    if [ -z "$commit_msg" ]; then
        commit_msg="Update dashboard - $(date '+%Y-%m-%d %H:%M')"
    fi

    # Add files
    echo ""
    echo -e "${BLUE}➕ Adding files...${NC}"
    git add streamlit_app.py auth_config.py requirements.txt .gitignore *.md 2>/dev/null || true

    # Check if there are changes
    if git diff --staged --quiet; then
        echo -e "${YELLOW}ℹ️  No changes to commit${NC}"
        return
    fi

    # Show what will be committed
    echo ""
    echo -e "${YELLOW}📦 Files to commit:${NC}"
    git diff --staged --name-only
    echo ""

    # Confirm
    echo -e "${YELLOW}Push to GitHub? (y/n):${NC}"
    read confirm

    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo -e "${RED}❌ Cancelled${NC}"
        return
    fi

    # Commit and push
    echo ""
    echo -e "${BLUE}💾 Committing...${NC}"
    git commit -m "$commit_msg

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

    echo ""
    echo -e "${BLUE}⬆️  Pushing...${NC}"
    git push origin main

    echo ""
    echo -e "${GREEN}✅ Successfully pushed!${NC}"
    echo -e "${BLUE}🔗 https://github.com/shortpitch99/sdb-quality-dashboard${NC}"
}

function quick_push() {
    echo -e "${BLUE}⚡ Quick push to GitHub${NC}"

    COMMIT_MSG="Update dashboard - $(date '+%Y-%m-%d %H:%M')"

    git add streamlit_app.py auth_config.py requirements.txt .gitignore *.md 2>/dev/null || true

    if git diff --staged --quiet; then
        echo -e "${YELLOW}ℹ️  No changes to commit${NC}"
        return
    fi

    git commit -m "$COMMIT_MSG" || true
    git push origin main

    echo -e "${GREEN}✅ Pushed!${NC}"
    echo -e "${BLUE}🔗 https://github.com/shortpitch99/sdb-quality-dashboard${NC}"
}

function show_status() {
    echo -e "${BLUE}📊 Git Status${NC}"
    echo ""
    git status
}

function show_diff() {
    echo -e "${BLUE}📝 Changes${NC}"
    echo ""
    git diff
}

function pull_changes() {
    echo -e "${BLUE}⬇️  Pulling from GitHub${NC}"
    git pull origin main
    echo -e "${GREEN}✅ Updated!${NC}"
}

function undo_commit() {
    echo -e "${YELLOW}⚠️  Undo last commit (local only)${NC}"
    echo ""
    echo "Last commit:"
    git log -1 --oneline
    echo ""
    echo -e "${YELLOW}Undo this commit? (y/n):${NC}"
    read confirm

    if [ "$confirm" == "y" ] || [ "$confirm" == "Y" ]; then
        git reset --soft HEAD~1
        echo -e "${GREEN}✅ Commit undone (changes still staged)${NC}"
    else
        echo -e "${RED}❌ Cancelled${NC}"
    fi
}

function clean_changes() {
    echo -e "${RED}⚠️  This will discard all uncommitted changes!${NC}"
    echo ""
    git status --short
    echo ""
    echo -e "${YELLOW}Discard these changes? (y/n):${NC}"
    read confirm

    if [ "$confirm" == "y" ] || [ "$confirm" == "Y" ]; then
        git restore .
        git clean -fd
        echo -e "${GREEN}✅ Changes discarded${NC}"
    else
        echo -e "${RED}❌ Cancelled${NC}"
    fi
}

# Main
case "${1:-}" in
    push)
        push_changes
        ;;
    quick)
        quick_push
        ;;
    status)
        show_status
        ;;
    diff)
        show_diff
        ;;
    pull)
        pull_changes
        ;;
    undo)
        undo_commit
        ;;
    clean)
        clean_changes
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac

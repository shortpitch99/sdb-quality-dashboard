#!/bin/bash
# Push Quality Dashboard changes to GitHub

set -e

echo "🚀 Pushing Quality Dashboard to GitHub"
echo "========================================"
echo ""

# Check if we're in a git repository
if [ ! -d .git ]; then
    echo "❌ Error: Not a git repository"
    exit 1
fi

# Show current status
echo "📋 Current status:"
git status --short
echo ""

# Ask for commit message
read -p "Enter commit message (or press Enter for default): " commit_msg

if [ -z "$commit_msg" ]; then
    commit_msg="Update Quality Dashboard - $(date '+%Y-%m-%d %H:%M')"
fi

echo ""
echo "📝 Commit message: $commit_msg"
echo ""

# Add essential files
echo "➕ Adding files..."
git add streamlit_app.py auth_config.py requirements.txt .gitignore 2>/dev/null || true
git add *.md 2>/dev/null || true

# Check if there are changes to commit
if git diff --staged --quiet; then
    echo "ℹ️  No changes to commit"
    exit 0
fi

# Show what will be committed
echo ""
echo "📦 Files to be committed:"
git diff --staged --name-only
echo ""

# Confirm before pushing
read -p "Push to GitHub? (y/n): " confirm

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "❌ Push cancelled"
    exit 0
fi

# Commit
echo ""
echo "💾 Creating commit..."
git commit -m "$commit_msg

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Push
echo ""
echo "⬆️  Pushing to GitHub..."
git push origin main

echo ""
echo "✅ Successfully pushed to GitHub!"
echo ""
echo "🔗 Repository: https://github.com/shortpitch99/sdb-quality-dashboard"
echo ""
echo "📝 Commit: $(git log -1 --oneline)"
echo ""

#!/bin/bash
# Quick push to GitHub - no prompts, just push!

set -e

# Default commit message with timestamp
COMMIT_MSG="Update dashboard - $(date '+%Y-%m-%d %H:%M')"

# Add and commit
git add streamlit_app.py auth_config.py requirements.txt .gitignore *.md 2>/dev/null || true
git commit -m "$COMMIT_MSG" || echo "No changes to commit"
git push origin main

echo "✅ Pushed to GitHub!"
echo "🔗 https://github.com/shortpitch99/sdb-quality-dashboard"

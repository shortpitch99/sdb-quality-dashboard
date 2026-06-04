# Git Helper Scripts

Three simple scripts to manage your GitHub repository:

## 🚀 Scripts Available

### 1. `quick_push.sh` - Fastest (Recommended)
**Use when:** You just want to push changes quickly

```bash
./quick_push.sh
```

**What it does:**
- Adds changed files
- Creates commit with timestamp
- Pushes to GitHub
- No prompts, just push!

---

### 2. `push_to_github.sh` - Interactive
**Use when:** You want to review before pushing

```bash
./push_to_github.sh
```

**What it does:**
- Shows current changes
- Asks for commit message
- Shows what will be committed
- Confirms before pushing
- Pushes to GitHub

---

### 3. `git_helper.sh` - Full Featured
**Use when:** You need more git operations

```bash
./git_helper.sh [command]
```

**Commands:**
- `push` - Push with confirmation
- `quick` - Quick push (no confirmation)
- `status` - Show git status
- `diff` - Show changes
- `pull` - Pull from GitHub
- `undo` - Undo last commit (local only)
- `clean` - Discard uncommitted changes

**Examples:**
```bash
./git_helper.sh push      # Interactive push
./git_helper.sh quick     # Quick push
./git_helper.sh status    # Check status
./git_helper.sh pull      # Pull latest
./git_helper.sh undo      # Undo last commit
```

---

## 📋 Common Workflows

### Daily Work: Push Changes
```bash
# Make changes to streamlit_app.py or auth_config.py
# Then:
./quick_push.sh
```

### Add New User: Push Updated Credentials
```bash
# Edit auth_config.py to add user
nano auth_config.py

# Push
./quick_push.sh
```

### Review Before Push
```bash
# Check what changed
./git_helper.sh status
./git_helper.sh diff

# Push with custom message
./push_to_github.sh
```

### Pull Latest from GitHub
```bash
./git_helper.sh pull
```

### Made a Mistake? Undo Last Commit
```bash
# Undo commit but keep changes
./git_helper.sh undo

# Or discard all changes
./git_helper.sh clean
```

---

## 🎯 Which Script to Use?

| Situation | Script | Why |
|-----------|--------|-----|
| Quick daily push | `quick_push.sh` | Fastest, no prompts |
| Want to review first | `push_to_github.sh` | See what's changing |
| Need other git ops | `git_helper.sh` | Full featured |

---

## 🔐 What Gets Pushed?

All scripts automatically push:
- ✅ `streamlit_app.py` - Main app
- ✅ `auth_config.py` - User credentials (safe - hashed)
- ✅ `requirements.txt` - Dependencies
- ✅ `.gitignore` - File exclusions
- ✅ `*.md` files - Documentation

**Protected (never pushed):**
- 🔒 `.encryption_key`
- 🔒 `.env.production`
- 🔒 `__pycache__/`, `venv/`

---

## 📝 Examples

### Example 1: Update Password
```bash
# Generate new password hash
python3 -c "import hashlib; print(hashlib.sha256('newpassword'.encode()).hexdigest())"

# Edit auth_config.py with new hash
nano auth_config.py

# Push
./quick_push.sh
```

### Example 2: Add New User
```bash
# Edit auth_config.py to add teammate
nano auth_config.py

# Review changes
./git_helper.sh diff

# Push
./quick_push.sh
```

### Example 3: Made Changes, Want to Review
```bash
# Modified streamlit_app.py
# Want to see what changed before pushing

./git_helper.sh status    # See modified files
./git_helper.sh diff       # See exact changes
./push_to_github.sh        # Push with review
```

### Example 4: Oops, Wrong Commit
```bash
# Just committed but haven't pushed yet
./git_helper.sh undo       # Undo commit
# Make corrections
./quick_push.sh            # Push corrected version
```

---

## 🚨 Troubleshooting

### "Permission denied" error
```bash
chmod +x *.sh
```

### "Not a git repository" error
```bash
# Make sure you're in the QC directory
cd /Users/rchowdhuri/QC
```

### Push rejected (behind remote)
```bash
# Pull first, then push
./git_helper.sh pull
./quick_push.sh
```

### Want to see help
```bash
./git_helper.sh help
```

---

## 💡 Pro Tips

1. **Use `quick_push.sh` daily** - It's the fastest
2. **Use `push_to_github.sh` for important changes** - Review before push
3. **Check status before pushing** - `./git_helper.sh status`
4. **Pull before starting work** - `./git_helper.sh pull`

---

## 🎉 Quick Start

**Most common use:**
```bash
# Edit your files
nano auth_config.py

# Push to GitHub
./quick_push.sh
```

**Done!** Your changes are live on GitHub!

---

## Repository

**GitHub:** https://github.com/shortpitch99/sdb-quality-dashboard

All scripts automatically push to this repository.

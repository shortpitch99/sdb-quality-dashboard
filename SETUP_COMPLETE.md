# ✅ Security Setup - COMPLETE!

The setup script has successfully created your security infrastructure!

## What Was Created

✅ `.encryption_key` - Your data encryption key (KEEP SECRET!)
✅ `.env.production` - Template for Snowflake credentials
✅ Updated `.gitignore` - Prevents committing secrets to git
✅ Installed packages: `cryptography`, `snowflake-connector-python`

## Next Steps

### 1. Edit .env.production with Your Snowflake Credentials

```bash
nano .env.production
```

Replace these values:
```bash
SNOWFLAKE_ACCOUNT=your_account.region        # e.g., xy12345.us-east-1
SNOWFLAKE_USER=your_username                 # Your Snowflake username
SNOWFLAKE_PASSWORD=your_password             # Your Snowflake password
SNOWFLAKE_DATABASE=QUALITY_DB                # Database name (create if needed)
SNOWFLAKE_SCHEMA=REPORTS                     # Schema name (create if needed)
SNOWFLAKE_WAREHOUSE=COMPUTE_WH               # Warehouse name (create if needed)
```

### 2. Add Yourself as Admin User in auth_config.py

Open `auth_config.py` and update the USERS dictionary:

```python
USERS = {
    "rchowdhuri": {
        "password": "6feb4c700de1982f91ee7a1b40ca4ded05d155af3987597cb179f430dd60da0b",
        "role": "admin",
        "allowed_components": ["Engine", "Store", "SDD", "Core App Efficiency"]
    }
}
```

**To change the password:**
```bash
python3 -c "import hashlib; print(hashlib.sha256('YOUR_PASSWORD_HERE'.encode()).hexdigest())"
```

Replace `YOUR_PASSWORD_HERE` with your desired password, then copy the hash into auth_config.py.

### 3. Create Snowflake Tables and Roles

```bash
# Load environment variables
source venv/bin/activate
source .env.production

# Create tables and setup RBAC
python upload_to_snowflake.py \
    --component Engine \
    --week cw22 \
    --create-tables \
    --setup-rbac
```

This creates:
- `QUALITY_REPORTS` table
- `QUALITY_REPORTS_ACCESS_LOG` table
- RBAC roles (QUALITY_ADMIN, QUALITY_VIEWER, etc.)

### 4. Upload Test Data (Encrypted)

```bash
# Upload latest Store report with encryption
python upload_to_snowflake.py \
    --component Store \
    --week cw22 \
    --encrypt
```

### 5. Test the Secure Dashboard

```bash
streamlit run streamlit_app_secure.py
```

Login with:
- **Username:** `rchowdhuri`
- **Password:** `mysecurepassword` (or whatever you set)

## Quick Commands Reference

### Upload Data (Encrypted)
```bash
source venv/bin/activate
source .env.production

# Single component
python upload_to_snowflake.py --component Engine --week cw23 --encrypt

# All components
for comp in Engine Store SDD; do
    python upload_to_snowflake.py --component $comp --week cw23 --encrypt
done
```

### Add New User

1. Generate password hash:
```bash
python3 -c "import hashlib; print(hashlib.sha256('their_password'.encode()).hexdigest())"
```

2. Add to `auth_config.py`:
```python
"teammate": {
    "password": "generated_hash_here",
    "role": "viewer",
    "allowed_components": ["Engine"]  # Only Engine access
}
```

3. Grant Snowflake role (optional):
```sql
GRANT ROLE ENGINE_VIEWER TO USER teammate;
```

### View Access Logs in Snowflake

```sql
SELECT 
    USERNAME,
    REPORT_ID,
    ACCESS_TIME,
    ACCESS_TYPE
FROM QUALITY_REPORTS_ACCESS_LOG
ORDER BY ACCESS_TIME DESC
LIMIT 100;
```

## Security Checklist

- [ ] Edited `.env.production` with real Snowflake credentials
- [ ] Changed default password in `auth_config.py`
- [ ] Created Snowflake tables (`--create-tables`)
- [ ] Setup RBAC roles (`--setup-rbac`)
- [ ] Uploaded test data with `--encrypt`
- [ ] Tested login/logout in secure dashboard
- [ ] Verified `.encryption_key` is in `.gitignore`
- [ ] NEVER commit `.env.production` or `.encryption_key` to git!

## Troubleshooting

### "Module not found" error
```bash
# Make sure you're in the virtual environment
source venv/bin/activate
pip install -r requirements.txt
```

### "Connection error" to Snowflake
```bash
# Test your credentials
python3 -c "
import snowflake.connector
import os
os.system('source .env.production')
# Check environment variables are loaded
"
```

### "Decryption failed"
- Make sure `.encryption_key` hasn't changed
- Check `DASHBOARD_ENCRYPTION_KEY` in `.env.production` matches `.encryption_key`

## What's Protected?

### 🔒 Encrypted Fields
- Git repository paths
- Author names
- Bug subjects & descriptions
- PRB titles
- Security issue details

### 📊 Not Encrypted (For Analytics)
- Metrics (counts, percentages)
- Dates and versions
- Component names
- Aggregated statistics

## Documentation

- 📖 **Complete Guide:** `SECURITY_SETUP.md`
- 🏗️ **Architecture:** `SECURITY_ARCHITECTURE.md`
- 📝 **Quick Reference:** `SECURITY_QUICK_REFERENCE.md`
- 📚 **Overview:** `SECURITY_SUMMARY.md`

## Need Help?

1. Check the documentation files above
2. Review error messages carefully
3. Verify environment variables are set correctly
4. Test Snowflake connection separately

---

**IMPORTANT REMINDERS:**

⚠️  **NEVER** commit `.encryption_key` or `.env.production` to git!
⚠️  **BACKUP** your `.encryption_key` securely (but not in git!)
⚠️  **USE STRONG PASSWORDS** (12+ characters)
⚠️  **ROTATE KEYS** every 90 days for best security

You're all set! 🎉

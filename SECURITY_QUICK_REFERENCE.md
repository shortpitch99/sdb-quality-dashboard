# Security Quick Reference Card

## 🚀 One-Time Setup (5 minutes)

```bash
# 1. Generate keys and setup
./setup_security.sh

# 2. Edit Snowflake credentials
nano .env.production

# 3. Create tables and roles
source .env.production
python upload_to_snowflake.py --component Engine --week cw22 --create-tables --setup-rbac
```

## 📤 Daily Usage - Upload Data

```bash
# Upload latest report for a component (encrypted)
python upload_to_snowflake.py --component Store --week cw22 --encrypt

# Upload specific report file
python upload_to_snowflake.py \
    --component SDD \
    --week cw23 \
    --report-path reports/SDD/quality_data_archive_20260602.json \
    --encrypt
```

## 👥 Add New User

1. Generate password hash:
```bash
python3 -c "import hashlib; print(hashlib.sha256('their_password'.encode()).hexdigest())"
```

2. Add to `auth_config.py`:
```python
"username": {
    "password": "generated_hash_here",
    "role": "viewer",  # or "admin"
    "allowed_components": ["Engine", "Store"]  # components they can access
}
```

3. Grant Snowflake role (optional):
```sql
GRANT ROLE ENGINE_VIEWER TO USER username;
```

## 🔑 Roles Explained

| Role | Can View | Can Upload | Use Case |
|------|----------|------------|----------|
| `admin` | All components | Yes | You |
| `viewer` | All components | No | Managers |
| `ENGINE_VIEWER` | Engine only | No | Engine team |
| `STORE_VIEWER` | Store only | No | Store team |
| `SDD_VIEWER` | SDD only | No | SDD team |

## 🔍 Common Commands

### View Access Logs
```sql
SELECT USERNAME, REPORT_ID, ACCESS_TIME 
FROM QUALITY_REPORTS_ACCESS_LOG 
ORDER BY ACCESS_TIME DESC 
LIMIT 100;
```

### List All Reports
```sql
SELECT COMPONENT, WEEK, REPORT_DATE, IS_ENCRYPTED, UPLOADED_BY
FROM QUALITY_REPORTS
ORDER BY REPORT_DATE DESC;
```

### Check User Roles
```sql
SHOW GRANTS TO USER rchowdhuri;
```

## 🛠️ Troubleshooting

### "Decryption failed"
**Fix:** Check encryption key in `.env.production` matches `.encryption_key`

### "Authentication failed" in Streamlit
**Fix:** Regenerate password hash and update `auth_config.py`

### "Insufficient privileges" in Snowflake
**Fix:** Grant role to user:
```sql
GRANT ROLE QUALITY_VIEWER TO USER username;
```

### Data not showing up
**Fix:** Check if encrypted data was uploaded:
```sql
SELECT IS_ENCRYPTED FROM QUALITY_REPORTS WHERE COMPONENT = 'Store';
```

## 📊 What Gets Encrypted?

✅ **Encrypted:**
- Git paths
- Author names
- Bug titles/descriptions
- PRB subjects
- Security issues

❌ **Not Encrypted:**
- Counts (bug count, PRB count)
- Percentages (coverage %)
- Dates and versions
- Aggregated metrics

## 🔐 Security Best Practices

1. ✅ Rotate encryption key every 90 days
2. ✅ Use strong passwords (12+ characters)
3. ✅ Enable MFA on Snowflake
4. ✅ Review access logs monthly
5. ✅ Never commit `.env.production` to git
6. ✅ Use secrets manager in production

## 📞 Support

- **Setup Issues:** See `SECURITY_SETUP.md`
- **Architecture:** See `SECURITY_SUMMARY.md`
- **Code Issues:** Check logs with `tail -f /tmp/streamlit.log`

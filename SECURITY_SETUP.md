# Security Setup Guide for Quality Dashboard

This guide explains how to secure your Quality Dashboard data with encryption and access control.

## Overview

The security implementation has three layers:

1. **Streamlit Authentication** - User login before accessing dashboard
2. **Data Encryption** - Sensitive fields encrypted before uploading to Snowflake
3. **Snowflake RBAC** - Role-based access control for fine-grained permissions

## Setup Steps

### 1. Install Required Packages

```bash
pip install cryptography snowflake-connector-python streamlit-authenticator
```

Update `requirements.txt`:
```
streamlit>=1.28.0
pandas
plotly
python-dotenv
cryptography>=41.0.0
snowflake-connector-python>=3.0.0
streamlit-authenticator>=0.2.3
```

### 2. Generate Encryption Key

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Save this key securely - you'll need it for encryption/decryption.

### 3. Configure Environment Variables

Create `.env.production` file:

```bash
# Snowflake Configuration
SNOWFLAKE_ACCOUNT=your_account.us-east-1
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=QUALITY_DB
SNOWFLAKE_SCHEMA=REPORTS
SNOWFLAKE_WAREHOUSE=COMPUTE_WH

# Encryption Key (generated in step 2)
DASHBOARD_ENCRYPTION_KEY=your_generated_key_here

# Dashboard Config
ENVIRONMENT=production
```

**Security Note:** Never commit `.env.production` to git! Add it to `.gitignore`.

### 4. Setup Snowflake Tables and Roles

```bash
# Create tables and setup RBAC
python upload_to_snowflake.py --component Engine --week cw22 --create-tables --setup-rbac
```

This creates:
- `QUALITY_REPORTS` table for storing data
- `QUALITY_REPORTS_ACCESS_LOG` for audit trail
- Roles: `QUALITY_ADMIN`, `QUALITY_VIEWER`, `ENGINE_VIEWER`, `STORE_VIEWER`, `SDD_VIEWER`

### 5. Grant User Access in Snowflake

```sql
-- Grant admin access
GRANT ROLE QUALITY_ADMIN TO USER rchowdhuri;

-- Grant viewer access to specific components
GRANT ROLE ENGINE_VIEWER TO USER teammate1;
GRANT ROLE STORE_VIEWER TO USER teammate2;

-- Grant full viewer access (all components)
GRANT ROLE QUALITY_VIEWER TO USER manager1;
```

### 6. Configure Streamlit Users

Edit `auth_config.py` and add users:

```python
USERS = {
    "rchowdhuri": {
        "password": hashlib.sha256("your_secure_password".encode()).hexdigest(),
        "role": "admin",
        "allowed_components": ["Engine", "Store", "SDD", "Core App Efficiency"]
    },
    "teammate1": {
        "password": hashlib.sha256("their_password".encode()).hexdigest(),
        "role": "viewer",
        "allowed_components": ["Engine"]  # Only Engine access
    },
    "manager1": {
        "password": hashlib.sha256("manager_password".encode()).hexdigest(),
        "role": "viewer",
        "allowed_components": ["Engine", "Store", "SDD", "Core App Efficiency"]
    }
}
```

**Best Practice:** In production, use proper authentication (OAuth, SAML, etc.) instead of hardcoded passwords.

## Usage

### Upload Data to Snowflake (with encryption)

```bash
# Upload single component with encryption
python upload_to_snowflake.py --component Store --week cw22 --encrypt

# Upload specific report file
python upload_to_snowflake.py \
    --component Engine \
    --week cw23 \
    --report-path reports/Engine/quality_data_archive_20260602_073349.json \
    --encrypt
```

### Access Dashboard

1. Navigate to your Streamlit app
2. Login with your credentials
3. You'll only see components you have access to
4. Data is automatically decrypted for viewing (if you have the encryption key)

## Row-Level Security in Snowflake

For fine-grained access control, create row access policies:

```sql
-- Policy to restrict access by component
CREATE OR REPLACE ROW ACCESS POLICY component_access_policy
AS (COMPONENT VARCHAR) RETURNS BOOLEAN ->
  CASE
    WHEN CURRENT_ROLE() = 'QUALITY_ADMIN' THEN TRUE
    WHEN CURRENT_ROLE() = 'ENGINE_VIEWER' AND COMPONENT = 'Engine' THEN TRUE
    WHEN CURRENT_ROLE() = 'STORE_VIEWER' AND COMPONENT = 'Store' THEN TRUE
    WHEN CURRENT_ROLE() = 'SDD_VIEWER' AND COMPONENT = 'SDD' THEN TRUE
    WHEN CURRENT_ROLE() = 'QUALITY_VIEWER' THEN TRUE
    ELSE FALSE
  END;

-- Apply policy to table
ALTER TABLE QUALITY_REPORTS
ADD ROW ACCESS POLICY component_access_policy ON (COMPONENT);
```

Now users can only see rows for components they have access to!

## What Gets Encrypted?

By default, these sensitive fields are encrypted:
- Git repository paths
- Author names
- Bug subjects and descriptions
- PRB titles
- Security issue details
- CI issue details

The encryption is transparent - when you view the dashboard with the correct encryption key, everything is decrypted automatically.

## Audit Trail

All data access is logged in `QUALITY_REPORTS_ACCESS_LOG`:

```sql
-- View recent access
SELECT 
    USERNAME,
    REPORT_ID,
    ACCESS_TIME,
    ACCESS_TYPE
FROM QUALITY_REPORTS_ACCESS_LOG
ORDER BY ACCESS_TIME DESC
LIMIT 100;

-- Access by user
SELECT 
    USERNAME,
    COUNT(*) as ACCESS_COUNT,
    MIN(ACCESS_TIME) as FIRST_ACCESS,
    MAX(ACCESS_TIME) as LAST_ACCESS
FROM QUALITY_REPORTS_ACCESS_LOG
GROUP BY USERNAME
ORDER BY ACCESS_COUNT DESC;
```

## Security Best Practices

1. **Rotate encryption keys regularly** (every 90 days)
2. **Use strong passwords** with minimum 12 characters
3. **Enable MFA** on Snowflake accounts
4. **Monitor access logs** for suspicious activity
5. **Use network policies** in Snowflake to restrict IP ranges
6. **Never commit** `.env` files or encryption keys to git
7. **Use secrets management** (AWS Secrets Manager, HashiCorp Vault) in production

## Troubleshooting

### "Decryption failed" error
- Verify `DASHBOARD_ENCRYPTION_KEY` matches the key used for encryption
- Check if data is actually encrypted (`_encrypted: true` in JSON)

### "Authentication failed" in Streamlit
- Verify password hash is correct in `auth_config.py`
- Try resetting password: `hashlib.sha256("new_password".encode()).hexdigest()`

### "Insufficient privileges" in Snowflake
- Check user has correct role granted
- Verify row access policy allows access to the component

## Migration from Unencrypted to Encrypted

If you have existing unencrypted data in Snowflake:

```bash
# Re-upload with encryption
for component in Engine Store SDD; do
    python upload_to_snowflake.py --component $component --week cw22 --encrypt
done
```

The upload script uses `MERGE`, so it will update existing records.

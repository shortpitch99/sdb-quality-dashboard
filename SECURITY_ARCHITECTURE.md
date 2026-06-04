# Security Architecture Diagram

## Overall Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         YOUR LOCAL MACHINE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐                                              │
│  │ Quality Reports  │                                              │
│  │ (JSON files)     │                                              │
│  └────────┬─────────┘                                              │
│           │                                                         │
│           │ 1. Read Report                                         │
│           ▼                                                         │
│  ┌──────────────────┐                                              │
│  │ data_encryption  │ ◄─── Encryption Key (.encryption_key)       │
│  │     .py          │                                              │
│  └────────┬─────────┘                                              │
│           │                                                         │
│           │ 2. Encrypt Sensitive Fields                           │
│           ▼                                                         │
│  ┌──────────────────┐                                              │
│  │ upload_to_       │                                              │
│  │ snowflake.py     │ ◄─── Snowflake Credentials (.env.production)│
│  └────────┬─────────┘                                              │
│           │                                                         │
└───────────┼─────────────────────────────────────────────────────────┘
            │
            │ 3. Upload Encrypted Data (HTTPS)
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         SNOWFLAKE CLOUD                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌────────────────────────────────────────────────────────────────┐│
│  │                    QUALITY_REPORTS Table                       ││
│  ├────────────────────────────────────────────────────────────────┤│
│  │ REPORT_ID │ COMPONENT │ DATA_JSON (ENCRYPTED) │ UPLOADED_BY   ││
│  ├────────────────────────────────────────────────────────────────┤│
│  │ Row Access Policy: component_access_policy                    ││
│  │   - Filters rows based on user's granted roles                ││
│  │   - ENGINE_VIEWER can only see Engine rows                    ││
│  └────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  ┌────────────────────────────────────────────────────────────────┐│
│  │                        RBAC Roles                              ││
│  ├────────────────────────────────────────────────────────────────┤│
│  │ QUALITY_ADMIN    → Full access to all data                    ││
│  │ QUALITY_VIEWER   → Read all components                        ││
│  │ ENGINE_VIEWER    → Read Engine rows only                      ││
│  │ STORE_VIEWER     → Read Store rows only                       ││
│  │ SDD_VIEWER       → Read SDD rows only                         ││
│  └────────────────────────────────────────────────────────────────┘│
│                                                                     │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  │ 4. Fetch Data (User queries via Streamlit)
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STREAMLIT DASHBOARD (Cloud)                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌────────────────────────────────────────────────────────────────┐│
│  │                      Login Screen                              ││
│  │  ┌──────────────────────────────────────────────────────────┐ ││
│  │  │  Username: [__________]                                  │ ││
│  │  │  Password: [__________]                                  │ ││
│  │  │            [  Login  ]                                   │ ││
│  │  └──────────────────────────────────────────────────────────┘ ││
│  │                      auth_config.py                            ││
│  │  - Verifies username/password                                  ││
│  │  - Checks user role and allowed components                     ││
│  └────────────────────────────────────────────────────────────────┘│
│                                 │                                   │
│                                 │ 5. Authenticated                  │
│                                 ▼                                   │
│  ┌────────────────────────────────────────────────────────────────┐│
│  │                     Dashboard Tabs                             ││
│  │  ┌────────┬────────┬─────┬───────────────────────────────┐   ││
│  │  │ Engine │ Store  │ SDD │ Core App Efficiency           │   ││
│  │  └────────┴────────┴─────┴───────────────────────────────┘   ││
│  │                                                                ││
│  │  Only shows tabs user has access to                           ││
│  │  - Admin: All tabs                                            ││
│  │  - ENGINE_VIEWER: Engine tab only                             ││
│  └────────────────────────────────────────────────────────────────┘│
│                                 │                                   │
│                                 │ 6. Fetch data from Snowflake      │
│                                 │    (Filtered by RBAC + Row Policy)│
│                                 ▼                                   │
│  ┌────────────────────────────────────────────────────────────────┐│
│  │              Data Decryption (data_encryption.py)              ││
│  │  - Decrypts sensitive fields using encryption key              ││
│  │  - Shows decrypted data in dashboard                           ││
│  └────────────────────────────────────────────────────────────────┘│
│                                 │                                   │
│                                 │ 7. Display Dashboard              │
│                                 ▼                                   │
│  ┌────────────────────────────────────────────────────────────────┐│
│  │                    Quality Metrics Display                     ││
│  │  📊 Code Coverage: 85.3%                                       ││
│  │  🐛 P0/P1 Bugs: 12                                             ││
│  │  🚨 PRBs: 5                                                    ││
│  │  📈 Code Changes: 1,995 lines                                  ││
│  └────────────────────────────────────────────────────────────────┘│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow - Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Authentication                                     │
├─────────────────────────────────────────────────────────────┤
│ • User enters username/password in Streamlit               │
│ • auth_config.py verifies credentials                      │
│ • Session created with user role + allowed components      │
│ • Unauthorized users blocked                               │
└─────────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Component Access Control                          │
├─────────────────────────────────────────────────────────────┤
│ • Dashboard checks st.session_state.allowed_components     │
│ • Only shows tabs user can access                          │
│ • Blocks rendering of unauthorized components              │
└─────────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Snowflake RBAC                                    │
├─────────────────────────────────────────────────────────────┤
│ • User's Snowflake role determines data access             │
│ • Row Access Policy filters data by component              │
│ • ENGINE_VIEWER can only query Engine rows                 │
│ • Unauthorized queries return empty results                │
└─────────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: Field-Level Encryption                            │
├─────────────────────────────────────────────────────────────┤
│ • Sensitive fields encrypted at rest in Snowflake          │
│ • Encryption key required to decrypt                       │
│ • Users without key see encrypted gibberish                │
│ • data_encryption.py transparently decrypts on read        │
└─────────────────────────────────────────────────────────────┘
                          ▼
              ✅ User sees dashboard data
```

## Attack Scenarios & Protection

### Scenario 1: Unauthorized User Tries to Access Dashboard
```
❌ Blocked at Layer 1 (Authentication)
   └─> Login page shown, access denied
```

### Scenario 2: Authenticated User Tries to Access Restricted Component
```
✅ Passes Layer 1 (Authenticated)
❌ Blocked at Layer 2 (Component Access)
   └─> Tab not shown in UI
```

### Scenario 3: User Tries Direct Snowflake Access
```
✅ Passes Layer 1 (Has Snowflake credentials)
❌ Blocked at Layer 3 (RBAC + Row Policy)
   └─> Query returns no rows (filtered by policy)
```

### Scenario 4: Snowflake Admin Tries to Read Encrypted Data
```
✅ Passes Layer 1, 2, 3 (Full Snowflake access)
❌ Blocked at Layer 4 (No Encryption Key)
   └─> Sees encrypted gibberish: "gAAAAABhkj2..."
```

### Scenario 5: Legitimate User with Full Access
```
✅ Passes Layer 1 (Authenticated as admin)
✅ Passes Layer 2 (Access to all components)
✅ Passes Layer 3 (QUALITY_ADMIN role)
✅ Passes Layer 4 (Has encryption key)
   └─> Full access to decrypted dashboard data
```

## Key Management

```
┌────────────────────────────────────────────┐
│        Encryption Key Storage              │
├────────────────────────────────────────────┤
│ Development:                               │
│   • .encryption_key file (local)          │
│   • .env.production (local)               │
│                                            │
│ Production (Recommended):                  │
│   • AWS Secrets Manager                    │
│   • Azure Key Vault                        │
│   • HashiCorp Vault                        │
│   • Google Cloud Secret Manager           │
│                                            │
│ ⚠️  NEVER commit keys to git!             │
└────────────────────────────────────────────┘
```

## Audit Trail

```
Every data access is logged:

QUALITY_REPORTS_ACCESS_LOG
├─ ACCESS_ID (auto-increment)
├─ REPORT_ID (which report)
├─ USERNAME (who accessed)
├─ ACCESS_TIME (when)
├─ ACCESS_TYPE (read/write)
└─ IP_ADDRESS (from where)

Query access patterns:
• Who accessed what data?
• When was data last accessed?
• Unusual access patterns?
• Compliance reporting
```

## Security Checklist

- [ ] Generated encryption key (`.encryption_key`)
- [ ] Created `.env.production` with Snowflake credentials
- [ ] Added `.encryption_key` and `.env.production` to `.gitignore`
- [ ] Created Snowflake tables (`--create-tables`)
- [ ] Setup Snowflake RBAC roles (`--setup-rbac`)
- [ ] Applied row access policy in Snowflake
- [ ] Uploaded encrypted test data
- [ ] Added users to `auth_config.py`
- [ ] Granted Snowflake roles to users
- [ ] Tested login/logout flow
- [ ] Verified component access restrictions
- [ ] Enabled MFA on Snowflake accounts
- [ ] Setup key rotation schedule (90 days)
- [ ] Configured audit log monitoring

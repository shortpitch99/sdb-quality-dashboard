# LLM Gateway Access Troubleshooting Guide

## Current Issue: HTTP 401 - Key Blocked

Your LLM gateway key is **blocked** (not expired), which prevents all API calls from succeeding.

```
⚠️ LLM Gateway HTTP 401: {"error":{"message":"Authentication Error, Key is blocked. 
Update via `/key/unblock` if you're admin.","type":"auth_error","param":"None","code":"401"}}
```

---

## Quick Fixes (Try in Order)

### 1. **Check Your VPN/Network Connection**

The gateway URL requires Salesforce internal network access:
```bash
# Test connectivity
curl -I https://eng-ai-model-gateway.sfproxy.devx-preprod.aws-esvc1-useast2.aws.sfdc.cl
```

If this fails with SSL errors, you may need:
- ✅ Connect to Salesforce VPN
- ✅ Configure SSL certificates for `sfproxy.devx-preprod` domains
- ✅ Add corporate CA certificates to your system

### 2. **Try to Unblock Your Key (If Admin)**

```bash
# Activate venv first
source venv/bin/activate

# Try the management script
python manage_llm_keys.py unblock

# Or manually via curl (if VPN connected)
curl -X POST \
  https://eng-ai-model-gateway.sfproxy.devx-preprod.aws-esvc1-useast2.aws.sfdc.cl/key/unblock \
  -H "Authorization: Bearer sk-gkK1Dj2xfWtf_wF1Cwd2CQ" \
  -H "Content-Type: application/json" \
  -d '{"key": "sk-gkK1Dj2xfWtf_wF1Cwd2CQ"}'
```

### 3. **Request a New Key**

Contact your LLM Gateway administrator or team:
- Slack channel: `#eng-ai-gateway` or `#ai-platform` (check your org)
- Email: AI Platform team
- Internal portal: Check if there's a self-service key management portal

**What to ask for:**
> "My LLM gateway key (sk-gkK1...Cwd2CQ) is blocked. Can you either:
> 1. Unblock my existing key, or
> 2. Generate a new key for user: rchowdhuri@salesforce.com"

### 4. **Try the Alternate (Commented) Key**

Your `.env` has a commented key that might still work:

```bash
# Edit .env - uncomment the old key
cd /Users/rchowdhuri/QC
nano .env

# Change:
# LLM_GW_EXPRESS_KEY=sk-aIXpkZbQuDLPNFFcANnwNw
# to:
LLM_GW_EXPRESS_KEY=sk-aIXpkZbQuDLPNFFcANnwNw

# Test it
source venv/bin/activate
python manage_llm_keys.py check
```

### 5. **Use Fallback Mode (No LLM)**

Your code has fallback content generation. While not ideal, it will let reports complete:

```bash
# Temporarily disable LLM by removing the key
cd /Users/rchowdhuri/QC
cp .env .env.backup
echo "# LLM_GW_EXPRESS_KEY=" > .env.tmp
cat .env | grep -v "LLM_GW_EXPRESS_KEY" >> .env.tmp
mv .env.tmp .env

# Run report (uses fallback content)
./run_report.sh cw15 Engine

# Restore when key is fixed
mv .env.backup .env
```

---

## Why Keys Get Blocked

Common reasons:
1. **Rate limit violations** - Too many requests in short time
2. **Suspicious activity** - Unusual usage patterns
3. **Policy violations** - Using key from unauthorized locations/IPs
4. **Expired compliance** - Need to re-attest to usage policies
5. **Manual block** - Admin explicitly blocked the key

---

## Long-term Improvements

### A. **Add Key Rotation Support**

Update `.env`:
```bash
# Primary key
LLM_GW_EXPRESS_KEY=sk-primary-key

# Fallback keys (comma-separated)
LLM_GW_EXPRESS_KEY_FALLBACK=sk-fallback-1,sk-fallback-2

# Admin key for key management
LLM_GATEWAY_ADMIN_KEY=sk-admin-key
```

### B. **Configure SSL Certificates**

If you're getting SSL errors, you need to configure corporate certificates:

```bash
# Option 1: Install Salesforce CA certificates
# Ask your IT team for the CA certificate bundle

# Option 2: Use system certificates (macOS)
export SSL_CERT_FILE=/etc/ssl/cert.pem
export REQUESTS_CA_BUNDLE=/etc/ssl/cert.pem

# Option 3: For development only (NOT RECOMMENDED for production)
# Disable SSL verification in Python:
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

### C. **Monitor Key Health**

Add this to your cron or scheduled jobs:

```bash
# Check key health daily
0 9 * * * cd /Users/rchowdhuri/QC && source venv/bin/activate && python manage_llm_keys.py check
```

### D. **Implement Retry with Backoff**

The code improvements I suggested above will add:
- Automatic retry on transient failures (429, 503)
- Exponential backoff to avoid rate limits
- Better error messages for different failure types
- Key rotation when primary key fails

---

## Testing Key Status

### Manual Test (via curl)
```bash
curl -X POST \
  https://eng-ai-model-gateway.sfproxy.devx-preprod.aws-esvc1-useast2.aws.sfdc.cl/chat/completions \
  -H "Authorization: Bearer sk-gkK1Dj2xfWtf_wF1Cwd2CQ" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-20250514",
    "messages": [{"role": "user", "content": "test"}],
    "max_tokens": 10
  }'
```

**Expected responses:**
- ✅ **200 OK** - Key is working
- ❌ **401 Unauthorized + "blocked"** - Key is blocked (current issue)
- ⚠️ **401 Unauthorized + "expired"** - Key expired, request new one
- ⚠️ **429 Too Many Requests** - Rate limited, wait and retry
- ⚠️ **503 Service Unavailable** - Gateway down, retry later

### Using the Management Script
```bash
cd /Users/rchowdhuri/QC
source venv/bin/activate

# Check key status
python manage_llm_keys.py check

# Try to unblock (if admin)
python manage_llm_keys.py unblock

# Create new key (if admin)
python manage_llm_keys.py create

# List all keys (if admin)
python manage_llm_keys.py list
```

---

## Current Configuration

**Gateway URL:**
```
https://eng-ai-model-gateway.sfproxy.devx-preprod.aws-esvc1-useast2.aws.sfdc.cl
```

**Current Key (in .env):**
```
LLM_GW_EXPRESS_KEY=sk-gkK1Dj2xfWtf_wF1Cwd2CQ (BLOCKED)
```

**User ID:**
```
OPENAI_USER_ID=rchowdhuri@salesforce.com
```

**Model:**
```
claude-sonnet-4-20250514
```

---

## Support Contacts

1. **LLM Gateway Team:**
   - Slack: Check `#eng-ai-gateway`, `#ai-platform`, or similar
   - Email: Your organization's AI/ML platform team

2. **Internal IT:**
   - For VPN/SSL certificate issues
   - For network access to `sfproxy.devx-preprod` domains

3. **Your Manager/Tech Lead:**
   - For approvals/access requests if needed

---

## Alternative: Use Public Claude API

If internal gateway continues to have issues, you could temporarily use Anthropic's public API:

```bash
# Get API key from https://console.anthropic.com
# Update .env:
LLM_GATEWAY_BASE_URL=https://api.anthropic.com
LLM_GW_EXPRESS_KEY=sk-ant-api03-...  # Anthropic API key
OPENAI_USER_ID=  # Not needed for public API
```

**Note:** This requires code changes to use Anthropic's API format instead of OpenAI format.

---

## Next Steps

1. ✅ **Try the alternate key** (commented in .env)
2. ✅ **Contact LLM Gateway admin** to unblock or get new key
3. ✅ **Verify VPN/network access** to the gateway
4. ✅ **Implement key rotation** for future resilience
5. ✅ **Add monitoring** for key health

Good luck! 🚀

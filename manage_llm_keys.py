#!/usr/bin/env python3
"""
LLM Gateway Key Management Utility

Usage:
    python manage_llm_keys.py check          # Check current key status
    python manage_llm_keys.py unblock        # Unblock current key (requires admin)
    python manage_llm_keys.py list           # List all keys (requires admin)
    python manage_llm_keys.py create         # Create new key (requires admin)
"""

import os
import sys
import requests
import urllib3
from dotenv import load_dotenv

# Disable SSL warnings for internal Salesforce gateways
# This is common for internal proxies with self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

GATEWAY_BASE_URL = os.getenv(
    "LLM_GATEWAY_BASE_URL",
    "https://eng-ai-model-gateway.sfproxy.devx-preprod.aws-esvc1-useast2.aws.sfdc.cl"
)
API_KEY = os.getenv("LLM_GW_EXPRESS_KEY", "")
ADMIN_KEY = os.getenv("LLM_GATEWAY_ADMIN_KEY", API_KEY)
USER_ID = os.getenv("OPENAI_USER_ID", "")


def check_key_status():
    """Check if the current key is valid."""
    print("🔍 Checking LLM Gateway key status...")
    print(f"   Key: {API_KEY[:20]}...")

    url = f"{GATEWAY_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "claude-sonnet-4-20250514",
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 10
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)

        if response.status_code == 200:
            print("✅ Key is VALID and working")
            return True
        elif response.status_code == 401:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get("error", {}).get("message", response.text)

            if "blocked" in error_msg.lower():
                print(f"❌ Key is BLOCKED: {error_msg}")
                print("\n💡 Try running: python manage_llm_keys.py unblock")
            else:
                print(f"❌ Key is INVALID/EXPIRED: {error_msg}")
                print("\n💡 Request a new key from your admin or generate one via:")
                print("   python manage_llm_keys.py create")
            return False
        else:
            print(f"⚠️ Unexpected status {response.status_code}: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ Error checking key: {e}")
        return False


def unblock_key():
    """Unblock the current key (requires admin privileges)."""
    print("🔓 Attempting to unblock key...")
    print(f"   Key: {API_KEY[:20]}...")

    # Try different possible endpoints
    endpoints = [
        f"{GATEWAY_BASE_URL}/key/unblock",
        f"{GATEWAY_BASE_URL}/api/key/unblock",
        f"{GATEWAY_BASE_URL}/admin/key/unblock",
    ]

    headers = {
        "Authorization": f"Bearer {ADMIN_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "key": API_KEY,
        "user_id": USER_ID
    }

    for endpoint in endpoints:
        try:
            print(f"\n   Trying: {endpoint}")
            response = requests.post(endpoint, headers=headers, json=payload, timeout=30, verify=False)

            if response.status_code in (200, 201):
                print(f"✅ Key unblocked successfully!")
                print(f"   Response: {response.json() if response.content else 'Success'}")
                return True
            elif response.status_code == 404:
                print(f"   ⚠️ Endpoint not found, trying next...")
                continue
            elif response.status_code == 401:
                print(f"   ❌ Unauthorized - you may not have admin privileges")
                break
            else:
                print(f"   ⚠️ Status {response.status_code}: {response.text[:200]}")

        except requests.exceptions.ConnectionError:
            print(f"   ⚠️ Connection error, trying next...")
            continue
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue

    print("\n❌ Failed to unblock key. Please contact your LLM Gateway administrator.")
    print("   They can unblock your key via the admin console or API.")
    return False


def list_keys():
    """List all keys (requires admin privileges)."""
    print("📋 Listing all keys...")

    endpoints = [
        f"{GATEWAY_BASE_URL}/keys",
        f"{GATEWAY_BASE_URL}/api/keys",
        f"{GATEWAY_BASE_URL}/admin/keys",
    ]

    headers = {
        "Authorization": f"Bearer {ADMIN_KEY}",
        "Content-Type": "application/json"
    }

    for endpoint in endpoints:
        try:
            print(f"\n   Trying: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=30, verify=False)

            if response.status_code == 200:
                keys_data = response.json()
                print(f"✅ Keys retrieved successfully!")
                print(f"\n{keys_data}")
                return True
            elif response.status_code == 404:
                print(f"   ⚠️ Endpoint not found, trying next...")
                continue
            elif response.status_code == 401:
                print(f"   ❌ Unauthorized - you may not have admin privileges")
                break
            else:
                print(f"   ⚠️ Status {response.status_code}: {response.text[:200]}")

        except requests.exceptions.ConnectionError:
            print(f"   ⚠️ Connection error, trying next...")
            continue
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue

    print("\n❌ Failed to list keys.")
    return False


def create_key():
    """Create a new key (requires admin privileges)."""
    print("🔑 Creating new key...")
    print(f"   User: {USER_ID}")

    endpoints = [
        f"{GATEWAY_BASE_URL}/keys",
        f"{GATEWAY_BASE_URL}/api/keys",
        f"{GATEWAY_BASE_URL}/admin/keys",
    ]

    headers = {
        "Authorization": f"Bearer {ADMIN_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "user_id": USER_ID,
        "description": "Generated by manage_llm_keys.py"
    }

    for endpoint in endpoints:
        try:
            print(f"\n   Trying: {endpoint}")
            response = requests.post(endpoint, headers=headers, json=payload, timeout=30, verify=False)

            if response.status_code in (200, 201):
                key_data = response.json()
                print(f"✅ Key created successfully!")
                print(f"\n{key_data}")

                if "key" in key_data:
                    print(f"\n📝 Add this to your .env file:")
                    print(f"   LLM_GW_EXPRESS_KEY={key_data['key']}")
                return True
            elif response.status_code == 404:
                print(f"   ⚠️ Endpoint not found, trying next...")
                continue
            elif response.status_code == 401:
                print(f"   ❌ Unauthorized - you may not have admin privileges")
                break
            else:
                print(f"   ⚠️ Status {response.status_code}: {response.text[:200]}")

        except requests.exceptions.ConnectionError:
            print(f"   ⚠️ Connection error, trying next...")
            continue
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue

    print("\n❌ Failed to create key. Please contact your LLM Gateway administrator.")
    return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if not API_KEY:
        print("❌ Error: LLM_GW_EXPRESS_KEY not found in .env")
        sys.exit(1)

    if command == "check":
        success = check_key_status()
        sys.exit(0 if success else 1)
    elif command == "unblock":
        success = unblock_key()
        sys.exit(0 if success else 1)
    elif command == "list":
        success = list_keys()
        sys.exit(0 if success else 1)
    elif command == "create":
        success = create_key()
        sys.exit(0 if success else 1)
    else:
        print(f"❌ Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

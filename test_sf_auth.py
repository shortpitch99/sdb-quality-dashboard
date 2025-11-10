#!/usr/bin/env python3
"""
Test script to debug Salesforce authentication and report access.
"""

import os
import json
import requests
from quality_report_generator import QualityDataCollector

def test_sf_authentication():
    """Test Salesforce authentication methods."""
    print("🔍 Testing Salesforce Authentication...")
    print("=" * 50)
    
    collector = QualityDataCollector()
    
    # Test 1: Check environment variables
    print("1. Checking Environment Variables:")
    sf_instance_url = os.getenv("SF_INSTANCE_URL", "")
    sf_access_token = os.getenv("SF_ACCESS_TOKEN", "")
    
    print(f"   SF_INSTANCE_URL: {'✅ Set' if sf_instance_url else '❌ Not set'}")
    print(f"   SF_ACCESS_TOKEN: {'✅ Set' if sf_access_token else '❌ Not set'}")
    
    if sf_instance_url and sf_access_token:
        print(f"   Instance URL: {sf_instance_url}")
        print(f"   Token (first 10 chars): {sf_access_token[:10]}...")
    
    # Test 2: Try CLI authentication
    print("\n2. Testing CLI Authentication:")
    try:
        session = collector._get_sf_session(use_gus_cli=True)
        if session:
            print("   ✅ CLI Authentication successful")
            print(f"   Instance URL: {session['instance_url']}")
            print(f"   Access Token (first 10 chars): {session['access_token'][:10]}...")
            return session
        else:
            print("   ❌ CLI Authentication failed")
    except Exception as e:
        print(f"   ❌ CLI Authentication error: {e}")
    
    # Test 3: Try environment variable authentication
    print("\n3. Testing Environment Variable Authentication:")
    try:
        session = collector._get_sf_session(use_gus_cli=False)
        if session:
            print("   ✅ Environment Authentication successful")
            print(f"   Instance URL: {session['instance_url']}")
            print(f"   Access Token (first 10 chars): {session['access_token'][:10]}...")
            return session
        else:
            print("   ❌ Environment Authentication failed")
    except Exception as e:
        print(f"   ❌ Environment Authentication error: {e}")
    
    return None

def test_report_access(session, report_id="00OEE000002XRUv2AO"):
    """Test access to a specific Salesforce report."""
    if not session:
        print("❌ No valid session available for report testing")
        return False
    
    print(f"\n🔍 Testing Report Access: {report_id}")
    print("=" * 50)
    
    collector = QualityDataCollector()
    
    # Test direct API call
    url = f"{session['instance_url'].rstrip('/')}/services/data/v62.0/analytics/reports/{report_id}"
    
    print(f"API URL: {url}")
    
    try:
        headers = {
            "Authorization": f"Bearer {session['access_token']}",
            "Accept": "application/json",
        }
        
        print("Making API request...")
        resp = requests.get(url, headers=headers, params={"includeDetails": "true"}, timeout=60)
        
        print(f"Response Status: {resp.status_code}")
        
        if 200 <= resp.status_code < 300:
            data = resp.json()
            print("✅ Report access successful!")
            
            # Check if we have data
            fact_map = data.get('factMap', {})
            print(f"Fact Map Keys: {len(fact_map)} entries")
            
            if fact_map:
                print("Sample fact map keys:", list(fact_map.keys())[:5])
                
                # Try to get rows
                rows = collector._get_rows_from_report(data)
                print(f"Extracted Rows: {len(rows)} rows")
                
                if rows:
                    print("✅ Report contains data!")
                    print("Sample row keys:", list(rows[0].keys()) if rows else "No rows")
                    return True
                else:
                    print("⚠️ Report accessible but contains no data rows")
            else:
                print("⚠️ Report accessible but factMap is empty")
            
        else:
            print(f"❌ Report access failed: {resp.status_code}")
            print(f"Response: {resp.text[:500]}")
            
    except Exception as e:
        print(f"❌ Report access error: {e}")
    
    return False

def test_cli_availability():
    """Test if Salesforce CLI is available."""
    print("\n🔍 Testing Salesforce CLI Availability:")
    print("=" * 50)
    
    collector = QualityDataCollector()
    cli, mode = collector._load_sh_cli()
    
    if cli and mode:
        print(f"✅ Salesforce CLI available: {mode}")
        
        # Test CLI command
        try:
            if mode == "sf":
                result = cli("org", "list", "--json", _tty_out=False)
            else:
                result = cli("force:org:list", "--json", _tty_out=False)
            
            org_info = json.loads(str(result))
            if org_info.get("status") == 0:
                orgs = org_info.get("result", {}).get("nonScratchOrgs", [])
                print(f"Available orgs: {len(orgs)}")
                for org in orgs[:3]:  # Show first 3 orgs
                    print(f"  - {org.get('alias', 'No alias')}: {org.get('username', 'No username')}")
            else:
                print("❌ CLI command failed")
                
        except Exception as e:
            print(f"❌ CLI test error: {e}")
    else:
        print("❌ Salesforce CLI not available")
        print("Install with: npm install -g @salesforce/cli")

def main():
    """Main test function."""
    print("🚀 Salesforce Authentication & Report Access Test")
    print("=" * 60)
    
    # Test CLI availability first
    test_cli_availability()
    
    # Test authentication
    session = test_sf_authentication()
    
    # Test report access if we have a session
    if session:
        success = test_report_access(session, "00OEE000002XRUv2AO")
        if success:
            print("\n🎉 All tests passed! Authentication and report access working.")
        else:
            print("\n⚠️ Authentication works but report access failed.")
    else:
        print("\n❌ Authentication failed. Please check your setup.")
        print("\nTroubleshooting steps:")
        print("1. Install Salesforce CLI: npm install -g @salesforce/cli")
        print("2. Login to Salesforce: sf org login web")
        print("3. Or set environment variables:")
        print("   export SF_INSTANCE_URL='https://gus.lightning.force.com'")
        print("   export SF_ACCESS_TOKEN='your_access_token'")

if __name__ == "__main__":
    main()

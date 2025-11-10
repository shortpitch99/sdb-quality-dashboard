#!/usr/bin/env python3
"""
Simple test script to verify report access using existing sfdx session.
"""

import json
import subprocess
import requests

def get_sfdx_session():
    """Get session info from sfdx."""
    try:
        result = subprocess.run(['sfdx', 'force:org:list', '--json'], 
                              capture_output=True, text=True, check=True)
        org_info = json.loads(result.stdout)
        
        if org_info.get("status") == 0:
            orgs = org_info.get("result", {}).get("nonScratchOrgs", [])
            if not orgs:
                orgs = org_info.get("result", {}).get("other", [])
            
            for org in orgs:
                if org.get("connectedStatus") == "Connected":
                    return {
                        "access_token": org.get("accessToken"),
                        "instance_url": org.get("instanceUrl"),
                        "username": org.get("username")
                    }
    except Exception as e:
        print(f"Error getting sfdx session: {e}")
    return None

def test_report_access(session, report_id="00OEE000002XRUv2AO"):
    """Test access to a specific report."""
    if not session:
        print("❌ No session available")
        return False
    
    print(f"🔍 Testing report {report_id}")
    print(f"📧 User: {session['username']}")
    print(f"🌐 Instance: {session['instance_url']}")
    
    url = f"{session['instance_url'].rstrip('/')}/services/data/v62.0/analytics/reports/{report_id}"
    
    headers = {
        "Authorization": f"Bearer {session['access_token']}",
        "Accept": "application/json",
    }
    
    try:
        response = requests.get(url, headers=headers, params={"includeDetails": "true"}, timeout=60)
        print(f"📊 Response Status: {response.status_code}")
        
        if 200 <= response.status_code < 300:
            data = response.json()
            fact_map = data.get('factMap', {})
            print(f"✅ Success! Found {len(fact_map)} fact map entries")
            
            if fact_map:
                # Show sample data
                sample_key = list(fact_map.keys())[0]
                sample_fact = fact_map[sample_key]
                print(f"📋 Sample fact: {sample_key} -> {len(sample_fact.get('rows', []))} rows")
                return True
            else:
                print("⚠️ Report accessible but no data found")
                return False
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🚀 Simple Report Access Test")
    print("=" * 40)
    
    session = get_sfdx_session()
    if session:
        success = test_report_access(session)
        if success:
            print("\n🎉 Report access working! Authentication is good.")
        else:
            print("\n⚠️ Authentication works but report has issues.")
    else:
        print("❌ Could not get authenticated session from sfdx")

if __name__ == "__main__":
    main()

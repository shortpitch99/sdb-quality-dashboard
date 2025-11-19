#!/usr/bin/env python3
"""
Test script to verify Salesforce authentication error handling
"""
import sys
import json
from quality_report_generator import QualityDataCollector

def test_auth_error():
    """Test the authentication error handling in _fetch_report method"""
    
    # Create a collector instance
    collector = QualityDataCollector()
    
    # Create a fake session with invalid token
    fake_session = {
        'access_token': 'invalid_token_12345',
        'instance_url': 'https://gus.salesforce.com'
    }
    
    print("🧪 Testing Salesforce authentication error handling...")
    print("📋 Using invalid token to trigger 401 error")
    
    try:
        # This should trigger a 401 error and cause sys.exit(1)
        result = collector._fetch_report('00OEE000001TXjB2AW', fake_session, 'v62.0')
        print("❌ Test failed - should have exited with authentication error")
        return False
    except SystemExit as e:
        if e.code == 1:
            print("✅ Test passed - correctly detected authentication error and exited")
            return True
        else:
            print(f"❌ Test failed - exited with wrong code: {e.code}")
            return False
    except Exception as e:
        print(f"❌ Test failed with unexpected exception: {e}")
        return False

if __name__ == "__main__":
    success = test_auth_error()
    sys.exit(0 if success else 1)

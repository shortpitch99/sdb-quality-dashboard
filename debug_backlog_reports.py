#!/usr/bin/env python3
"""
Debug script to check what data is being returned from the backlog reports.
"""

import json
import subprocess
import requests
from quality_report_generator import QualityDataCollector

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

def debug_report(session, report_id, report_name):
    """Debug a specific report to see what data it returns."""
    print(f"\n🔍 Debugging {report_name} ({report_id})")
    print("=" * 60)
    
    collector = QualityDataCollector()
    
    # Fetch raw report data
    raw_data = collector._fetch_report(report_id, session, "v62.0")
    if not raw_data:
        print("❌ Failed to fetch report data")
        return
    
    print(f"✅ Report fetched successfully")
    
    # Analyze the structure
    fact_map = raw_data.get('factMap', {})
    print(f"📊 Fact Map: {len(fact_map)} entries")
    
    if fact_map:
        print("📋 Fact Map Keys:", list(fact_map.keys())[:10])  # Show first 10 keys
        
        # Count total rows across all facts
        total_rows = 0
        for key, fact in fact_map.items():
            rows = fact.get('rows', [])
            total_rows += len(rows)
            if len(rows) > 0:
                print(f"   {key}: {len(rows)} rows")
        
        print(f"📈 Total Rows Across All Facts: {total_rows}")
    
    # Test the parsing method
    print(f"\n🔧 Testing Parsing Method:")
    rows = collector._get_rows_from_report(raw_data)
    print(f"📋 Parsed Rows: {len(rows)}")
    
    if rows:
        print("📄 Sample Row Keys:", list(rows[0].keys()) if rows else "No rows")
        print("📄 First Few Rows:")
        for i, row in enumerate(rows[:5]):
            print(f"   Row {i+1}: {dict(list(row.items())[:3])}...")  # Show first 3 fields
    
    # Test specific parsing methods
    if report_name == "All-time Bug Backlog":
        print(f"\n🧪 Testing All-time Backlog Parsing:")
        backlog_items = collector.load_alltime_backlog_from_report(report_id, session, "v62.0")
        print(f"📊 Parsed Backlog Items: {len(backlog_items)}")
        
        if backlog_items:
            p0_p1_count = len([b for b in backlog_items if 'P0' in str(b.get('severity', '')) or 'P1' in str(b.get('severity', ''))])
            print(f"🔥 P0/P1 Critical Items: {p0_p1_count}")
            print(f"📋 Sample Item: {backlog_items[0] if backlog_items else 'None'}")
    
    elif report_name == "PRB Backlog":
        print(f"\n🧪 Testing PRB Backlog Parsing:")
        prb_items = collector.load_prb_backlog_from_report(report_id, session, "v62.0")
        print(f"📊 Parsed PRB Items: {len(prb_items)}")
        
        if prb_items:
            p0_p1_count = len([b for b in prb_items if 'P0' in str(b.get('priority', '')) or 'P1' in str(b.get('priority', ''))])
            print(f"🔥 P0/P1 Critical Items: {p0_p1_count}")
            print(f"📋 Sample Item: {prb_items[0] if prb_items else 'None'}")
    
    # Show report metadata
    print(f"\n📋 Report Metadata:")
    report_metadata = raw_data.get('reportMetadata', {})
    if report_metadata:
        print(f"   Name: {report_metadata.get('name', 'Unknown')}")
        print(f"   Type: {report_metadata.get('reportType', {}).get('type', 'Unknown')}")
        
        # Show column info
        detail_columns = report_metadata.get('detailColumns', [])
        print(f"   Columns ({len(detail_columns)}): {detail_columns[:5]}...")  # First 5 columns

def main():
    print("🚀 Backlog Reports Debug Analysis")
    print("=" * 60)
    
    session = get_sfdx_session()
    if not session:
        print("❌ Could not get authenticated session")
        return
    
    print(f"📧 User: {session['username']}")
    print(f"🌐 Instance: {session['instance_url']}")
    
    # Debug both backlog reports
    debug_report(session, "00OEE000002XRUv2AO", "All-time Bug Backlog")
    debug_report(session, "00OEE000002ZnZN2A0", "PRB Backlog")

if __name__ == "__main__":
    main()

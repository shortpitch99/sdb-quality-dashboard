#!/usr/bin/env python3
"""
Debug script to check CI Issues and Security Issues report data and priority parsing.
"""

import json
import subprocess
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

def debug_work_items_report(session, report_id, report_name, issue_type):
    """Debug a work items report to see what data it returns."""
    print(f"\n🔍 Debugging {report_name} ({report_id})")
    print("=" * 60)
    
    collector = QualityDataCollector()
    
    # Test the load_work_items_from_report method
    print(f"🧪 Testing load_work_items_from_report:")
    work_items = collector.load_work_items_from_report(report_id, session, issue_type, "v62.0")
    print(f"📊 Total Work Items: {len(work_items)}")
    
    if work_items:
        print(f"📄 Sample Item: {work_items[0]}")
        
        # Analyze priorities
        priorities = {}
        for item in work_items:
            priority = item.get('priority', 'Unknown')
            priorities[priority] = priorities.get(priority, 0) + 1
        
        print(f"📊 Priority Breakdown:")
        for priority, count in sorted(priorities.items()):
            print(f"   {priority}: {count}")
        
        # Count P0/P1 items
        p0_count = len([item for item in work_items if 'P0' in str(item.get('priority', '')).upper()])
        p1_count = len([item for item in work_items if 'P1' in str(item.get('priority', '')).upper()])
        
        print(f"🔥 P0 Items: {p0_count}")
        print(f"🔥 P1 Items: {p1_count}")
        print(f"🔥 Total P0/P1: {p0_count + p1_count}")
    
    # Also check raw report structure
    print(f"\n🔬 Raw Report Analysis:")
    raw_data = collector._fetch_report(report_id, session, "v62.0")
    if raw_data:
        metadata = raw_data.get('reportMetadata', {})
        detail_columns = metadata.get('detailColumns', [])
        print(f"📋 Report Columns ({len(detail_columns)}):")
        for i, col in enumerate(detail_columns):
            print(f"   {i}: {col}")
        
        # Check a sample row
        rows = collector._get_rows_from_report(raw_data)
        if rows:
            print(f"\n📄 Sample Raw Row:")
            sample_row = rows[0]
            for key, value in sample_row.items():
                if 'priority' in key.lower() or 'severity' in key.lower():
                    print(f"   {key}: {value}")

def main():
    print("🚀 CI Issues and Security Issues Debug Analysis")
    print("=" * 60)
    
    session = get_sfdx_session()
    if not session:
        print("❌ Could not get authenticated session")
        return
    
    print(f"📧 User: {session['username']}")
    print(f"🌐 Instance: {session['instance_url']}")
    
    # Debug CI Issues report
    debug_work_items_report(session, "00OEE000002WjvJ2AS", "CI Issues", "CI")
    
    # Debug Security Issues report  
    debug_work_items_report(session, "00OB0000002qWjvMAE", "Security Issues", "security")

if __name__ == "__main__":
    main()

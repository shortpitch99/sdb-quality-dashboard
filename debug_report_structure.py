#!/usr/bin/env python3
"""
Debug script to examine the detailed structure of Salesforce report data.
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

def analyze_report_structure(session, report_id, report_name):
    """Analyze the detailed structure of a report."""
    print(f"\n🔍 Analyzing {report_name} Structure")
    print("=" * 60)
    
    collector = QualityDataCollector()
    raw_data = collector._fetch_report(report_id, session, "v62.0")
    
    if not raw_data:
        print("❌ Failed to fetch report")
        return
    
    # Examine report metadata
    print("📋 Report Metadata:")
    metadata = raw_data.get('reportMetadata', {})
    print(f"   Name: {metadata.get('name')}")
    print(f"   Type: {metadata.get('reportType', {}).get('type')}")
    
    detail_columns = metadata.get('detailColumns', [])
    print(f"   Detail Columns ({len(detail_columns)}):")
    for i, col in enumerate(detail_columns):
        print(f"      {i}: {col}")
    
    # Examine fact map structure
    fact_map = raw_data.get('factMap', {})
    print(f"\n📊 Fact Map Analysis:")
    print(f"   Total Facts: {len(fact_map)}")
    
    # Look at first fact with data
    sample_fact_key = None
    sample_fact = None
    for key, fact in fact_map.items():
        if fact.get('rows') and len(fact['rows']) > 0:
            sample_fact_key = key
            sample_fact = fact
            break
    
    if sample_fact:
        print(f"\n🔬 Sample Fact Analysis ({sample_fact_key}):")
        rows = sample_fact.get('rows', [])
        print(f"   Rows: {len(rows)}")
        
        if rows:
            sample_row = rows[0]
            print(f"\n📄 Sample Row Structure:")
            print(f"   Row Keys: {list(sample_row.keys())}")
            
            # Examine data cells
            data_cells = sample_row.get('dataCells', [])
            print(f"\n🔢 Data Cells ({len(data_cells)}):")
            for i, cell in enumerate(data_cells):
                print(f"      Cell {i}: {dict(cell)}")
                
            # Try to map to columns
            print(f"\n🗂️ Column Mapping Attempt:")
            for i, cell in enumerate(data_cells):
                col_name = detail_columns[i] if i < len(detail_columns) else f"Unknown_{i}"
                value = cell.get('value', cell.get('label', 'No value'))
                field_name = cell.get('fieldName', 'No fieldName')
                print(f"      {col_name} -> {field_name} = {value}")

def create_enhanced_parser(session, report_id):
    """Create an enhanced parser for the specific report structure."""
    print(f"\n🔧 Creating Enhanced Parser for {report_id}")
    print("=" * 60)
    
    collector = QualityDataCollector()
    raw_data = collector._fetch_report(report_id, session, "v62.0")
    
    if not raw_data:
        print("❌ Failed to fetch report")
        return []
    
    # Get column mapping
    metadata = raw_data.get('reportMetadata', {})
    detail_columns = metadata.get('detailColumns', [])
    
    print(f"📋 Using columns: {detail_columns}")
    
    # Enhanced parsing
    fact_map = raw_data.get('factMap', {})
    all_rows = []
    
    for key, fact in fact_map.items():
        for row in fact.get('rows', []):
            data_cells = row.get('dataCells', [])
            parsed_row = {}
            
            # Map by position since fieldName might not be available
            for i, cell in enumerate(data_cells):
                if i < len(detail_columns):
                    column_name = detail_columns[i]
                    value = cell.get('value', cell.get('label'))
                    parsed_row[column_name] = value
                    
                    # Also try fieldName if available
                    field_name = cell.get('fieldName')
                    if field_name:
                        parsed_row[field_name] = value
            
            if parsed_row:  # Only add if we got some data
                all_rows.append(parsed_row)
    
    print(f"✅ Enhanced parsing extracted {len(all_rows)} rows")
    
    if all_rows:
        print(f"📄 Sample parsed row: {dict(list(all_rows[0].items())[:3])}")
    
    return all_rows

def main():
    print("🚀 Detailed Report Structure Analysis")
    print("=" * 60)
    
    session = get_sfdx_session()
    if not session:
        print("❌ Could not get authenticated session")
        return
    
    # Analyze both reports
    analyze_report_structure(session, "00OEE000002XRUv2AO", "All-time Bug Backlog")
    analyze_report_structure(session, "00OEE000002ZnZN2A0", "PRB Backlog")
    
    # Test enhanced parsing
    print("\n" + "="*60)
    print("🧪 Testing Enhanced Parsing")
    print("="*60)
    
    alltime_rows = create_enhanced_parser(session, "00OEE000002XRUv2AO")
    prb_rows = create_enhanced_parser(session, "00OEE000002ZnZN2A0")
    
    print(f"\n📊 Results:")
    print(f"   All-time Backlog: {len(alltime_rows)} rows")
    print(f"   PRB Backlog: {len(prb_rows)} rows")

if __name__ == "__main__":
    main()

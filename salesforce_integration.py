#!/usr/bin/env python3
"""
Salesforce Integration Module
Handles extraction of PRB and Critical Issues data from Salesforce reports.
"""

import requests
import json
import csv
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs
import time

class SalesforceReportExtractor:
    """Extracts data from Salesforce Lightning reports."""
    
    def __init__(self, session_id: str, instance_url: str):
        """
        Initialize Salesforce extractor.
        
        Args:
            session_id: Salesforce session ID for authentication
            instance_url: Salesforce instance URL (e.g., 'gus.lightning.force.com')
        """
        self.session_id = session_id
        self.instance_url = instance_url.replace('https://', '').replace('http://', '')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {session_id}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def extract_report_data(self, report_url: str, max_records: int = 200) -> List[Dict[str, Any]]:
        """
        Extract data from a Salesforce report URL.
        
        Args:
            report_url: Full Salesforce report URL
            max_records: Maximum number of records to retrieve
            
        Returns:
            List of dictionaries containing report data
        """
        try:
            # Parse report ID from URL
            report_id = self._extract_report_id(report_url)
            if not report_id:
                raise ValueError("Could not extract report ID from URL")
            
            # Get report metadata
            metadata = self._get_report_metadata(report_id)
            
            # Get report data
            report_data = self._get_report_data(report_id, max_records)
            
            # Parse and structure the data
            structured_data = self._parse_report_data(report_data, metadata)
            
            return structured_data
            
        except Exception as e:
            print(f"Error extracting Salesforce report data: {e}")
            return []
    
    def _extract_report_id(self, report_url: str) -> Optional[str]:
        """Extract report ID from Salesforce URL."""
        try:
            # Handle different URL formats
            if '/lightning/r/Report/' in report_url:
                # Lightning URL format
                parts = report_url.split('/lightning/r/Report/')
                if len(parts) > 1:
                    report_id = parts[1].split('/')[0]
                    return report_id
            elif 'reportId=' in report_url:
                # Classic URL format
                parsed_url = urlparse(report_url)
                query_params = parse_qs(parsed_url.query)
                if 'reportId' in query_params:
                    return query_params['reportId'][0]
            
            return None
        except Exception:
            return None
    
    def _get_report_metadata(self, report_id: str) -> Dict[str, Any]:
        """Get report metadata from Salesforce API."""
        url = f"https://{self.instance_url}/services/data/v58.0/analytics/reports/{report_id}/describe"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting report metadata: {e}")
            return {}
    
    def _get_report_data(self, report_id: str, max_records: int) -> Dict[str, Any]:
        """Get report data from Salesforce API."""
        url = f"https://{self.instance_url}/services/data/v58.0/analytics/reports/{report_id}"
        
        # Add query parameters for data retrieval
        params = {
            'includeDetails': 'true'
        }
        
        try:
            response = self.session.post(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting report data: {e}")
            return {}
    
    def _parse_report_data(self, report_data: Dict[str, Any], metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse raw report data into structured format."""
        parsed_data = []
        
        try:
            # Extract field mappings from metadata
            field_map = {}
            if 'reportMetadata' in metadata and 'detailColumns' in metadata['reportMetadata']:
                for i, column in enumerate(metadata['reportMetadata']['detailColumns']):
                    field_map[i] = column
            
            # Extract data rows
            if 'factMap' in report_data:
                fact_map = report_data['factMap']
                
                # Handle different report formats
                if 'T!T' in fact_map:  # Tabular report
                    rows = fact_map['T!T'].get('rows', [])
                    for row in rows:
                        row_data = {}
                        for i, cell in enumerate(row.get('dataCells', [])):
                            field_name = field_map.get(i, f'field_{i}')
                            row_data[field_name] = cell.get('label', cell.get('value', ''))
                        
                        if row_data:  # Only add non-empty rows
                            parsed_data.append(row_data)
            
            return parsed_data
            
        except Exception as e:
            print(f"Error parsing report data: {e}")
            return []
    
    def extract_prb_data(self, report_url: str) -> List[Dict[str, Any]]:
        """
        Extract PRB (Problem Report) data with specific parsing logic.
        
        Expected fields: ID, Title, Priority, Status, Description, Created Date
        """
        raw_data = self.extract_report_data(report_url)
        
        prb_data = []
        for row in raw_data:
            # Map common field names to standardized format
            prb_item = {
                'id': self._get_field_value(row, ['ID', 'Case Number', 'Number', 'PRB ID']),
                'title': self._get_field_value(row, ['Title', 'Subject', 'Summary', 'Description']),
                'priority': self._get_field_value(row, ['Priority', 'Severity', 'Urgency']),
                'status': self._get_field_value(row, ['Status', 'State', 'Case Status']),
                'description': self._get_field_value(row, ['Description', 'Details', 'Comments']),
                'created_date': self._get_field_value(row, ['Created Date', 'Date Created', 'Opened Date'])
            }
            
            # Only add if we have at least ID and title
            if prb_item['id'] and prb_item['title']:
                prb_data.append(prb_item)
        
        return prb_data
    
    def extract_critical_issues(self, report_url: str) -> List[Dict[str, Any]]:
        """
        Extract Critical Issues data with specific parsing logic.
        
        Expected fields: ID, Title, Severity, Status, Description, Impact, Created Date
        """
        raw_data = self.extract_report_data(report_url)
        
        critical_issues = []
        for row in raw_data:
            issue_item = {
                'id': self._get_field_value(row, ['ID', 'Issue ID', 'Incident ID', 'Number']),
                'title': self._get_field_value(row, ['Title', 'Subject', 'Issue Summary']),
                'severity': self._get_field_value(row, ['Severity', 'Priority', 'Critical Level']),
                'status': self._get_field_value(row, ['Status', 'State', 'Issue Status']),
                'description': self._get_field_value(row, ['Description', 'Details', 'Root Cause']),
                'impact': self._get_field_value(row, ['Impact', 'Customer Impact', 'Business Impact']),
                'created_date': self._get_field_value(row, ['Created Date', 'Reported Date', 'Incident Date'])
            }
            
            # Only add if we have at least ID and title
            if issue_item['id'] and issue_item['title']:
                critical_issues.append(issue_item)
        
        return critical_issues
    
    def _get_field_value(self, row: Dict[str, Any], possible_field_names: List[str]) -> str:
        """Get field value by trying multiple possible field names."""
        for field_name in possible_field_names:
            # Try exact match first
            if field_name in row:
                return str(row[field_name]) if row[field_name] is not None else ''
            
            # Try case-insensitive match
            for key in row.keys():
                if key.lower() == field_name.lower():
                    return str(row[key]) if row[key] is not None else ''
        
        return ''
    
    def save_raw_data_to_csv(self, data: List[Dict[str, Any]], filename: str):
        """Save raw report data to CSV file for debugging/archival."""
        if not data:
            print(f"No data to save to {filename}")
            return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            
            print(f"Raw data saved to {filename}")
            
        except Exception as e:
            print(f"Error saving data to CSV: {e}")

def test_salesforce_connection():
    """Test Salesforce connection and data extraction."""
    import os
    
    session_id = os.getenv('SALESFORCE_SESSION_ID')
    instance_url = os.getenv('SALESFORCE_INSTANCE', 'gus.lightning.force.com')
    
    if not session_id:
        print("No Salesforce session ID provided. Set SALESFORCE_SESSION_ID environment variable.")
        return
    
    extractor = SalesforceReportExtractor(session_id, instance_url)
    
    # Test PRB extraction
    print("Testing PRB data extraction...")
    prb_url = "https://gus.lightning.force.com/lightning/r/Report/00OEE000001TXjB2AW/view"
    prb_data = extractor.extract_prb_data(prb_url)
    print(f"Extracted {len(prb_data)} PRB records")
    
    if prb_data:
        print("Sample PRB record:")
        print(json.dumps(prb_data[0], indent=2))
        
        # Save raw data
        extractor.save_raw_data_to_csv(prb_data, 'prb_data_raw.csv')
    
    # Test Critical Issues extraction
    print("\nTesting Critical Issues data extraction...")
    critical_url = "https://gus.lightning.force.com/lightning/r/Report/00OEE0000014M4b2AE/view"
    critical_data = extractor.extract_critical_issues(critical_url)
    print(f"Extracted {len(critical_data)} critical issue records")
    
    if critical_data:
        print("Sample critical issue record:")
        print(json.dumps(critical_data[0], indent=2))
        
        # Save raw data
        extractor.save_raw_data_to_csv(critical_data, 'critical_issues_raw.csv')

if __name__ == "__main__":
    test_salesforce_connection()

#!/usr/bin/env python3
"""
Quality Report Dashboard - Streamlit Web Application
Interactive dashboard for viewing and analyzing quality reports.
"""

import streamlit as st
import os
import json
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import glob
from typing import Any, Dict, List, Optional, Tuple
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our quality report components
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quality_report_generator import QualityDataCollector, QualityReportGenerator, resolve_git_repo_path

# Configure Streamlit page
st.set_page_config(
    page_title="SDB Service Quality Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

class QualityReportDashboard:
    """Streamlit dashboard for quality reports."""
    
    def __init__(self):
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.reports_dir = os.path.join(script_dir, "reports")
        self.archive_dir = os.path.join(script_dir, "archive")
        
        # Ensure directories exist
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.archive_dir, exist_ok=True)
    
    def display_banner_with_timestamp(self, selected_week_reports: Dict) -> None:
        """Display the main banner with timestamp information from selected reports."""
        timestamp_text = "Quality Metrics & Analytics"
        
        # Get timestamp from any available report
        if selected_week_reports:
            for component_report in selected_week_reports.values():
                if 'path' in component_report:
                    try:
                        with open(component_report['path'], 'r') as f:
                            data = json.load(f)
                        generated_at = data.get('generated_at')
                        
                        if generated_at:
                            # Parse timestamp and calculate week range
                            from datetime import datetime, timedelta
                            dt = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
                            
                            # Calculate the previous week range (Monday to Sunday)
                            days_since_monday = dt.weekday()  # 0=Monday, 6=Sunday
                            current_week_start = dt - timedelta(days=days_since_monday)
                            # Get the previous week
                            week_start = current_week_start - timedelta(days=7)
                            week_end = week_start + timedelta(days=6)
                            
                            # Format dates
                            report_period = f"Week of {week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}"
                            collection_time = dt.strftime('%m/%d %H:%M')
                            
                            timestamp_text = f"Quality Report: {report_period}<br><small style='font-size: 0.8rem; color: #666;'>Data collected: {collection_time}</small>"
                            break
                    except Exception:
                        continue
        
        # Display banner
        st.markdown(f"""
        <div style="background: #f5f5f5; color: black; text-align: center; padding: 8px 20px; border-radius: 8px; margin: 10px auto 15px auto; max-width: 1040px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); border-top: 3px solid #333333;">
            <h1 style="margin: 0; font-size: 2.2rem; font-weight: 700; color: black; text-shadow: none; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">SDB Quality Dashboard</h1>
            <div style="width: 140px; height: 2px; background: linear-gradient(90deg, #4CAF50, #2196F3, #FF9800); margin: 8px auto;"></div>
            <p style="margin: 4px 0 0 0; font-size: 0.9rem; color: #333333;">{timestamp_text}</p>
        </div>
        """, unsafe_allow_html=True)
    
    def display_data_timestamp(self, data: Dict[str, Any]) -> None:
        """Display the report date range and collection timestamp."""
        generated_at = data.get('generated_at')
        
        if generated_at:
            try:
                # Parse the ISO timestamp
                from datetime import datetime, timedelta
                dt = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
                
                # Calculate the previous week range (Monday to Sunday)
                # Quality reports typically cover the previous week's data
                days_since_monday = dt.weekday()  # 0=Monday, 6=Sunday
                current_week_start = dt - timedelta(days=days_since_monday)
                # Get the previous week
                week_start = current_week_start - timedelta(days=7)
                week_end = week_start + timedelta(days=6)
                
                # Format dates
                report_period = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}"
                collection_time = dt.strftime('%m/%d %H:%M')
                
                # Display report period banner
                st.markdown(f"""
                <div style="text-align: center; padding: 12px; margin-bottom: 20px; 
                           background-color: #f8f9fa; border-radius: 8px; 
                           border-left: 4px solid #28a745;">
                    <p style="margin: 0; font-size: 1rem; color: #333; font-weight: 500;">
                        📅 <strong>Quality Report:</strong> Week of {report_period}
                    </p>
                    <p style="margin: 5px 0 0 0; font-size: 0.8rem; color: #666;">
                        Data collected: {collection_time}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                # Fallback if timestamp parsing fails
                st.markdown(f"""
                <div style="text-align: center; padding: 10px; margin-bottom: 20px; 
                           background-color: #f0f2f6; border-radius: 8px; 
                           border-left: 4px solid #0066cc;">
                    <p style="margin: 0; font-size: 0.9rem; color: #666;">
                        📅 Quality Report - Data collected: <strong>{generated_at}</strong>
                    </p>
                </div>
                """, unsafe_allow_html=True)
        else:
            # No timestamp available
            st.markdown(f"""
            <div style="text-align: center; padding: 10px; margin-bottom: 20px; 
                       background-color: #f0f2f6; border-radius: 8px; 
                       border-left: 4px solid #666;">
                <p style="margin: 0; font-size: 0.9rem; color: #666;">
                    📅 Quality Report - Collection timestamp not available
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    def get_reports(self) -> List[Dict[str, Any]]:
        """Get all available JSON archive files sorted by date (newest first)."""
        report_files = []
        
        # Get all JSON archive files from both directories
        search_dirs = [self.archive_dir, self.reports_dir]
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                pattern = os.path.join(search_dir, "quality_data_archive_*.json")
                files = glob.glob(pattern)
                
                for file_path in files:
                    try:
                        # Load JSON to get metadata
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                        
                        # Get date from metadata (preferred) or filename fallback
                        report_date = None
                        report_period = None
                        
                        if 'metadata' in data:
                            # Use report period end date from metadata for proper chronological ordering
                            if 'report_period_end' in data['metadata']:
                                try:
                                    report_date = datetime.strptime(data['metadata']['report_period_end'], '%Y-%m-%d')
                                    report_period = data['metadata'].get('report_period_display', '')
                                except ValueError:
                                    pass
                            
                            # Fallback to generated_at if report_period_end not available
                            if not report_date and 'generated_at' in data['metadata']:
                                try:
                                    report_date = datetime.fromisoformat(data['metadata']['generated_at'].replace('Z', '+00:00'))
                                except ValueError:
                                    pass
                        
                        # Final fallback to filename parsing
                        if not report_date:
                            filename = os.path.basename(file_path)
                            # Pattern: quality_data_archive_YYYYMMDD_HHMMSS.json
                            parts = filename.replace('.json', '').split('_')
                            if len(parts) >= 4:
                                date_str = f"{parts[-2]}_{parts[-1]}"
                                try:
                                    report_date = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                                except ValueError:
                                    pass
                        
                        if report_date:
                            report_files.append({
                                'path': file_path,
                                'date': report_date,
                                'type': 'Archive',
                                'filename': os.path.basename(file_path),
                                'period': report_period or report_date.strftime('%B %d-%d, %Y')
                            })
                    except (ValueError, IndexError, json.JSONDecodeError) as e:
                        # Skip files that don't match expected pattern or are corrupted
                        continue
        
        # Sort by date (newest first)
        report_files.sort(key=lambda x: x['date'], reverse=True)
        return report_files
    
    def get_archive_data(self, archive_file_path: str = None) -> Optional[Dict[str, Any]]:
        """Get archived data from specified file or most recent if none specified."""
        if archive_file_path:
            # Load specific archive file
            try:
                with open(archive_file_path, 'r') as f:
                    data = json.load(f)
                    return data
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error loading archive data from {archive_file_path}: {e}")
                return None
        else:
            # Fallback to most recent file
            search_dirs = [self.archive_dir, self.reports_dir]
            archive_files = []
            
            for search_dir in search_dirs:
                if os.path.exists(search_dir):
                    pattern = os.path.join(search_dir, "quality_data_archive_*.json")
                    archive_files.extend(glob.glob(pattern))
            
            if archive_files:
                # Get the most recent archive file (by modification time)
                archive_file = max(archive_files, key=os.path.getmtime)
                return self.get_archive_data(archive_file)
        
        return None
    
    def get_report_files(self) -> List[Dict[str, Any]]:
        """Get list of available report files with metadata."""
        report_files = []
        
        # Get all markdown files in reports directory
        pattern = os.path.join(self.reports_dir, "*.md")
        files = glob.glob(pattern)
        
        for file_path in files:
            filename = os.path.basename(file_path)
            file_stat = os.stat(file_path)
            
            # Extract date from filename if possible
            date_match = re.search(r'(\d{8}_\d{6})', filename)
            if date_match:
                try:
                    date_str = date_match.group(1)
                    file_date = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                except:
                    file_date = datetime.fromtimestamp(file_stat.st_mtime)
            else:
                file_date = datetime.fromtimestamp(file_stat.st_mtime)
            
            # Determine report type
            report_type = "Comprehensive" if "comprehensive" in filename else "Compact"
            
            report_files.append({
                'filename': filename,
                'path': file_path,
                'date': file_date,
                'type': report_type,
                'size': file_stat.st_size,
                'display_name': f"{report_type} Report - {file_date.strftime('%Y-%m-%d %H:%M')}"
            })
        
        # Sort by date, newest first
        report_files.sort(key=lambda x: x['date'], reverse=True)
        return report_files
    
    def get_component_reports(self, component: str) -> List[Dict[str, Any]]:
        """Get reports for a specific component."""
        component_reports = []
        component_dir = os.path.join(self.reports_dir, component)
        
        if not os.path.exists(component_dir):
            return component_reports
        
        try:
            for filename in os.listdir(component_dir):
                if filename.startswith('quality_data_archive_') and filename.endswith('.json'):
                    file_path = os.path.join(component_dir, filename)
                    
                    # Extract timestamp from filename
                    timestamp_match = re.search(r'quality_data_archive_(\d{8}_\d{6})\.json', filename)
                    if timestamp_match:
                        timestamp_str = timestamp_match.group(1)
                        try:
                            timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                            
                            component_reports.append({
                                'filename': filename,
                                'path': file_path,
                                'timestamp': timestamp,
                                'component': component,
                                'size': os.path.getsize(file_path)
                            })
                        except ValueError:
                            continue
        except Exception as e:
            st.error(f"Error reading component reports: {e}")
        
        # Sort by timestamp (newest first)
        component_reports.sort(key=lambda x: x['timestamp'], reverse=True)
        return component_reports
    
    def get_deployment_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get deployment data from either deployments or stagger_deployments key."""
        deployments = data.get('deployments', [])
        if not deployments:
            # Fallback to stagger_deployments format if available
            deployments = data.get('stagger_deployments', [])
        return deployments

    def parse_ci_data(self) -> List[Dict[str, Any]]:
        """CI data is now loaded from archived reports, not from ci.txt file."""
        # This function is kept for compatibility but CI data should come from archived reports
        return []
    
    def parse_security_data(self) -> List[Dict[str, Any]]:
        """Parse security bugs data from ss.txt file."""
        security_file = "ss.txt"  # Changed from security.txt to ss.txt
        security_data = []
        
        if not os.path.exists(security_file):
            return security_data
            
        try:
            with open(security_file, 'r') as f:
                lines = f.readlines()
                
            current_team = None
            current_priority = None
            
            for line in lines:
                line = line.strip()
                
                if not line:  # Skip empty lines
                    continue
                
                # Skip header/formatting lines - enhanced to include drill down
                if any(skip_word in line.lower() for skip_word in ['sorted by', 'select row', 'drill down', 'work:', 'subtotal', 'total(']):
                    continue
                
                # Parse team names (e.g., "Sayonara Data Management(13)")
                # Must contain team keywords AND have format "TeamName(number)" not "description(number issues)"
                if (line and '(' in line and line.endswith(')') and not line.startswith('P') and not line.startswith('W-') 
                    and not 'issues)' in line and not '/' in line and not '-' in line):
                    if any(team_keyword in line for team_keyword in ['Sayonara', 'SDB']):
                        current_team = line.split('(')[0].strip()
                        continue
                
                # Parse priority (e.g., "P4(13)")
                if line.startswith('P') and '(' in line and line.endswith(')'):
                    current_priority = line.split('(')[0].strip()
                    continue
                
                # Parse individual security issues with Work ID
                if line.startswith('W-'):
                    work_id = line
                    
                    # For security, we'll treat all issues in ss.txt as security-related
                    security_issue = {
                        'team': current_team or 'Unknown Team',
                        'work_id': work_id,
                        'subject': 'Security Issue',
                        'status': 'New',
                        'bug_type': 'Security Bug',
                        'priority': current_priority or 'P4'  # Use parsed priority, default to P4
                    }
                    security_data.append(security_issue)
            
            return security_data
                        
        except Exception as e:
            st.error(f"Error parsing security data: {e}")
            
        return security_data
    
    def parse_leftshift_data(self) -> List[Dict[str, Any]]:
        """Parse left shift bugs data from leftshift.txt file."""
        leftshift_file = "leftshift.txt"
        leftshift_data = []
        
        if not os.path.exists(leftshift_file):
            return leftshift_data
            
        try:
            with open(leftshift_file, 'r') as f:
                lines = f.readlines()
                
            current_team = None
            current_priority = None
            
            for line in lines:
                line = line.strip()
                
                if not line:  # Skip empty lines
                    continue
                
                # Skip header/formatting lines
                if any(skip_word in line.lower() for skip_word in ['sorted by', 'select row', 'work:', 'subtotal', 'total(']):
                    continue
                
                # Parse team names (e.g., "SDB Production Readiness(1)")
                if line and '(' in line and line.endswith(')') and not line.startswith('P') and not line.startswith('W-'):
                    if any(team_keyword in line for team_keyword in ['SDB', 'Sayonara', 'Production']):
                        current_team = line.split('(')[0].strip()
                        continue
                        
                # Parse priority (e.g., "P2(1)")
                if line.startswith('P') and '(' in line and line.endswith(')'):
                    current_priority = line.split('(')[0].strip()
                    continue
                
                # Parse individual left shift issues with Work ID  
                if line.startswith('W-'):
                    work_id = line
                    
                    leftshift_data.append({
                        'team': current_team or 'Unknown Team',
                        'work_id': work_id,
                        'subject': 'Left Shift Issue',
                        'status': 'New',
                        'priority': current_priority or 'P2'
                    })
                        
        except Exception as e:
            st.error(f"Error parsing left shift data: {e}")
            
        return leftshift_data
    
    def calculate_week_over_week_changes(self, current_data: Dict[str, Any], component: str) -> Dict[str, str]:
        """Calculate week-over-week percentage changes for key metrics."""
        changes = {}
        
        try:
            # Get component reports and find previous week
            component_reports = self.get_component_reports(component)
            if len(component_reports) < 2:
                return {}  # Need at least 2 weeks of data
            
            # Reports are sorted newest first, so [1] is previous week
            with open(component_reports[1]['path'], 'r') as f:
                previous_data = json.load(f)
            
            # Calculate changes for each metric
            def calc_pct_change(current_val, previous_val):
                if previous_val == 0:
                    return "+∞%" if current_val > 0 else "0%"
                pct = ((current_val - previous_val) / previous_val) * 100
                if pct > 0:
                    return f"+{pct:.1f}%"
                elif pct < 0:
                    return f"{pct:.1f}%"
                else:
                    return "0%"
            
            # At Risk Features
            current_at_risk = len([r for r in current_data.get('risks', []) if r.get('status') == 'At Risk'])
            previous_at_risk = len([r for r in previous_data.get('risks', []) if r.get('status') == 'At Risk'])
            changes['at_risk'] = calc_pct_change(current_at_risk, previous_at_risk)
            
            # Critical PRBs (P0/P1)
            current_prbs = current_data.get('prbs', [])
            current_critical_prbs = len([p for p in current_prbs if 'P0' in str(p.get('priority', '')) or 'P1' in str(p.get('priority', '')) or 'Sev0' in str(p.get('priority', '')) or 'Sev1' in str(p.get('priority', ''))])
            
            previous_prbs = previous_data.get('prbs', [])
            previous_critical_prbs = len([p for p in previous_prbs if 'P0' in str(p.get('priority', '')) or 'P1' in str(p.get('priority', '')) or 'Sev0' in str(p.get('priority', '')) or 'Sev1' in str(p.get('priority', ''))])
            changes['critical_prbs'] = calc_pct_change(current_critical_prbs, previous_critical_prbs)
            
            # Production Bugs
            current_bugs = current_data.get('bugs', [])
            current_prod_bugs = len([b for b in current_bugs if 'P0' in str(b.get('severity', '')) or 'P1' in str(b.get('severity', ''))])
            
            previous_bugs = previous_data.get('bugs', [])
            previous_prod_bugs = len([b for b in previous_bugs if 'P0' in str(b.get('severity', '')) or 'P1' in str(b.get('severity', ''))])
            changes['prod_bugs'] = calc_pct_change(current_prod_bugs, previous_prod_bugs)
            
            # Coverage (if available)
            current_coverage = current_data.get('coverage_summary', {}).get('overall', {}).get('line_coverage', 0)
            previous_coverage = previous_data.get('coverage_summary', {}).get('overall', {}).get('line_coverage', 0)
            if current_coverage > 0 and previous_coverage > 0:
                changes['coverage'] = calc_pct_change(current_coverage, previous_coverage)
            
            # CI Bug Score - use data from archived report
            current_ci_bugs = current_data.get('ci_issues', [])
            current_ci_score = sum(4 if 'P0' in str(bug.get('priority', '')) or 'P1' in str(bug.get('priority', '')) else 1 for bug in current_ci_bugs)
            
            # Load previous CI data (simplified for demo)
            changes['ci_score'] = "±0%"  # Placeholder - would need previous CI data file
            
            # Security Bugs - use data from archived report
            current_sec_bugs = current_data.get('security_issues', [])
            current_sec_score = sum(4 if 'P0' in str(bug.get('priority', '')) or 'P1' in str(bug.get('priority', '')) else 1 for bug in current_sec_bugs)
            changes['sec_score'] = "±0%"  # Placeholder
            
            # Left Shift - use data from archived report
            current_ls_bugs = current_data.get('leftshift_issues', [])
            current_ls_score = sum(4 if 'P0' in str(bug.get('priority', '')) or 'P1' in str(bug.get('priority', '')) else 1 for bug in current_ls_bugs)
            changes['ls_score'] = "±0%"  # Placeholder

            current_abs_bugs = current_data.get('abs_issues', [])
            current_abs_score = sum(4 if 'P0' in str(bug.get('priority', '')) or 'P1' in str(bug.get('priority', '')) else 1 for bug in current_abs_bugs)
            changes['abs_score'] = "±0%"  # Placeholder
            
            # Bug Backlog (critical bugs and total bugs)
            current_bugs = current_data.get('bugs', [])
            current_critical_backlog = len([b for b in current_bugs if 'P0' in str(b.get('severity', '')) or 'P1' in str(b.get('severity', ''))])
            current_total_backlog = len(current_bugs)
            
            previous_bugs = previous_data.get('bugs', [])
            previous_critical_backlog = len([b for b in previous_bugs if 'P0' in str(b.get('severity', '')) or 'P1' in str(b.get('severity', ''))])
            previous_total_backlog = len(previous_bugs)
            
            changes['critical_backlog'] = calc_pct_change(current_critical_backlog, previous_critical_backlog)
            changes['total_backlog'] = calc_pct_change(current_total_backlog, previous_total_backlog)
            
            # All-time Backlog (weighted score: 10×P0/P1 + 1×P2+)
            def _alltime_weighted_for_week(d: Dict[str, Any]) -> int:
                ab = d.get("alltime_backlog", [])
                if ab:
                    return alltime_backlog_weighted_score(ab)
                bugs = d.get("bugs", [])
                return alltime_backlog_weighted_score(bugs)

            current_alltime_score = _alltime_weighted_for_week(current_data)
            previous_alltime_score = _alltime_weighted_for_week(previous_data)
            changes["alltime_backlog"] = calc_pct_change(current_alltime_score, previous_alltime_score)
            
            # PRB Backlog (Salesforce `prb_backlog` or file-mode `prb_bugs`)
            current_prb_backlog = current_data.get('prb_backlog') or current_data.get('prb_bugs') or []
            current_critical_prb_backlog = len([b for b in current_prb_backlog if 'P0' in str(b.get('priority', '')) or 'P1' in str(b.get('priority', ''))])
            
            previous_prb_backlog = previous_data.get('prb_backlog') or previous_data.get('prb_bugs') or []
            previous_critical_prb_backlog = len([b for b in previous_prb_backlog if 'P0' in str(b.get('priority', '')) or 'P1' in str(b.get('priority', ''))])
            changes['prb_backlog'] = calc_pct_change(current_critical_prb_backlog, previous_critical_prb_backlog)
            
            # System Availability
            current_availability = current_data.get('system_availability', {}).get('achieved', 0.0)
            previous_availability = previous_data.get('system_availability', {}).get('achieved', 0.0)
            if current_availability > 0 and previous_availability > 0:
                changes['availability'] = calc_pct_change(current_availability, previous_availability)
            
            # Code Changes (lines changed from git stats)
            current_git_stats = current_data.get('git_stats', {})
            current_lines_changed = current_git_stats.get('lines_changed', 0)
            
            previous_git_stats = previous_data.get('git_stats', {})
            previous_lines_changed = previous_git_stats.get('lines_changed', 0)
            
            if current_lines_changed >= 0 and previous_lines_changed >= 0:  # Allow 0 values
                changes['code_changes'] = calc_pct_change(current_lines_changed, previous_lines_changed)
            
        except Exception as e:
            # If we can't calculate changes, return empty dict
            print(f"Could not calculate week-over-week changes: {e}")
            return {}
        
        return changes

    def inject_metric_dashboard_styles(self) -> None:
        """CSS for metric KPI cards (safe to call multiple times)."""
        st.markdown("""
        <style>
        /* KPI panels — modern card UI (gradient accent, depth, refined type) */
        .metric-card {
            position: relative;
            overflow: hidden;
            font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(165deg, #ffffff 0%, #f8fafc 45%, #f1f5f9 100%);
            border: 1px solid rgba(148, 163, 184, 0.45);
            border-radius: 16px;
            padding: 1.125rem 1.25rem;
            text-align: center;
            box-shadow:
                0 1px 2px rgba(15, 23, 42, 0.04),
                0 8px 28px rgba(15, 23, 42, 0.07);
            min-height: 148px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1),
                box-shadow 0.28s ease,
                border-color 0.25s ease;
        }
        .metric-card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #2563eb, #7c3aed, #0891b2);
            opacity: 0.92;
            z-index: 0;
        }
        .metric-card > * {
            position: relative;
            z-index: 1;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow:
                0 4px 12px rgba(15, 23, 42, 0.08),
                0 16px 40px rgba(15, 23, 42, 0.1);
            border-color: rgba(148, 163, 184, 0.65);
        }
        .metric-card-clickable {
            cursor: pointer;
        }
        .metric-card-clickable:hover {
            transform: translateY(-4px);
            box-shadow:
                0 8px 24px rgba(37, 99, 235, 0.14),
                0 20px 48px rgba(15, 23, 42, 0.12);
            border-color: rgba(59, 130, 246, 0.55);
        }
        .metric-card-clickable:active {
            transform: translateY(-1px);
            transition-duration: 0.1s;
        }
        .metric-value {
            font-size: 2.1rem;
            font-weight: 800;
            margin: 0.35rem 0;
            line-height: 1.05;
            letter-spacing: -0.03em;
            font-variant-numeric: tabular-nums;
            color: #0f172a;
        }
        .metric-label {
            font-size: 0.7rem;
            color: #64748b;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            margin-bottom: 0.2rem;
        }
        .metric-delta {
            font-size: 0.65rem;
            font-weight: 700;
            margin-top: 0.35rem;
            padding: 0.42rem 1rem;
            border-radius: 9999px;
            display: inline-block;
            letter-spacing: 0.08em;
            border: none;
            background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
            color: #475569;
            box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.35), 0 2px 6px rgba(15, 23, 42, 0.06);
        }
        .metric-delta-green {
            background: linear-gradient(180deg, #ecfdf5 0%, #d1fae5 100%) !important;
            color: #047857 !important;
            box-shadow: 0 0 0 1px rgba(16, 185, 129, 0.35), 0 2px 10px rgba(16, 185, 129, 0.18) !important;
        }
        .metric-delta-yellow {
            background: linear-gradient(180deg, #fffbeb 0%, #fef3c7 100%) !important;
            color: #b45309 !important;
            box-shadow: 0 0 0 1px rgba(245, 158, 11, 0.4), 0 2px 10px rgba(245, 158, 11, 0.15) !important;
        }
        .metric-delta-red {
            background: linear-gradient(180deg, #fef2f2 0%, #fecaca 100%) !important;
            color: #b91c1c !important;
            box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.35), 0 2px 10px rgba(239, 68, 68, 0.15) !important;
        }
        .metric-delta-gray {
            background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%) !important;
            color: #64748b !important;
            box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.45), 0 2px 6px rgba(15, 23, 42, 0.05) !important;
        }
        .metric-total {
            font-size: 0.8125rem;
            color: #64748b;
            font-weight: 500;
            margin-top: 0.25rem;
            letter-spacing: 0.01em;
        }
        .metric-value-row {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.75rem;
            flex-wrap: wrap;
            margin: 0.3rem 0;
        }
        .metric-value-row .metric-value {
            margin: 0;
        }
        .metric-value-row .metric-delta {
            margin-top: 0;
        }
        /* Line Coverage: fill card like other dev KPIs (label + value row + subtitle line) */
        .metric-card--line-coverage {
            justify-content: flex-start;
        }
        .metric-line-coverage-body {
            flex: 1 1 auto;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            gap: 0.35rem;
            width: 100%;
            min-height: 0;
        }
        .metric-line-coverage-body .metric-total {
            min-height: 1.35em;
            line-height: 1.35;
        }
        .metric-line-coverage-body .metric-delta {
            margin-top: 0.35rem;
        }
        .metric-card--line-coverage::before {
            background: linear-gradient(90deg, #0ea5e9, #6366f1, #a855f7);
        }
        </style>
        """, unsafe_allow_html=True)

    def render_production_kpi_row_hybrid(
        self,
        shared_data: Optional[Dict[str, Any]],
        tab_data: Dict[str, Any],
        tab_component: str,
        level_label: Optional[str] = None,
    ) -> None:
        """Production metrics: fleet-wide row (Engine) + {label}-level row (component report)."""
        self.inject_metric_dashboard_styles()
        st.markdown('<h4 id="production-metrics">🏭 Production Metrics</h4>', unsafe_allow_html=True)

        name = level_label if level_label is not None else tab_component
        eng = PRODUCTION_METRICS_SOURCE
        shared_changes = (
            self.calculate_week_over_week_changes(shared_data, eng)
            if shared_data is not None
            else {}
        )
        tab_changes = self.calculate_week_over_week_changes(tab_data, tab_component)

        risks_tab = tab_data.get('risks', [])
        risk_status_count: Dict[str, int] = {}
        for risk in risks_tab:
            status = risk.get('status', 'Unknown')
            risk_status_count[status] = risk_status_count.get(status, 0) + 1
        at_risk_count = risk_status_count.get('At Risk', 0)
        total_risks = len(risks_tab)

        bugs_tab = tab_data.get('bugs', [])
        p0_bugs = len([b for b in bugs_tab if 'P0' in str(b.get('severity', ''))])
        p1_bugs = len([b for b in bugs_tab if 'P1' in str(b.get('severity', ''))])
        p2_plus_bugs = len(
            [b for b in bugs_tab if any(p in str(b.get('severity', '')) for p in ['P2', 'P3', 'P4'])]
        )
        critical_prod_bugs = p0_bugs + p1_bugs
        bug_score = (critical_prod_bugs * 4) + (p2_plus_bugs * 1)
        if bug_score > 32:
            prod_bug_status = "RED"
        elif bug_score > 16:
            prod_bug_status = "YELLOW"
        else:
            prod_bug_status = "GREEN"
        total_bugs = len(bugs_tab)

        changes = dict(shared_changes)
        if tab_changes.get('at_risk'):
            changes['at_risk'] = tab_changes['at_risk']
        if tab_changes.get('prod_bugs'):
            changes['prod_bugs'] = tab_changes['prod_bugs']

        if shared_data is not None:
            prbs = shared_data.get('prbs', [])
            p0_prbs = len([p for p in prbs if 'P0' in str(p.get('priority', '')) or 'Sev0' in str(p.get('priority', ''))])
            p1_prbs = len([p for p in prbs if 'P1' in str(p.get('priority', '')) or 'Sev1' in str(p.get('priority', ''))])
            critical_prbs = p0_prbs + p1_prbs
            if p0_prbs > 0:
                prb_status = "CRITICAL"
            elif critical_prbs > 4:
                prb_status = "HIGH RISK"
            elif critical_prbs > 2:
                prb_status = "ELEVATED"
            else:
                prb_status = "GREEN"
            total_prbs = len(prbs)

            deployments = self.get_deployment_data(shared_data)
            dominant_version = "N/A"
            second_version = "N/A"
            dominant_percentage = 0.0
            second_percentage = 0.0
            if deployments:
                version_counts: Dict[str, int] = {}
                total_cells = 0
                for deployment in deployments:
                    version = deployment.get('version', 'Unknown')
                    count = deployment.get('count', deployment.get('cells', 0))
                    if count > 0 and version != 'Unknown':
                        version_counts[version] = version_counts.get(version, 0) + count
                        total_cells += count
                if version_counts:
                    sorted_versions = sorted(version_counts.items(), key=lambda x: x[1], reverse=True)
                    dominant_version_data = sorted_versions[0]
                    dominant_version = f"v{dominant_version_data[0]}"
                    dominant_percentage = (dominant_version_data[1] / total_cells * 100) if total_cells > 0 else 0
                    if len(sorted_versions) > 1:
                        second_version_data = sorted_versions[1]
                        second_version = f"v{second_version_data[0]}"
                        second_percentage = (second_version_data[1] / total_cells * 100) if total_cells > 0 else 0

            availability_data = shared_data.get('system_availability', {})
            availability_achieved = availability_data.get('achieved', 0.0)
            availability_slo = availability_data.get('slo', 99.9)
        else:
            critical_prbs = 0
            prb_status = "—"
            total_prbs = 0
            dominant_version = "—"
            second_version = "N/A"
            dominant_percentage = 0.0
            second_percentage = 0.0
            availability_achieved = 0.0
            availability_slo = 99.9

        st.markdown("##### Fleet-wide metrics")
        st.caption(
            f"General fleet signals from the **{eng}** report — same values on every tab for the selected week."
        )
        fleet1, fleet2, fleet3 = st.columns(3)

        with fleet1:
            if shared_data is not None:
                prb_delta_class = "metric-delta-green" if prb_status == "GREEN" else (
                    "metric-delta-yellow" if prb_status in ["ELEVATED"] else "metric-delta-red"
                )
                critical_prbs_display = f"{critical_prbs}"
                if changes.get('critical_prbs'):
                    critical_prbs_display += f" <span style='font-size: 1.0rem; color: #666;'>({changes['critical_prbs']})</span>"
                st.markdown(f"""
                <a href="#problem-reports-analysis" style="text-decoration: none; color: inherit;">
                    <div class="metric-card metric-card-clickable">
                    <div class="metric-label">🚨 Sev 0/1 PRBs</div>
                    <div class="metric-value">{critical_prbs_display}</div>
                        <div class="metric-total">of {total_prbs} total</div>
                        <div class="metric-delta {prb_delta_class}">
                        {prb_status}
                    </div>
                </div>
                </a>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="metric-card">
                    <div class="metric-label">🚨 Sev 0/1 PRBs</div>
                    <div class="metric-value">—</div>
                    <div class="metric-total">No Engine report</div>
                    <div class="metric-delta metric-delta-yellow">N/A</div>
                </div>
                """, unsafe_allow_html=True)

        with fleet2:
            if shared_data is not None:
                second_line = f"2nd: {second_version} ({second_percentage:.1f}%)" if second_version != "N/A" else "Single version"
                st.markdown(f"""
                <a href="#deployment-analysis" style="text-decoration: none; color: inherit;">
                    <div class="metric-card metric-card-clickable">
                        <div class="metric-label">🚀 Prod Deployment</div>
                    <div class="metric-value">{dominant_version}</div>
                        <div class="metric-total">Dominant in fleet ({dominant_percentage:.1f}%)</div>
                    <div class="metric-delta">
                            {second_line}
                        </div>
                    </div>
                </a>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="metric-card">
                    <div class="metric-label">🚀 Prod Deployment</div>
                    <div class="metric-value">—</div>
                    <div class="metric-total">No Engine report</div>
                    <div class="metric-delta metric-delta-yellow">N/A</div>
                </div>
                """, unsafe_allow_html=True)

        with fleet3:
            if shared_data is not None:
                availability_display = f"{availability_achieved:.2f}%"
                if changes.get('availability'):
                    availability_display += f" <span style='font-size: 1.0rem; color: #666;'>({changes['availability']})</span>"
                if availability_achieved >= availability_slo:
                    availability_delta_class = "metric-delta-green"
                    availability_status = "MEETS SLO"
                elif availability_achieved >= (availability_slo - 0.1):
                    availability_delta_class = "metric-delta-yellow"
                    availability_status = "NEAR SLO"
                else:
                    availability_delta_class = "metric-delta-red"
                    availability_status = "BELOW SLO"
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">⚡ System Availability</div>
                    <div class="metric-value">{availability_display}</div>
                    <div class="metric-total">SLO: {availability_slo}%</div>
                    <div class="metric-delta {availability_delta_class}">
                        {availability_status}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="metric-card">
                    <div class="metric-label">⚡ System Availability</div>
                    <div class="metric-value">—</div>
                    <div class="metric-total">No Engine report</div>
                    <div class="metric-delta metric-delta-yellow">N/A</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("")
        st.markdown(f"##### {name}-level metrics")
        st.caption(
            f"Component-specific production signals for **{name}** — change when you switch tabs."
        )
        tab1, tab2 = st.columns(2)

        with tab1:
            risk_delta_class = "metric-delta-green" if at_risk_count == 0 else (
                "metric-delta-yellow" if at_risk_count <= 2 else "metric-delta-red"
            )
            at_risk_display = f"{at_risk_count}"
            if changes.get('at_risk'):
                at_risk_display += f" <span style='font-size: 1.0rem; color: #666;'>({changes['at_risk']})</span>"
            st.markdown(f"""
            <a href="#risk-assessment" style="text-decoration: none; color: inherit;">
                <div class="metric-card metric-card-clickable">
                    <div class="metric-label">🚀 Feature Rollout Risk</div>
                <div class="metric-value">{at_risk_display}</div>
                    <div class="metric-total">of {total_risks} total</div>
                    <div class="metric-delta {risk_delta_class}">
                        {"GREEN" if at_risk_count == 0 else ("YELLOW" if at_risk_count <= 2 else "RED")}
                </div>
            </div>
            </a>
            """, unsafe_allow_html=True)

        with tab2:
            prod_delta_class = "metric-delta-green" if prod_bug_status == "GREEN" else (
                "metric-delta-yellow" if prod_bug_status == "YELLOW" else "metric-delta-red"
            )
            critical_prod_bugs_display = f"{critical_prod_bugs}"
            if changes.get('prod_bugs'):
                critical_prod_bugs_display += f" <span style='font-size: 1.0rem; color: #666;'>({changes['prod_bugs']})</span>"
            p0p1_href = p0p1_prod_bugs_metric_href(tab_component)
            p0p1_extra = ' target="_blank" rel="noopener noreferrer"' if p0p1_href.startswith('https') else ''
            st.markdown(f"""
            <a href="{p0p1_href}"{p0p1_extra} style="text-decoration: none; color: inherit;">
                <div class="metric-card metric-card-clickable">
                    <div class="metric-label">🐛 P0/P1 Prod Bugs</div>
                <div class="metric-value">{critical_prod_bugs_display}</div>
                    <div class="metric-total">of {total_bugs} total</div>
                    <div class="metric-delta {prod_delta_class}">
                        {prod_bug_status}
                </div>
            </div>
            </a>
            """, unsafe_allow_html=True)

        engine_tab_note = (
            " On the **Engine** tab, both rows still read one Engine JSON—different fields for fleet vs rollout/bugs."
            if tab_component == eng
            else ""
        )
        st.caption(
            f"**Fleet-wide row:** PRBs, deployment, availability (**{eng}**). "
            f"**{name}-level row:** rollout risk and P0/P1 prod bugs (report folder **`{tab_component}`**)."
            f"{engine_tab_note}"
        )
    
    def create_metrics_dashboard(
        self,
        data: Dict[str, Any],
        component: str = None,
        kpi_scope: str = 'all',
        development_heading_suffix: Optional[str] = None,
    ):
        """Render KPI cards. kpi_scope: 'all' | 'production' | 'development'."""
        
        # Calculate week-over-week changes if component is provided
        changes = {}
        if component:
            changes = self.calculate_week_over_week_changes(data, component)
        
        # Calculate all metrics first
        risks = data.get('risks', [])
        risk_status_count = {}
        for risk in risks:
            status = risk.get('status', 'Unknown')
            risk_status_count[status] = risk_status_count.get(status, 0) + 1
        
        at_risk_count = risk_status_count.get('At Risk', 0)
        
        # PRB metrics - focus on P0/P1 (Sev 0/1) regardless of status
        prbs = data.get('prbs', [])
        p0_prbs = len([p for p in prbs if 'P0' in str(p.get('priority', '')) or 'Sev0' in str(p.get('priority', ''))])
        p1_prbs = len([p for p in prbs if 'P1' in str(p.get('priority', '')) or 'Sev1' in str(p.get('priority', ''))])
        critical_prbs = p0_prbs + p1_prbs
        
        # Determine PRB status
        if p0_prbs > 0:
            prb_status = "CRITICAL"
            prb_color = "#C0392B"  # Bright Red
            prb_bg_color = "#FADBD8"
        elif critical_prbs > 4:
            prb_status = "HIGH RISK"
            prb_color = "#E74C3C"  # Red
            prb_bg_color = "#FADBD8"
        elif critical_prbs > 2:
            prb_status = "ELEVATED"
            prb_color = "#F39C12"  # Orange
            prb_bg_color = "#FEF9E7"
        else:
            prb_status = "GREEN"
            prb_color = "#27AE60"  # Green
            prb_bg_color = "#D5F4E6"
        
        # Production Bug metrics with scoring system
        bugs = data.get('bugs', [])
        p0_bugs = len([b for b in bugs if 'P0' in str(b.get('severity', ''))])
        p1_bugs = len([b for b in bugs if 'P1' in str(b.get('severity', ''))])
        p2_plus_bugs = len([b for b in bugs if any(p in str(b.get('severity', '')) for p in ['P2', 'P3', 'P4'])])
        
        
        # Production bug scoring: P0/P1 = 4 points, P2+ = 1 point
        critical_prod_bugs = p0_bugs + p1_bugs  # Count of P0/P1 bugs
        bug_score = (critical_prod_bugs * 4) + (p2_plus_bugs * 1)
        
        # Determine production bug status based on scoring
        if bug_score > 32:
            prod_bug_status = "RED"
            prod_bug_color = "#C0392B"
        elif bug_score > 16:
            prod_bug_status = "YELLOW" 
            prod_bug_color = "#F39C12"
        else:
            prod_bug_status = "GREEN"
            prod_bug_color = "#27AE60"
        
        # Other metrics - use Overall Line Coverage from coverage.txt instead of component average
        coverage_summary = data.get('coverage_summary', {})
        if coverage_summary and 'overall' in coverage_summary:
            # Use actual Overall Line Coverage from coverage.txt
            avg_coverage = coverage_summary['overall'].get('line_coverage', 0.0)
        else:
            # Fallback to component-based average if coverage.txt data not available
            coverage = data.get('coverage', [])
            avg_coverage = sum(c.get('line_coverage', 0) for c in coverage) / len(coverage) if coverage else 0
        
        # Calculate CI metrics with scoring system
        ci_issues = data.get('ci_issues', [])
        ci_p0_bugs = len([b for b in ci_issues if 'P0' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        ci_p1_bugs = len([b for b in ci_issues if 'P1' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        ci_p2_plus_bugs = len([b for b in ci_issues if any(p in str(b.get('severity', '') + str(b.get('priority', ''))).upper() for p in ['P2', 'P3', 'P4'])])
        
        # Handle reports without priority data - apply fallback logic
        if ci_p0_bugs == 0 and ci_p1_bugs == 0 and ci_p2_plus_bugs == 0 and len(ci_issues) > 0:
            # All items defaulted to P2, redistribute based on estimated priorities
            estimated_high_priority = max(1, len(ci_issues) // 5)  # 20% high priority
            ci_p1_bugs = estimated_high_priority
            ci_p2_plus_bugs = len(ci_issues) - estimated_high_priority
        
        # CI scoring: P0/P1 = 4 points, P2+ = 1 point
        ci_bug_score = (ci_p0_bugs + ci_p1_bugs) * 4 + ci_p2_plus_bugs * 1
        
        # Determine CI status: Yellow > 25, Red > 50
        if ci_bug_score > 50:
            ci_bug_status = "RED"
        elif ci_bug_score > 25:
            ci_bug_status = "YELLOW"
        else:
            ci_bug_status = "GREEN"
        
        # Calculate security bug metrics with scoring system
        security_bugs = data.get('security_issues', [])
        sec_p0_bugs = len([b for b in security_bugs if 'P0' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        sec_p1_bugs = len([b for b in security_bugs if 'P1' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        sec_p2_plus_bugs = len([b for b in security_bugs if any(p in str(b.get('severity', '') + str(b.get('priority', ''))).upper() for p in ['P2', 'P3', 'P4'])])
        
        # Security issues now have real priority data - no fallback needed
        
        # Security bug scoring: P0/P1 = 4 points, P2+ = 1 point
        critical_sec_bugs = sec_p0_bugs + sec_p1_bugs
        sec_bug_score = critical_sec_bugs * 4 + sec_p2_plus_bugs * 1
        
        # Determine security bug status: Yellow > 16, Red > 32
        if sec_bug_score > 32:
            sec_bug_status = "RED"
        elif sec_bug_score > 16:
            sec_bug_status = "YELLOW"
        else:
            sec_bug_status = "GREEN"
        
        # Calculate Left Shift metrics with same scoring system
        leftshift_issues = data.get('leftshift_issues', [])
        ls_p0_bugs = len([b for b in leftshift_issues if 'P0' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        ls_p1_bugs = len([b for b in leftshift_issues if 'P1' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        ls_p2_plus_bugs = len([b for b in leftshift_issues if any(p in str(b.get('severity', '') + str(b.get('priority', ''))).upper() for p in ['P2', 'P3', 'P4'])])
        
        # Left Shift scoring: P0/P1 = 4 points, P2+ = 1 point
        critical_ls_bugs = ls_p0_bugs + ls_p1_bugs
        ls_bug_score = critical_ls_bugs * 4 + ls_p2_plus_bugs * 1
        
        # Determine Left Shift status: Yellow > 25, Red > 50
        if ls_bug_score > 50:
            ls_bug_status = "RED"
        elif ls_bug_score > 25:
            ls_bug_status = "YELLOW"
        else:
            ls_bug_status = "GREEN"
        
        # Calculate ABS bug metrics (same scoring as Left Shift)
        abs_issues = data.get('abs_issues', [])
        abs_p0_bugs = len([b for b in abs_issues if 'P0' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        abs_p1_bugs = len([b for b in abs_issues if 'P1' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        abs_p2_plus_bugs = len([b for b in abs_issues if any(p in str(b.get('severity', '') + str(b.get('priority', ''))).upper() for p in ['P2', 'P3', 'P4'])])
        critical_abs_bugs = abs_p0_bugs + abs_p1_bugs
        abs_bug_score = critical_abs_bugs * 4 + abs_p2_plus_bugs * 1
        if abs_bug_score > 50:
            abs_bug_status = "RED"
        elif abs_bug_score > 25:
            abs_bug_status = "YELLOW"
        else:
            abs_bug_status = "GREEN"
        
        # Display professional metric cards
        self.create_two_line_metric_cards(
            at_risk_count,
            len(risks),
            critical_prbs,
            prb_status,
            prb_color,
            prb_bg_color,
            critical_prod_bugs,
            prod_bug_status,
            avg_coverage,
            data,
            ci_bug_score,
            ci_bug_status,
            critical_sec_bugs,
            sec_bug_status,
            ls_bug_score,
            ls_bug_status,
            abs_bug_score,
            abs_bug_status,
            changes,
            kpi_scope=kpi_scope,
            development_heading_suffix=development_heading_suffix,
            prod_bugs_link_folder=component,
        )


    def create_two_line_metric_cards(
        self,
        at_risk_count,
        total_risks,
        critical_prbs,
        prb_status,
        prb_color,
        prb_bg_color,
        critical_prod_bugs,
        prod_bug_status,
        avg_coverage,
        data,
        ci_bug_score,
        ci_bug_status,
        critical_sec_bugs,
        sec_bug_status,
        ls_bug_score,
        ls_bug_status,
        abs_bug_score,
        abs_bug_status,
        changes: Dict[str, str] = None,
        kpi_scope: str = 'all',
        development_heading_suffix: Optional[str] = None,
        prod_bugs_link_folder: Optional[str] = None,
    ):
        """KPI cards: production row, development rows, or both (kpi_scope)."""
        
        # Use empty dict if no changes provided
        if changes is None:
            changes = {}
        
        # Calculate CI P0/P1 counts for display
        ci_issues = data.get('ci_issues', [])
        ci_p0_bugs = len([b for b in ci_issues if 'P0' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        ci_p1_bugs = len([b for b in ci_issues if 'P1' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        ci_p0_p1_count = ci_p0_bugs + ci_p1_bugs
        
        # Calculate Left Shift P0/P1 counts for display
        leftshift_issues = data.get('leftshift_issues', [])
        ls_p0_bugs = len([b for b in leftshift_issues if 'P0' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        ls_p1_bugs = len([b for b in leftshift_issues if 'P1' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        ls_p0_p1_count = ls_p0_bugs + ls_p1_bugs
        
        # ABS bugs P0/P1 counts for display
        abs_issues = data.get('abs_issues', [])
        abs_p0_bugs = len([b for b in abs_issues if 'P0' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        abs_p1_bugs = len([b for b in abs_issues if 'P1' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        abs_p0_p1_count = abs_p0_bugs + abs_p1_bugs
        
        # Calculate deployment metrics
        deployments = self.get_deployment_data(data)
        deployment_status, deployment_summary = self.calculate_deployment_status(data)
        
        # Calculate dominant SDB version from deployment.csv data
        dominant_version = "N/A"
        second_version = "N/A"
        dominant_percentage = 0
        second_percentage = 0
        
        if deployments:
            version_counts = {}
            total_cells = 0
            
            for deployment in deployments:
                version = deployment.get('version', 'Unknown')
                count = deployment.get('count', deployment.get('cells', 0))
                
                if count > 0 and version != 'Unknown':
                    version_counts[version] = version_counts.get(version, 0) + count
                    total_cells += count
            
            if version_counts:
                # Sort versions by cell count (descending)
                sorted_versions = sorted(version_counts.items(), key=lambda x: x[1], reverse=True)
                
                # Get dominant version (most cells)
                dominant_version_data = sorted_versions[0]
                dominant_version = f"v{dominant_version_data[0]}"
                dominant_percentage = (dominant_version_data[1] / total_cells * 100) if total_cells > 0 else 0
                
                # Get second most prevalent version if it exists
                if len(sorted_versions) > 1:
                    second_version_data = sorted_versions[1]
                    second_version = f"v{second_version_data[0]}"
                    second_percentage = (second_version_data[1] / total_cells * 100) if total_cells > 0 else 0
        
        self.inject_metric_dashboard_styles()

        show_production = kpi_scope in ('all', 'production')
        show_development = kpi_scope in ('all', 'development')

        if not show_production and not show_development:
            return

        # Production Metrics (Top Row)
        if show_production:
            st.markdown('<h4 id="production-metrics">🏭 Production Metrics</h4>', unsafe_allow_html=True)
            col1, col2, col3, col4, col5_prod = st.columns(5)
        
            with col1:
                # Feature Rollout Risk color logic: green if 0, yellow if 1-2, red if >2
                risk_delta_class = "metric-delta-green" if at_risk_count == 0 else ("metric-delta-yellow" if at_risk_count <= 2 else "metric-delta-red")
                at_risk_display = f"{at_risk_count}"
                if changes.get('at_risk'):
                    at_risk_display += f" <span style='font-size: 1.0rem; color: #666;'>({changes['at_risk']})</span>"
                st.markdown(f"""
                <a href="#risk-assessment" style="text-decoration: none; color: inherit;">
                    <div class="metric-card metric-card-clickable">
                        <div class="metric-label">🚀 Feature Rollout Risk</div>
                    <div class="metric-value">{at_risk_display}</div>
                        <div class="metric-total">of {total_risks} total</div>
                        <div class="metric-delta {risk_delta_class}">
                            {"GREEN" if at_risk_count == 0 else ("YELLOW" if at_risk_count <= 2 else "RED")}
                    </div>
                </div>
                </a>
                """, unsafe_allow_html=True)

            with col2:
                total_prbs = len(data.get('prbs', []))
                prb_delta_class = "metric-delta-green" if prb_status == "GREEN" else ("metric-delta-yellow" if prb_status in ["ELEVATED", "YELLOW"] else "metric-delta-red")
                critical_prbs_display = f"{critical_prbs}"
                if changes.get('critical_prbs'):
                    critical_prbs_display += f" <span style='font-size: 1.0rem; color: #666;'>({changes['critical_prbs']})</span>"
                st.markdown(f"""
                <a href="#problem-reports-analysis" style="text-decoration: none; color: inherit;">
                    <div class="metric-card metric-card-clickable">
                    <div class="metric-label">🚨 Sev 0/1 PRBs</div>
                    <div class="metric-value">{critical_prbs_display}</div>
                        <div class="metric-total">of {total_prbs} total</div>
                        <div class="metric-delta {prb_delta_class}">
                        {prb_status}
                    </div>
                </div>
                </a>
                """, unsafe_allow_html=True)

            with col3:
                total_bugs = len(data.get('bugs', []))
                prod_delta_class = "metric-delta-green" if prod_bug_status == "GREEN" else ("metric-delta-yellow" if prod_bug_status == "YELLOW" else "metric-delta-red")
                critical_prod_bugs_display = f"{critical_prod_bugs}"
                if changes.get('prod_bugs'):
                    critical_prod_bugs_display += f" <span style='font-size: 1.0rem; color: #666;'>({changes['prod_bugs']})</span>"
                p0p1_href = p0p1_prod_bugs_metric_href(prod_bugs_link_folder)
                p0p1_extra = ' target="_blank" rel="noopener noreferrer"' if p0p1_href.startswith('https') else ''
                st.markdown(f"""
                <a href="{p0p1_href}"{p0p1_extra} style="text-decoration: none; color: inherit;">
                    <div class="metric-card metric-card-clickable">
                        <div class="metric-label">🐛 P0/P1 Prod Bugs</div>
                    <div class="metric-value">{critical_prod_bugs_display}</div>
                        <div class="metric-total">of {total_bugs} total</div>
                        <div class="metric-delta {prod_delta_class}">
                            {prod_bug_status}
                    </div>
                </div>
                </a>
                """, unsafe_allow_html=True)

            with col4:
                second_line = f"2nd: {second_version} ({second_percentage:.1f}%)" if second_version != "N/A" else "Single version"
                st.markdown(f"""
                <a href="#deployment-analysis" style="text-decoration: none; color: inherit;">
                    <div class="metric-card metric-card-clickable">
                        <div class="metric-label">🚀 Prod Deployment</div>
                    <div class="metric-value">{dominant_version}</div>
                        <div class="metric-total">Dominant in fleet ({dominant_percentage:.1f}%)</div>
                    <div class="metric-delta">
                            {second_line}
                        </div>
                    </div>
                </a>
                """, unsafe_allow_html=True)

            with col5_prod:
                availability_data = data.get('system_availability', {})
                availability_achieved = availability_data.get('achieved', 0.0)
                availability_slo = availability_data.get('slo', 99.9)
                availability_display = f"{availability_achieved:.2f}%"
                if changes.get('availability'):
                    availability_display += f" <span style='font-size: 1.0rem; color: #666;'>({changes['availability']})</span>"
                if availability_achieved >= availability_slo:
                    availability_delta_class = "metric-delta-green"
                    availability_status = "MEETS SLO"
                elif availability_achieved >= (availability_slo - 0.1):
                    availability_delta_class = "metric-delta-yellow"
                    availability_status = "NEAR SLO"
                else:
                    availability_delta_class = "metric-delta-red"
                    availability_status = "BELOW SLO"
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">⚡ System Availability</div>
                    <div class="metric-value">{availability_display}</div>
                    <div class="metric-total">SLO: {availability_slo}%</div>
                    <div class="metric-delta {availability_delta_class}">
                        {availability_status}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        if show_development:
            dev_heading = "#### 💻 Development Metrics"
            if development_heading_suffix:
                dev_heading += f" — {development_heading_suffix}"
            st.markdown(dev_heading)
            dev_r1_a, dev_r1_b, dev_r1_c, dev_r1_d = st.columns(4)

            with dev_r1_a:
                # Coverage color logic: green if >= 80%, yellow if >= 70%, red if < 70%
                coverage_delta_class = "metric-delta-green" if avg_coverage >= 80 else ("metric-delta-yellow" if avg_coverage >= 70 else "metric-delta-red")
                if avg_coverage >= 80:
                    coverage_status = "GREEN"
                elif avg_coverage >= 70:
                    coverage_status = "YELLOW"
                else:
                    coverage_status = "RED"

                # Format the value with week-over-week change
                coverage_display = f"{avg_coverage:.1f}%"
                if changes.get('coverage'):
                    coverage_display += f" <span style='font-size: 1.0rem; color: #666;'>({changes['coverage']})</span>"

                st.markdown(f"""
                <a href="#code-coverage-analysis" style="text-decoration: none; color: inherit;">
                    <div class="metric-card metric-card-clickable metric-card--line-coverage">
                        <div class="metric-label">📊 Line Coverage</div>
                        <div class="metric-line-coverage-body">
                            <div class="metric-value">{coverage_display}</div>
                            <div class="metric-delta {coverage_delta_class}">
                                {coverage_status}
                            </div>
                            <div class="metric-total">&nbsp;</div>
                        </div>
                    </div>
                </a>
                """, unsafe_allow_html=True)

            with dev_r1_b:
                total_ci_issues = len(data.get('ci_issues', []))
                ci_p0_p1_count = ci_p0_bugs + ci_p1_bugs
                ci_delta_class = "metric-delta-green" if ci_bug_status == "GREEN" else ("metric-delta-yellow" if ci_bug_status == "YELLOW" else "metric-delta-red")
                
                # Format the value with week-over-week change
                ci_p0_p1_display = f"{ci_p0_p1_count}"
                if changes.get('ci_score'):
                    ci_p0_p1_display += f" <span style='font-size: 1.0rem; color: #666;'>({changes['ci_score']})</span>"
                
                ci_href = p0p1_ci_issues_metric_href(prod_bugs_link_folder)
                ci_extra = ' target="_blank" rel="noopener noreferrer"' if ci_href.startswith('https') else ''
                st.markdown(f"""
                <a href="{ci_href}"{ci_extra} style="text-decoration: none; color: inherit;">
                    <div class="metric-card metric-card-clickable">
                        <div class="metric-label">🔧 P0/P1 CI Issues</div>
                        <div class="metric-value">{ci_p0_p1_display}</div>
                        <div class="metric-total">{total_ci_issues} bugs</div>
                        <div class="metric-delta {ci_delta_class}">
                            {ci_bug_status}
                    </div>
                </div>
                </a>
                """, unsafe_allow_html=True)

            with dev_r1_c:
                total_security_bugs = len(data.get('security_issues', []))
                sec_delta_class = "metric-delta-green" if sec_bug_status == "GREEN" else ("metric-delta-yellow" if sec_bug_status == "YELLOW" else "metric-delta-red")
                
                # Format the value with week-over-week change
                critical_sec_bugs_display = f"{critical_sec_bugs}"
                if changes.get('sec_score'):
                    critical_sec_bugs_display += f" <span style='font-size: 1.0rem; color: #666;'>({changes['sec_score']})</span>"
                
                sec_href = p0p1_security_bugs_metric_href(prod_bugs_link_folder)
                sec_extra = ' target="_blank" rel="noopener noreferrer"' if sec_href.startswith('https') else ''
                st.markdown(f"""
                <a href="{sec_href}"{sec_extra} style="text-decoration: none; color: inherit;">
                    <div class="metric-card metric-card-clickable">
                        <div class="metric-label">🔒 P0/P1 Security Bugs</div>
                    <div class="metric-value">{critical_sec_bugs_display}</div>
                        <div class="metric-total">{total_security_bugs} bugs</div>
                        <div class="metric-delta {sec_delta_class}">
                            {sec_bug_status}
                    </div>
                </div>
                </a>
                """, unsafe_allow_html=True)

            with dev_r1_d:
                total_leftshift_bugs = len(data.get('leftshift_issues', []))
                ls_delta_class = "metric-delta-green" if ls_bug_status == "GREEN" else ("metric-delta-yellow" if ls_bug_status == "YELLOW" else "metric-delta-red")
                
                # Format the value with week-over-week change
                ls_p0_p1_display = f"{ls_p0_p1_count}"
                if changes.get('ls_score'):
                    ls_p0_p1_display += f" <span style='font-size: 1.0rem; color: #666;'>({changes['ls_score']})</span>"
                
                ls_href = p0p1_left_shift_metric_href(prod_bugs_link_folder)
                ls_extra = ' target="_blank" rel="noopener noreferrer"' if ls_href.startswith('https') else ''
                st.markdown(f"""
                <a href="{ls_href}"{ls_extra} style="text-decoration: none; color: inherit;">
                    <div class="metric-card metric-card-clickable">
                        <div class="metric-label">⬅️ P0/P1 Left Shift</div>
                        <div class="metric-value">{ls_p0_p1_display}</div>
                        <div class="metric-total">{total_leftshift_bugs} bugs</div>
                        <div class="metric-delta {ls_delta_class}">
                            {ls_bug_status}
                        </div>
                    </div>
                </a>
                """, unsafe_allow_html=True)

            st.markdown("")
            dev_r2_a, dev_r2_b, dev_r2_c, dev_r2_d = st.columns(4)

            with dev_r2_a:
                total_abs_bugs = len(data.get('abs_issues', []))
                abs_delta_class = "metric-delta-green" if abs_bug_status == "GREEN" else ("metric-delta-yellow" if abs_bug_status == "YELLOW" else "metric-delta-red")
                abs_p0_p1_display = f"{abs_p0_p1_count}"
                if changes.get('abs_score'):
                    abs_p0_p1_display += f" <span style='font-size: 1.0rem; color: #666;'>({changes['abs_score']})</span>"
                abs_href = p0p1_abs_bugs_metric_href(prod_bugs_link_folder)
                abs_extra = ' target="_blank" rel="noopener noreferrer"' if abs_href.startswith('https') else ''
                st.markdown(f"""
                <a href="{abs_href}"{abs_extra} style="text-decoration: none; color: inherit;">
                    <div class="metric-card metric-card-clickable">
                        <div class="metric-label">🔷 P0/P1 ABS Bugs</div>
                        <div class="metric-value">{abs_p0_p1_display}</div>
                        <div class="metric-total">{total_abs_bugs} bugs</div>
                        <div class="metric-delta {abs_delta_class}">
                            {abs_bug_status}
                        </div>
                    </div>
                </a>
                """, unsafe_allow_html=True)

            with dev_r2_b:
                # Calculate code changes metrics using archived git stats
                git_stats = data.get('git_stats', {})
                
                if git_stats:
                    # Use pre-computed git stats from archive
                    current_week_changes = git_stats.get('lines_changed', 0)
                    total_commits = git_stats.get('total_commits', 0)
                    
                    # Code Changes thresholds
                    # GREEN: < 10000 lines, YELLOW: 10000-19999 lines, RED: >= 20000 lines
                    if current_week_changes < 10000:
                        change_status = "GREEN"
                        change_delta_class = "metric-delta-green"
                    elif current_week_changes < 20000:
                        change_status = "YELLOW" 
                        change_delta_class = "metric-delta-yellow"
                    else:
                        change_status = "RED"
                        change_delta_class = "metric-delta-red"
                else:
                    # Fallback when no git stats available
                    current_week_changes = 0
                    change_status = "UNKNOWN"
                    change_delta_class = "metric-delta-gray"
                
                # Format the value with week-over-week change
                code_changes_display = f"{current_week_changes:,}"
                if changes.get('code_changes'):
                    code_changes_display += f" <span style='font-size: 1.0rem; color: #666;'>({changes['code_changes']})</span>"
                
                st.markdown(f"""
                <a href="#code-changes-analysis" style="text-decoration: none; color: inherit;">
                    <div class="metric-card metric-card-clickable">
                        <div class="metric-label">📈 Code Changes</div>
                        <div class="metric-value">{code_changes_display}</div>
                        <div class="metric-total">lines changed</div>
                        <div class="metric-delta {change_delta_class}">
                            {change_status}
                        </div>
                    </div>
                </a>
                """, unsafe_allow_html=True)

            with dev_r2_c:
                # All-time Bug Backlog — weighted score (10× P0/P1 + 1× P2+) drives color
                alltime_backlog = data.get('alltime_backlog', [])
                if alltime_backlog:
                    backlog_rows = alltime_backlog
                else:
                    backlog_rows = data.get("bugs", [])

                backlog_weighted_score = alltime_backlog_weighted_score(backlog_rows)
                backlog_status, backlog_delta_class = alltime_backlog_status_from_score(
                    backlog_weighted_score
                )
                total_alltime_bugs = len(backlog_rows)

                score_display = f"{backlog_weighted_score:,}"
                if changes.get("alltime_backlog"):
                    score_display += f" <span style='font-size: 1.0rem; color: #666;'>({changes['alltime_backlog']})</span>"
                elif changes.get("critical_backlog") and not alltime_backlog:
                    score_display += f" <span style='font-size: 1.0rem; color: #666;'>({changes['critical_backlog']})</span>"

                atbl_href = all_time_bug_backlog_metric_href(prod_bugs_link_folder)
                atbl_extra = ' target="_blank" rel="noopener noreferrer"' if atbl_href.startswith('https') else ''
                st.markdown(f"""
                <a href="{atbl_href}"{atbl_extra} style="text-decoration: none; color: inherit;">
                    <div class="metric-card metric-card-clickable">
                        <div class="metric-label">🐛 All-time Bug Backlog</div>
                        <div class="metric-value">{score_display}</div>
                        <div class="metric-total">{total_alltime_bugs} bugs</div>
                        <div class="metric-delta {backlog_delta_class}">
                            {backlog_status}
                        </div>
                    </div>
                </a>
                """, unsafe_allow_html=True)

            with dev_r2_d:
                # API archives use `prb_backlog`; file-only runs may only have `prb_bugs`. Empty list => show 0, not "No Data".
                prb_backlog = data.get('prb_backlog') or data.get('prb_bugs') or []
                critical_prb_backlog = len([b for b in prb_backlog if 'P0' in str(b.get('priority', '')) or 'P1' in str(b.get('priority', ''))])
                total_prb_backlog = len(prb_backlog)
                prb_backlog_delta_class = "metric-delta-green" if critical_prb_backlog == 0 else ("metric-delta-yellow" if critical_prb_backlog <= 3 else "metric-delta-red")
                prb_backlog_status = "GREEN" if critical_prb_backlog == 0 else ("YELLOW" if critical_prb_backlog <= 3 else "RED")
                critical_prb_backlog_display = f"{critical_prb_backlog}"
                if changes.get('prb_backlog'):
                    critical_prb_backlog_display += f" <span style='font-size: 1.0rem; color: #666;'>({changes['prb_backlog']})</span>"
                bfp_href = backlog_from_prb_metric_href(prod_bugs_link_folder)
                bfp_extra = ' target="_blank" rel="noopener noreferrer"' if bfp_href.startswith('https') else ''
                st.markdown(f"""
                <a href="{bfp_href}"{bfp_extra} style="text-decoration: none; color: inherit;">
                    <div class="metric-card metric-card-clickable">
                        <div class="metric-label">📋 Backlog from PRB</div>
                        <div class="metric-value">{critical_prb_backlog_display}</div>
                        <div class="metric-total">{total_prb_backlog} bugs</div>
                        <div class="metric-delta {prb_backlog_delta_class}">
                            {prb_backlog_status}
                        </div>
                    </div>
                </a>
                """, unsafe_allow_html=True)

    def categorize_file_change(self, filepath: str) -> str:
        """Categorize file changes with deeper SDB-specific analysis."""
        filepath_lower = filepath.lower()
        
        # Skip non-SDB related files
        if any(excluded in filepath_lower for excluded in ['sfstore', 'zookeeper', 'kafka', 'redis', 'memcache', 'test', 'doc']):
            return 'SKIP'
        
        # Database schema and migration files
        if any(keyword in filepath_lower for keyword in ['migration', 'schema', 'ddl', 'alter_table']):
            return 'Schema & Migrations'
        
        # SQL files and stored procedures
        if filepath_lower.endswith('.sql') or any(keyword in filepath_lower for keyword in ['procedure', 'function', 'trigger', 'view']):
            return 'SQL Scripts & Procedures'
        
        # Connection and session management
        if any(keyword in filepath_lower for keyword in ['connection', 'pool', 'session', 'auth']):
            return 'Connection Management'
        
        # Query optimization and execution
        if any(keyword in filepath_lower for keyword in ['query', 'optimizer', 'planner', 'executor', 'index']):
            return 'Query Engine & Optimization'
        
        # Transaction and concurrency control
        if any(keyword in filepath_lower for keyword in ['transaction', 'lock', 'concurrency', 'isolation', 'mvcc']):
            return 'Transaction & Concurrency'
        
        # Storage and buffer management
        if any(keyword in filepath_lower for keyword in ['storage', 'buffer', 'cache', 'disk', 'wal', 'checkpoint']):
            return 'Storage & Buffer Management'
        
        # Replication and high availability
        if any(keyword in filepath_lower for keyword in ['replication', 'replica', 'standby', 'recovery', 'backup']):
            return 'Replication & HA'
        
        # Monitoring and statistics
        if any(keyword in filepath_lower for keyword in ['stats', 'monitor', 'metric', 'log', 'audit']):
            return 'Monitoring & Statistics'
        
        # Configuration and parameters
        if any(keyword in filepath_lower for keyword in ['config', 'param', 'setting', 'guc']):
            return 'Configuration Management'
        
        # Extensions and plugins
        if any(keyword in filepath_lower for keyword in ['extension', 'plugin', 'contrib']):
            return 'Extensions & Plugins'
        
        # Core SDB internals
        if any(keyword in filepath_lower for keyword in ['postgres', 'pg_', 'backend', 'postmaster']):
            return 'SDB Internals'
        
        # Database layer and ORM
        if any(keyword in filepath_lower for keyword in ['database', 'db', 'orm', 'model', 'entity']):
            return 'Database Access Layer'
        
        # API and service layer that might interact with DB
        if any(keyword in filepath_lower for keyword in ['api', 'service', 'controller']) and 'src' in filepath_lower:
            return 'Application Database Interface'
        
        # Configuration files
        if filepath_lower.endswith(('.conf', '.ini', '.yaml', '.yml', '.json')) and any(keyword in filepath_lower for keyword in ['db', 'database', 'postgres', 'sdb']):
            return 'Database Configuration'
        
        return 'SKIP'
    
    def categorize_file_change_generic(self, filepath: str) -> str:
        """Bucket changes by extension / tests for non-SDB repositories (bookkeeper, sdd, etc.)."""
        fp = filepath.replace('\\', '/').lower()
        if '/node_modules/' in fp or '/.git/' in fp:
            return 'SKIP'
        parts = fp.split('/')
        if 'test' in parts or 'tests' in parts or fp.endswith('_test.go'):
            return 'Tests'
        ext = os.path.splitext(filepath)[1].lower()
        if ext in ('.java', '.jj', '.jjt'):
            return 'Java'
        if ext in ('.cpp', '.cc', '.cxx', '.h', '.hpp'):
            return 'C/C++'
        if ext == '.py':
            return 'Python'
        if ext == '.go':
            return 'Go'
        if ext in ('.sql',):
            return 'SQL'
        if ext in ('.yml', '.yaml', '.json', '.xml', '.gradle', '.properties'):
            return 'Config / build'
        if ext:
            return ext[1:].upper()
        return 'Other'
    
    def analyze_changes_with_llm(self, file_changes: list, dates: dict) -> str:
        """Get pre-generated code change risk analysis from LLM content or show unavailable message."""
        # Check if we have pre-generated LLM content
        if hasattr(self, 'llm_content') and self.llm_content:
            risk_analysis = self.llm_content.get('risk_analysis', '')
            if risk_analysis:
                return risk_analysis
        
        # No LLM content available
        return "**Code Change Risk Analysis:** Content not available - requires LLM generation during report creation"
    
    def create_code_changes_analysis(self, data: Dict[str, Any], component: Optional[str] = None):
        """Create comprehensive code changes analysis with visualization and risk assessment."""
        import subprocess
        import os
        from datetime import datetime, timedelta
        from quality_report_generator import get_report_dates
        
        dates = get_report_dates()
        comp = component or (data.get('metadata') or {}).get('report_component') or 'Engine'
        git_stats_pre = data.get('git_stats') or {}
        repo_path = git_stats_pre.get('repository_path') or resolve_git_repo_path(comp)
        is_sdb_repo = os.path.basename(os.path.normpath(repo_path)).lower() == 'sdb'
        
        def get_git_changes_by_path(start_date, end_date, git_root: str, sdb_style: bool):
            """Get git changes; SDB uses deep categorization, other repos use extension buckets."""
            try:
                if not os.path.exists(git_root) or not os.path.exists(os.path.join(git_root, '.git')):
                    return {}, []
                
                cmd = f'cd {git_root} && git log --since="{start_date}" --until="{end_date}" --numstat --pretty=format:"" | grep -v "^$"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode != 0:
                    return {}, []
                
                excluded_modules = ['sfstore', 'zookeeper', 'kafka', 'redis', 'memcache']
                
                changes_by_path = {}
                file_changes_for_llm = []
                
                for line in result.stdout.strip().split('\n'):
                    if line and '\t' in line:
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            added = int(parts[0]) if parts[0].isdigit() else 0
                            deleted = int(parts[1]) if parts[1].isdigit() else 0
                            filepath = parts[2].lower()
                            original_filepath = parts[2]
                            
                            if sdb_style:
                                if any(excluded in filepath for excluded in excluded_modules):
                                    continue
                                category = self.categorize_file_change(original_filepath)
                            else:
                                category = self.categorize_file_change_generic(original_filepath)
                            
                            if category == 'SKIP':
                                continue
                            
                            if category not in changes_by_path:
                                changes_by_path[category] = {'added': 0, 'deleted': 0, 'files': 0, 'file_details': []}
                            
                            changes_by_path[category]['added'] += added
                            changes_by_path[category]['deleted'] += deleted
                            changes_by_path[category]['files'] += 1
                            changes_by_path[category]['file_details'].append({
                                'path': original_filepath,
                                'added': added,
                                'deleted': deleted
                            })
                            
                            # Collect significant changes for LLM analysis
                            if added + deleted > 50:  # Only analyze substantial changes
                                file_changes_for_llm.append({
                                    'path': original_filepath,
                                    'added': added,
                                    'deleted': deleted,
                                    'category': category
                                })
                
                return changes_by_path, file_changes_for_llm
            except Exception as e:
                print(f"Error in get_git_changes_by_path: {e}")
                return {}, []
        
        # Try to get git stats from archived data first
        git_stats = data.get('git_stats', {})
        if git_stats:
            # Use pre-computed git stats from the archive
            st.markdown("#### 📊 Code Changes Summary")
            st.caption(f"Git repository: `{git_stats.get('repository_path') or repo_path}` · component: **{comp}**")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Commits", git_stats.get('total_commits', 0))
                st.metric("Lines Added", git_stats.get('lines_added', 0))
                st.metric("Lines Deleted", git_stats.get('lines_deleted', 0))
            with col2:
                st.metric("Files Changed", git_stats.get('files_changed', 0))
                st.metric("Authors", len(git_stats.get('authors', [])))
                
                # Code Churn Risk with color coding
                churn_risk = git_stats.get('code_churn_risk', 'Unknown')
                lines_changed = git_stats.get('lines_changed', 0)
                
                # Map risk levels to GREEN/YELLOW/RED
                if churn_risk == 'Low':
                    risk_display = "GREEN"
                    risk_color = "#27AE60"  # Green
                elif churn_risk == 'Medium':
                    risk_display = "YELLOW"
                    risk_color = "#F39C12"  # Orange
                elif churn_risk == 'High':
                    risk_display = "RED"
                    risk_color = "#C0392B"  # Red
                else:
                    risk_display = churn_risk
                    risk_color = "#7F8C8D"  # Gray
                
                st.markdown(f"""
                <div style="background-color: white; padding: 1rem; border-radius: 0.5rem; border: 1px solid #e0e0e0;">
                    <div style="color: #666; font-size: 0.875rem; margin-bottom: 0.25rem;">Code Churn Risk</div>
                    <div style="font-size: 1.75rem; font-weight: 600; color: {risk_color};">{risk_display}</div>
                    <div style="color: #888; font-size: 0.75rem;">{lines_changed:,} lines changed</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Show most changed files if available
            most_changed = git_stats.get('most_changed_files', [])
            if most_changed:
                st.markdown("#### 📁 Most Changed Files")
                for i, file_info in enumerate(most_changed[:5]):
                    st.write(f"{i+1}. **{file_info.get('file', 'Unknown')}** - {file_info.get('total_changes', 0)} changes")
            return
        
        # Fallback: Try to get changes from git (won't work on Streamlit Cloud)
        try:
            current_week_start = dates['period_start_full']
            current_week_end = dates['period_end_full']
            changes_data, file_changes_for_llm = get_git_changes_by_path(
                current_week_start, current_week_end, repo_path, is_sdb_repo
            )
        except Exception as e:
            st.info("📊 Code changes analysis not available (git repository not accessible)")
            st.info(f"💡 Expected clone at: `{repo_path}` (component **{comp}**)")
            return
        
        if not changes_data:
            st.info("📊 No code changes data available for the reporting period")
            return
        
        # Create visualization
        col1, col2 = st.columns([3, 2])
        
        with col1:
            chart_title = "SDB-focused code changes" if is_sdb_repo else "Repository code changes"
            st.markdown(f"#### 📈 {chart_title}")
            
            # Prepare data for chart
            categories = list(changes_data.keys())
            total_changes = [changes_data[d]['added'] + changes_data[d]['deleted'] for d in categories]
            added_lines = [changes_data[d]['added'] for d in categories]
            deleted_lines = [changes_data[d]['deleted'] for d in categories]
            
            # Sort by total changes
            sorted_data = sorted(zip(categories, total_changes, added_lines, deleted_lines), 
                               key=lambda x: x[1], reverse=True)
            categories, total_changes, added_lines, deleted_lines = zip(*sorted_data)
            
            # Create stacked bar chart
            import plotly.graph_objects as go
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                name='Lines Added',
                x=categories,
                y=added_lines,
                marker_color='#27AE60',
                hovertemplate='<b>%{x}</b><br>Added: %{y} lines<extra></extra>'
            ))
            
            fig.add_trace(go.Bar(
                name='Lines Deleted',
                x=categories,
                y=deleted_lines,
                marker_color='#C0392B',
                hovertemplate='<b>%{x}</b><br>Deleted: %{y} lines<extra></extra>'
            ))
            
            fig.update_layout(
                title=f"{chart_title} ({dates['period_start']} - {dates['period_end']}) · `{os.path.basename(repo_path)}`",
                barmode='stack',
                xaxis_title="Component Category",
                yaxis_title="Lines Changed",
                xaxis={'tickangle': -45},
                height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add detailed file breakdown for top categories
            if categories:
                st.markdown("#### 📋 Detailed File Changes")
                top_category = categories[0]
                file_details = changes_data[top_category]['file_details']
                
                st.markdown(f"**Top Changed Category: {top_category}**")
                for detail in sorted(file_details, key=lambda x: x['added'] + x['deleted'], reverse=True)[:5]:
                    total_file_changes = detail['added'] + detail['deleted']
                    st.markdown(f"• `{detail['path']}`: +{detail['added']} -{detail['deleted']} ({total_file_changes} total)")
                
                if len(file_details) > 5:
                    st.markdown(f"... and {len(file_details) - 5} more files")
        
        with col2:
            st.markdown("#### 🎯 Risk Assessment")
            
            # Calculate SDB-specific risk metrics
            total_lines_changed = sum(total_changes)
            high_change_categories = [d for d, c in zip(categories, total_changes) if c > total_lines_changed * 0.2]
            
            # SDB-specific risk assessment logic
            risk_factors = []
            risk_level = "LOW"
            risk_color = "🟢"
            
            # Volume-based risk (lower thresholds for DB changes)
            if total_lines_changed > 2000:
                risk_factors.append("High volume of SDB changes")
                risk_level = "HIGH"
                risk_color = "🔴"
            elif total_lines_changed > 800:
                risk_factors.append("Moderate volume of SDB changes")
                risk_level = "MEDIUM" 
                risk_color = "🟡"
            
            # SDB-specific high-risk categories
            high_risk_categories = ['Database Schema/Migrations', 'SDB Internals', 'SQL Queries/Procedures']
            schema_changes = any(cat in high_change_categories for cat in ['Database Schema/Migrations'])
            core_sdb_changes = any(cat in high_change_categories for cat in ['SDB Internals'])
            query_changes = any(cat in high_change_categories for cat in ['SQL Queries/Procedures'])
            
            if schema_changes:
                risk_factors.append("Database schema/migration changes detected")
                risk_level = "HIGH"
                risk_color = "🔴"
            
            if core_sdb_changes:
                risk_factors.append("SDB core component modifications")
                if risk_level != "HIGH":
                    risk_level = "MEDIUM"
                    risk_color = "🟡"
            
            if query_changes:
                risk_factors.append("SQL query/procedure modifications")
                if risk_level == "LOW":
                    risk_level = "MEDIUM"
                    risk_color = "🟡"
            
            # Check for concentrated changes in critical areas
            if len(high_change_categories) <= 2 and total_lines_changed > 500:
                risk_factors.append("Changes concentrated in few SDB components")
                if risk_level == "LOW":
                    risk_level = "MEDIUM"
                    risk_color = "🟡"
            
            # Display risk assessment
            st.markdown(f"""
            <div style="padding: 15px; border-radius: 8px; background-color: #f8f9fa; border-left: 4px solid #007bff;">
                <h5>{risk_color} Risk Level: {risk_level}</h5>
                <p><strong>Total Changes:</strong> {total_lines_changed:,} lines</p>
                <p><strong>Components Affected:</strong> {len(categories)}</p>
                <p><strong>Top Change Areas:</strong></p>
                <ul>
            """, unsafe_allow_html=True)
            
            for i, (cat_name, changes) in enumerate(zip(categories[:3], total_changes[:3])):
                percentage = (changes / total_lines_changed * 100) if total_lines_changed > 0 else 0
                st.markdown(f"<li>{cat_name}: {changes:,} lines ({percentage:.1f}%)</li>", unsafe_allow_html=True)
            
            st.markdown("</ul>", unsafe_allow_html=True)
            
            if risk_factors:
                st.markdown("<p><strong>Risk Factors:</strong></p><ul>", unsafe_allow_html=True)
                for factor in risk_factors:
                    st.markdown(f"<li>{factor}</li>", unsafe_allow_html=True)
                st.markdown("</ul>", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Narrative Analysis
        st.markdown("#### 📝 Change Impact Analysis")
        
        # Generate narrative based on data
        narrative_parts = []
        
        if total_lines_changed > 0:
            top_category = categories[0]
            top_changes = total_changes[0]
            top_percentage = (top_changes / total_lines_changed * 100)
            
            narrative_parts.append(f"During the reporting period ({dates['period_start']} - {dates['period_end']}), "
                                 f"**{total_lines_changed:,} lines of SDB-related code** were modified across **{len(categories)} component categories**.")
            
            narrative_parts.append(f"The **{top_category}** category had the highest activity with "
                                 f"**{top_changes:,} lines changed** ({top_percentage:.1f}% of total changes).")
            
            # SDB-specific feature enablement analysis
            if 'Schema' in top_category or 'Migration' in top_category:
                narrative_parts.append("🔴 **Critical Database Schema Changes** - Schema modifications and migrations carry high risk. "
                                     "These changes are typically **enabled by default** once deployed and can affect data integrity. "
                                     "Ensure thorough testing in staging environments and consider maintenance windows.")
            elif 'SDB Internals' in top_category:
                narrative_parts.append("🟡 **SDB Core Modifications** - Changes to core SDB components require extensive validation. "
                                     "These modifications may affect database performance, connection handling, or query execution. "
                                     "Consider **feature flags for new functionality** and gradual rollout.")
            elif 'SQL Queries' in top_category or 'Procedures' in top_category:
                narrative_parts.append("🟡 **SQL Query/Procedure Changes** - Query modifications can impact performance and data access patterns. "
                                     "New queries are typically **enabled immediately** but should be monitored for performance regressions. "
                                     "Consider query plan analysis and index optimization.")
            elif 'Database Layer' in top_category:
                narrative_parts.append("🟢 **Database Layer Changes** - Application-level database interaction changes are generally lower risk. "
                                     "These can often be **feature-flagged** and rolled out incrementally to validate behavior.")
            
            # SDB-specific default enablement assessment
            if risk_level == "HIGH":
                narrative_parts.append("🚨 **SDB Deployment Recommendation**: High-risk database changes require **careful orchestration**. "
                                     "Schema changes should be deployed during **maintenance windows** with rollback procedures ready. "
                                     "New features should be **disabled by default** with gradual enablement after validation.")
            elif risk_level == "MEDIUM":
                narrative_parts.append("⚡ **SDB Deployment Recommendation**: Moderate-risk database changes should include **enhanced monitoring** "
                                     "of query performance, connection pools, and error rates. Consider **staged rollout** with canary deployments "
                                     "and feature flags where applicable.")
            else:
                narrative_parts.append("✅ **SDB Assessment**: Low-risk database changes can proceed with standard deployment practices. "
                                     "Continue monitoring database metrics including query performance, connection counts, and error rates. "
                                     "Most changes can be **enabled by default** with standard monitoring.")
        
        # Display narrative
        for part in narrative_parts:
            st.markdown(part)
        
        # Add LLM-powered risk analysis section
        if file_changes_for_llm:
            st.markdown("---")
            st.markdown("#### 🤖 **AI-Powered Risk Analysis**")
            
            with st.spinner("Analyzing code changes for risk assessment..."):
                llm_analysis = self.analyze_changes_with_llm(file_changes_for_llm, dates)
            
            st.markdown(llm_analysis)
    
    def calculate_deployment_status(self, data: Dict[str, Any]) -> tuple:
        """Calculate deployment status using enhanced LLM analysis of deployment.txt."""
        deployment_summary = data.get('deployment_summary', '')
        deployments = self.get_deployment_data(data)
        
        if not deployment_summary and not deployments:
            return "YELLOW", "No deployment data available"
        
        # Enhanced LLM-like analysis of deployment.txt content
        if deployment_summary:
            summary_lower = deployment_summary.lower()
            
            # RED indicators (Critical deployment issues)
            critical_indicators = [
                'failed', 'failure', 'critical', 'down', 'outage', 'emergency', 
                'rollback', 'abort', 'severe', 'broken', 'crash', 'unavailable'
            ]
            
            # YELLOW indicators (Warnings or concerns)  
            warning_indicators = [
                'warning', 'delay', 'issue', 'problem', 'slow', 'concern', 
                'timeout', 'retry', 'partial', 'degraded', 'investigating'
            ]
            
            # GREEN indicators (Positive deployment signals)
            positive_indicators = [
                'successful', 'smooth', 'completed', 'validated', 'passed', 
                'healthy', 'nominal', 'zero', 'no issues', 'on schedule'
            ]
            
            # Count indicator matches
            critical_count = sum(1 for word in critical_indicators if word in summary_lower)
            warning_count = sum(1 for word in warning_indicators if word in summary_lower)
            positive_count = sum(1 for word in positive_indicators if word in summary_lower)
            
            # LLM-like decision logic
            if critical_count > 0:
                return "RED", f"Critical deployment issues detected ({critical_count} indicators)"
            elif warning_count > positive_count:
                return "YELLOW", f"Deployment concerns noted ({warning_count} warning indicators)"
            elif positive_count >= 2:
                return "GREEN", f"Deployment proceeding well ({positive_count} positive indicators)"
            elif warning_count > 0:
                return "YELLOW", "Mixed deployment signals"
            else:
                return "GREEN", "Standard deployment operations"
        
        # Fallback: Analyze deployment.csv data patterns
        if deployments:
            total_cells = sum(d.get('count', d.get('cells', 0)) for d in deployments)
            failed = len([d for d in deployments if d.get('status') == 'Failed'])
            
            if failed > 0:
                return "RED", f"{failed} failed deployments"
            elif total_cells < 100:
                return "YELLOW", f"Limited deployment scale ({total_cells} cells)"
            else:
                return "GREEN", f"Fleet deployment active ({total_cells} cells)"
        
        return "YELLOW", "Limited deployment visibility"
    
    def create_deployment_stacked_bar(self, data: Dict[str, Any]):
        """Create stacked bar chart showing staggers with version stacks from deployment.csv."""
        deployments = self.get_deployment_data(data)
        if not deployments:
            st.info("📊 No deployment.csv data available for stacked bar chart")
            return
        
        
        # Build data structure for stacked bar chart: stagger -> version -> count
        stagger_version_counts = {}
        all_versions = set()
        
        # Process deployments from CSV
        for deployment in deployments:
            stagger = deployment.get('stagger', deployment.get('stage', 'Unknown'))
            version = deployment.get('version', 'Unknown')  
            count = deployment.get('count', deployment.get('cells', 0))
            
            if count > 0:  # Only include records with actual cell counts
                if stagger not in stagger_version_counts:
                    stagger_version_counts[stagger] = {}
                
                stagger_version_counts[stagger][version] = stagger_version_counts[stagger].get(version, 0) + count
                all_versions.add(version)
        
        # Sort staggers in the preferred order: SB0, SB1, SB2, R0, R1, R2a, R2b, etc.
        stagger_order = ['SB0', 'SB1', 'SB2', 'R0', 'R1', 'R2a', 'R2b', 'R3a', 'R3b']
        sorted_staggers = []
        for stagger in stagger_order:
            if stagger in stagger_version_counts:
                sorted_staggers.append(stagger)
        # Add any remaining staggers not in the predefined order
        for stagger in sorted(stagger_version_counts.keys()):
            if stagger not in sorted_staggers:
                sorted_staggers.append(stagger)
        
        sorted_versions = sorted(all_versions, key=lambda v: tuple(map(int, v.split('.'))))
        
        
        if not stagger_version_counts:
            st.warning("📊 No data available for stacked bar chart")
            return
        
        # Create stacked bar chart
        fig = go.Figure()
        
        # Color palette for versions
        colors = px.colors.qualitative.Set3[:len(sorted_versions)]
        if len(sorted_versions) > len(colors):
            colors = colors * ((len(sorted_versions) // len(colors)) + 1)
        
        # Add one trace per version (stack)
        for i, version in enumerate(sorted_versions):
            version_counts = []
            for stagger in sorted_staggers:
                count = stagger_version_counts[stagger].get(version, 0)
                version_counts.append(count)
            
            fig.add_trace(go.Bar(
                name=f"v{version}",
                x=sorted_staggers,
                y=version_counts,
                marker_color=colors[i],
                hovertemplate=f'<b>v{version}</b><br>Stagger: %{{x}}<br>Cells: %{{y}}<extra></extra>'
            ))
        
        # Update layout for stacked bars
        fig.update_layout(
            title="🚀 Deployment Cell Distribution<br><sub>Each bar shows cell count by version for each stagger</sub>",
            xaxis_title="Stagger",
            yaxis_title="Cell Count",
            barmode='stack',
            height=500,
            font=dict(size=12),
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.05
            )
        )
        
        st.plotly_chart(fig, use_container_width=True, key="deployment_stacked_bar")
    
    def create_version_pie_chart(self, data: Dict[str, Any]):
        """Create pie chart of SDB versions from deployment.csv data."""
        deployments = self.get_deployment_data(data)
        if not deployments:
            st.info("📊 No deployment.csv data available for version chart")
            return
            
        
        # Aggregate cells by SDB version across all stages
        version_counts = {}
        total_cells = 0
        
        for deployment in deployments:
            version = deployment.get('version', 'Unknown')
            count = deployment.get('count', deployment.get('cells', 0))
            
            if count > 0:  # Only count records with actual cells
                version_counts[version] = version_counts.get(version, 0) + count
                total_cells += count
        
        
        if version_counts and total_cells > 0:
            # Sort versions for better visualization
            sorted_versions = sorted(version_counts.items(), key=lambda x: x[1], reverse=True)
            
            fig = px.pie(
                values=[count for version, count in sorted_versions],
                names=[f"v{version}" for version, count in sorted_versions],
                title=f"📊 Release Version Distribution by Cell Count<br><sub>{total_cells} total cells across fleet</sub>",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            
            # Enhance hover info
            fig.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>Cells: %{value}<br>Percentage: %{percent}<extra></extra>'
            )
            
            fig.update_layout(showlegend=True, height=400)
            st.plotly_chart(fig, use_container_width=True, key="version_pie_chart")
        else:
            st.warning(f"📊 No valid version data for pie chart (found {total_cells} total cells)")
    
    def create_deployment_insights(self, data: Dict[str, Any]):
        """Create enhanced deployment insights using only deployment.csv metrics and deployment.txt LLM analysis."""
        deployments = self.get_deployment_data(data)
        deployment_summary = data.get('deployment_summary', '')
        
        if not deployments and not deployment_summary:
            st.info("No deployment analysis data available")
            return
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### 📊 **Fleet Deployment Metrics**")
            
            if deployments:
                # Analyze deployment.csv data with detailed breakdown
                total_cells = sum(d.get('count', d.get('cells', 0)) for d in deployments)
                stage_counts = {}
                version_counts = {}
                
                for deployment in deployments:
                    stage = deployment.get('stagger', deployment.get('stage', 'Unknown'))
                    version = deployment.get('version', 'Unknown') 
                    count = deployment.get('count', deployment.get('cells', 0))
                    
                    if count > 0:
                        stage_counts[stage] = stage_counts.get(stage, 0) + count
                        version_counts[version] = version_counts.get(version, 0) + count
                
                # Display key metrics
                st.metric("🎯 Active Stages", len(stage_counts))
                st.metric("📱 SDB Versions", len(version_counts))
                
                # Top deployments breakdown
                if version_counts:
                    top_version = max(version_counts.items(), key=lambda x: x[1])
                    coverage_pct = (top_version[1]/total_cells*100) if total_cells > 0 else 0
                    st.write(f"🥇 **Dominant Version**: v{top_version[0]} ({top_version[1]} cells, {coverage_pct:.1f}%)")
                    
                if stage_counts:
                    # Show top 3 stages
                    top_stages = sorted(stage_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                    st.write("**🎯 Top Deployment Stages:**")
                    for stage, count in top_stages:
                        st.write(f"• {stage}: {count} cells")
                
        with col2:
            st.markdown("#### 🤖 **Smart Deployment Analysis**")
            
            if deployment_summary:
                # Enhanced LLM analysis with CSV correlation
                status, status_detail = self.calculate_deployment_status(data)
                
                # Display status with more context
                status_emoji = "🔴" if status == "RED" else "🟡" if status == "YELLOW" else "🟢"
                st.write(f"{status_emoji} **Overall Status**: {status}")
                st.caption(status_detail)
                
                # Correlate deployment.txt insights with CSV data
                summary_lower = deployment_summary.lower()
                
                # Extract version mentions and cross-reference with CSV
                mentioned_versions = []
                for line in deployment_summary.split('\n'):
                    if any(v in line for v in ['258.', '260.']):
                        for version in version_counts.keys():
                            if version in line:
                                mentioned_versions.append(version)
                
                if mentioned_versions:
                    st.markdown("**📋 Version Activity Correlation:**")
                    for version in set(mentioned_versions):
                        cells = version_counts.get(version, 0)
                        st.write(f"• v{version}: {cells} cells deployed (mentioned in summary)")
                
                # Extract key insights with smart filtering
                insights = self._extract_deployment_insights(deployment_summary, deployments)
                if insights:
                    st.markdown("**🎯 Key Insights:**")
                    for insight in insights[:4]:  # Show top 4
                        st.write(f"• {insight}")
                        
            else:
                st.info("📝 No deployment.txt summary available")
                if deployments:
                    st.write("**📊 Based on CSV data only:**")
                    st.write(f"• Fleet covers {len(set(d.get('stagger', '') for d in deployments))} deployment stages")
                    st.write(f"• Running {len(set(d.get('version', '') for d in deployments))} different SDB versions")
                    
    def _extract_deployment_insights(self, summary: str, deployments: list) -> list:
        """Generate LLM-style narrative insights from deployment summary."""
        insights = []
        lines = [line.strip() for line in summary.split('\n') if line.strip()]
        
        # Parse deployment content for narrative creation
        completed_items = []
        in_progress_items = []
        planned_items = []
        challenges = []
        high_risk_items = []
        
        for line in lines:
            line_lower = line.lower()
            
            # High risk items
            if 'high risk' in line_lower or 'paused' in line_lower:
                clean_line = line.replace(':done-3:', '').strip()
                if clean_line:
                    high_risk_items.append(clean_line)
            
            # Completed items
            elif ':done-3:' in line or 'completed' in line_lower:
                clean_line = line.replace(':done-3:', '✅').strip()
                if clean_line:
                    completed_items.append(clean_line)
            
            # In progress items    
            elif 'in progress' in line_lower:
                clean_line = line.replace('- In Progress', '⚠️ In Progress:').strip()
                if clean_line:
                    in_progress_items.append(clean_line)
            
            # Planned items
            elif line.startswith(('Plan for', 'Below releases planned', 'Next week')) or 'planned' in line_lower:
                if 'plan for next week' in line_lower:
                    insights.append("📅 Next week's deployment schedule is defined with multiple releases planned")
                elif len(line) > 15:
                    planned_items.append(line)
            
            # Challenges
            elif 'challenge' in line_lower and 'nil' not in line_lower:
                challenges.append(line)
        
        # Generate narrative insights
        if high_risk_items:
            insights.append(f"🔴 Critical: {len(high_risk_items)} deployment(s) at high risk requiring immediate attention")
        
        if completed_items:
            insights.append(f"✅ Successfully completed {len(completed_items)} planned deployments this week")
        
        if in_progress_items:
            insights.append(f"⚠️ {len(in_progress_items)} deployment(s) currently in progress")
        
        if challenges and 'nil' not in challenges[0].lower():
            insights.append("⚠️ Active deployment challenges identified requiring resolution")
        else:
            insights.append("✅ No deployment challenges reported this week")
        
        # Version-specific insights
        version_mentions = []
        for line in lines:
            if '258.' in line or '260.' in line:
                version_matches = []
                import re
                versions = re.findall(r'\d{3}\.\d+(?:\.\d+)?', line)
                version_mentions.extend(versions)
        
        if version_mentions:
            unique_versions = list(set(version_mentions))
            insights.append(f"🔄 Active deployment activity across {len(unique_versions)} SDB versions")
        
        return insights[:5]  # Return top 5 narrative insights

    def create_risk_chart(self, data: Dict[str, Any], key_suffix: str = ""):
        """Create risk status and priority visualization."""
        risks = data.get('risks', [])
        if not risks:
            return
        
        # Create two columns for side-by-side charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Count risks by status
            risk_counts = {}
            for risk in risks:
                status = risk.get('status', 'Unknown')
                risk_counts[status] = risk_counts.get(status, 0) + 1
            
            # Create DataFrame for better control over colors
            risk_df = pd.DataFrame([
                {'Status': status, 'Count': count} 
                for status, count in risk_counts.items()
            ])
            
            # Define explicit color mapping
            def get_risk_color(status):
                color_map = {
                    'Green': '#28a745',      # Bright green ✅ On track
                    'Yellow': '#ffc107',     # Bright yellow ⚠️ At risk  
                    'Red': '#dc3545',        # Bright red 🚨 Critical
                    'At Risk': '#dc3545',   # Bright red 🚨 Critical
                    'Critical': '#dc3545',  # Bright red 🚨 Critical
                    'High': '#dc3545',      # Bright red 🚨 Critical
                    'Unknown': '#6c757d'    # Gray ❓ Unknown
                }
                return color_map.get(status, '#6c757d')
            
            # Apply colors to dataframe
            risk_df['Color'] = risk_df['Status'].apply(get_risk_color)
            
            # Create pie chart with explicit colors
            fig = px.pie(
                risk_df,
                values='Count',
                names='Status', 
                title="Risk Distribution by Status",
                color='Status',
                color_discrete_map={
                    'Green': '#28a745',      # Bright green ✅
                    'Yellow': '#ffc107',     # Bright yellow ⚠️
                    'Red': '#dc3545',        # Bright red 🚨
                    'At Risk': '#dc3545',   # Bright red 🚨
                    'Critical': '#dc3545',  # Bright red 🚨
                    'High': '#dc3545',      # Bright red 🚨
                    'Unknown': '#6c757d'    # Gray ❓
                }
            )
            
            # Force the colors by updating traces
            fig.update_traces(
                marker=dict(
                    colors=[get_risk_color(status) for status in risk_df['Status']]
                )
            )
            
            st.plotly_chart(fig, use_container_width=True, key=f"risk_distribution_chart{key_suffix}")
        
        with col2:
            # Count risks by priority
            priority_counts = {}
            for risk in risks:
                priority = risk.get('priority', 'Unknown')
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            # Create DataFrame for priority distribution
            priority_df = pd.DataFrame([
                {'Priority': priority, 'Count': count} 
                for priority, count in priority_counts.items()
            ])
            
            # Define priority color mapping
            def get_priority_color(priority):
                color_map = {
                    'P0': '#8B0000',        # Dark red for P0 (highest priority)
                    'P1': '#dc3545',        # Red for P1
                    'P2': '#ffc107',        # Yellow for P2
                    'P3': '#28a745',        # Green for P3
                    'P4': '#6c757d',        # Gray for P4 (lowest priority)
                    'High': '#dc3545',      # Red for High
                    'Medium': '#ffc107',    # Yellow for Medium
                    'Low': '#28a745',       # Green for Low
                    'Critical': '#8B0000',  # Dark red for Critical
                    'Unknown': '#6c757d'    # Gray for Unknown
                }
                return color_map.get(priority, '#6c757d')
            
            # Apply colors to dataframe
            priority_df['Color'] = priority_df['Priority'].apply(get_priority_color)
            
            # Create priority pie chart
            fig2 = px.pie(
                priority_df,
                values='Count',
                names='Priority', 
                title="Risk Distribution by Priority",
                color='Priority',
                color_discrete_map={
                    'P0': '#8B0000',        # Dark red for P0
                    'P1': '#dc3545',        # Red for P1
                    'P2': '#ffc107',        # Yellow for P2
                    'P3': '#28a745',        # Green for P3
                    'P4': '#6c757d',        # Gray for P4
                    'High': '#dc3545',      # Red for High
                    'Medium': '#ffc107',    # Yellow for Medium
                    'Low': '#28a745',       # Green for Low
                    'Critical': '#8B0000',  # Dark red for Critical
                    'Unknown': '#6c757d'    # Gray for Unknown
                }
            )
            
            # Force the colors by updating traces
            fig2.update_traces(
                marker=dict(
                    colors=[get_priority_color(priority) for priority in priority_df['Priority']]
                )
            )
            
            st.plotly_chart(fig2, use_container_width=True, key=f"risk_priority_chart{key_suffix}")
    
    def create_coverage_chart(self, data: Dict[str, Any], key_suffix: str = ""):
        """Create coverage visualization."""
        coverage = data.get('coverage', [])
        if not coverage:
            return
        
        # Create DataFrame for coverage data
        coverage_df = pd.DataFrame([
            {
                'Component': c.get('component', 'Unknown'),
                'Line Coverage': c.get('line_coverage', 0),
                'Branch Coverage': c.get('branch_coverage', 0),
                'Function Coverage': c.get('function_coverage', 0),
                'Tests': c.get('test_count', 0)
            }
            for c in coverage
        ])
        
        # Create bar chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Line Coverage',
            x=coverage_df['Component'],
            y=coverage_df['Line Coverage'],
            marker_color='lightblue'
        ))
        
        fig.add_trace(go.Bar(
            name='Branch Coverage',
            x=coverage_df['Component'],
            y=coverage_df['Branch Coverage'],
            marker_color='lightgreen'
        ))
        
        fig.add_trace(go.Bar(
            name='Function Coverage',
            x=coverage_df['Component'],
            y=coverage_df['Function Coverage'],
            marker_color='lightsalmon'
        ))
        
        fig.update_layout(
            title='Test Coverage by Component',
            xaxis_title='Component',
            yaxis_title='Coverage %',
            barmode='group'
        )
        
        st.plotly_chart(fig, use_container_width=True, key=f"coverage_chart{key_suffix}")
    
    def create_coverage_comparison_chart(self, data: Dict[str, Any], key_suffix: str = ""):
        """Create coverage comparison chart showing New Code vs Overall Coverage from coverage.txt."""
        coverage_summary = data.get('coverage_summary', {})
        if not coverage_summary:
            st.info("📊 No coverage summary data available")
            return
        
        
        # Extract New Code and Overall coverage data from coverage.txt parsing
        new_code_data = coverage_summary.get('new_code', {})
        overall_data = coverage_summary.get('overall', {})
        
        if not new_code_data or not overall_data:
            st.warning("📊 Coverage data incomplete. Using fallback component data.")
            # Fallback to component coverage if summary not available
            coverage = data.get('coverage', [])
            if coverage:
                self.create_coverage_chart(data, key_suffix)
            return
        
        # Prepare comparison data
        metrics = ['Coverage', 'Line Coverage', 'Condition Coverage']
        new_code_values = [
            new_code_data.get('coverage', 0),
            new_code_data.get('line_coverage', 0), 
            new_code_data.get('condition_coverage', 0)
        ]
        overall_values = [
            overall_data.get('coverage', 0),
            overall_data.get('line_coverage', 0),
            overall_data.get('condition_coverage', 0)
        ]
        
        # Create comparison bar chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='New Code Coverage',
            x=metrics,
            y=new_code_values,
            marker_color='#3498DB',  # Bright Blue
            hovertemplate='<b>New Code</b><br>%{x}: %{y:.1f}%<extra></extra>'
        ))
        
        fig.add_trace(go.Bar(
            name='Overall Coverage',
            x=metrics,
            y=overall_values,
            marker_color='#E67E22',  # Bright Orange
            hovertemplate='<b>Overall</b><br>%{x}: %{y:.1f}%<extra></extra>'
        ))
        
        # Add target lines for reference
        fig.add_hline(y=80, line_dash="dash", line_color="green", 
                     annotation_text="Target: 80%", annotation_position="top right")
        fig.add_hline(y=70, line_dash="dash", line_color="orange", 
                     annotation_text="Minimum: 70%", annotation_position="top right")
        
        fig.update_layout(
            title='📊 Code Coverage Comparison: New Code vs Overall',
            xaxis_title='Coverage Metrics',
            yaxis_title='Coverage Percentage (%)',
            barmode='group',
            height=450,
            font=dict(size=12),
            yaxis=dict(range=[0, 100])
        )
        
        st.plotly_chart(fig, use_container_width=True, key=f"coverage_comparison_chart{key_suffix}")
    
    def create_prb_analysis(self, data: Dict[str, Any], key_suffix: str = ""):
        """Create PRB analysis visualization by priority levels."""
        prbs = data.get('prbs', [])
        if not prbs:
            st.info("📊 No PRB data available")
            return
        
        # Categorize PRBs by severity levels
        p0_prbs = len([p for p in prbs if 'P0' in str(p.get('priority', '')) or 'Sev0' in str(p.get('priority', ''))])
        p1_prbs = len([p for p in prbs if 'P1' in str(p.get('priority', '')) or 'Sev1' in str(p.get('priority', '')) or 'Critical' in str(p.get('priority', ''))])
        p2_prbs = len([p for p in prbs if 'P2' in str(p.get('priority', '')) or 'Sev2' in str(p.get('priority', ''))])
        p3_prbs = len([p for p in prbs if 'P3' in str(p.get('priority', '')) or 'Sev3' in str(p.get('priority', ''))])
        p4_prbs = len([p for p in prbs if 'P4' in str(p.get('priority', '')) or 'Sev4' in str(p.get('priority', '')) or 'Low' in str(p.get('priority', ''))])
        
        # Only show severity levels that have PRBs
        priority_data = []
        colors = []
        
        if p0_prbs > 0:
            priority_data.append({'Priority': 'Sev 0 - Critical', 'Count': p0_prbs})
            colors.append('#8b0000')  # Dark Red
        if p1_prbs > 0:
            priority_data.append({'Priority': 'Sev 1 - High', 'Count': p1_prbs})
            colors.append('#dc3545')  # Red
        if p2_prbs > 0:
            priority_data.append({'Priority': 'Sev 2 - Medium', 'Count': p2_prbs})
            colors.append('#fd7e14')  # Orange
        if p3_prbs > 0:
            priority_data.append({'Priority': 'Sev 3 - Low', 'Count': p3_prbs})
            colors.append('#ffc107')  # Yellow
        if p4_prbs > 0:
            priority_data.append({'Priority': 'Sev 4 - Minimal', 'Count': p4_prbs})
            colors.append('#28a745')  # Green
        
        if not priority_data:
            st.info("📊 No categorized PRB data available")
            return
        
        # Create DataFrame
        prb_df = pd.DataFrame(priority_data)
        
        # Create horizontal bar chart with severity colors
        fig = px.bar(
            prb_df,
            x='Count',
            y='Priority',
            orientation='h',
            title="PRB Distribution by Severity Level",
            color='Priority',
            color_discrete_map={
                'Sev 0 - Critical': '#8b0000',  # Dark Red
                'Sev 1 - High': '#dc3545',      # Red
                'Sev 2 - Medium': '#fd7e14',    # Orange  
                'Sev 3 - Low': '#ffc107',       # Yellow
                'Sev 4 - Minimal': '#28a745'    # Green
            }
        )
        
        # Update layout for better readability
        fig.update_layout(
            showlegend=False,
            xaxis_title="Number of PRBs",
            yaxis_title="Severity Level",
            height=300
        )
        
        st.plotly_chart(fig, use_container_width=True, key=f"prb_analysis_chart{key_suffix}")
    
    def create_deployment_timeline(self, data: Dict[str, Any]):
        """Create deployment visualization."""
        deployments = data.get('stagger_deployments', [])
        if not deployments:
            deployments = data.get('deployments', [])
        
        if not deployments:
            st.info("📅 No deployment data available")
            return
        
        # Create deployment frequency chart
        deployment_data = []
        for d in deployments[:10]:  # Latest 10 deployments
            deployment_data.append({
                'Version': d.get('version', 'Unknown')[:20],  # Truncate long version names
                'Cells': d.get('cells_count', d.get('cells', 0)),
                'Status': d.get('status', 'Completed'),
                'Date': d.get('date', 'Unknown')
            })
        
        if deployment_data:
            deployment_df = pd.DataFrame(deployment_data)
            
            # Create bar chart showing cell counts per deployment
            fig = px.bar(
                deployment_df,
                x='Version',
                y='Cells',
                title="Deployment Cell Distribution",
                color='Status',
                hover_data=['Date'],
                color_discrete_map={
                    'Completed': '#2E8B57',
                    'In Progress': '#FFD700',
                    'Failed': '#DC143C',
                    'Pending': '#708090'
                }
            )
            fig.update_layout(xaxis_tickangle=45)
            st.plotly_chart(fig, use_container_width=True, key="deployment_timeline_chart")
    
    def create_bug_severity_chart(self, data: Dict[str, Any]):
        """Create production bug priority breakdown chart with scoring visualization."""
        bugs = data.get('bugs', [])
        
        if not bugs:
            st.info("🐛 No production bug data available")
            return
        
        # Count by priority (P0, P1, P2, P3+)
        priority_counts = {
            'P0': len([b for b in bugs if 'P0' in str(b.get('severity', ''))]),
            'P1': len([b for b in bugs if 'P1' in str(b.get('severity', ''))]),
            'P2': len([b for b in bugs if 'P2' in str(b.get('severity', ''))]),
            'P3+': len([b for b in bugs if any(p in str(b.get('severity', '')) for p in ['P3', 'P4'])])
        }
        
        # Remove zero counts for cleaner chart
        priority_counts = {k: v for k, v in priority_counts.items() if v > 0}
        
        if not priority_counts:
            st.info("📊 No production bugs by priority")
            return
        
        # Create donut chart with production bug priorities
        fig = px.pie(
            values=list(priority_counts.values()),
            names=list(priority_counts.keys()),
            title="Production Bugs by Priority",
            hole=0.4,
            color_discrete_map={
                'P0': '#dc3545',    # Red - Critical
                'P1': '#fd7e14',    # Orange - High  
                'P2': '#ffc107',    # Yellow - Medium
                'P3+': '#28a745'    # Green - Low
            }
        )
        
        # Calculate and show bug score
        critical_bugs = priority_counts.get('P0', 0) + priority_counts.get('P1', 0)
        p2_plus_bugs = priority_counts.get('P2', 0) + priority_counts.get('P3+', 0)
        bug_score = (critical_bugs * 4) + (p2_plus_bugs * 1)
        
        # Add subtitle with scoring
        fig.update_layout(
            annotations=[
                dict(
                    text=f"Bug Score: {bug_score} pts<br>P0/P1: {critical_bugs} × 4pts<br>P2+: {p2_plus_bugs} × 1pt",
                    x=0.5, y=0.5, font_size=12, showarrow=False
                )
            ]
        )
        
        st.plotly_chart(fig, use_container_width=True, key="bug_severity_chart")
    
    def create_ci_issues_chart(self, data: Dict[str, Any]):
        """Create CI issues stacked bar chart by team and priority."""
        ci_data = data.get('ci_issues', [])
        
        if not ci_data:
            st.info("🔧 No CI issues data available")
            return
        
        # Parse CI data and group by team and priority
        team_priority_counts = {}
        for issue in ci_data:
            team = issue.get('team', 'Unknown Team')
            priority = issue.get('priority', 'P2')  # Default to P2 if not specified
            
            if team not in team_priority_counts:
                team_priority_counts[team] = {}
            if priority not in team_priority_counts[team]:
                team_priority_counts[team][priority] = 0
            team_priority_counts[team][priority] += 1
        
        if not team_priority_counts:
            st.info("📊 No CI issues found")
            return
        
        # Prepare data for stacked bar chart - stack by priority
        teams = sorted(team_priority_counts.keys())
        all_priorities = set()
        for team_data in team_priority_counts.values():
            all_priorities.update(team_data.keys())
        priorities = sorted(list(all_priorities))
        
        fig = go.Figure()
        
        # Color map for priorities (distinctive and accessible)
        priority_colors = {
            'P0': '#C0392B', 'P1': '#E67E22', 'P2': '#F39C12', 'P3': '#27AE60', 'P4': '#8E44AD'
        }
        
        # Create stacked bars - each priority is a layer in the stack
        for priority in priorities:
            values = [team_priority_counts[team].get(priority, 0) for team in teams]
            fig.add_trace(go.Bar(
                name=f'{priority}',
                x=teams,
                y=values,
                marker_color=priority_colors.get(priority, '#6c757d'),
                hovertemplate=f'<b>%{{x}}</b><br>{priority}: %{{y}} issues<extra></extra>'
        ))
        
        fig.update_layout(
            title="CI Issues by Team (Stacked by Priority)",
            barmode='stack',
            xaxis_title="Team",
            yaxis_title="Number of Issues",
            xaxis={'tickangle': -45},
            legend_title="Priority"
        )
        
        st.plotly_chart(fig, use_container_width=True, key="ci_issues_chart")
    
    def create_security_bugs_chart(self, data: Dict[str, Any]):
        """Create security bugs stacked bar chart by team and priority."""
        security_data = data.get('security_issues', [])
        
        if not security_data:
            st.info("🔒 No security bugs data available")
            return
        
        # Parse security data and group by team and priority
        team_priority_counts = {}
        for bug in security_data:
            # Security issues use 'component' field for team info
            team = bug.get('team', bug.get('component', 'Unknown Team'))
            # Infer priority from subject or use default
            subject = bug.get('subject', '')
            priority = 'P2'  # Default priority based on data pattern
            
            if team not in team_priority_counts:
                team_priority_counts[team] = {}
            if priority not in team_priority_counts[team]:
                team_priority_counts[team][priority] = 0
            team_priority_counts[team][priority] += 1
        
        if not team_priority_counts:
            st.info("📊 No security bugs found")
            return
        
        # Prepare data for stacked bar chart
        teams = list(team_priority_counts.keys())
        priorities = set()
        for team_data in team_priority_counts.values():
            priorities.update(team_data.keys())
        priorities = sorted(list(priorities))
        
        fig = go.Figure()
        
        # Color map for priorities (distinctive and accessible)
        priority_colors = {
            'P0': '#C0392B', 'P1': '#E67E22', 'P2': '#F39C12', 'P3': '#27AE60', 'P4': '#8E44AD'
        }
        
        for priority in priorities:
            values = [team_priority_counts[team].get(priority, 0) for team in teams]
            fig.add_trace(go.Bar(
                name=priority,
                x=teams,
                y=values,
                marker_color=priority_colors.get(priority, '#6c757d')
            ))
        
        fig.update_layout(
            title="Security Bugs by Team (Stacked by Priority)",
            barmode='stack',
            xaxis_title="Team",
            yaxis_title="Number of Bugs",
            xaxis={'tickangle': -45},
            legend_title="Priority"
        )
        
        st.plotly_chart(fig, use_container_width=True, key="security_bugs_chart")
    
    def create_leftshift_bugs_chart(self, data: Dict[str, Any]):
        """Create left shift bugs stacked bar chart by team and priority."""
        leftshift_data = data.get('leftshift_issues', [])
        
        if not leftshift_data:
            st.info("⬅️ No left shift bugs data available")
            return
        
        # Parse left shift data and group by team and priority
        team_priority_counts = {}
        for bug in leftshift_data:
            team = bug.get('team', 'Unknown Team')
            priority = bug.get('priority', 'P2')  # Default priority
            
            if team not in team_priority_counts:
                team_priority_counts[team] = {}
            if priority not in team_priority_counts[team]:
                team_priority_counts[team][priority] = 0
            team_priority_counts[team][priority] += 1
        
        if not team_priority_counts:
            st.info("📊 No left shift bugs found")
            return
        
        # Prepare data for stacked bar chart
        teams = list(team_priority_counts.keys())
        priorities = set()
        for team_data in team_priority_counts.values():
            priorities.update(team_data.keys())
        priorities = sorted(list(priorities))
        
        fig = go.Figure()
        
        # Color map for priorities (distinctive and accessible)
        priority_colors = {
            'P0': '#C0392B', 'P1': '#E67E22', 'P2': '#F39C12', 'P3': '#27AE60', 'P4': '#8E44AD'
        }
        
        for priority in priorities:
            values = [team_priority_counts[team].get(priority, 0) for team in teams]
            fig.add_trace(go.Bar(
                name=priority,
                x=teams,
                y=values,
                marker_color=priority_colors.get(priority, '#6c757d')
            ))
        
        fig.update_layout(
            title="Left Shift Bugs by Team (Stacked by Priority)",
            barmode='stack',
            xaxis_title="Team",
            yaxis_title="Number of Bugs",
            xaxis={'tickangle': -45},
            legend_title="Priority"
        )
        
        st.plotly_chart(fig, use_container_width=True, key="leftshift_bugs_chart")
    
    def create_abs_bugs_chart(self, data: Dict[str, Any]):
        """Create ABS bugs stacked bar chart by team and priority."""
        abs_data = data.get('abs_issues', [])
        
        if not abs_data:
            st.info("🔷 No ABS bugs data available")
            return
        
        team_priority_counts = {}
        for bug in abs_data:
            team = bug.get('team', 'Unknown Team')
            priority = bug.get('priority', 'P2')
            
            if team not in team_priority_counts:
                team_priority_counts[team] = {}
            if priority not in team_priority_counts[team]:
                team_priority_counts[team][priority] = 0
            team_priority_counts[team][priority] += 1
        
        if not team_priority_counts:
            st.info("📊 No ABS bugs found")
            return
        
        teams = list(team_priority_counts.keys())
        priorities = set()
        for team_data in team_priority_counts.values():
            priorities.update(team_data.keys())
        priorities = sorted(list(priorities))
        
        fig = go.Figure()
        
        priority_colors = {
            'P0': '#C0392B', 'P1': '#E67E22', 'P2': '#F39C12', 'P3': '#27AE60', 'P4': '#8E44AD'
        }
        
        for priority in priorities:
            values = [team_priority_counts[team].get(priority, 0) for team in teams]
            fig.add_trace(go.Bar(
                name=priority,
                x=teams,
                y=values,
                marker_color=priority_colors.get(priority, '#6c757d')
            ))
        
        fig.update_layout(
            title="ABS Bugs by Team (Stacked by Priority)",
            barmode='stack',
            xaxis_title="Team",
            yaxis_title="Number of Bugs",
            xaxis={'tickangle': -45},
            legend_title="Priority"
        )
        
        st.plotly_chart(fig, use_container_width=True, key="abs_bugs_chart")
    
    def create_trend_analysis(self, data: Dict[str, Any]):
        """Get pre-generated trend analysis from LLM content or show unavailable message."""
        # Check if we have pre-generated LLM content
        if hasattr(self, 'llm_content') and self.llm_content:
            trend_analysis = self.llm_content.get('trend_analysis', '')
            if trend_analysis:
                st.markdown("### 📈 Quality Trends Analysis")
                st.markdown(trend_analysis)
                return
        
        # No LLM content available
        st.markdown("### 📈 Quality Trends Analysis")
        st.info("**Trend Analysis:** Content not available - requires LLM generation during report creation")
    
    def create_weekly_trends(self, report_files: List[Dict[str, Any]], chart_key_suffix: str = ""):
        """Render week-over-week trends using past reports' metadata counts."""
        if not report_files:
            return
        
        rows = []
        for rf in report_files:
            try:
                with open(rf['path'], 'r') as f:
                    data = json.load(f)
                meta = data.get('metadata', {})
                # Prefer explicit report period end date for x-axis
                date_str = meta.get('report_period_end')
                if date_str:
                    xdate = datetime.strptime(date_str, '%Y-%m-%d')
                else:
                    # Fallback to generated_at
                    gen = meta.get('generated_at')
                    xdate = datetime.fromisoformat(gen.replace('Z', '+00:00')) if gen else rf.get('date')
                
                # Calculate scores for each metric using the same scoring logic as the dashboard
                
                # 1. Feature Rollout Risk Score (count of at-risk features)
                risks = data.get('risks', [])
                risk_score = len([r for r in risks if r.get('status') in ['Red', 'At Risk', 'Critical']])
                
                # 2. Sev 0/1 PRBs Score (count of P0/P1 PRBs)
                prbs = data.get('prbs', [])
                p0_prbs = len([p for p in prbs if 'P0' in str(p.get('priority', '')) or 'Sev0' in str(p.get('priority', ''))])
                p1_prbs = len([p for p in prbs if 'P1' in str(p.get('priority', '')) or 'Sev1' in str(p.get('priority', ''))])
                prb_score = p0_prbs + p1_prbs
                
                # 3. Production Bugs Score (P0/P1 × 4 + P2+ × 1)
                bugs = data.get('bugs', [])
                p0_bugs = len([b for b in bugs if 'P0' in str(b.get('severity', ''))])
                p1_bugs = len([b for b in bugs if 'P1' in str(b.get('severity', ''))])
                p2_plus_bugs = len([b for b in bugs if any(p in str(b.get('severity', '')) for p in ['P2', 'P3', 'P4'])])
                prod_bug_score = (p0_bugs + p1_bugs) * 4 + p2_plus_bugs * 1
                
                # 4. CI Issues Score (P0/P1 × 4 + P2+ × 1)
                ci_issues = data.get('ci_issues', [])
                ci_p0_bugs = len([b for b in ci_issues if 'P0' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
                ci_p1_bugs = len([b for b in ci_issues if 'P1' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
                ci_p2_plus_bugs = len([b for b in ci_issues if any(p in str(b.get('severity', '') + str(b.get('priority', ''))).upper() for p in ['P2', 'P3', 'P4'])])
                ci_score = (ci_p0_bugs + ci_p1_bugs) * 4 + ci_p2_plus_bugs * 1
                
                # 5. Security Issues Score (P0/P1 × 4 + P2+ × 1)
                security_issues = data.get('security_issues', [])
                sec_p0_bugs = len([b for b in security_issues if 'P0' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
                sec_p1_bugs = len([b for b in security_issues if 'P1' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
                sec_p2_plus_bugs = len([b for b in security_issues if any(p in str(b.get('severity', '') + str(b.get('priority', ''))).upper() for p in ['P2', 'P3', 'P4'])])
                security_score = (sec_p0_bugs + sec_p1_bugs) * 4 + sec_p2_plus_bugs * 1
                
                # 6. Left Shift Score (P0/P1 × 4 + P2+ × 1)
                leftshift_issues = data.get('leftshift_issues', [])
                ls_p0_bugs = len([b for b in leftshift_issues if 'P0' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
                ls_p1_bugs = len([b for b in leftshift_issues if 'P1' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
                ls_p2_plus_bugs = len([b for b in leftshift_issues if any(p in str(b.get('severity', '') + str(b.get('priority', ''))).upper() for p in ['P2', 'P3', 'P4'])])
                leftshift_score = (ls_p0_bugs + ls_p1_bugs) * 4 + ls_p2_plus_bugs * 1
                
                # 7. ABS bugs score (P0/P1 × 4 + P2+ × 1)
                abs_issues_hist = data.get('abs_issues', [])
                abs_p0_bugs = len([b for b in abs_issues_hist if 'P0' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
                abs_p1_bugs = len([b for b in abs_issues_hist if 'P1' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
                abs_p2_plus_bugs = len([b for b in abs_issues_hist if any(p in str(b.get('severity', '') + str(b.get('priority', ''))).upper() for p in ['P2', 'P3', 'P4'])])
                abs_score = (abs_p0_bugs + abs_p1_bugs) * 4 + abs_p2_plus_bugs * 1
                
                # 8. Total Line Coverage (extract from coverage_summary)
                coverage_summary = data.get('coverage_summary', {})
                overall_coverage = coverage_summary.get('overall', {})
                total_line_coverage = overall_coverage.get('line_coverage', 0)
                
                # Add row to data
                rows.append({
                    'date': xdate,
                    'Feature Rollout Risk': risk_score,
                    'Sev 0/1 PRBs': prb_score,
                    'P0/P1 Production Bugs': prod_bug_score,
                    'P0/P1 CI Issues': ci_score,
                    'P0/P1 Security Issues': security_score,
                    'P0/P1 Left Shift': leftshift_score,
                    'P0/P1 ABS Bugs': abs_score,
                    'Total Line Coverage %': total_line_coverage
                })
                
            except Exception as e:
                print(f"Error processing report {rf.get('path', 'unknown')}: {e}")
                continue

        if not rows:
            st.info("No historical data available for trends analysis")
            return

        df = pd.DataFrame(rows).sort_values('date')
        
        # Define score metrics (left Y-axis)
        score_cols = ['Feature Rollout Risk', 'Sev 0/1 PRBs', 'P0/P1 Production Bugs', 
                     'P0/P1 CI Issues', 'P0/P1 Security Issues', 'P0/P1 Left Shift', 'P0/P1 ABS Bugs']
        
        
        # Create dual-axis chart
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Define distinctive colors for each metric (improved contrast and accessibility)
        colors = {
            'Feature Rollout Risk': '#E74C3C',      # Bright Red (critical issues)
            'Sev 0/1 PRBs': '#F39C12',             # Bright Orange (high severity)
            'P0/P1 Production Bugs': '#8E44AD',     # Purple (production focus)
            'P0/P1 CI Issues': '#3498DB',          # Bright Blue (CI/CD)
            'P0/P1 Security Issues': '#27AE60',     # Green (security)
            'P0/P1 Left Shift': '#E67E22',         # Dark Orange (development)
            'P0/P1 ABS Bugs': '#1ABC9C',           # Teal (ABS)
            'Total Line Coverage %': '#2C3E50'      # Dark Blue-Gray (coverage metric)
        }

        # Left axis: KPI scores
        for metric in score_cols:
            if metric in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df['date'], 
                        y=df[metric], 
                        mode='lines+markers', 
                        name=metric,
                        line=dict(color=colors.get(metric, '#333333'), width=2),
                        marker=dict(size=6),
                        hovertemplate=f'<b>{metric}</b><br>Date: %{{x}}<br>Score: %{{y}}<extra></extra>'
                    ),
                    secondary_y=False
                )

        # Right axis: Total Line Coverage
        if 'Total Line Coverage %' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['date'], 
                    y=df['Total Line Coverage %'], 
                    mode='lines+markers', 
                    name='Total Line Coverage %',
                    line=dict(color=colors['Total Line Coverage %'], width=3, dash='dash'),
                    marker=dict(size=8, symbol='diamond'),
                    hovertemplate='<b>Total Line Coverage</b><br>Date: %{x}<br>Coverage: %{y:.1f}%<extra></extra>'
                ),
                secondary_y=True
            )

        # Update axes
        fig.update_yaxes(
            title_text='<b>KPI Scores</b>', 
            secondary_y=False,
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)'
        )
        fig.update_yaxes(
            title_text='<b>Coverage %</b>', 
            secondary_y=True,
            range=[max(0, min(df['Total Line Coverage %']) - 5) if 'Total Line Coverage %' in df.columns else 0, 
                   min(100, max(df['Total Line Coverage %']) + 5) if 'Total Line Coverage %' in df.columns else 100],
            showgrid=False
        )
        
        fig.update_xaxes(
            title_text='<b>Week Ending</b>',
            title_standoff=10,  # Bring X-axis title closer to chart
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)'
        )
        
        # Update layout for compact and visually appealing design
        fig.update_layout(
            title={
                'text': '<b>Week-over-Week Quality Trends</b>',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18, 'color': '#2E86AB'}
            },
            legend=dict(
                orientation='h', 
                yanchor='bottom', 
                y=-0.45,  # Position line legends even lower for more separation
                xanchor='center', 
                x=0.5,
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='rgba(0,0,0,0.2)',
                borderwidth=1,
                font=dict(size=9)  # Smaller legend font
            ),
            margin=dict(l=60, r=60, t=80, b=200),  # Increased bottom margin for lower legend position
            height=480,  # Keep height to accommodate legend
            hovermode='x unified',
            plot_bgcolor='rgba(248,249,250,0.8)',
            paper_bgcolor='white',
            font=dict(family="Inter, Arial, sans-serif", size=12, color="#2c3e50")
        )
        
        safe_suffix = chart_key_suffix.replace(" ", "_") if chart_key_suffix else "default"
        st.plotly_chart(fig, use_container_width=True, key=f"weekly_trends_chart_scores_{safe_suffix}")
    
    def create_risk_insights(self, data: Dict[str, Any]):
        """Create risk insights panel based on archived risk data."""
        risks = data.get('risks', []) if isinstance(data, dict) else []
        if not risks:
            st.info("No risk data available")
            return
        
        # Group risks by status
        green_risks = [r for r in risks if str(r.get('status', '')).lower() in ['green', 'on track']]
        yellow_risks = [r for r in risks if str(r.get('status', '')).lower() in ['yellow', 'at risk']]
        red_risks = [r for r in risks if str(r.get('status', '')).lower() in ['red', 'critical']]
        
        st.markdown("#### 📊 Risk Summary")
        st.metric("Total Features", len(risks))
        
        # What's going well
        st.markdown("#### ✅ What's Going Well")
        if green_risks:
            for risk in green_risks:
                feature = risk.get('feature') or risk.get('name') or 'Unknown'
                priority = risk.get('priority', 'Unknown')
                st.write(f"🟢 **{feature}**")
                st.caption(f"Priority: {priority}")
        else:
            st.write("No features currently on track")
        
        # Areas of concern
        st.markdown("#### ⚠️ Areas of Concern")
        if yellow_risks or red_risks:
            for risk in yellow_risks + red_risks:
                status = str(risk.get('status', '')).lower()
                color = "🔴" if status in ['red', 'critical'] else "🟡"
                feature = risk.get('feature') or risk.get('name') or 'Unknown'
                priority = risk.get('priority', 'Unknown')
                st.write(f"{color} **{feature}**")
                st.caption(f"Priority: {priority}")
            else:
                st.write("All features are on track! 🎉")

    def generate_prb_narrative(self, prb: dict) -> str:
        """Get pre-generated PRB narrative from LLM content or show unavailable message."""
        prb_id = prb.get('id', 'Unknown')
        
        # Check if we have pre-generated LLM content
        if hasattr(self, 'llm_content') and self.llm_content:
            narratives = self.llm_content.get('prb_narratives', {})
            if prb_id in narratives:
                return narratives[prb_id]
        
        # No LLM content available
        return f"**PRB Analysis:** Content not available - requires LLM generation during report creation for {prb_id}"
    
    def generate_enhanced_fallback_narrative(self, prb: dict, prb_data: str) -> str:
        """Enhanced fallback narrative generation when LLM is unavailable."""
        return f"**PRB Analysis:** Content not available - requires LLM generation during report creation for {prb.get('id', 'Unknown')}"
    
    def generate_lower_priority_summary(self, lower_prbs: list) -> str:
        """Get pre-generated lower priority summary from LLM content or show unavailable message."""
        # Check if we have pre-generated LLM content
        if hasattr(self, 'llm_content') and self.llm_content:
            summary = self.llm_content.get('lower_priority_summary', '')
            if summary:
                return summary
        
        # No LLM content available
        return "**Current Sev 2+ Issues:** Content not available - requires LLM generation during report creation"
    
    def generate_exhaustive_prb_analysis(self, prb: dict) -> str:
        """Get pre-generated exhaustive PRB analysis from LLM content or show unavailable message."""
        prb_id = prb.get('id', 'Unknown')
        
        # Check if we have pre-generated LLM content
        if hasattr(self, 'llm_content') and self.llm_content:
            analyses = self.llm_content.get('prb_analyses', {})
            if prb_id in analyses:
                return analyses[prb_id]
        
        # No LLM content available
        return f"**Exhaustive Analysis:** Content not available - requires LLM generation during report creation for {prb_id}"
    
    def deduplicate_prbs(self, prbs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate PRBs based on ID, falling back to content similarity."""
        if not prbs:
            return prbs

        unique_prbs = []
        seen_ids = set()
        seen_incidents = set()

        for prb in prbs:
            prb_id = prb.get('id', '').strip()

            # Deduplicate by ID first
            if prb_id:
                if prb_id in seen_ids:
                    continue
                seen_ids.add(prb_id)
            else:
                # Fall back to content signature for items without an ID
                what_happened = prb.get('what_happened', '').strip()
                created_date = prb.get('created_date', '')
                team = prb.get('team', '')
                incident_signature = f"{what_happened}|{created_date}|{team}"
                if incident_signature in seen_incidents:
                    continue
                seen_incidents.add(incident_signature)

            unique_prbs.append(prb)

        return unique_prbs
    
    def create_prb_insights(self, data: Dict[str, Any]):
        """Create enhanced PRB insights panel with AI-generated narratives."""
        prbs = data.get('prbs', [])
        if not prbs:
            st.info("No PRB data available")
            return
        
        # Remove duplicate PRBs based on content similarity
        prbs = self.deduplicate_prbs(prbs)
        
        # Analyze PRBs by severity (regardless of status - focus on all Sev 0/1 PRBs)
        p0_prbs = [p for p in prbs if 'P0' in str(p.get('priority', '')) or 'Sev0' in str(p.get('priority', ''))]
        p1_prbs = [p for p in prbs if 'P1' in str(p.get('priority', '')) or 'Sev1' in str(p.get('priority', '')) or 'Critical' in str(p.get('priority', ''))]
        p2_prbs = [p for p in prbs if 'P2' in str(p.get('priority', '')) or 'Sev2' in str(p.get('priority', ''))]
        p3_prbs = [p for p in prbs if 'P3' in str(p.get('priority', '')) or 'Sev3' in str(p.get('priority', ''))]
        
        # All PRBs regardless of status (focus on volume for the week)
        critical_prbs_total = len(p0_prbs) + len(p1_prbs)  # Sev 0 + Sev 1
        
        st.markdown("#### 📊 [PRB Severity Breakdown (All PRBs This Week)](https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=report&wave__assetId=00OEE000001TXjB2AW)")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            # Sev 0 - always red if any exist
            sev0_color = "inverse" if len(p0_prbs) > 0 else "normal"
            st.metric("🔴 Sev 0", len(p0_prbs), delta="CRITICAL" if len(p0_prbs) > 0 else "None", delta_color=sev0_color)
        with col2:
            st.metric("🟠 Sev 1", len(p1_prbs), delta="HIGH")
        with col3:
            st.metric("🟡 Sev 2", len(p2_prbs), delta="MEDIUM")
        with col4:
            # Overall status based on Sev 0/1 count
            if len(p0_prbs) > 0:
                status = "🔴 RED"
                status_color = "inverse"
            elif critical_prbs_total > 4:
                status = "🔴 RED" 
                status_color = "inverse"
            elif critical_prbs_total > 2:
                status = "🟡 YELLOW"
                status_color = "off"
            else:
                status = "🟢 GREEN"
                status_color = "normal"
            st.metric("📊 Status", status, delta=f"{critical_prbs_total} Sev 0/1", delta_color=status_color)
        
        st.markdown("#### ✅ **What's Going Well**") 
        resolved_prbs = [p for p in prbs if p.get('status') == 'Resolved']
        if resolved_prbs:
            st.write(f"📈 **{len(resolved_prbs)} PRBs resolved** - Effective incident management")
            
            # Show resolution by severity
            resolved_p0 = [p for p in p0_prbs if p.get('status') == 'Resolved']
            resolved_p1 = [p for p in p1_prbs if p.get('status') == 'Resolved']
            if resolved_p0:
                st.write(f"🎯 **{len(resolved_p0)} Sev 0 critical issues resolved** - Excellent crisis response")
            if resolved_p1:
                st.write(f"🔧 **{len(resolved_p1)} Sev 1 high priority issues closed** - Strong incident response")
        
        # Weekly volume assessment
        if critical_prbs_total <= 2:
            st.write(f"🌟 **Low critical volume** - Only {critical_prbs_total} Sev 0/1 PRBs this week")
        elif len(p0_prbs) == 0 and critical_prbs_total <= 4:
            st.write(f"⚠️ **Manageable load** - No Sev 0 PRBs, {critical_prbs_total} total Sev 0/1")
            
        # Individual narratives for P0/P1 issues
        st.markdown("#### 🚨 **Critical Issues Analysis**")
        
        if len(p0_prbs) > 0:
            st.error(f"🚨 **{len(p0_prbs)} SEV 0 CRITICAL PRBs** - Maximum severity detected!")
            st.markdown("**Sev 0 Issues:**")
            for prb in p0_prbs:
                st.markdown(f"**🔴 {prb.get('id', 'Unknown')}**")
                narrative = self.generate_prb_narrative(prb)
                st.markdown(narrative)
                st.markdown("---")
                
        if len(p1_prbs) > 0:
            if len(p0_prbs) == 0:
                st.warning(f"🟠 **{len(p1_prbs)} SEV 1 HIGH priority PRBs** - Requires attention")
            st.markdown("**Sev 1 Issues:**")
            for prb in p1_prbs:
                st.markdown(f"**🟠 {prb.get('id', 'Unknown')}**")
                narrative = self.generate_prb_narrative(prb)
                st.markdown(narrative)
                st.markdown("---")
        
        # Comprehensive analysis for P2+ issues
        if len(p2_prbs) > 0 or len(p3_prbs) > 0:
            st.markdown("#### 📋 **Lower Priority Issues Analysis**")
            total_lower = len(p2_prbs) + len(p3_prbs)
            st.info(f"**{total_lower} Sev 2+ PRBs** - Detailed analysis and standard processes")
            
            if p2_prbs:
                st.markdown("**Sev 2 Issues:**")
                for prb in p2_prbs:
                    st.markdown(f"**🟡 {prb.get('id', 'Unknown')}**")
                    narrative = self.generate_prb_narrative(prb)
                    st.markdown(narrative)
                    st.markdown("---")
            
            if p3_prbs:
                st.markdown("**Sev 3 Issues:**")
                for prb in p3_prbs:
                    st.markdown(f"**⚪ {prb.get('id', 'Unknown')}**")
                    narrative = self.generate_prb_narrative(prb)
                    st.markdown(narrative)
                    st.markdown("---")
            
            # Generate comprehensive summary of all lower priority issues
            if len(p2_prbs) + len(p3_prbs) > 0:
                st.markdown("#### 📊 **Overall Sev 2+ Issues Summary**")
                lower_summary = self.generate_lower_priority_summary(p2_prbs + p3_prbs)
                st.markdown(lower_summary)
        
        if len(p0_prbs) == 0 and len(p1_prbs) == 0:
            st.success("🎉 **No Sev 0/1 PRBs this week** - Excellent operational stability!")
            
        # Detailed exhaustive summary section with comprehensive LLM analysis
        if len(prbs) > 0:
            with st.expander("📋 **Exhaustive Details**", expanded=False):
                st.markdown("### Complete PRB Analysis with AI-Generated Insights")
                for prb in sorted(prbs, key=lambda x: x.get('priority', 'P9')):
                    priority_emoji = "🔴" if 'P0' in str(prb.get('priority', '')) else "🟠" if 'P1' in str(prb.get('priority', '')) else "🟡" if 'P2' in str(prb.get('priority', '')) else "⚪"
                    st.markdown(f"**{priority_emoji} {prb.get('id', 'Unknown')} - {prb.get('title', 'No title')[:100]}**")
                    
                    # AI-Generated Comprehensive Analysis for each PRB
                    st.markdown("#### 🤖 **AI Analysis**")
                    exhaustive_narrative = self.generate_exhaustive_prb_analysis(prb)
                    st.markdown(exhaustive_narrative)
                    
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.write(f"**Priority:** {prb.get('priority', 'Unknown')}")
                        st.write(f"**Status:** {prb.get('status', 'Unknown')}")
                        st.write(f"**Created:** {prb.get('created_date', 'Unknown')}")
                    
                    with col2:
                        # Show detailed technical information
                        team = prb.get('team', '') or getattr(prb, 'team', '')
                        impact = prb.get('customer_impact', '') or getattr(prb, 'customer_impact', '')
                        if team:
                            st.write(f"**Team:** {team}")
                        if impact:
                            st.write(f"**Impact:** {impact}")
                    
                    # Full description and technical details with comprehensive data
                    if prb.get('description'):
                        st.text_area(f"Description - {prb.get('id')}", prb.get('description'), height=100, key=f"desc_{prb.get('id')}")
                    
                    # Comprehensive technical details 
                    what_happened = prb.get('what_happened', '') or getattr(prb, 'what_happened', '')
                    if what_happened:
                        st.text_area(f"What Happened (Complete) - {prb.get('id')}", what_happened, height=120, key=f"what_{prb.get('id')}")
                    
                    proximate_cause = prb.get('proximate_cause', '') or getattr(prb, 'proximate_cause', '')
                    if proximate_cause:
                        st.text_area(f"Root Cause (Complete) - {prb.get('id')}", proximate_cause, height=120, key=f"cause_{prb.get('id')}")
                    
                    how_resolved = prb.get('how_resolved', '') or getattr(prb, 'how_resolved', '')
                    if how_resolved:
                        st.text_area(f"Resolution (Complete) - {prb.get('id')}", how_resolved, height=120, key=f"resolution_{prb.get('id')}")
                    
                    next_steps = prb.get('next_steps', '') or getattr(prb, 'next_steps', '')
                    if next_steps:
                        st.text_area(f"Next Steps (Complete) - {prb.get('id')}", next_steps, height=120, key=f"next_{prb.get('id')}")
                    
                    user_experience = prb.get('user_experience', '') or getattr(prb, 'user_experience', '')
                    if user_experience:
                        st.text_area(f"User Experience - {prb.get('id')}", user_experience, height=100, key=f"user_{prb.get('id')}")
                    
                    st.markdown("---")
        
        # Summary Assessment based on weekly volume
        st.markdown("#### 📋 **Weekly Risk Assessment**")
        
        # Apply color-coding rules
        if len(p0_prbs) > 0:
            st.error(f"🔴 **RED STATUS**: {len(p0_prbs)} Sev 0 PRBs detected - Any Sev 0 = Red")
        elif critical_prbs_total > 4:
            st.error(f"🔴 **RED STATUS**: {critical_prbs_total} Sev 0/1 PRBs - High volume (>4)")
        elif critical_prbs_total > 2:
            st.warning(f"🟡 **YELLOW STATUS**: {critical_prbs_total} Sev 0/1 PRBs - Elevated volume (>2)")
        else:
            st.success(f"🟢 **GREEN STATUS**: {critical_prbs_total} Sev 0/1 PRBs - Normal operational level")
        
        # Actionable recommendations
        if len(p0_prbs) > 0:
            st.write(f"🚨 **IMMEDIATE ACTION**: All-hands response for {len(p0_prbs)} Sev 0 critical incidents")
        elif critical_prbs_total > 4:
            st.write(f"⚡ **HIGH PRIORITY**: Scale incident response resources - {critical_prbs_total} critical incidents")
        elif critical_prbs_total > 2:
            st.write(f"🔧 **ELEVATED ATTENTION**: Monitor closely and ensure adequate coverage for {critical_prbs_total} incidents")
        else:
            st.write("📅 **GREEN STATUS**: Continue standard incident management procedures")
    
    def create_bug_insights(self, data: Dict[str, Any]):
        """Create production bug insights panel with scoring system."""
        bugs = data.get('bugs', [])
        
        if not bugs:
            st.info("No production bug data available")
            return
        
        # Analyze by priority with new scoring system
        p0_bugs = [b for b in bugs if 'P0' in str(b.get('severity', ''))]
        p1_bugs = [b for b in bugs if 'P1' in str(b.get('severity', ''))]  
        p2_bugs = [b for b in bugs if 'P2' in str(b.get('severity', ''))]
        p3_plus_bugs = [b for b in bugs if any(p in str(b.get('severity', '')) for p in ['P3', 'P4'])]
        
        # Calculate production bug score
        critical_count = len(p0_bugs) + len(p1_bugs)
        p2_plus_count = len(p2_bugs) + len(p3_plus_bugs)
        bug_score = (critical_count * 4) + (p2_plus_count * 1)
        
        # Determine status
        if bug_score > 32:
            status = "🔴 RED"
        elif bug_score > 16:
            status = "🟡 YELLOW"
        else:
            status = "🟢 GREEN"
        
        st.markdown("#### 📊 [Production Bug Summary](https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=report&wave__assetId=00OEE0000014M4b2AE)") 
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔴 P0/P1 Bugs", critical_count)
        with col2:
            st.metric("🟡 P2+ Bugs", p2_plus_count) 
        with col3:
            st.metric("📊 Bug Score", f"{bug_score} pts", delta=status)
        
        st.markdown("#### ✅ **What's Going Well**")
        
        # Fleet Stability Assessment
        if critical_count == 0:
            st.write("🎯 **Zero P0/P1 production bugs** - Excellent fleet stability!")
        elif critical_count <= 2:
            st.write(f"🔧 **Low critical bug count** - Only {critical_count} P0/P1 bugs identified")
            
        if bug_score <= 16:
            st.write("🟢 **GREEN status maintained** - Production bug score within acceptable limits")
            
        # Show distribution insight
        if len(bugs) > 0:
            p2_plus_ratio = p2_plus_count / len(bugs) 
            if p2_plus_ratio > 0.8:
                st.write(f"📈 **Mostly lower severity** - {p2_plus_ratio:.0%} of bugs are P2+ priority")
        
        st.write(f"🔍 **{len(bugs)} total production bugs** being tracked and managed")
        
        st.markdown("#### 🚨 **Priority Actions**")
        if critical_count > 0:
            st.write(f"🔴 **{critical_count} P0/P1 production bugs** require immediate attention")
            # Show top P0 bugs first, then P1
            for bug in (p0_bugs + p1_bugs)[:3]:  # Show top 3 critical
                bug_id = bug.get('id', bug.get('work_id', 'Unknown'))
                bug_title = bug.get('title', bug.get('subject', 'Production Bug'))
                st.write(f"• **{bug_id}**: {bug_title}")
        elif p2_plus_count > 8:
            st.write(f"🟡 **{p2_plus_count} P2+ production bugs** need attention - High volume")
        elif bug_score > 16:
            st.write(f"🟡 **Bug score at {bug_score} points** - Monitor closely")
        else:
            st.write("🎉 **Production fleet stable** - All bugs under control")
    
    def create_deployment_insights(self, data: Dict[str, Any]):
        """Create deployment insights panel."""
        deployments = data.get('stagger_deployments', [])
        if not deployments:
            deployments = data.get('deployments', [])
        
        if not deployments:
            st.info("No deployment data available")
            return
        
        # Analyze deployments
        completed = [d for d in deployments if d.get('status') == 'Completed']
        in_progress = [d for d in deployments if d.get('status') == 'In Progress']
        failed = [d for d in deployments if d.get('status') == 'Failed']
        total_cells = sum(d.get('cells_count', d.get('cells', 0)) for d in deployments)
        
        
        st.markdown("#### ✅ **What's Going Well**")
        if completed:
            success_rate = len(completed) / len(deployments) * 100
            st.write(f"🎯 **{success_rate:.1f}% deployment success rate**")
            st.write(f"📦 **{len(completed)} successful deployments** completed")
            completed_cells = sum(d.get('cells_count', d.get('cells', 0)) for d in completed)
            st.write(f"🌐 **{completed_cells:,} cells** successfully deployed")
        
        st.markdown("#### 🔄 **Current Activity**")
        if in_progress:
            st.write(f"⚡ **{len(in_progress)} deployments** currently in progress")
            for dep in in_progress[:2]:  # Show top 2 in progress
                cells = dep.get('cells_count', dep.get('cells', 0))
                st.write(f"• {dep.get('version', 'Unknown')} - {cells} cells")
        elif failed:
            st.write(f"⚠️ **{len(failed)} failed deployments** need attention")
        else:
            st.write("All deployments completed successfully! 🚀")
    
    def create_coverage_insights(self, data: Dict[str, Any]):
        """Create enhanced coverage insights panel with detailed commentary."""
        coverage_summary = data.get('coverage_summary', {})
        coverage_components = data.get('coverage', [])
        
        if not coverage_summary and not coverage_components:
            st.info("No coverage data available")
            return
            
        st.markdown("#### 📊 Coverage Analysis")
        
        if coverage_summary:
            # Use detailed coverage.txt data
            new_code = coverage_summary.get('new_code', {})
            overall = coverage_summary.get('overall', {})
            
            # Display key metrics comparison
            col1, col2 = st.columns(2)
            with col1:
                st.metric("New Code Line Coverage", f"{new_code.get('line_coverage', 0):.1f}%")
                st.metric("Overall Line Coverage", f"{overall.get('line_coverage', 0):.1f}%")
                
            with col2:
                st.metric("New Code Condition Coverage", f"{new_code.get('condition_coverage', 0):.1f}%")
                st.metric("Overall Condition Coverage", f"{overall.get('condition_coverage', 0):.1f}%")
            
            st.markdown("#### 📈 **Code Quality Commentary**")
            
            # New code analysis
            new_line_cov = new_code.get('line_coverage', 0)
            overall_line_cov = overall.get('line_coverage', 0)
            
            if new_line_cov >= 90:
                st.write("🌟 **Excellent new code quality** - New code line coverage exceeds 90%, demonstrating strong testing discipline")
            elif new_line_cov >= 80:
                st.write("✅ **Good new code quality** - New code line coverage meets target standards")
            elif new_line_cov >= 70:
                st.write("⚠️ **New code coverage below target** - Consider increasing test coverage for new developments")
            else:
                st.write("🔴 **Critical: Low new code coverage** - Immediate focus needed on testing new code")
            
            # Overall codebase health
            if overall_line_cov >= 80:
                st.write(f"💪 **Healthy codebase** - Overall line coverage at {overall_line_cov:.1f}% indicates mature test suite")
            elif overall_line_cov >= 70:
                st.write(f"📊 **Moderate codebase coverage** - At {overall_line_cov:.1f}%, there's room for improvement in overall testing")
            else:
                st.write(f"⚡ **Action needed** - Overall coverage at {overall_line_cov:.1f}% requires strategic testing investment")
            
            # Gap analysis
            coverage_gap = new_line_cov - overall_line_cov
            if coverage_gap > 10:
                st.write(f"📈 **Positive trend** - New code coverage is {coverage_gap:.1f}% higher than overall, showing improvement")
            elif coverage_gap > 0:
                st.write("📊 **Steady progress** - New code coverage slightly exceeds overall baseline")
            else:
                st.write("⚠️ **Declining trend** - New code coverage below overall average needs attention")
            
            st.markdown("#### 🎯 **Coverage Metrics Deep Dive**")
            
            # Condition vs Line coverage analysis
            new_condition_cov = new_code.get('condition_coverage', 0)
            overall_condition_cov = overall.get('condition_coverage', 0)
            
            if new_condition_cov < new_line_cov - 15:
                st.write("⚠️ **Branch coverage gap** - Condition coverage significantly lower than line coverage indicates incomplete decision path testing")
            elif new_condition_cov > new_line_cov + 5:
                st.write("✅ **Thorough decision testing** - Condition coverage exceeds line coverage, showing comprehensive branch testing")
            else:
                st.write("📊 **Balanced coverage approach** - Line and condition coverage are well-aligned")
            
            # Scale and impact analysis
            total_lines = overall.get('lines_to_cover', 0)
            uncovered_lines = overall.get('uncovered_lines', 0)
            
            if total_lines > 0:
                st.write(f"📏 **Codebase scale**: {total_lines:,} lines to cover with {uncovered_lines:,} uncovered lines")
                if uncovered_lines > 100000:
                    st.write("🎯 **Large improvement opportunity** - Consider incremental coverage improvement strategy")
                elif uncovered_lines < 50000:
                    st.write("🎯 **Achievable improvement target** - Focused effort can significantly impact overall coverage")
                    
        else:
            # Fallback to component-based analysis if coverage.txt data not available
            avg_line = sum(c.get('line_coverage', 0) for c in coverage_components) / len(coverage_components)
            st.write(f"📊 Using component-level coverage data: {avg_line:.1f}% average line coverage")
            
            good_coverage = [c for c in coverage_components if c.get('line_coverage', 0) >= 80]
            if good_coverage:
                st.write(f"✅ {len(good_coverage)} components with excellent coverage")
            
            poor_coverage = [c for c in coverage_components if c.get('line_coverage', 0) < 60]  
            if poor_coverage:
                st.write(f"⚠️ {len(poor_coverage)} components need coverage improvement")
    
    def create_trend_insights(self, data: Dict[str, Any]):
        """Create LLM-generated narrative analysis of quality trends."""
        # Extract current values for all 7 key metrics
        risks = len([r for r in data.get('risks', []) if r.get('status') in ['Red', 'At Risk', 'Critical']])
        
        # PRBs - P0/P1 count
        prbs = data.get('prbs', [])
        p0_p1_prbs = len([p for p in prbs if 'P0' in str(p.get('priority', '')) or 'P1' in str(p.get('priority', '')) or 'Sev0' in str(p.get('priority', '')) or 'Sev1' in str(p.get('priority', ''))])
        
        # Production Bugs - P0/P1 count
        bugs = data.get('bugs', [])
        p0_p1_bugs = len([b for b in bugs if 'P0' in str(b.get('severity', '')) or 'P1' in str(b.get('severity', ''))])
        
        # Coverage percentage
        coverage_data = data.get('coverage', [])
        avg_coverage = 67.8  # Default from coverage.txt
        if coverage_data:
            coverages = [c.get('line_coverage', 0) for c in coverage_data if c.get('line_coverage')]
            if coverages:
                avg_coverage = sum(coverages) / len(coverages)
        
        # CI Issues - P0/P1 count (fallback to total if no priority data)
        ci_issues = data.get('ci_issues', [])
        ci_p0_p1 = len([b for b in ci_issues if 'P0' in str(b.get('severity', '') + str(b.get('priority', ''))).upper() or 'P1' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        
        # If no P0/P1 items found but we have CI issues, it likely means the report lacks priority data
        # In this case, we'll show a subset of total issues as "high priority" for scoring purposes
        if ci_p0_p1 == 0 and len(ci_issues) > 0:
            # Assume 20% of CI issues are high priority when priority data is missing
            ci_p0_p1 = max(1, len(ci_issues) // 5)
        
        # Security Bugs - P0/P1 count (fallback to total if no priority data)
        security_bugs = data.get('security_issues', [])
        sec_p0_p1 = len([b for b in security_bugs if 'P0' in str(b.get('severity', '') + str(b.get('priority', ''))).upper() or 'P1' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        
        # Security issues now have real priority data - no fallback needed
        
        # Left Shift - P0/P1 count
        leftshift_issues = data.get('leftshift_issues', [])
        ls_p0_p1 = len([b for b in leftshift_issues if 'P0' in str(b.get('severity', '') + str(b.get('priority', ''))).upper() or 'P1' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        
        # Create metrics summary for LLM analysis
        metrics_summary = f"""
        Current Quality Metrics:
        - Feature Rollout Risk: {risks} at-risk features
        - Sev 0/1 PRBs: {p0_p1_prbs} critical incidents
        - P0/P1 Production Bugs: {p0_p1_bugs} high-priority bugs
        - Line Coverage: {avg_coverage:.1f}%
        - P0/P1 CI Issues: {ci_p0_p1} critical CI problems
        - P0/P1 Security Bugs: {sec_p0_p1} critical security issues (Coverity and 3PP Scan)
        - P0/P1 Left Shift: {ls_p0_p1} critical left-shift issues
        """
        
        # Generate LLM narrative (simulated for now - in production this would call actual LLM)
        st.markdown("### 📈 Quality Trends Analysis")
        
        # Simulate LLM analysis based on metrics
        if risks == 0 and p0_p1_prbs == 0 and p0_p1_bugs <= 2:
            narrative = """
            **🟢 Overall Quality Status: EXCELLENT**
            
            Our quality metrics demonstrate exceptional performance across all key areas. With zero feature rollout risks and no critical PRBs, the engineering team is maintaining high standards. The minimal P0/P1 production bugs indicate robust testing and deployment processes.
            
            **Key Strengths:**
            • Zero critical incidents and feature risks show strong operational discipline
            • Security posture is solid with minimal critical vulnerabilities
            • CI pipeline stability supports continuous delivery
            
            **Recommendations:**
            • Maintain current quality practices and processes
            • Continue focus on preventive measures and left-shift testing
            • Consider sharing best practices across teams
            """
        elif risks <= 2 and p0_p1_prbs <= 1 and p0_p1_bugs <= 5:
            narrative = """
            **Overall System Health: GOOD**
            
            Quality metrics are within acceptable ranges with minor areas for attention. The low number of critical issues suggests effective quality processes, though some vigilance is needed to prevent escalation.
            
            **Key Observations:**
            • Feature rollout risks are manageable but require monitoring
            • Critical bug count is reasonable for current development velocity
            • Security scanning is identifying issues before production impact
            
            **Recommendations:**
            • Focus on resolving existing P0/P1 issues quickly
            • Strengthen left-shift practices to catch issues earlier
            • Monitor trends closely to prevent quality degradation
            """
        else:
            narrative = """
            **🔴 Overall Quality Status: NEEDS ATTENTION**
            
            Several quality metrics indicate areas requiring immediate focus. The elevated number of critical issues across multiple categories suggests systemic challenges that need coordinated response.
            
            **Critical Areas:**
            • High feature rollout risks may impact delivery timelines
            • Multiple P0/P1 issues require immediate triage and resolution
            • Security vulnerabilities need urgent remediation
            
            **Immediate Actions Required:**
            • Implement daily standups focused on P0/P1 issue resolution
            • Increase code review rigor and testing coverage
            • Consider temporary feature freeze until critical issues are resolved
            """
        
        st.markdown(narrative)
        
        # Add coverage-specific insights
        if avg_coverage >= 80:
            coverage_insight = "✅ **Code Coverage**: Excellent coverage levels support quality objectives"
        elif avg_coverage >= 70:
            coverage_insight = "⚠️ **Code Coverage**: Approaching minimum threshold - focus on improving test coverage"
        else:
            coverage_insight = "🚨 **Code Coverage**: Below quality standards - immediate action needed to improve testing"
        
        st.markdown(coverage_insight)
        
        # Provide actionable insights based on total critical issues
        total_critical = risks + p0_p1_prbs + p0_p1_bugs + ci_p0_p1 + sec_p0_p1 + ls_p0_p1
        if total_critical > 5:
            st.write(f"⚡ **Focus area:** Resolve {total_critical} critical issues across all categories")
        elif total_critical > 0:
            st.write(f"📋 **Focus area:** Address {total_critical} remaining critical issues")
        else:
            st.write("🚀 **System health is strong** - maintain current practices!")
    
    def generate_new_report(self):
        """Generate a new quality report."""
        st.subheader("🔄 Generate New Report")
        
        with st.form("generate_report_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                risk_file = st.text_input("Risk File", value="risks.txt")
                deployment_file = st.text_input("Deployment CSV", value="deployments.csv")
                
            with col2:
                report_type = st.selectbox("Report Type", ["comprehensive", "compact"])
            
            augmentation_file = st.text_input("PRB Augmentation File (optional)", value="prb_augmentation.json")
            
            submit_button = st.form_submit_button("Generate Report")
            
            if submit_button:
                with st.spinner("Generating quality report..."):
                    try:
                        # Initialize data collector
                        collector = QualityDataCollector()
                        
                        # Collect data
                        if os.path.exists(risk_file):
                            collector.load_risk_data(risk_file)
                        
                        collector.extract_prb_data(
                            "https://gus.lightning.force.com/lightning/r/Report/00OEE000001TXjB2AW/view",
                            augmentation_file if os.path.exists(augmentation_file) else None
                        )
                        
                        collector.extract_critical_issues(
                            "https://gus.lightning.force.com/lightning/r/Report/00OEE0000014M4b2AE/view"
                        )
                        
                        if os.path.exists(deployment_file):
                            collector.load_deployment_data(deployment_file)
                        
                        # Initialize coverage metrics (legacy JSON format no longer required)
                        collector.load_coverage_metrics()
                        
                        # Archive data
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        archive_file = os.path.join(self.archive_dir, f"quality_data_archive_{timestamp}.json")
                        collector.save_archive_data(archive_file)
                        
                        # Generate report
                        report_generator = QualityReportGenerator()
                        report_content = report_generator.generate_report(collector.data, report_type)
                        
                        st.success(f"✅ Report generated successfully!")
                        st.info(f"📄 Data archived: {archive_file}")
                        
                        # Refresh the page to show new report
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error generating report: {e}")

# Report output directory names (must match quality_report_generator / run_report.sh)
REPORT_FOLDER_COMPONENTS = (
    'Engine', 'Store', 'SDD', 'Core App Efficiency',
)

# Shared production KPIs use this report for the selected week (fleet-wide view)
PRODUCTION_METRICS_SOURCE = 'Engine'

# GUS Salesforce report IDs for P0/P1 production bugs (metric card + detail link), keyed by report folder name
P0P1_PROD_BUGS_REPORT_ID_BY_COMPONENT: Dict[str, str] = {
    'Engine': '00OEE0000030kAn2AI',
    'Store': '00OEE0000030lLN2AY',
    'SDD': '00OEE0000030lOb2AI',
}

# GUS Salesforce report IDs for P0/P1 CI issues (metric card + detail links)
P0P1_CI_ISSUES_REPORT_ID_BY_COMPONENT: Dict[str, str] = {
    'Engine': '00OEE000002WjvJ2AS',
    'Store': '00OEE0000030lWf2AI',
    'SDD': '00OEE0000030lej2AA',
}

# GUS Salesforce report IDs for P0/P1 security bugs (metric card + detail links)
P0P1_SECURITY_BUGS_REPORT_ID_BY_COMPONENT: Dict[str, str] = {
    'Engine': '00OB0000002qWjvMAE',
    'Store': '00OEE0000030lwT2AQ',
    'SDD': '00OEE0000030lzh2AA',
}

# GUS Salesforce report IDs for P0/P1 left shift (metric card + detail links)
P0P1_LEFT_SHIFT_REPORT_ID_BY_COMPONENT: Dict[str, str] = {
    'Engine': '00OEE000002Wjld2AC',
    'Store': '00OEE0000030m7l2AA',
    'SDD': '00OEE0000030m9N2AQ',
}

# GUS Salesforce report IDs for P0/P1 ABS bugs (metric card + detail links)
P0P1_ABS_BUGS_REPORT_ID_BY_COMPONENT: Dict[str, str] = {
    'Engine': '00OEE000002bDht2AE',
    'Store': '00OEE0000030o6L2AQ',
    'SDD': '00OEE0000030o7x2AA',
}

# GUS Salesforce report IDs for All-time Bug Backlog (second dev metrics row)
ALL_TIME_BUG_BACKLOG_REPORT_ID_BY_COMPONENT: Dict[str, str] = {
    'Engine': '00OEE000002XRUv2AO',
    'Store': '00OEE0000030oHd2AI',
    'SDD': '00OEE0000030oKr2AI',
}

# GUS Salesforce report IDs for Backlog from PRB (second dev metrics row)
BACKLOG_FROM_PRB_REPORT_ID_BY_COMPONENT: Dict[str, str] = {
    'Engine': '00OEE000002ZnZN2A0',
    'Store': '00OEE0000030oCn2AI',
    'SDD': '00OEE0000030oEP2AY',
}


def gus_report_view_url(report_id: str) -> str:
    return f"https://gus.lightning.force.com/lightning/r/Report/{report_id}/view"


def p0p1_prod_bugs_report_url(tab_folder: Optional[str]) -> Optional[str]:
    if not tab_folder:
        return None
    rid = P0P1_PROD_BUGS_REPORT_ID_BY_COMPONENT.get(tab_folder)
    return gus_report_view_url(rid) if rid else None


def p0p1_prod_bugs_metric_href(tab_folder: Optional[str]) -> str:
    """Metric card link: GUS report when configured, else in-page anchor."""
    url = p0p1_prod_bugs_report_url(tab_folder)
    return url if url else '#production-bug-analysis'


def p0p1_ci_issues_report_url(tab_folder: Optional[str]) -> Optional[str]:
    if not tab_folder:
        return None
    rid = P0P1_CI_ISSUES_REPORT_ID_BY_COMPONENT.get(tab_folder)
    return gus_report_view_url(rid) if rid else None


def p0p1_ci_issues_metric_href(tab_folder: Optional[str]) -> str:
    """P0/P1 CI Issues metric card: GUS report when configured, else in-page anchor."""
    url = p0p1_ci_issues_report_url(tab_folder)
    return url if url else '#ci-issues-analysis'


def p0p1_security_bugs_report_url(tab_folder: Optional[str]) -> Optional[str]:
    if not tab_folder:
        return None
    rid = P0P1_SECURITY_BUGS_REPORT_ID_BY_COMPONENT.get(tab_folder)
    return gus_report_view_url(rid) if rid else None


def p0p1_security_bugs_metric_href(tab_folder: Optional[str]) -> str:
    """P0/P1 Security Bugs metric card: GUS report when configured, else in-page anchor."""
    url = p0p1_security_bugs_report_url(tab_folder)
    return url if url else '#security-analysis'


def p0p1_left_shift_report_url(tab_folder: Optional[str]) -> Optional[str]:
    if not tab_folder:
        return None
    rid = P0P1_LEFT_SHIFT_REPORT_ID_BY_COMPONENT.get(tab_folder)
    return gus_report_view_url(rid) if rid else None


def p0p1_left_shift_metric_href(tab_folder: Optional[str]) -> str:
    """P0/P1 Left Shift metric card: GUS report when configured, else in-page anchor."""
    url = p0p1_left_shift_report_url(tab_folder)
    return url if url else '#left-shift-bugs'


def p0p1_abs_bugs_report_url(tab_folder: Optional[str]) -> Optional[str]:
    if not tab_folder:
        return None
    rid = P0P1_ABS_BUGS_REPORT_ID_BY_COMPONENT.get(tab_folder)
    return gus_report_view_url(rid) if rid else None


def p0p1_abs_bugs_metric_href(tab_folder: Optional[str]) -> str:
    """P0/P1 ABS bugs metric card: GUS report when configured, else in-page anchor."""
    url = p0p1_abs_bugs_report_url(tab_folder)
    return url if url else '#abs-bugs'


# All-time backlog: 1 P0/P1 counts like 10 P2; P2/P3/P4 (and unknown) count as 1 each.
ALLTIME_BACKLOG_WEIGHT_P0P1 = 10
ALLTIME_BACKLOG_WEIGHT_MINOR = 1
# Bands on weighted score: <10 ≈ under 1× P0/P1 equiv; 10–50 ≈ old 1–5 P0/P1; >50 high
ALLTIME_BACKLOG_SCORE_GREEN_LT = 10
ALLTIME_BACKLOG_SCORE_YELLOW_MAX = 50


def alltime_backlog_weighted_score(items: List[Dict[str, Any]]) -> int:
    """Weighted backlog score: each P0/P1 = 10 points, each P2+ / unknown = 1 point."""
    total = 0
    for b in items:
        s = str(b.get("severity", "") or b.get("priority", "")).upper()
        if (
            "P0" in s
            or "P1" in s
            or "SEV0" in s
            or "SEV1" in s
        ):
            total += ALLTIME_BACKLOG_WEIGHT_P0P1
        else:
            total += ALLTIME_BACKLOG_WEIGHT_MINOR
    return total


def alltime_backlog_status_from_score(score: int) -> Tuple[str, str]:
    """Return (status label, metric-delta CSS class) for weighted all-time backlog score."""
    if score < ALLTIME_BACKLOG_SCORE_GREEN_LT:
        return "GREEN", "metric-delta-green"
    if score <= ALLTIME_BACKLOG_SCORE_YELLOW_MAX:
        return "YELLOW", "metric-delta-yellow"
    return "RED", "metric-delta-red"


def all_time_bug_backlog_report_url(tab_folder: Optional[str]) -> Optional[str]:
    if not tab_folder:
        return None
    rid = ALL_TIME_BUG_BACKLOG_REPORT_ID_BY_COMPONENT.get(tab_folder)
    return gus_report_view_url(rid) if rid else None


def all_time_bug_backlog_metric_href(tab_folder: Optional[str]) -> str:
    """All-time Bug Backlog card: GUS report when configured, else in-page anchor."""
    url = all_time_bug_backlog_report_url(tab_folder)
    return url if url else '#production-metrics'


def backlog_from_prb_report_url(tab_folder: Optional[str]) -> Optional[str]:
    if not tab_folder:
        return None
    rid = BACKLOG_FROM_PRB_REPORT_ID_BY_COMPONENT.get(tab_folder)
    return gus_report_view_url(rid) if rid else None


def backlog_from_prb_metric_href(tab_folder: Optional[str]) -> str:
    """Backlog from PRB card: GUS report when configured, else in-page anchor."""
    url = backlog_from_prb_report_url(tab_folder)
    return url if url else '#production-metrics'


def render_component_weekly_trends(
    dashboard: QualityReportDashboard,
    component: str,
    display_label: str,
) -> None:
    """Week-over-week KPI trends for this component (before Problem Reports Analysis)."""
    st.markdown("### 📊 Weekly Trends")
    st.caption(
        f"Week-over-week trends for **{display_label}** from archived reports under `{component}`."
    )
    component_reports = dashboard.get_component_reports(component)
    if len(component_reports) > 1:
        st.markdown("#### Week-over-Week KPI Trends")
        dashboard.create_weekly_trends(component_reports, chart_key_suffix=component)
    else:
        st.info(
            f"📈 Weekly trends need multiple {display_label} reports. "
            f"Generate more with `./run_report.sh <week> {component}`."
        )


def render_component_development_metrics(component: str, display_name: Optional[str] = None):
    """Development-only sections for a component (report folder name).

    display_name: optional label for headings (e.g. **Store** for the Store tab).
    """
    dashboard = QualityReportDashboard()
    label = display_name if display_name is not None else component

    selected_week_reports = getattr(st.session_state, 'selected_week_reports', {})
    selected_week = getattr(st.session_state, 'selected_week', None)

    if component not in selected_week_reports:
        st.subheader(f"📈 {label} Development Metrics")
        if selected_week:
            st.info(f"📅 Selected week: {selected_week}")
            st.warning(f"No {label} report available for the selected week.")
        else:
            st.info("No week selected.")

        component_reports = dashboard.get_component_reports(component)
        if component_reports:
            st.info(
                f"💡 {label} has {len(component_reports)} reports available. "
                f"Select a week from the sidebar that includes data for `{component}`."
            )
        else:
            st.info(
                f"💡 No reports found for `{component}`. "
                f"Use `./run_report.sh <week> {component}` to generate reports."
            )
        return

    try:
        report_to_use = selected_week_reports[component]
        with open(report_to_use['path'], 'r') as f:
            data = json.load(f)

        dashboard.llm_content = data.get('llm_content', {})

        eng_key = PRODUCTION_METRICS_SOURCE
        engine_data = None
        if eng_key in selected_week_reports:
            try:
                with open(selected_week_reports[eng_key]['path'], 'r') as ef:
                    engine_data = json.load(ef)
            except Exception:
                engine_data = None

        dashboard.render_production_kpi_row_hybrid(engine_data, data, component, level_label=label)
        dashboard.create_metrics_dashboard(
            data,
            component,
            kpi_scope='development',
            development_heading_suffix=label,
        )
        st.markdown("---")
        render_component_weekly_trends(dashboard, component, label)
        st.markdown("---")

        # PRB Analysis
        st.markdown('<h3 id="problem-reports-analysis">🚨 Problem Reports Analysis</h3>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: right; margin-top: -10px;"><a href="#production-metrics" style="font-size: 0.8rem; color: #666;">↑ Back to top</a></p>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1])
        with col1:
            dashboard.create_prb_analysis(data, f"_{component}")
        with col2:
            dashboard.create_prb_insights(data)
        
        # Bug Analysis
        st.markdown('<h3 id="production-bug-analysis">🐛 Production Bug Analysis</h3>', unsafe_allow_html=True)
        p0p1_gus = p0p1_prod_bugs_report_url(component)
        if p0p1_gus:
            st.markdown(
                f'<p style="margin: -4px 0 10px 0;"><a href="{p0p1_gus}" target="_blank" rel="noopener noreferrer">'
                f'📋 P0/P1 production bugs — GUS report</a></p>',
                unsafe_allow_html=True,
            )
        st.markdown('<p style="text-align: right; margin-top: -10px;"><a href="#production-metrics" style="font-size: 0.8rem; color: #666;">↑ Back to top</a></p>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1])
        with col1:
            dashboard.create_bug_severity_chart(data)
        with col2:
            dashboard.create_bug_insights(data)
        
        # Coverage Analysis
        st.markdown('<h3 id="code-coverage-analysis">📊 <a href="https://sonarqube.sfcq.buildndeliver-s.aws-esvc1-useast2.aws.sfdc.cl/component_measures?id=sayonara.sayonaradb.sdb&metric=uncovered_lines&view=list" target="_blank" style="color: inherit; text-decoration: none;">Code Coverage Analysis</a></h3>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: right; margin-top: -10px;"><a href="#production-metrics" style="font-size: 0.8rem; color: #666;">↑ Back to top</a></p>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1])
        with col1:
            dashboard.create_coverage_comparison_chart(data)
        with col2:
            dashboard.create_coverage_insights(data)
        
        # CI Issues
        st.markdown('<h3 id="ci-issues-analysis">🔧 CI Issues Analysis</h3>', unsafe_allow_html=True)
        ci_issues_gus = p0p1_ci_issues_report_url(component)
        if ci_issues_gus:
            st.markdown(
                f'<p style="margin: -4px 0 10px 0;"><a href="{ci_issues_gus}" target="_blank" rel="noopener noreferrer">'
                f'🔧 P0/P1 CI issues — GUS report</a></p>',
                unsafe_allow_html=True,
            )
        st.markdown('<p style="text-align: right; margin-top: -10px;"><a href="#production-metrics" style="font-size: 0.8rem; color: #666;">↑ Back to top</a></p>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1])
        with col1:
            dashboard.create_ci_issues_chart(data)
        with col2:
            if ci_issues_gus:
                st.markdown(f"#### 📊 [CI Issues Insights]({ci_issues_gus})")
            else:
                st.markdown("#### 📊 CI Issues Insights")
            ci_data = data.get('ci_issues', [])
            if ci_data:
                total_ci_issues = len(ci_data)
                # Calculate priority breakdown
                priority_counts = {}
                for issue in ci_data:
                    priority = issue.get('priority', 'Unknown')
                    priority_counts[priority] = priority_counts.get(priority, 0) + 1
                
                # Create priority breakdown string
                priority_breakdown = ", ".join([f"{p}:{count}" for p, count in sorted(priority_counts.items())])
                st.metric("Total CI Issues", f"{total_ci_issues} ({priority_breakdown})")
                
                teams = list(set(issue.get('team', 'Unknown') for issue in ci_data))
                st.metric("Teams Affected", len(teams))
                st.markdown("**Top Teams:**")
                team_counts = {}
                for issue in ci_data:
                    team = issue.get('team', 'Unknown')
                    team_counts[team] = team_counts.get(team, 0) + 1
                for team, count in sorted(team_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
                    st.write(f"• {team}: {count} issues")
            else:
                st.info("No CI issues data available")
        
        # Security Analysis
        st.markdown("---")
        st.markdown('<h3 id="security-analysis">🔒 Security Bugs</h3>', unsafe_allow_html=True)
        security_gus = p0p1_security_bugs_report_url(component)
        if security_gus:
            st.markdown(
                f'<p style="margin: -4px 0 10px 0;"><a href="{security_gus}" target="_blank" rel="noopener noreferrer">'
                f'🔒 P0/P1 security bugs — GUS report</a></p>',
                unsafe_allow_html=True,
            )
        st.markdown('<p style="text-align: right; margin-top: -10px;"><a href="#production-metrics" style="font-size: 0.8rem; color: #666;">↑ Back to top</a></p>', unsafe_allow_html=True)
        st.markdown("*Source: Coverity and 3PP Scan*")
        col1, col2 = st.columns([1, 1])
        with col1:
            dashboard.create_security_bugs_chart(data)
        with col2:
            st.markdown("#### 🛡️ Security Analysis")
            security_data = data.get('security_issues', [])
            if security_data:
                total_security_bugs = len(security_data)
                # Calculate priority breakdown
                priority_counts = {}
                for bug in security_data:
                    priority = bug.get('priority', 'Unknown')
                    priority_counts[priority] = priority_counts.get(priority, 0) + 1
                
                # Create priority breakdown string
                priority_breakdown = ", ".join([f"{p}:{count}" for p, count in sorted(priority_counts.items())])
                st.metric("Total Security Bugs", f"{total_security_bugs} ({priority_breakdown})")
                
                teams = list(set(bug.get('team', bug.get('component', 'Unknown')) for bug in security_data))
                st.metric("Teams Affected", len(teams))
                st.markdown("**Security Bug Types:**")
                bug_types = {}
                for bug in security_data:
                    subject = bug.get('subject', '')
                    if 'RESOURCE_LEAK' in subject:
                        bug_types['Resource Leak'] = bug_types.get('Resource Leak', 0) + 1
                    elif 'OVERRUN' in subject:
                        bug_types['Buffer Overrun'] = bug_types.get('Buffer Overrun', 0) + 1
                    elif 'USE_AFTER_FREE' in subject:
                        bug_types['Use After Free'] = bug_types.get('Use After Free', 0) + 1
                    else:
                        bug_types['Other'] = bug_types.get('Other', 0) + 1
                for bug_type, count in sorted(bug_types.items(), key=lambda x: x[1], reverse=True)[:3]:
                    st.write(f"• {bug_type}: {count}")
            else:
                st.info("No security bugs data available")

        # Left Shift Analysis
        st.markdown("---")
        st.markdown('<h3 id="left-shift-bugs">⬅️ Left Shift Bugs</h3>', unsafe_allow_html=True)
        left_shift_gus = p0p1_left_shift_report_url(component)
        if left_shift_gus:
            st.markdown(
                f'<p style="margin: -4px 0 10px 0;"><a href="{left_shift_gus}" target="_blank" rel="noopener noreferrer">'
                f'⬅️ P0/P1 left shift — GUS report</a></p>',
                unsafe_allow_html=True,
            )
        st.markdown('<p style="text-align: right; margin-top: -10px;"><a href="#production-metrics" style="font-size: 0.8rem; color: #666;">↑ Back to top</a></p>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1])
        with col1:
            dashboard.create_leftshift_bugs_chart(data)
        with col2:
            if left_shift_gus:
                st.markdown(f"#### 📈 [Left Shift Insights]({left_shift_gus})")
            else:
                st.markdown("#### 📈 Left Shift Insights")
            leftshift_data = data.get('leftshift_issues', [])
            if leftshift_data:
                total_leftshift_bugs = len(leftshift_data)
                # Calculate priority breakdown
                priority_counts = {}
                for bug in leftshift_data:
                    priority = bug.get('priority', 'Unknown')
                    priority_counts[priority] = priority_counts.get(priority, 0) + 1
                
                # Create priority breakdown string
                priority_breakdown = ", ".join([f"{p}:{count}" for p, count in sorted(priority_counts.items())])
                st.metric("Total Left Shift Bugs", f"{total_leftshift_bugs} ({priority_breakdown})")
                
                teams = list(set(bug.get('team', 'Unknown') for bug in leftshift_data))
                st.metric("Teams Affected", len(teams))
                st.markdown("**Recent Activity:**")
                for bug in leftshift_data[:3]:  # Show top 3 recent bugs
                    subject = bug.get('subject', 'Unknown Issue')[:50] + "..."
                    team = bug.get('team', 'Unknown Team')
                    st.write(f"• {team}: {subject}")
            else:
                st.info("No left shift bugs data available")

        # ABS bugs
        st.markdown("---")
        st.markdown('<h3 id="abs-bugs">🔷 ABS Bugs</h3>', unsafe_allow_html=True)
        abs_gus = p0p1_abs_bugs_report_url(component)
        if abs_gus:
            st.markdown(
                f'<p style="margin: -4px 0 10px 0;"><a href="{abs_gus}" target="_blank" rel="noopener noreferrer">'
                f'🔷 P0/P1 ABS bugs — GUS report</a></p>',
                unsafe_allow_html=True,
            )
        st.markdown('<p style="text-align: right; margin-top: -10px;"><a href="#production-metrics" style="font-size: 0.8rem; color: #666;">↑ Back to top</a></p>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1])
        with col1:
            dashboard.create_abs_bugs_chart(data)
        with col2:
            if abs_gus:
                st.markdown(f"#### 📈 [ABS Insights]({abs_gus})")
            else:
                st.markdown("#### 📈 ABS Insights")
            abs_list = data.get('abs_issues', [])
            if abs_list:
                total_abs = len(abs_list)
                priority_counts = {}
                for bug in abs_list:
                    priority = bug.get('priority', 'Unknown')
                    priority_counts[priority] = priority_counts.get(priority, 0) + 1
                priority_breakdown = ", ".join([f"{p}:{count}" for p, count in sorted(priority_counts.items())])
                st.metric("Total ABS Bugs", f"{total_abs} ({priority_breakdown})")
                teams = list(set(bug.get('team', 'Unknown') for bug in abs_list))
                st.metric("Teams Affected", len(teams))
                st.markdown("**Recent activity:**")
                for bug in abs_list[:3]:
                    subject = bug.get('subject', 'Unknown Issue')[:50] + "..."
                    team = bug.get('team', 'Unknown Team')
                    st.write(f"• {team}: {subject}")
            else:
                st.info("No ABS bugs data available")

        # Deployment Analysis
        st.markdown("---")
        st.markdown('<h3 id="deployment-analysis">🚀 <a href="https://bdmpresto-superset-server.sfproxy.uip.aws-esvc1-useast2.aws.sfdc.cl/superset/sqllab?savedQueryId=25468" target="_blank">Deployment Analysis</a></h3>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: right; margin-top: -10px;"><a href="#production-metrics" style="font-size: 0.8rem; color: #666;">↑ Back to top</a></p>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1])
        with col1:
            dashboard.create_deployment_stacked_bar(data)
        with col2:
            dashboard.create_version_pie_chart(data)
        
        # Add deployment insights
        dashboard.create_deployment_insights(data)

        # Risk Assessment
        st.markdown("---")
        st.markdown('<h3 id="risk-assessment">🎯 Risk Assessment</h3>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: right; margin-top: -10px;"><a href="#production-metrics" style="font-size: 0.8rem; color: #666;">↑ Back to top</a></p>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1])
        with col1:
            dashboard.create_risk_chart(data, f"_{component}")
        with col2:
            dashboard.create_risk_insights(data)

        # Code Changes Analysis
        st.markdown("---")
        st.markdown('<h3 id="code-changes-analysis">📊 Code Changes Analysis</h3>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: right; margin-top: -10px;"><a href="#production-metrics" style="font-size: 0.8rem; color: #666;">↑ Back to top</a></p>', unsafe_allow_html=True)
        dashboard.create_code_changes_analysis(data, component=component)

        # Trend Analysis
        st.markdown("---")
        st.markdown("### 📈 Quality Trends")
        col1, col2 = st.columns([1, 1])
        with col1:
            dashboard.create_trend_analysis(data)
        with col2:
            dashboard.create_trend_insights(data)
            
    except Exception as e:
        st.error(f"Error loading {label} data: {e}")


def main():
    """Main Streamlit application."""
    
    # Display professional title banner - stretchable across full width
    st.markdown("""
    <style>
    .title-banner {
        width: 100%;
        margin-bottom: 20px;
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .fallback-title {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        text-align: center;
        padding: 30px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .fallback-title h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: bold;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        letter-spacing: 2px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Display video banner with title overlay
    if False and os.path.exists("title.mp4"):
        # CSS for video banner with text overlay
        st.markdown("""
        <style>
        .video-banner-container {
            position: relative;
            width: 100%;
            margin-bottom: 20px;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        .video-title-overlay {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 10;
            text-align: center;
            pointer-events: none;
            width: 100%;
        }
        .video-title-text {
            color: white;
            font-size: 3.2rem;
            margin: 0;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-weight: 700;
            text-shadow: 3px 3px 8px rgba(0,0,0,0.8), 1px 1px 3px rgba(0,0,0,0.9);
            letter-spacing: 0.02em;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Create container with video and overlay
        st.markdown('<div class="video-banner-container">', unsafe_allow_html=True)
        
        # Display the video
        st.video("title.mp4", autoplay=True, loop=True, muted=True)
        
        # Add title overlay
        st.markdown("""
        <div class="video-title-overlay">
            <h1 class="video-title-text">SDB Service Quality Dashboard</h1>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
    elif os.path.exists("SDB_galaxy_banner.jpg"):
        st.image("SDB_galaxy_banner.jpg", width="stretch")
    elif os.path.exists("assets/SDB_galaxy_banner.jpg"):
        st.image("assets/SDB_galaxy_banner.jpg", width="stretch")
    else:
        # Dynamic banner will be displayed after report selection
        pass
    
    st.markdown("---")
    
    dashboard = QualityReportDashboard()
    
    # Sidebar for report selection (MUST run before component tabs)
    components = list(REPORT_FOLDER_COMPONENTS)
    st.sidebar.title("📋 Quality Reports")

    # Get all reports from all components and group by week
    all_reports = []

    for component in components:
        component_reports = dashboard.get_component_reports(component)
        for report in component_reports:
            report['component'] = component
            all_reports.append(report)
    
    # Group reports by week (using date as key)
    weeks = {}
    for report in all_reports:
        # Use date as week key (YYYY-MM-DD format)
        week_key = report['timestamp'].strftime('%Y-%m-%d')
        if week_key not in weeks:
            weeks[week_key] = {
                'date': report['timestamp'],
                'reports': {}
            }
        weeks[week_key]['reports'][report['component']] = report
    
    # Sort weeks by date (newest first)
    sorted_weeks = sorted(weeks.items(), key=lambda x: x[1]['date'], reverse=True)
    
    if sorted_weeks:
        st.sidebar.markdown("### 📅 Reports by Week")
        
        # Use session state to track selected week
        if 'selected_week' not in st.session_state:
            st.session_state.selected_week = sorted_weeks[0][0] if sorted_weeks else None
        
        # Initialize selected_week_reports if not exists
        if 'selected_week_reports' not in st.session_state:
            st.session_state.selected_week_reports = {}
        
        selected_week_key = None
        
        # Show weeks
        for i, (week_key, week_data) in enumerate(sorted_weeks[:15]):  # Show latest 15
            is_selected = st.session_state.selected_week == week_key
            
            # Create display name with just the date
            display_name = week_data['date'].strftime('%m/%d %H:%M')
            component_count = len(week_data['reports'])
            
            if st.sidebar.button(
                f"{'🟢' if is_selected else '📄'} {display_name}",
                key=f"week_{i}",
                help=f"Week from {week_data['date'].strftime('%Y-%m-%d %H:%M')} ({component_count} components)",
                type="primary" if is_selected else "secondary"
            ):
                st.session_state.selected_week = week_key
                selected_week_key = week_key
        
        # Always update selected week's reports to ensure consistency
        if st.session_state.selected_week and st.session_state.selected_week in weeks:
            st.session_state.selected_week_reports = weeks[st.session_state.selected_week]['reports']
        else:
            st.session_state.selected_week_reports = {}
    else:
        st.sidebar.warning("📭 No reports found")
        st.session_state.selected_week = None
        st.session_state.selected_week_reports = {}
    
    st.sidebar.markdown("---")
    
    # Show report counts (aligned with four dashboard tabs)
    st.sidebar.markdown("### 📊 Available Reports")
    eng = dashboard.get_component_reports('Engine')
    st.sidebar.write(f"🔧 **Engine**: {len(eng)} reports" if eng else "🔧 Engine: No reports")

    store_reports = dashboard.get_component_reports('Store')
    st.sidebar.write(f"📦 **Store**: {len(store_reports)} reports" if store_reports else "📦 Store: No reports")

    sdd_reports = dashboard.get_component_reports('SDD')
    st.sidebar.write(f"💾 **SDD**: {len(sdd_reports)} reports" if sdd_reports else "💾 SDD: No reports")

    core = dashboard.get_component_reports('Core App Efficiency')
    core_label = "Core Optimizer and SFSQL"
    if core:
        st.sidebar.write(f"⚡ **{core_label}**: {len(core)} reports")
    else:
        st.sidebar.write(f"⚡ {core_label}: No reports")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔄 Actions")
    st.sidebar.info("📊 Select a week above, then open a dashboard tab to view data")
    st.sidebar.info(
        "💡 Generate reports with `./run_report.sh <week> <component>` "
        "(`Engine`, `Store`, `SDD`, `Core App Efficiency`)."
    )
    st.sidebar.info(
        "🏭 **Production metrics:** **Fleet-wide** row (Engine) plus a second row named for the open tab "
        "(e.g. **Engine-level**, **Store-level**): rollout risk & P0/P1 prod bugs from that tab’s report."
    )

    # Display dynamic banner with timestamp information
    dashboard.display_banner_with_timestamp(st.session_state.selected_week_reports)

    main_tab_labels = [
        "🔧 Engine",
        "📦 Store",
        "💾 SDD",
        "⚡ Core Optimizer and SFSQL",
    ]
    main_tabs = st.tabs(main_tab_labels)

    with main_tabs[0]:
        render_component_development_metrics("Engine")
    with main_tabs[1]:
        render_component_development_metrics("Store", display_name="Store")
    with main_tabs[2]:
        render_component_development_metrics("SDD", display_name="SDD")
    with main_tabs[3]:
        render_component_development_metrics(
            "Core App Efficiency",
            display_name="Core Optimizer and SFSQL",
        )

    # KPI Legend Section
    st.markdown("---")
    st.markdown("### 📊 KPI Color Definitions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### 🐛 **Bug Metrics (Production, CI, Security, Left Shift, ABS)**
        - **🟢 GREEN**: Low risk - minimal critical issues
        - **🟡 YELLOW**: Moderate risk - standard review needed  
        - **🔴 RED**: High risk - extra scrutiny required
        
        **Scoring**: P0/P1 bugs = 4 points, P2+ bugs = 1 point
        - **Production Bugs**: Green ≤16, Yellow 17-32, Red >32
        - **CI Issues**: Green ≤25, Yellow 26-50, Red >50
        - **Security Issues**: Green ≤16, Yellow 17-32, Red >32
        - **Left Shift**: Green ≤25, Yellow 26-50, Red >50
        - **ABS Bugs**: Green ≤25, Yellow 26-50, Red >50
        """)
    
    with col2:
        st.markdown("""
        #### 🚨 **PRB Metrics**
        - **🟢 GREEN**: ≤2 critical PRBs
        - **🟡 ELEVATED**: 3-4 critical PRBs
        - **🔴 HIGH RISK**: >4 critical PRBs or any P0 PRBs
        
        #### 📈 **Code Changes**
        - **🟢 GREEN**: <10 commits & <3,000 lines (Stable)
        - **🟡 YELLOW**: <25 commits & <8,000 lines (Moderate)
        - **🔴 RED**: ≥25 commits or ≥8,000 lines (High Activity)
        
        #### 🎯 **Feature Rollout Risk**
        - Count of features with Red/At Risk/Critical status
        
        #### 🐛 **All-time Bug Backlog**
        - **Weighted score**: 10 points per P0/P1 bug, 1 point per P2+ (1 P0/P1 ≈ 10 P2)
        - **🟢 GREEN**: score under 10 · **🟡 YELLOW**: 10–50 · **🔴 RED**: over 50
        
        #### 📋 **Backlog from PRB**
        - **🔘 PENDING**: PRB-related followup items
        - Coming soon - will track post-PRB action items
        """)
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray; font-size: 0.8em;'>
        Quality Reports Dashboard | Built with Streamlit | Powered by Salesforce LLM Gateway
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()

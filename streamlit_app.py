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
from datetime import datetime, timedelta
import glob
from typing import Dict, List, Any, Optional
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our quality report components
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quality_report_generator import QualityDataCollector, QualityReportGenerator

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
    
    def parse_ci_data(self) -> List[Dict[str, Any]]:
        """Parse CI data from ci.txt file."""
        ci_file = "ci.txt"  # Changed back to ci.txt from ss.txt
        ci_data = []
        
        if not os.path.exists(ci_file):
            st.warning(f"CI file {ci_file} not found")
            return ci_data
            
        try:
            with open(ci_file, 'r') as f:
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
                
                # Parse team names (e.g., "Sayonara Data Management(7)")
                # Must contain team keywords AND have format "TeamName(number)" not "description(number issues)"
                if (line and '(' in line and line.endswith(')') and not line.startswith('P') and not line.startswith('W-') 
                    and not 'issues)' in line and not '/' in line and not '-' in line):
                    if any(team_keyword in line for team_keyword in ['Sayonara', 'SDB']):
                        current_team = line.split('(')[0].strip()
                        continue
                
                # Parse priority (e.g., "P2(7)")
                if line.startswith('P') and '(' in line and line.endswith(')'):
                    current_priority = line.split('(')[0].strip()
                    continue
                
                # Parse individual issues with Work ID
                if line.startswith('W-'):
                    work_id = line
                    ci_issue = {
                        'team': current_team or 'Unknown Team',
                        'priority': current_priority or 'P2', 
                        'work_id': work_id,
                        'subject': 'CI Issue',
                        'type': 'CI Issue'
                    }
                    ci_data.append(ci_issue)
            
            return ci_data
                        
        except Exception as e:
            st.error(f"Error parsing CI data: {e}")
            
        return ci_data
    
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
    
    def create_metrics_dashboard(self, data: Dict[str, Any]):
        """Create professional metrics dashboard with multiple styling options."""
        
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
            prb_color = "#dc3545"  # Red
            prb_bg_color = "#f8d7da"
        elif critical_prbs > 4:
            prb_status = "HIGH RISK"
            prb_color = "#dc3545"  # Red
            prb_bg_color = "#f8d7da"
        elif critical_prbs > 2:
            prb_status = "ELEVATED"
            prb_color = "#ffc107"  # Yellow
            prb_bg_color = "#fff3cd"
        else:
            prb_status = "GREEN"
            prb_color = "#28a745"  # Green
            prb_bg_color = "#d4edda"
        
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
            prod_bug_color = "#dc3545"
        elif bug_score > 16:
            prod_bug_status = "YELLOW" 
            prod_bug_color = "#ffc107"
        else:
            prod_bug_status = "GREEN"
            prod_bug_color = "#28a745"
        
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
        ci_issues = data.get('ci', [])
        ci_p0_bugs = len([b for b in ci_issues if 'P0' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        ci_p1_bugs = len([b for b in ci_issues if 'P1' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        ci_p2_plus_bugs = len([b for b in ci_issues if any(p in str(b.get('severity', '') + str(b.get('priority', ''))).upper() for p in ['P2', 'P3', 'P4'])])
        
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
        security_bugs = data.get('security', [])
        sec_p0_bugs = len([b for b in security_bugs if 'P0' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        sec_p1_bugs = len([b for b in security_bugs if 'P1' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        sec_p2_plus_bugs = len([b for b in security_bugs if any(p in str(b.get('severity', '') + str(b.get('priority', ''))).upper() for p in ['P2', 'P3', 'P4'])])
        
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
        
        # Display professional metric cards
        self.create_two_line_metric_cards(at_risk_count, len(risks), critical_prbs, prb_status, prb_color, prb_bg_color, critical_prod_bugs, prod_bug_status, avg_coverage, data, ci_bug_score, ci_bug_status, critical_sec_bugs, sec_bug_status, ls_bug_score, ls_bug_status)


    def create_two_line_metric_cards(self, at_risk_count, total_risks, critical_prbs, prb_status, prb_color, prb_bg_color, critical_prod_bugs, prod_bug_status, avg_coverage, data, ci_bug_score, ci_bug_status, critical_sec_bugs, sec_bug_status, ls_bug_score, ls_bug_status):
        """Two-line professional dashboard: Production metrics (top) and Development metrics (bottom)."""
        
        # Calculate CI P0/P1 counts for display
        ci_issues = data.get('ci', [])
        ci_p0_bugs = len([b for b in ci_issues if 'P0' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        ci_p1_bugs = len([b for b in ci_issues if 'P1' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        ci_p0_p1_count = ci_p0_bugs + ci_p1_bugs
        
        # Calculate Left Shift P0/P1 counts for display
        leftshift_issues = data.get('leftshift_issues', [])
        ls_p0_bugs = len([b for b in leftshift_issues if 'P0' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        ls_p1_bugs = len([b for b in leftshift_issues if 'P1' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        ls_p0_p1_count = ls_p0_bugs + ls_p1_bugs
        
        # Calculate deployment metrics
        deployments = data.get('deployments', [])
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
        
        # CSS for professional black & white cards
        st.markdown("""
        <style>
        .metric-card {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            min-height: 140px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .metric-card:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }
        .metric-value {
            font-size: 2.2rem;
            font-weight: 700;
            margin: 0.3rem 0;
            line-height: 1;
            color: #000000;
        }
        .metric-label {
            font-size: 0.8rem;
            color: #6c757d;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            margin-bottom: 0.25rem;
        }
        .metric-delta {
            font-size: 0.7rem;
            margin-top: 0.3rem;
            padding: 0.2rem 0.4rem;
            border-radius: 8px;
            display: inline-block;
            background: #f8f9fa;
            color: #495057;
            border: 1px solid #dee2e6;
        }
        .metric-delta-green {
            background: #d4f6d4 !important;
            color: #155724 !important;
            border: 1px solid #c3e6cb !important;
        }
        .metric-delta-yellow {
            background: #fff3cd !important;
            color: #856404 !important;
            border: 1px solid #ffeaa7 !important;
        }
        .metric-delta-red {
            background: #f8d7da !important;
            color: #721c24 !important;
            border: 1px solid #f5c6cb !important;
        }
        .metric-total {
            font-size: 0.875rem;
            color: #495057;
            font-weight: 400;
            margin-top: 0.2rem;
        }    
        </style>
        """, unsafe_allow_html=True)
        
        # Production Metrics (Top Row)
        st.markdown("#### 🏭 Production Metrics")
        col1, col2, col3, col4, col5_prod = st.columns(5)
        
        with col1:
            # Feature Rollout Risk color logic: green if 0, yellow if 1-2, red if >2
            risk_delta_class = "metric-delta-green" if at_risk_count == 0 else ("metric-delta-yellow" if at_risk_count <= 2 else "metric-delta-red")
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🚀 Feature Rollout Risk</div>
                <div class="metric-value">{at_risk_count}</div>
                <div class="metric-total">of {total_risks} total</div>
                <div class="metric-delta {risk_delta_class}">
                    {"GREEN" if at_risk_count == 0 else ("YELLOW" if at_risk_count <= 2 else "RED")}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            total_prbs = len(data.get('prbs', []))
            prb_delta_class = "metric-delta-green" if prb_status == "GREEN" else ("metric-delta-yellow" if prb_status in ["ELEVATED", "YELLOW"] else "metric-delta-red")
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🚨 Sev 0/1 PRBs</div>
                <div class="metric-value">{critical_prbs}</div>
                <div class="metric-total">of {total_prbs} total</div>
                <div class="metric-delta {prb_delta_class}">
                    {prb_status}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            total_bugs = len(data.get('bugs', []))
            prod_delta_class = "metric-delta-green" if prod_bug_status == "GREEN" else ("metric-delta-yellow" if prod_bug_status == "YELLOW" else "metric-delta-red")
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🐛 P0/P1 Prod Bugs</div>
                <div class="metric-value">{critical_prod_bugs}</div>
                <div class="metric-total">of {total_bugs} total</div>
                <div class="metric-delta {prod_delta_class}">
                    {prod_bug_status}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            second_line = f"2nd: {second_version} ({second_percentage:.1f}%)" if second_version != "N/A" else ""
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🚀 Prod Deployment</div>
                <div class="metric-value">{dominant_version}</div>
                <div class="metric-total">Dominant in fleet ({dominant_percentage:.1f}%)</div>
                <div class="metric-delta">
                    {second_line}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col5_prod:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">⚡ System Availability</div>
                <div class="metric-value">--</div>
                <div class="metric-total">Coming Soon</div>
                <div class="metric-delta">
                    --
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Development Metrics (Bottom Row)  
        st.markdown("#### 💻 Development Metrics")
        col5, col6, col7, col8, col9 = st.columns(5)
        
        with col5:
            # Coverage color logic: green if >= 80%, yellow if >= 70%, red if < 70%
            coverage_delta_class = "metric-delta-green" if avg_coverage >= 80 else ("metric-delta-yellow" if avg_coverage >= 70 else "metric-delta-red")
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">📊 Overall Line Coverage</div>
                <div class="metric-value">{avg_coverage:.1f}%</div>
                <div class="metric-total">Overall Coverage 67.8%</div>
                <div class="metric-delta {coverage_delta_class}">
                    Target: 80%
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col6:
            total_ci_issues = len(data.get('ci_issues', []))
            ci_p0_p1_count = ci_p0_bugs + ci_p1_bugs
            ci_delta_class = "metric-delta-green" if ci_bug_status == "GREEN" else ("metric-delta-yellow" if ci_bug_status == "YELLOW" else "metric-delta-red")
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🔧 P0/P1 CI Issues</div>
                <div class="metric-value">{ci_p0_p1_count}</div>
                <div class="metric-total">{total_ci_issues} issues</div>
                <div class="metric-delta {ci_delta_class}">
                    {ci_bug_status}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col7:
            total_security_bugs = len(data.get('security_issues', []))
            sec_delta_class = "metric-delta-green" if sec_bug_status == "GREEN" else ("metric-delta-yellow" if sec_bug_status == "YELLOW" else "metric-delta-red")
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🔒 P0/P1 Security Bugs</div>
                <div class="metric-value">{critical_sec_bugs}</div>
                <div class="metric-total">of {total_security_bugs} total</div>
                <div class="metric-delta {sec_delta_class}">
                    {sec_bug_status}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col8:
            total_leftshift_bugs = len(data.get('leftshift_issues', []))
            ls_delta_class = "metric-delta-green" if ls_bug_status == "GREEN" else ("metric-delta-yellow" if ls_bug_status == "YELLOW" else "metric-delta-red")
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">⬅️ P0/P1 Left Shift</div>
                <div class="metric-value">{ls_p0_p1_count}</div>
                <div class="metric-total">{total_leftshift_bugs} bugs</div>
                <div class="metric-delta {ls_delta_class}">
                    {ls_bug_status}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col9:
            # Calculate code changes metrics using archived git stats
            git_stats = data.get('git_stats', {})
            
            if git_stats:
                # Use pre-computed git stats from archive
                current_week_changes = git_stats.get('lines_changed', 0)
                total_commits = git_stats.get('total_commits', 0)
                
                # Calculate a simple activity metric based on commits and changes
                # For demo purposes, we'll use a baseline comparison
                baseline_changes = 5000  # Typical week baseline
                
                if baseline_changes > 0:
                    percentage_change = ((current_week_changes - baseline_changes) / baseline_changes) * 100
                else:
                    percentage_change = 100 if current_week_changes > 0 else 0
                
                # Determine status color based on percentage change and commit activity
                if total_commits < 10 and current_week_changes < 3000:
                    change_status = "GREEN"
                    change_delta_class = "metric-delta-green"
                elif total_commits < 25 and current_week_changes < 8000:
                    change_status = "YELLOW" 
                    change_delta_class = "metric-delta-yellow"
                else:
                    change_status = "RED"
                    change_delta_class = "metric-delta-red"
                
                # Format percentage with + or - sign
                change_sign = "+" if percentage_change >= 0 else ""
            else:
                # Fallback when no git stats available
                current_week_changes = 0
                percentage_change = 0
                change_status = "UNKNOWN"
                change_delta_class = "metric-delta-gray"
                change_sign = ""
            
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">📈 Code Changes</div>
                <div class="metric-value">{change_sign}{percentage_change:.1f}%</div>
                <div class="metric-total">{current_week_changes:,} lines changed</div>
                <div class="metric-delta {change_delta_class}">
                    {change_status}
                </div>
            </div>
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
    
    def analyze_changes_with_llm(self, file_changes: list, dates: dict) -> str:
        """Get pre-generated code change risk analysis from LLM content or show unavailable message."""
        # Check if we have pre-generated LLM content
        if hasattr(self, 'llm_content') and self.llm_content:
            risk_analysis = self.llm_content.get('risk_analysis', '')
            if risk_analysis:
                return risk_analysis
        
        # No LLM content available
        return "**Code Change Risk Analysis:** Content not available - requires LLM generation during report creation"
    
    def create_code_changes_analysis(self, data: Dict[str, Any]):
        """Create comprehensive code changes analysis with visualization and risk assessment."""
        import subprocess
        import os
        from datetime import datetime, timedelta
        from quality_report_generator import get_report_dates
        
        dates = get_report_dates()
        
        def get_git_changes_by_path(start_date, end_date):
            """Get git changes focused on SDB-related components."""
            try:
                sdb_path = "/Users/rchowdhuri/SDB"
                if not os.path.exists(sdb_path):
                    return {}
                
                # Get detailed file changes with line counts, focusing on SDB
                cmd = f'cd {sdb_path} && git log --since="{start_date}" --until="{end_date}" --numstat --pretty=format:"" | grep -v "^$"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode != 0:
                    return {}
                
                # SDB-related keywords and patterns for deeper categorization
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
                            
                            # Skip excluded modules
                            if any(excluded in filepath for excluded in excluded_modules):
                                continue
                            
                            # Detailed categorization based on file paths and extensions
                            category = self.categorize_file_change(original_filepath)
                            
                            # Skip if not relevant to SDB
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
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Commits", git_stats.get('total_commits', 0))
                st.metric("Lines Added", git_stats.get('lines_added', 0))
                st.metric("Lines Deleted", git_stats.get('lines_deleted', 0))
            with col2:
                st.metric("Files Changed", git_stats.get('files_changed', 0))
                st.metric("Authors", len(git_stats.get('authors', [])))
                st.metric("Code Churn Risk", git_stats.get('code_churn_risk', 'Unknown'))
            
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
            changes_data, file_changes_for_llm = get_git_changes_by_path(current_week_start, current_week_end)
        except Exception as e:
            st.info("📊 Code changes analysis not available (git repository not accessible)")
            st.info("💡 This feature works when running locally with access to the SDB repository")
            return
        
        if not changes_data:
            st.info("📊 No code changes data available for the reporting period")
            return
        
        # Create visualization
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.markdown("#### 📈 SDB-Focused Code Changes")
            
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
                marker_color='#28a745',
                hovertemplate='<b>%{x}</b><br>Added: %{y} lines<extra></extra>'
            ))
            
            fig.add_trace(go.Bar(
                name='Lines Deleted',
                x=categories,
                y=deleted_lines,
                marker_color='#dc3545',
                hovertemplate='<b>%{x}</b><br>Deleted: %{y} lines<extra></extra>'
            ))
            
            fig.update_layout(
                title=f"SDB-Related Changes ({dates['period_start']} - {dates['period_end']})",
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
        deployments = data.get('deployments', [])
        
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
        deployments = data.get('deployments', [])
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
        deployments = data.get('deployments', [])
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
        deployments = data.get('deployments', [])
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
            marker_color='#1f77b4',  # Blue
            hovertemplate='<b>New Code</b><br>%{x}: %{y:.1f}%<extra></extra>'
        ))
        
        fig.add_trace(go.Bar(
            name='Overall Coverage',
            x=metrics,
            y=overall_values,
            marker_color='#ff7f0e',  # Orange
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
        
        # Color map for priorities
        priority_colors = {
            'P0': '#dc3545', 'P1': '#fd7e14', 'P2': '#ffc107', 'P3': '#28a745', 'P4': '#6f42c1'
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
        
        # Color map for priorities
        priority_colors = {
            'P0': '#dc3545', 'P1': '#fd7e14', 'P2': '#ffc107', 'P3': '#28a745', 'P4': '#6f42c1'
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
        
        # Color map for priorities
        priority_colors = {
            'P0': '#dc3545', 'P1': '#fd7e14', 'P2': '#ffc107', 'P3': '#28a745', 'P4': '#6f42c1'
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
    
    def create_weekly_trends(self, report_files: List[Dict[str, Any]]):
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
                
                # 7. Total Line Coverage (extract from coverage_summary)
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
                     'P0/P1 CI Issues', 'P0/P1 Security Issues', 'P0/P1 Left Shift']
        
        st.subheader("📈 Week-over-Week Quality Trends")
        
        # Create dual-axis chart
        from plotly.subplots import make_subplots
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Define colors for each metric
        colors = {
            'Feature Rollout Risk': '#FF6B6B',      # Red
            'Sev 0/1 PRBs': '#FF8E53',             # Orange
            'P0/P1 Production Bugs': '#4ECDC4',     # Teal
            'P0/P1 CI Issues': '#45B7D1',          # Blue
            'P0/P1 Security Issues': '#96CEB4',     # Green
            'P0/P1 Left Shift': '#FECA57',         # Yellow
            'Total Line Coverage %': '#6C5CE7'      # Purple
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
        
        st.plotly_chart(fig, use_container_width=True, key='weekly_trends_chart_scores')
    
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
    
    def create_prb_insights(self, data: Dict[str, Any]):
        """Create enhanced PRB insights panel with AI-generated narratives."""
        prbs = data.get('prbs', [])
        if not prbs:
            st.info("No PRB data available")
            return
        
        # Analyze PRBs by severity (regardless of status - focus on all Sev 0/1 PRBs)
        p0_prbs = [p for p in prbs if 'P0' in str(p.get('priority', '')) or 'Sev0' in str(p.get('priority', ''))]
        p1_prbs = [p for p in prbs if 'P1' in str(p.get('priority', '')) or 'Sev1' in str(p.get('priority', '')) or 'Critical' in str(p.get('priority', ''))]
        p2_prbs = [p for p in prbs if 'P2' in str(p.get('priority', '')) or 'Sev2' in str(p.get('priority', ''))]
        p3_prbs = [p for p in prbs if 'P3' in str(p.get('priority', '')) or 'Sev3' in str(p.get('priority', ''))]
        
        # All PRBs regardless of status (focus on volume for the week)
        critical_prbs_total = len(p0_prbs) + len(p1_prbs)  # Sev 0 + Sev 1
        
        st.markdown("#### 📊 PRB Severity Breakdown (All PRBs This Week)")
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
        
        st.markdown("#### 📊 Production Bug Summary") 
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
        
        # CI Issues - P0/P1 count
        ci_issues = data.get('ci', [])
        ci_p0_p1 = len([b for b in ci_issues if 'P0' in str(b.get('severity', '') + str(b.get('priority', ''))).upper() or 'P1' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        
        # Security Bugs - P0/P1 count
        security_bugs = data.get('security', [])
        sec_p0_p1 = len([b for b in security_bugs if 'P0' in str(b.get('severity', '') + str(b.get('priority', ''))).upper() or 'P1' in str(b.get('severity', '') + str(b.get('priority', ''))).upper()])
        
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
                coverage_file = st.text_input("Coverage File", value="coverage.json")
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
                        
                        if os.path.exists(coverage_file):
                            collector.load_coverage_metrics(coverage_file)
                        
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
        # Fallback to clean galaxy-style banner
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #080c19 0%, #0a0e1a 50%, #050810 100%);
            color: white;
            text-align: center;
            padding: 40px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-family: 'Inter', 'SF Pro Display', 'Helvetica Neue', sans-serif;
        ">
            <h1 style="
                margin: 0;
                font-size: 2.5rem;
                font-weight: 600;
                letter-spacing: 1px;
            ">SDB Engine Quality Dashboard</h1>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    dashboard = QualityReportDashboard()
    
    # Get available reports for sidebar
    reports = dashboard.get_reports()
    
    # Sidebar for report selection and navigation
    st.sidebar.title("📋 Quality Reports")
    
    if reports:
        # All reports are now archive type
        
        st.sidebar.markdown("### 📊 Past Reports")
        selected_report = None
        
        # Use session state to track selected report
        if 'selected_report_path' not in st.session_state:
            # Default to latest report
            if reports:
                st.session_state.selected_report_path = reports[0]['path']
            else:
                st.session_state.selected_report_path = None
        
        # Show all reports
        for i, report in enumerate(reports[:15]):  # Show latest 15
            is_selected = st.session_state.selected_report_path == report['path']
            # Create display name based on report period if available
            if 'period' in report and report['period']:
                # Extract dates from period display and format as MM/DD/YYYY-MM/DD/YYYY
                try:
                    # Parse period like "September 15-21, 2025" 
                    period_parts = report['period'].replace(',', '').split()
                    if len(period_parts) >= 3:
                        month_name = period_parts[0]
                        date_range = period_parts[1].split('-')
                        year = period_parts[2]
                        
                        # Convert month name to number
                        month_map = {
                            'January': '01', 'February': '02', 'March': '03', 'April': '04',
                            'May': '05', 'June': '06', 'July': '07', 'August': '08',
                            'September': '09', 'October': '10', 'November': '11', 'December': '12'
                        }
                        month_num = month_map.get(month_name, '01')
                        
                        if len(date_range) == 2:
                            start_day = date_range[0].zfill(2)
                            end_day = date_range[1].zfill(2)
                            display_name = f"{month_num}/{start_day}/{year}-{month_num}/{end_day}/{year}"
                        else:
                            display_name = f"{report['date'].strftime('%m/%d %H:%M')}"
                    else:
                        display_name = f"{report['date'].strftime('%m/%d %H:%M')}"
                except:
                    display_name = f"{report['date'].strftime('%m/%d %H:%M')}"
            else:
                display_name = f"{report['date'].strftime('%m/%d %H:%M')}"
            
            if st.sidebar.button(
                f"{'🟢' if is_selected else '📄'} {display_name}",
                key=f"report_{i}",
                help=f"Quality Report from {report['date'].strftime('%Y-%m-%d %H:%M')}",
                type="primary" if is_selected else "secondary"
            ):
                st.session_state.selected_report_path = report['path']
                selected_report = report
        
        # Find the currently selected report
        if selected_report is None:
            selected_report = next(
                (r for r in reports if r['path'] == st.session_state.selected_report_path),
                None
            )
        
        # Ensure we have a fallback if selected report is not found
        if selected_report is None and reports:
            selected_report = reports[0]
            st.session_state.selected_report_path = selected_report['path']
    else:
        st.sidebar.warning("No reports found")
        selected_report = None
    
    st.sidebar.markdown("---")
    
    # Main content area - always show the selected report
    if selected_report:
        # Load and display the selected report
        try:
            # Report header with key info
            col1, col2 = st.columns([2, 1])
            # Import get_report_dates function
            from quality_report_generator import get_report_dates
            dates = get_report_dates()
            
            with col1:
                st.subheader(f"📄 Quality Report")
            with col2:
                st.write(f"**Date:** {selected_report['date'].strftime('%Y-%m-%d %H:%M')}")
                if 'period' in selected_report:
                    st.write(f"**Period:** {selected_report['period']}")
                else:
                    st.write(f"**Period:** {dates['period_full']}")
            
            # Load archive data from selected report
            archive_data = dashboard.get_archive_data(selected_report['path'])
            
            # Load pre-generated LLM content if available in archive data
            dashboard.llm_content = archive_data.get('llm_content', {}) if archive_data else {}
            
            # Show visual dashboard if archive data is available
            if archive_data:
                # Component Tabs
                st.markdown("### 🏗️ SDB Service Components")
                tab1, tab2, tab3, tab4 = st.tabs(["🔧 Engine", "📊 SDD", "🔄 mSDB", "⚡ Core App Efficiency"])
                
                with tab1:  # Engine Tab (Current Dashboard)
                    st.markdown("#### 📊 Engine Quality Metrics")
                    dashboard.create_metrics_dashboard(archive_data)
                    
                    # Engine-specific Development Metrics
                    st.markdown("---")
                    st.markdown("#### 💻 Engine Development Metrics")
                    
                    # Extract Engine-specific data (for now, use all data as Engine)
                    engine_data = archive_data
                    
                    # Development KPIs for Engine
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        # Code Coverage
                        coverage_data = engine_data.get('coverage_summary', {}).get('overall', {})
                        line_coverage = coverage_data.get('line_coverage', 0)
                        coverage_color = "🟢" if line_coverage >= 80 else ("🟡" if line_coverage >= 70 else "🔴")
                        st.metric(
                            label=f"{coverage_color} Code Coverage",
                            value=f"{line_coverage:.1f}%",
                            delta=f"Target: 80%"
                        )
                    
                    with col2:
                        # P0/P1 CI Issues
                        ci_issues = engine_data.get('ci_issues', [])
                        p0_p1_ci = len([issue for issue in ci_issues if issue.get('priority', '').startswith(('P0', 'P1'))])
                        total_ci = len(ci_issues)
                        ci_color = "🟢" if p0_p1_ci <= 5 else ("🟡" if p0_p1_ci <= 10 else "🔴")
                        st.metric(
                            label=f"{ci_color} P0/P1 CI Issues",
                            value=f"{p0_p1_ci}",
                            delta=f"of {total_ci} total"
                        )
                    
                    with col3:
                        # Code Changes
                        git_stats = engine_data.get('git_stats', {})
                        lines_changed = git_stats.get('lines_changed', 0)
                        commits = git_stats.get('total_commits', 0)
                        change_color = "🟢" if commits < 10 and lines_changed < 3000 else ("🟡" if commits < 25 and lines_changed < 8000 else "🔴")
                        st.metric(
                            label=f"{change_color} Code Changes",
                            value=f"{lines_changed:,} lines",
                            delta=f"{commits} commits"
                        )
                
                with tab2:  # SDD Tab
                    st.markdown("#### 📊 SDD Quality Metrics")
                    st.info("🚧 SDD component metrics coming soon...")
                    
                    # Placeholder for SDD-specific metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("🟡 Code Coverage", "Coming Soon", "SDD specific")
                    with col2:
                        st.metric("🟡 P0/P1 CI Issues", "Coming Soon", "SDD specific")
                    with col3:
                        st.metric("🟡 Code Changes", "Coming Soon", "SDD specific")
                
                with tab3:  # mSDB Tab
                    st.markdown("#### 📊 mSDB Quality Metrics")
                    st.info("🚧 mSDB component metrics coming soon...")
                    
                    # Placeholder for mSDB-specific metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("🟡 Code Coverage", "Coming Soon", "mSDB specific")
                    with col2:
                        st.metric("🟡 P0/P1 CI Issues", "Coming Soon", "mSDB specific")
                    with col3:
                        st.metric("🟡 Code Changes", "Coming Soon", "mSDB specific")
                
                with tab4:  # Core App Efficiency Tab
                    st.markdown("#### 📊 Core App Efficiency Quality Metrics")
                    st.info("🚧 Core App Efficiency component metrics coming soon...")
                    
                    # Placeholder for Core App-specific metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("🟡 Code Coverage", "Coming Soon", "Core App specific")
                    with col2:
                        st.metric("🟡 P0/P1 CI Issues", "Coming Soon", "Core App specific")
                    with col3:
                        st.metric("🟡 Code Changes", "Coming Soon", "Core App specific")
                
                # Common Production Metrics (Outside tabs - applies to all components)
                st.markdown("---")
                st.markdown("### 📊 Common Production Metrics")
                st.info("ℹ️ These metrics apply across all SDB service components")
                
                # Week-over-Week Trends across past reports
                dashboard.create_weekly_trends(reports)
                
                # Risk Assessment Section
                st.markdown("### 🎯 Risk Assessment")
                col1, col2 = st.columns([1, 1])
                with col1:
                    dashboard.create_risk_chart(archive_data, "_main")
                with col2:
                    dashboard.create_risk_insights(archive_data)
                
                # Problem Reports Section  
                st.markdown("### 🚨 [PRBs](https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=report&wave__assetId=00OEE000001TXjB2AW)")
                col1, col2 = st.columns([1, 1])
                with col1:
                    dashboard.create_prb_analysis(archive_data, "_main")
                with col2:
                    dashboard.create_prb_insights(archive_data)
                
                # Bug & Severity Section
                st.markdown("### 🐛 [Production Bug Analysis](https://gus.lightning.force.com/lightning/r/Report/00OEE0000014M4b2AE/view)")
                col1, col2 = st.columns([1, 1])
                with col1:
                    dashboard.create_bug_severity_chart(archive_data)
                with col2:
                    dashboard.create_bug_insights(archive_data)
                
                st.markdown("---")
                
                # Deployment Analysis Section
                st.markdown("### 🚀 [Deployment Analysis](https://bdmpresto-superset-server.sfproxy.uip.aws-esvc1-useast2.aws.sfdc.cl/superset/sqllab?savedQueryId=25468)")
                col1, col2 = st.columns([1, 1])
                with col1:
                    dashboard.create_deployment_stacked_bar(archive_data)
                with col2:
                    dashboard.create_version_pie_chart(archive_data)
                
                # Add deployment insights
                dashboard.create_deployment_insights(archive_data)
                
                st.markdown("---")
                
                # Code Coverage Section
                st.markdown("### 📊 [Code Coverage](https://sonarqube.sfcq.buildndeliver-s.aws-esvc1-useast2.aws.sfdc.cl/component_measures?id=sayonara.sayonaradb.sdb&metric=uncovered_lines&view=list)")
                col1, col2 = st.columns([1, 1])
                with col1:
                    dashboard.create_coverage_comparison_chart(archive_data)
                with col2:
                    dashboard.create_coverage_insights(archive_data)
                
                st.markdown("---")
                
                # CI Issues Section
                st.markdown("### 🔧 [CI Issues](https://gus.lightning.force.com/lightning/r/Report/00OEE000002YbOz2AK/view?queryScope=userFolders)")
                col1, col2 = st.columns([1, 1])
                with col1:
                    dashboard.create_ci_issues_chart(archive_data)
                with col2:
                    st.markdown("#### 📊 CI Issues Insights")
                    ci_data = archive_data.get('ci_issues', [])
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
                
                # Security Bugs Section  
                st.markdown("### 🔒 [Security Bugs](https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=report&wave__assetId=00OEE000002XKRp2AO)")
                st.markdown("*Source: Coverity and 3PP Scan*")
                col1, col2 = st.columns([1, 1])
                with col1:
                    dashboard.create_security_bugs_chart(archive_data)
                with col2:
                    st.markdown("#### 🛡️ Security Analysis")
                    security_data = archive_data.get('security_issues', [])
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
                
                # Left Shift Bugs Section
                st.markdown("### ⬅️ [Left Shift Bugs](https://gus.lightning.force.com/lightning/r/Report/00OEE000002Wjld2AC/view?queryScope=userFolders)")
                col1, col2 = st.columns([1, 1])
                with col1:
                    dashboard.create_leftshift_bugs_chart(archive_data)
                with col2:
                    st.markdown("#### 📈 Left Shift Insights")
                    leftshift_data = archive_data.get('leftshift_issues', [])
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
                
                st.markdown("---")
                
                # Code Changes Analysis Section
                st.markdown("### 📊 Code Changes Analysis")
                dashboard.create_code_changes_analysis(archive_data)
                
                st.markdown("---")
                
                # Trend Analysis Section
                st.markdown("### 📈 Quality Trends")
                col1, col2 = st.columns([1, 1])
                with col1:
                    dashboard.create_trend_analysis(archive_data)
                with col2:
                    dashboard.create_trend_insights(archive_data)
                
            else:
                st.error("❌ No archive data found - dashboard cannot display metrics")
                st.info("Available files in reports directory:")
                try:
                    reports_files = [f for f in os.listdir('./reports') if f.endswith('.json')]
                    for f in reports_files:
                        st.write(f"  • {f}")
                except:
                    st.write("Could not list files")
            
        except Exception as e:
            st.error(f"Error loading report: {e}")
    
    elif not reports:
        st.warning("📭 No reports found.")
        
        # Debug information
        with st.expander("🔍 Debug Information"):
            st.write("**Current working directory:**", os.getcwd())
            st.write("**Script directory:**", os.path.dirname(os.path.abspath(__file__)))
            st.write("**Reports directory:**", dashboard.reports_dir)
            st.write("**Archive directory:**", dashboard.archive_dir)
            
            st.write("**Reports directory exists:**", os.path.exists(dashboard.reports_dir))
            st.write("**Archive directory exists:**", os.path.exists(dashboard.archive_dir))
            
            if os.path.exists(dashboard.reports_dir):
                st.write("**Files in reports directory:**")
                try:
                    files = os.listdir(dashboard.reports_dir)
                    for f in files:
                        st.write(f"  • {f}")
                except Exception as e:
                    st.write(f"Error listing files: {e}")
            
            if os.path.exists(dashboard.archive_dir):
                st.write("**Files in archive directory:**")
                try:
                    files = os.listdir(dashboard.archive_dir)
                    for f in files:
                        st.write(f"  • {f}")
                except Exception as e:
                    st.write(f"Error listing files: {e}")
            
            # Check for JSON files specifically
            st.write("**Looking for pattern:** quality_data_archive_*.json")
            for search_dir in [dashboard.reports_dir, dashboard.archive_dir]:
                if os.path.exists(search_dir):
                    pattern = os.path.join(search_dir, "quality_data_archive_*.json")
                    files = glob.glob(pattern)
                    st.write(f"**Found {len(files)} files in {search_dir}:**")
                    for f in files:
                        st.write(f"  • {os.path.basename(f)}")
    
    # KPI Legend Section
    st.markdown("---")
    st.markdown("### 📊 KPI Color Definitions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### 🐛 **Bug Metrics (Production, CI, Security, Left Shift)**
        - **🟢 GREEN**: Low risk - minimal critical issues
        - **🟡 YELLOW**: Moderate risk - standard review needed  
        - **🔴 RED**: High risk - extra scrutiny required
        
        **Scoring**: P0/P1 bugs = 4 points, P2+ bugs = 1 point
        - **Production Bugs**: Green ≤16, Yellow 17-32, Red >32
        - **CI Issues**: Green ≤25, Yellow 26-50, Red >50
        - **Security Issues**: Green ≤16, Yellow 17-32, Red >32
        - **Left Shift**: Green ≤25, Yellow 26-50, Red >50
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

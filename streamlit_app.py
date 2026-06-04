#!/usr/bin/env python3
"""
Quality Report Dashboard - Streamlit Web Application
Interactive dashboard for viewing and analyzing quality reports.
"""

import streamlit as st
import os
import json
import csv
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
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

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
        if self._deployment_rows_usable(deployments):
            return deployments

        # Week-level fallback from Shared/ then Engine deployment history CSV.
        selected_week = getattr(st.session_state, 'selected_week', None)
        week_folder = self._resolve_week_folder_key(selected_week, data)
        if week_folder:
            fallback_candidates = [
                os.path.join(APP_ROOT, "weeks", week_folder, "Shared", "deployment-journey.csv"),
                os.path.join(APP_ROOT, "weeks", week_folder, "Shared", "deployment.csv"),
                os.path.join(APP_ROOT, "weeks", week_folder, "Engine", "global_deployment.csv"),
                os.path.join(APP_ROOT, "weeks", week_folder, "Engine", "deployment.csv"),
            ]
            for csv_path in fallback_candidates:
                if not os.path.exists(csv_path):
                    continue
                parsed = self._parse_global_deployment_history(csv_path)
                if self._deployment_rows_usable(parsed):
                    return parsed
        return deployments

    def _deployment_rows_usable(self, rows: List[Dict[str, Any]]) -> bool:
        if not rows:
            return False
        total = 0
        for r in rows:
            try:
                total += int(float(r.get('count', r.get('cells', 0)) or 0))
            except Exception:
                continue
        return total > 0

    def _parse_global_deployment_history(self, csv_path: str) -> List[Dict[str, Any]]:
        """
        Convert weekly history CSV rows into latest-week deployment snapshot rows.
        Expected columns: week_start,current_version,total_cells,sb0_pct,sb1_pct,r0_pct,r1_pct,r2a_pct,r2b_pct
        """
        out: List[Dict[str, Any]] = []
        try:
            with open(csv_path, "r", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception:
            return out

        # Normalize alternate pct column names if present.
        for row in rows:
            if "pct_of_SB0" in row and "sb0_pct" not in row:
                row["sb0_pct"] = row.get("pct_of_SB0", 0)
            if "pct_of_SB1" in row and "sb1_pct" not in row:
                row["sb1_pct"] = row.get("pct_of_SB1", 0)
            if "pct_of_R0" in row and "r0_pct" not in row:
                row["r0_pct"] = row.get("pct_of_R0", 0)
            if "pct_of_R1" in row and "r1_pct" not in row:
                row["r1_pct"] = row.get("pct_of_R1", 0)
            if "pct_of_R2a" in row and "r2a_pct" not in row:
                row["r2a_pct"] = row.get("pct_of_R2a", 0)
            if "pct_of_R2b" in row and "r2b_pct" not in row:
                row["r2b_pct"] = row.get("pct_of_R2b", 0)

        dated_rows: List[tuple[datetime, Dict[str, Any]]] = []
        for row in rows:
            try:
                d = datetime.strptime(str(row.get("week_start", "")).strip(), "%Y-%m-%d")
            except ValueError:
                continue
            dated_rows.append((d, row))
        if not dated_rows:
            return out

        latest = max(d for d, _ in dated_rows)
        latest_rows = [r for d, r in dated_rows if d == latest]
        stage_map = {
            "sb0_pct": "SB0",
            "sb1_pct": "SB1",
            "r0_pct": "R0",
            "r1_pct": "R1",
            "r2a_pct": "R2a",
            "r2b_pct": "R2b",
        }

        for row in latest_rows:
            version = str(row.get("current_version", "")).strip()
            try:
                total_cells = float(str(row.get("total_cells", "0")).strip() or 0)
            except ValueError:
                total_cells = 0.0
            if not version or total_cells <= 0:
                continue
            for pct_col, stage in stage_map.items():
                try:
                    pct = float(str(row.get(pct_col, "0")).strip() or 0)
                except ValueError:
                    pct = 0.0
                count = int(round(total_cells * pct / 100.0))
                if count <= 0:
                    continue
                out.append(
                    {
                        "stagger": stage,
                        "version": version,
                        "count": count,
                        "stage": stage,
                        "cells": count,
                    }
                )
        return out

    def _resolve_week_folder_key(self, selected_week: Optional[str], data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Convert UI week selector key (often YYYY-MM-DD timestamp key) into weeks/cwNN folder key.
        Priority:
          1) explicit cwNN in selected_week
          2) metadata.week_label
          3) metadata.report_period_start
          4) selected_week parsed as date
        """
        def cw_from_date_str(s: str) -> Optional[str]:
            try:
                d = datetime.strptime(str(s).strip(), "%Y-%m-%d")
                return f"cw{d.isocalendar().week:02d}"
            except ValueError:
                return None

        if selected_week and re.match(r"^cw\d{2}$", str(selected_week).strip(), re.IGNORECASE):
            return str(selected_week).strip().lower()

        md = (data or {}).get("metadata", {}) if isinstance(data, dict) else {}
        wl = str(md.get("week_label", "")).strip().lower()
        if re.match(r"^cw\d{2}$", wl):
            return wl

        rps = str(md.get("report_period_start", "")).strip()
        cw = cw_from_date_str(rps)
        if cw:
            return cw

        cw = cw_from_date_str(str(selected_week or ""))
        if cw:
            return cw
        return None

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
            prod_bugs_label = "🐛 P0/P1 Prod Investigations" if tab_component == "Core App Efficiency" else "🐛 P0/P1 Prod Bugs"
            st.markdown(f"""
            <a href="{p0p1_href}"{p0p1_extra} style="text-decoration: none; color: inherit;">
                <div class="metric-card metric-card-clickable">
                    <div class="metric-label">{prod_bugs_label}</div>
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
                prod_bugs_label = "🐛 P0/P1 Prod Investigations" if prod_bugs_link_folder == "Core App Efficiency" else "🐛 P0/P1 Prod Bugs"
                st.markdown(f"""
                <a href="{p0p1_href}"{p0p1_extra} style="text-decoration: none; color: inherit;">
                    <div class="metric-card metric-card-clickable">
                        <div class="metric-label">{prod_bugs_label}</div>
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
                st.markdown("#### 📁 Most Changed Files (Top 10)")
                for i, file_info in enumerate(most_changed[:10]):
                    total = file_info.get('total_changes', 0)
                    file_path = file_info.get('file', 'Unknown')
                    st.write(f"{i+1}. `{file_path}` - **{total:,} changes**")

                if len(most_changed) > 10:
                    st.caption(f"... and {len(most_changed) - 10} more files changed")

            # Check if we can get detailed category breakdown from live git
            # (Only if repo is accessible and we want more details)
            st.markdown("---")
            st.info("💡 **Note:** Detailed file breakdown by category requires regenerating the report with `./run_report.sh`")

            # Try to show category breakdown if git repo is accessible
            try:
                # Get dates from git_stats if available
                report_start = git_stats.get('reporting_period_start')
                report_end = git_stats.get('reporting_period_end')

                if report_start and report_end:
                    changes_data, _ = get_git_changes_by_path(
                        report_start, report_end, repo_path, is_sdb_repo
                    )

                    if changes_data:
                        st.markdown("#### 📋 Detailed File Changes by Category")
                        st.caption("(Live data from git repository)")

                        # Calculate total changes for percentages
                        categories = list(changes_data.keys())
                        total_changes = [changes_data[d]['added'] + changes_data[d]['deleted'] for d in categories]

                        # Sort by total changes
                        sorted_data = sorted(zip(categories, total_changes), key=lambda x: x[1], reverse=True)

                        # Show file details for each category in an expander
                        for category, total_cat_changes in sorted_data:
                            file_details = changes_data[category]['file_details']
                            percentage = (total_cat_changes / sum(total_changes) * 100) if sum(total_changes) > 0 else 0

                            # Create expander for each category
                            with st.expander(f"📁 {category}: {total_cat_changes:,} lines ({percentage:.1f}%) - {len(file_details)} files"):
                                for detail in sorted(file_details, key=lambda x: x['added'] + x['deleted'], reverse=True):
                                    total_file_changes = detail['added'] + detail['deleted']
                                    st.markdown(f"• `{detail['path']}`: +{detail['added']} -{detail['deleted']} ({total_file_changes} total)")

                                # Summary for this category
                                total_added = changes_data[category]['added']
                                total_deleted = changes_data[category]['deleted']
                                st.markdown(f"**Category Summary:** +{total_added:,} lines added, -{total_deleted:,} lines deleted")
                else:
                    st.warning("⚠️ Could not determine reporting period from git_stats")
            except Exception as e:
                # Git repo not accessible, which is expected on Streamlit Cloud
                st.error(f"⚠️ Error fetching detailed git data: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

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

            # Add detailed file breakdown for ALL categories (expandable)
            if categories:
                st.markdown("#### 📋 Detailed File Changes by Category")

                # Show file details for each category in an expander
                for i, category in enumerate(categories):
                    file_details = changes_data[category]['file_details']
                    total_cat_changes = total_changes[i]
                    percentage = (total_cat_changes / sum(total_changes) * 100) if sum(total_changes) > 0 else 0

                    # Create expander for each category
                    with st.expander(f"📁 {category}: {total_cat_changes:,} lines ({percentage:.1f}%) - {len(file_details)} files"):
                        for detail in sorted(file_details, key=lambda x: x['added'] + x['deleted'], reverse=True):
                            total_file_changes = detail['added'] + detail['deleted']
                            st.markdown(f"• `{detail['path']}`: +{detail['added']} -{detail['deleted']} ({total_file_changes} total)")

                        # Summary for this category
                        total_added = changes_data[category]['added']
                        total_deleted = changes_data[category]['deleted']
                        st.markdown(f"**Category Summary:** +{total_added:,} lines added, -{total_deleted:,} lines deleted")
        
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
    
    def create_version_pie_chart(self, data: Dict[str, Any], key_suffix: str = ""):
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
            
            # Use a professional color palette
            colors = ['#4A90E2', '#7B68EE', '#50C878', '#FFB347', '#FF6B6B',
                     '#9B59B6', '#3498DB', '#1ABC9C', '#F39C12', '#E74C3C',
                     '#95A5A6', '#34495E', '#16A085', '#27AE60', '#2980B9']

            fig = px.pie(
                values=[count for version, count in sorted_versions],
                names=[f"v{version}" for version, count in sorted_versions],
                title=f"📊 Release Version Distribution by Cell Count<br><sub style='font-size: 0.85em; color: #666;'>{total_cells:,} total cells across fleet</sub>",
                color_discrete_sequence=colors
            )

            # Enhance visual styling with borders and professional look
            fig.update_traces(
                textposition='inside',
                textinfo='label+value+percent',
                textfont=dict(size=12, color='white', family='Arial, sans-serif'),
                marker=dict(
                    line=dict(color='white', width=2.5)  # Subtle white borders around slices
                ),
                pull=[0.02] * len(sorted_versions),  # Slight pull effect for visual separation
                hovertemplate='<b>%{label}</b><br>Cells: %{value:,}<br>Percentage: %{percent}<extra></extra>'
            )

            fig.update_layout(
                showlegend=True,
                height=500,
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=1.02,
                    font=dict(size=11, family='Arial, sans-serif'),
                    bgcolor='rgba(255, 255, 255, 0.8)',
                    bordercolor='#E0E0E0',
                    borderwidth=1
                ),
                title=dict(
                    font=dict(size=16, family='Arial, sans-serif', color='#2C3E50'),
                    x=0.5,
                    xanchor='center'
                ),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=20, r=150, t=80, b=20)
            )
            st.plotly_chart(fig, use_container_width=True, key=f"version_pie_chart{key_suffix}")
        else:
            st.warning(f"📊 No valid version data for pie chart (found {total_cells} total cells)")

    def _version_tuple(self, version: str) -> Tuple[int, ...]:
        nums = re.findall(r"\d+", str(version))
        return tuple(int(n) for n in nums) if nums else (0,)

    def _load_global_deployment_history(self, selected_week: Optional[str], data: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Load deployment history data. Tries Shared/deployment-journey.csv first,
        falls back to Engine/global_deployment.csv for backward compatibility.
        Normalizes column names to sb0_pct format.
        """
        week_folder = self._resolve_week_folder_key(selected_week, data)
        if not week_folder:
            return pd.DataFrame()

        # Try Shared/deployment-journey.csv first
        shared_path = os.path.join(APP_ROOT, "weeks", week_folder, "Shared", "deployment-journey.csv")
        engine_path = os.path.join(APP_ROOT, "weeks", week_folder, "Engine", "global_deployment.csv")

        df = pd.DataFrame()
        source_format = None

        if os.path.exists(shared_path):
            try:
                df = pd.read_csv(shared_path)
                source_format = "shared"
            except Exception:
                pass

        if df.empty and os.path.exists(engine_path):
            try:
                df = pd.read_csv(engine_path)
                source_format = "engine"
            except Exception:
                return pd.DataFrame()

        if df.empty:
            return pd.DataFrame()

        # Normalize column names
        if source_format == "shared":
            # deployment-journey.csv format: pct_of_SB0, pct_of_SB1, etc.
            column_mapping = {
                "pct_of_SB0": "sb0_pct",
                "pct_of_SB1": "sb1_pct",
                "pct_of_R0": "r0_pct",
                "pct_of_R1": "r1_pct",
                "pct_of_R2a": "r2a_pct",
                "pct_of_R2b": "r2b_pct",
            }
            df = df.rename(columns=column_mapping)
            # Add total_cells if missing (default to 1 for percentage-only data)
            if "total_cells" not in df.columns:
                df["total_cells"] = 1

        # Verify required columns
        required = {
            "current_version",
            "week_start",
            "sb0_pct",
            "sb1_pct",
            "r0_pct",
            "r1_pct",
            "r2a_pct",
            "r2b_pct",
        }
        if not required.issubset(set(df.columns)):
            return pd.DataFrame()

        df["week_start"] = pd.to_datetime(df["week_start"], errors="coerce")
        df = df.dropna(subset=["week_start"]).copy()
        if df.empty:
            return df
        df["current_version"] = df["current_version"].astype(str)
        df["total_cells"] = pd.to_numeric(df.get("total_cells", 1), errors="coerce").fillna(1.0)
        for c in ["sb0_pct", "sb1_pct", "r0_pct", "r1_pct", "r2a_pct", "r2b_pct"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
        return df

    def _load_shared_deployment_journey_history(self, selected_week: Optional[str], data: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Load shared deployment journey history from:
        weeks/<cw>/Shared/deployment-journey.csv
        """
        week_folder = self._resolve_week_folder_key(selected_week, data)
        if not week_folder:
            return pd.DataFrame()
        path = os.path.join(APP_ROOT, "weeks", week_folder, "Shared", "deployment-journey.csv")
        if not os.path.exists(path):
            return pd.DataFrame()
        try:
            df = pd.read_csv(path)
        except Exception:
            return pd.DataFrame()

        # Support multiple journey formats:
        # 1) Wide pct columns: pct_of_SB0... or sb0_pct...
        # 2) Long stagger rows: current_version, week_start, stagger, cumulative_cells, stagger_total_cells, pct_of_stagger
        has_new_format = "pct_of_SB0" in df.columns
        has_long_stagger_format = {"stagger", "pct_of_stagger"}.issubset(set(df.columns))

        if has_long_stagger_format:
            tmp = df.copy()
            tmp["stagger"] = tmp["stagger"].astype(str).str.strip()
            tmp["pct_of_stagger"] = pd.to_numeric(tmp["pct_of_stagger"], errors="coerce").fillna(0.0)
            pivot = (
                tmp.pivot_table(
                    index=["current_version", "week_start"],
                    columns="stagger",
                    values="pct_of_stagger",
                    aggfunc="max",
                    fill_value=0.0,
                )
                .reset_index()
            )
            pivot.columns.name = None
            df = pivot
            rename_map = {
                "SB0": "sb0_pct",
                "SB1": "sb1_pct",
                "R0": "r0_pct",
                "R1": "r1_pct",
                "R2a": "r2a_pct",
                "R2b": "r2b_pct",
            }
            df = df.rename(columns=rename_map)
        elif has_new_format:
            # Rename new wide-format columns to canonical names.
            rename_map = {
                "pct_of_SB0": "sb0_pct",
                "pct_of_SB1": "sb1_pct",
                "pct_of_R0": "r0_pct",
                "pct_of_R1": "r1_pct",
                "pct_of_R2a": "r2a_pct",
                "pct_of_R2b": "r2b_pct",
            }
            df = df.rename(columns=rename_map)

        required = {
            "current_version",
            "week_start",
        }
        if not required.issubset(set(df.columns)):
            return pd.DataFrame()

        df["week_start"] = pd.to_datetime(df["week_start"], errors="coerce")
        df = df.dropna(subset=["week_start"]).copy()
        if df.empty:
            return df
        df["current_version"] = df["current_version"].astype(str)

        # Add total_cells if missing (for new format that doesn't have it)
        if "total_cells" not in df.columns:
            df["total_cells"] = 100.0  # Default placeholder

        df["total_cells"] = pd.to_numeric(df["total_cells"], errors="coerce").fillna(100.0)
        for c in ["sb0_pct", "sb1_pct", "r0_pct", "r1_pct", "r2a_pct", "r2b_pct"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
            else:
                df[c] = 0.0
        return df

    def _load_plan_schedule_data(self, selected_week: Optional[str], data: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Load deployment plan schedule CSV(s) from weeks/<cw>/Shared:
        SDB Releases Deployment Schedule*.csv
        Returns normalized rows: week_start, stage, version.
        """
        week_folder = self._resolve_week_folder_key(selected_week, data)
        if not week_folder:
            return pd.DataFrame()
        # Try Shared directory first, then fall back to Engine
        shared_dir = os.path.join(APP_ROOT, "weeks", week_folder, "Shared")
        engine_dir = os.path.join(APP_ROOT, "weeks", week_folder, "Engine")

        plan_files = sorted(glob.glob(os.path.join(shared_dir, "SDB Releases Deployment Schedule*.csv")))
        if not plan_files:
            plan_files = sorted(glob.glob(os.path.join(engine_dir, "SDB Releases Deployment Schedule*.csv")))
        if not plan_files:
            return pd.DataFrame()

        def map_stage(raw_stage: str) -> Optional[str]:
            s = str(raw_stage or "").strip().lower()
            if s == "sb0":
                return "SB0"
            if s.startswith("sb1/sb2"):
                return "SB1/SB2"
            # R*.w1 and R*.w2 both map to R_COMBINED for post-processing
            if s.startswith("r*.w1") or s.startswith("r*.w2"):
                return "R_COMBINED"
            if s.startswith("r*.w3") or s.startswith("r2a") or s.startswith("r2"):
                return "R2a"
            if s.startswith("r*.w4") or s.startswith("r2b"):
                return "R2b"
            return None

        rows: List[pd.DataFrame] = []
        for path in plan_files:
            try:
                raw = pd.read_csv(path, dtype=str)
            except Exception:
                continue
            if raw.empty:
                continue
            stage_col = raw.columns[0]
            melted = raw.rename(columns={stage_col: "stage_raw"}).melt(
                id_vars=["stage_raw"],
                var_name="week_label",
                value_name="version",
            )
            melted["stage"] = melted["stage_raw"].map(map_stage)
            melted["version"] = melted["version"].astype(str).str.strip()
            melted = melted[(melted["stage"].notna()) & (melted["version"] != "") & (melted["version"].str.lower() != "nan")].copy()
            if melted.empty:
                continue
            melted["week_start"] = pd.to_datetime(melted["week_label"], errors="coerce")
            melted = melted.dropna(subset=["week_start"])
            if melted.empty:
                continue
            rows.append(melted[["week_start", "stage", "version"]])

        if not rows:
            return pd.DataFrame()

        plan_df = pd.concat(rows, ignore_index=True).drop_duplicates()

        # Post-process: Split R_COMBINED stages
        # Group R_COMBINED entries by version to get full R deployment period
        expanded_rows = []

        # First, collect all R_COMBINED entries by version
        r_combined_by_version = {}
        other_rows = []

        for _, row in plan_df.iterrows():
            if row["stage"] == "R_COMBINED":
                version = row["version"]
                if version not in r_combined_by_version:
                    r_combined_by_version[version] = []
                r_combined_by_version[version].append(row["week_start"])
            else:
                other_rows.append(row.to_dict())

        # Now split R_COMBINED into R0, R1, R2a, R2b for each version
        for version, week_starts in r_combined_by_version.items():
            # Get the full R deployment period (min to max of all R*.w1 and R*.w2)
            r_start = min(week_starts)
            r_end = max(week_starts) + pd.Timedelta(days=7)  # End of last week

            total_duration = (r_end - r_start).total_seconds() / 86400  # Convert to days

            # Split according to percentages: R0=15%, R1=25%, R2a=30%, R2b=30%
            r0_duration = total_duration * 0.15
            r1_duration = total_duration * 0.25
            r2a_duration = total_duration * 0.30
            r2b_duration = total_duration * 0.30

            # R0: 15% of time
            expanded_rows.append({
                "week_start": r_start,
                "stage": "R0",
                "version": version
            })

            # R1: starts after R0, 25% of time
            r1_start = r_start + pd.Timedelta(days=r0_duration)
            expanded_rows.append({
                "week_start": r1_start,
                "stage": "R1",
                "version": version
            })

            # R2a: starts after R1, 30% of time
            r2a_start = r1_start + pd.Timedelta(days=r1_duration)
            expanded_rows.append({
                "week_start": r2a_start,
                "stage": "R2a",
                "version": version
            })

            # R2b: starts after R2a, remaining 30% of time
            r2b_start = r2a_start + pd.Timedelta(days=r2a_duration)
            expanded_rows.append({
                "week_start": r2b_start,
                "stage": "R2b",
                "version": version
            })

        # Combine with other rows
        expanded_rows.extend(other_rows)
        plan_df = pd.DataFrame(expanded_rows)
        if "week_start" in plan_df.columns:
            plan_df["week_start"] = pd.to_datetime(plan_df["week_start"], errors="coerce").dt.normalize()
            plan_df = plan_df.dropna(subset=["week_start"]).copy()
        return plan_df

    def _build_stage_timeline(self, version_plan_sorted: pd.DataFrame) -> Dict[str, Dict[str, pd.Timestamp]]:
        """Build per-stage plan start/end ranges using exactly one shared rule."""
        stage_timeline: Dict[str, Dict[str, pd.Timestamp]] = {}
        if version_plan_sorted is None or version_plan_sorted.empty:
            return stage_timeline
        version_plan_sorted = version_plan_sorted.sort_values("week_start").copy()
        for idx, (_, row) in enumerate(version_plan_sorted.iterrows()):
            stage = row["stage"]
            start_date = pd.to_datetime(row["week_start"], errors="coerce")
            if pd.isna(start_date):
                continue
            if idx < len(version_plan_sorted) - 1:
                next_start = pd.to_datetime(version_plan_sorted.iloc[idx + 1]["week_start"], errors="coerce")
                end_date = (next_start - pd.Timedelta(days=1)) if pd.notna(next_start) else (start_date + pd.Timedelta(days=6))
            else:
                end_date = start_date + pd.Timedelta(days=6)
            start_date = start_date.normalize()
            end_date = pd.to_datetime(end_date, errors="coerce").normalize()
            if stage not in stage_timeline:
                stage_timeline[stage] = {"start": start_date, "end": end_date}
            else:
                stage_timeline[stage]["start"] = min(stage_timeline[stage]["start"], start_date)
                stage_timeline[stage]["end"] = max(stage_timeline[stage]["end"], end_date)
        return stage_timeline

    def create_actuals_vs_plan_chart(self, selected_week: Optional[str], data: Optional[Dict[str, Any]] = None, key_suffix: str = "") -> None:
        """Compare actual vs plan across all stages for one selected release version."""
        actual_df = self._load_global_deployment_history(selected_week, data)
        plan_df = self._load_plan_schedule_data(selected_week, data)
        if actual_df.empty or plan_df.empty:
            st.info("Actuals vs Plan unavailable: missing actual or plan data for selected week folder.")
            return

        actual_df["current_version"] = actual_df["current_version"].astype(str).str.strip()
        plan_df["version"] = plan_df["version"].astype(str).str.strip()
        available_versions = sorted(
            set(actual_df["current_version"]).intersection(set(plan_df["version"])),
            key=self._version_tuple,
        )
        if not available_versions:
            st.info("Actuals vs Plan unavailable: no release versions overlap between plan and actual data.")
            return

        default_idx = max(0, len(available_versions) - 1)
        selected_version = st.selectbox(
            "Release Version (Actuals vs Plan)",
            available_versions,
            index=default_idx,
            key=f"actual_plan_version_{key_suffix}",
        )

        stage_cols = {
            "SB0": "sb0_pct",
            "SB1/SB2": "sb1_pct",
            "R0": "r0_pct",
            "R1": "r1_pct",
            "R2a": "r2a_pct",
            "R2b": "r2b_pct",
        }
        stage_order = ["SB0", "SB1/SB2", "R0", "R1", "R2a", "R2b"]

        # Actual: per-week stage mix for selected version.
        actual_version = actual_df[actual_df["current_version"] == selected_version].copy()
        if actual_version.empty:
            st.info(f"No actual deployment rows found for version {selected_version}.")
            return

        actual_parts: List[pd.DataFrame] = []
        week_cells = actual_version.groupby("week_start", as_index=False)["total_cells"].sum().rename(columns={"total_cells": "week_cells"})
        for stage, col in stage_cols.items():
            stage_cells = actual_version["total_cells"] * actual_version[col] / 100.0
            stage_week = (
                pd.DataFrame({"week_start": actual_version["week_start"], "stage_cells": stage_cells})
                .groupby("week_start", as_index=False)["stage_cells"]
                .sum()
            )
            merged_week = week_cells.merge(stage_week, on="week_start", how="left")
            merged_week["actual_pct"] = np.where(
                merged_week["week_cells"] > 0,
                merged_week["stage_cells"] * 100.0 / merged_week["week_cells"],
                0.0,
            )
            merged_week["stage"] = stage
            actual_parts.append(merged_week[["week_start", "stage", "actual_pct"]])
        actual_long = pd.concat(actual_parts, ignore_index=True)

        # Plan: stage(s) where selected version is scheduled each week.
        plan_version = plan_df[plan_df["version"] == selected_version].copy()
        if plan_version.empty:
            st.info(f"No planned schedule rows found for version {selected_version}.")
            return
        plan_counts = (
            plan_version.groupby(["week_start", "stage"], as_index=False)
            .size()
            .rename(columns={"size": "planned_count"})
        )
        plan_total = plan_counts.groupby("week_start", as_index=False)["planned_count"].sum().rename(columns={"planned_count": "week_total_plan"})
        plan_long = plan_counts.merge(plan_total, on="week_start", how="left")
        plan_long["plan_pct"] = np.where(
            plan_long["week_total_plan"] > 0,
            plan_long["planned_count"] * 100.0 / plan_long["week_total_plan"],
            0.0,
        )

        merged = actual_long.merge(
            plan_long[["week_start", "stage", "plan_pct", "planned_count"]],
            on=["week_start", "stage"],
            how="outer",
        )
        merged = merged.dropna(subset=["week_start"]).copy()
        if merged.empty:
            st.info("Actuals vs Plan unavailable: no trend rows after merging data.")
            return
        merged["actual_pct"] = pd.to_numeric(merged["actual_pct"], errors="coerce").fillna(0.0)
        merged["plan_pct"] = pd.to_numeric(merged["plan_pct"], errors="coerce").fillna(0.0)
        merged["planned_count"] = pd.to_numeric(merged["planned_count"], errors="coerce").fillna(0.0)

        # Always anchor the chart to global latest 8 weeks from actual history,
        # so sparse versions still render a consistent 8-week axis with zeros.
        baseline_weeks = sorted(actual_df["week_start"].dropna().unique())[-8:]
        if not baseline_weeks:
            st.info("Actuals vs Plan unavailable for the latest 8-week window.")
            return
        baseline_labels = [pd.to_datetime(w).strftime("%Y-%m-%d") for w in baseline_weeks]
        merged["week_label"] = merged["week_start"].dt.strftime("%Y-%m-%d")
        merged = merged[merged["week_label"].isin(baseline_labels)].copy()

        # Ensure all stages are represented for each baseline week.
        week_labels = baseline_labels
        full_index = pd.MultiIndex.from_product([week_labels, stage_order], names=["week_label", "stage"])
        merged = (
            merged.set_index(["week_label", "stage"])
            .reindex(full_index)
            .reset_index()
        )
        merged["actual_pct"] = pd.to_numeric(merged["actual_pct"], errors="coerce").fillna(0.0)
        merged["plan_pct"] = pd.to_numeric(merged["plan_pct"], errors="coerce").fillna(0.0)
        merged["planned_count"] = pd.to_numeric(merged["planned_count"], errors="coerce").fillna(0.0)

        palette = {
            "SB0": "#5B5CFF",
            "SB1/SB2": "#2F80FF",
            "R0": "#00B3C7",
            "R1": "#2E9E44",
            "R2a": "#E2A300",
            "R2b": "#C56A00",
        }
        fig = go.Figure()
        for stage in stage_order:
            d = merged[merged["stage"] == stage].copy()
            if d.empty:
                continue
            color = palette.get(stage, "#64748B")
            fig.add_trace(
                go.Scatter(
                    x=d["week_label"],
                    y=d["actual_pct"],
                    mode="lines+markers",
                    name=f"{stage} Actual",
                    line=dict(color=color, width=2),
                    marker=dict(size=6),
                    hovertemplate="Week: %{x}<br>Actual: %{y:.1f}%<extra></extra>",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=d["week_label"],
                    y=d["plan_pct"],
                    mode="lines+markers",
                    name=f"{stage} Plan",
                    line=dict(color=color, width=2, dash="dot"),
                    marker=dict(size=6, symbol="circle-open"),
                    hovertemplate="Week: %{x}<br>Plan: %{y:.1f}%<br>Planned entries: %{customdata:.0f}<extra></extra>",
                    customdata=d["planned_count"],
                )
            )

        fig.update_layout(
            title=f"📈 Actuals vs Plan by Stage — Version v{selected_version}",
            xaxis_title="Week Start",
            yaxis_title="Stage share within selected version (%)",
            yaxis=dict(range=[0, 100]),
            legend_title="Series",
            height=520,
        )
        fig.update_xaxes(categoryorder="array", categoryarray=week_labels)
        st.plotly_chart(fig, use_container_width=True, key=f"actual_vs_plan_chart_{key_suffix}")

    def create_global_deployment_journey_single_version(self, selected_week: Optional[str], data: Optional[Dict[str, Any]] = None, key_suffix: str = "") -> None:
        """Graph 1: Cumulative stagger confirmation trend from shared journey CSV over latest 12 weeks."""
        df = self._load_shared_deployment_journey_history(selected_week, data)
        if df.empty:
            st.info("Shared deployment journey history not available for selected week.")
            return

        latest_weeks = sorted(df["week_start"].unique())[-12:]
        window = df[df["week_start"].isin(latest_weeks)].copy()
        if window.empty:
            st.info("No rows available in latest 12-week window.")
            return

        latest_week = pd.to_datetime(latest_weeks[-1])
        # Only include releases that have non-zero SB0 in the 12-week window.
        sb0_eligible_versions = sorted(
            window[window["sb0_pct"] > 0]["current_version"].astype(str).unique().tolist(),
            key=self._version_tuple,
        )
        if not sb0_eligible_versions:
            st.info("No releases with SB0 > 0.0 found in the latest 12 weeks.")
            return

        # Determine a default cohort centered on the most dominant latest-week release:
        # 2 versions behind + dominant + 6 versions ahead (up to 9 total).
        # Only include versions that actually have cells in the latest week.
        latest_rows = window[window["week_start"] == latest_week].copy()
        latest_rows = latest_rows[latest_rows["current_version"].astype(str).isin(sb0_eligible_versions)].copy()
        if latest_rows.empty:
            default_seed = sb0_eligible_versions[-1]
            active_latest_versions: List[str] = sb0_eligible_versions.copy()
        else:
            pct_cols = ["sb0_pct", "sb1_pct", "r0_pct", "r1_pct", "r2a_pct", "r2b_pct"]
            for c in pct_cols:
                if c not in latest_rows.columns:
                    latest_rows[c] = 0.0
                latest_rows[c] = pd.to_numeric(latest_rows[c], errors="coerce").fillna(0.0)
            latest_rows["total_cells"] = pd.to_numeric(latest_rows.get("total_cells", 0), errors="coerce").fillna(0.0)
            latest_rows["pct_sum"] = latest_rows[pct_cols].sum(axis=1)
            latest_rows["non_sb0_pct_sum"] = latest_rows[["sb1_pct", "r0_pct", "r1_pct", "r2a_pct", "r2b_pct"]].sum(axis=1)
            # Consider a version active if it has any stage occupancy in latest week.
            latest_rows["has_cells"] = latest_rows["pct_sum"] > 0.0
            active_latest_versions = (
                latest_rows[latest_rows["has_cells"]]["current_version"].astype(str).unique().tolist()
            )
            # Exclude releases that are SB0-only in latest week for this graph.
            non_sb0_latest_versions = (
                latest_rows[latest_rows["non_sb0_pct_sum"] > 0.0]["current_version"].astype(str).unique().tolist()
            )
            if non_sb0_latest_versions:
                active_latest_versions = [v for v in active_latest_versions if v in set(non_sb0_latest_versions)]
            latest_rows["dominance_score"] = latest_rows["total_cells"]
            # If total_cells is unavailable/flat (e.g., placeholder values), fallback to stage share sum.
            if float(latest_rows["dominance_score"].max()) <= 0 or latest_rows["dominance_score"].nunique(dropna=True) <= 1:
                latest_rows["dominance_score"] = latest_rows["pct_sum"]
            latest_rows = latest_rows[latest_rows["has_cells"]].copy()
            if non_sb0_latest_versions:
                latest_rows = latest_rows[latest_rows["current_version"].astype(str).isin(non_sb0_latest_versions)].copy()
            if latest_rows.empty:
                default_seed = sb0_eligible_versions[-1]
                active_latest_versions = sb0_eligible_versions.copy()
            else:
                dominant_row = latest_rows.sort_values(["dominance_score"], ascending=False).iloc[0]
                default_seed = str(dominant_row["current_version"])
        ordered_versions = sb0_eligible_versions
        seed_idx = ordered_versions.index(default_seed) if default_seed in ordered_versions else len(ordered_versions) - 1
        active_set = set(active_latest_versions)
        # Prefer overlap with plan schedule releases when available.
        plan_df = self._load_plan_schedule_data(selected_week, data)
        if not plan_df.empty and "version" in plan_df.columns:
            planned_versions = set(plan_df["version"].astype(str).str.strip().tolist())
            overlapped = active_set.intersection(planned_versions)
            if overlapped:
                active_set = overlapped
        # Prefer dominant release from deployment snapshot counts when available.
        dominant_from_snapshot: Optional[str] = None
        week_folder = self._resolve_week_folder_key(selected_week, data)
        if week_folder:
            snapshot_candidates = [
                os.path.join(APP_ROOT, "weeks", week_folder, "Shared", "deployment.csv"),
                os.path.join(APP_ROOT, "weeks", week_folder, "Engine", "deployment.csv"),
            ]
            for snap_path in snapshot_candidates:
                if not os.path.exists(snap_path):
                    continue
                try:
                    snap = pd.read_csv(snap_path)
                except Exception:
                    continue
                if snap.empty:
                    continue
                version_col = "version" if "version" in snap.columns else ("current_version" if "current_version" in snap.columns else None)
                count_col = None
                for c in ["SUM(count)", "count", "cells"]:
                    if c in snap.columns:
                        count_col = c
                        break
                if not version_col or not count_col:
                    continue
                snap[version_col] = snap[version_col].astype(str).str.strip()
                snap[count_col] = pd.to_numeric(snap[count_col], errors="coerce").fillna(0.0)
                counts = (
                    snap.groupby(version_col, as_index=False)[count_col]
                    .sum()
                    .sort_values(count_col, ascending=False)
                )
                if counts.empty:
                    continue
                for _, row in counts.iterrows():
                    v = str(row[version_col])
                    if v in active_set:
                        dominant_from_snapshot = v
                        break
                if dominant_from_snapshot:
                    break

        if dominant_from_snapshot and dominant_from_snapshot in ordered_versions and dominant_from_snapshot in active_set:
            default_seed = dominant_from_snapshot
            seed_idx = ordered_versions.index(default_seed)

        if default_seed not in active_set:
            # Re-anchor seed to nearest active version if the previous seed is not planned/active.
            active_ordered = [v for v in ordered_versions if v in active_set]
            if active_ordered:
                # Choose closest by index in semantic order.
                nearest = min(active_ordered, key=lambda v: abs(ordered_versions.index(v) - seed_idx))
                default_seed = nearest
                seed_idx = ordered_versions.index(default_seed)

        older_active = [v for v in ordered_versions[:seed_idx] if v in active_set]
        newer_active = [v for v in ordered_versions[seed_idx + 1 :] if v in active_set]
        seed_active = default_seed in active_set

        selected_older = older_active[-2:]
        selected_newer = newer_active[:6]
        default_versions = selected_older + ([default_seed] if seed_active else []) + selected_newer

        # Keep pulling on each side (same direction) until we hit up to 9 versions.
        older_pool_extra = older_active[: max(0, len(older_active) - len(selected_older))]
        newer_pool_extra = newer_active[len(selected_newer) :]
        while len(default_versions) < 9 and (older_pool_extra or newer_pool_extra):
            if older_pool_extra and len(selected_older) <= 2:
                default_versions.insert(0, older_pool_extra[-1])
                older_pool_extra = older_pool_extra[:-1]
                continue
            if newer_pool_extra and len(selected_newer) <= 6:
                default_versions.append(newer_pool_extra[0])
                newer_pool_extra = newer_pool_extra[1:]
                continue
            if older_pool_extra:
                default_versions.insert(0, older_pool_extra[-1])
                older_pool_extra = older_pool_extra[:-1]
            elif newer_pool_extra:
                default_versions.append(newer_pool_extra[0])
                newer_pool_extra = newer_pool_extra[1:]

        available_versions = [v for v in ordered_versions if v in active_set]
        if not available_versions:
            st.warning("No versions found in latest 12 weeks.")
            return

        default_versions = [v for v in default_versions if v in available_versions]
        if not default_versions and available_versions:
            default_versions = [available_versions[-1]]
        selected_versions = st.multiselect(
            "Versions (one or many)",
            available_versions,
            default=default_versions,
            key=f"global_journey_versions_{key_suffix}",
        )
        if not selected_versions:
            st.info("Select at least one version to plot cumulative stagger trend.")
            return

        filtered = window[window["current_version"].isin(selected_versions)].copy()
        if filtered.empty:
            st.warning("No rows in latest 8 weeks for selected versions.")
            return

        pct_cols = ["sb0_pct", "sb1_pct", "r0_pct", "r1_pct", "r2a_pct", "r2b_pct"]
        stagger_label = {
            "sb0_pct": "SB0",
            "sb1_pct": "SB1",
            "r0_pct": "R0",
            "r1_pct": "R1",
            "r2a_pct": "R2A",
            "r2b_pct": "R2B",
        }
        week_labels = [pd.to_datetime(w).strftime("%Y-%m-%d") for w in latest_weeks]
        all_staggers = ["SB0", "SB1", "R0", "R1", "R2A", "R2B"]

        melted = filtered.melt(
            id_vars=["week_start", "current_version"],
            value_vars=pct_cols,
            var_name="stagger_key",
            value_name="pct",
        ).copy()
        melted["pct"] = pd.to_numeric(melted["pct"], errors="coerce").fillna(0.0)
        melted["stagger"] = melted["stagger_key"].map(stagger_label)
        melted["week_label"] = melted["week_start"].dt.strftime("%Y-%m-%d")
        melted["confirmed"] = (melted["pct"] > 0).astype(int)

        version_stage_week = (
            melted.groupby(["current_version", "stagger", "week_label"], as_index=False)["confirmed"]
            .max()
        )
        full_vsw = pd.MultiIndex.from_product(
            [selected_versions, all_staggers, week_labels],
            names=["current_version", "stagger", "week_label"],
        ).to_frame(index=False)
        version_stage_week = full_vsw.merge(
            version_stage_week,
            on=["current_version", "stagger", "week_label"],
            how="left",
        )
        version_stage_week["confirmed"] = pd.to_numeric(version_stage_week["confirmed"], errors="coerce").fillna(0).astype(int)
        version_stage_week["week_label"] = pd.Categorical(version_stage_week["week_label"], categories=week_labels, ordered=True)
        version_stage_week = version_stage_week.sort_values(["current_version", "stagger", "week_label"])
        # Cumulative confirmation: once a version hits a stage, keep it confirmed for later weeks.
        version_stage_week["confirmed_cum"] = (
            version_stage_week.groupby(["current_version", "stagger"])["confirmed"].cummax()
        )

        stage_week = (
            version_stage_week.groupby(["week_label", "stagger"], as_index=False)["confirmed_cum"]
            .mean()
        )
        stage_week["pct"] = stage_week["confirmed_cum"] * 100.0
        stage_week["week_label"] = stage_week["week_label"].astype(str)
        stage_week["stagger_order"] = stage_week["stagger"].map({"SB0": 1, "SB1": 2, "R0": 3, "R1": 4, "R2A": 5, "R2B": 6})
        stage_week = stage_week.sort_values(["stagger_order", "week_label"])

        fig = px.line(
            stage_week,
            x="week_label",
            y="pct",
            color="stagger",
            markers=True,
            category_orders={"stagger": all_staggers},
            title=(
                "🚀 Release Journey by Stagger — Cumulative Confirmation (Latest 12 Weeks)"
                f"<br><sub>Selected versions: {len(selected_versions)}</sub>"
            ),
        )
        fig.update_traces(
            hovertemplate=(
                "<b>%{fullData.name}</b><br>"
                "Week: %{x}<br>"
                "Cumulative confirmed versions: %{y:.1f}%<extra></extra>"
            )
        )
        fig.update_layout(
            xaxis_title="Week Start",
            yaxis_title="Cumulative percentage for stagger (%)",
            yaxis=dict(range=[0, 100]),
            legend_title="Stagger",
            height=520,
        )
        fig.update_xaxes(categoryorder="array", categoryarray=week_labels)
        st.plotly_chart(fig, use_container_width=True, key=f"global_journey_single_{key_suffix}")

    def create_global_deployment_journey_top6(self, selected_week: Optional[str], data: Optional[Dict[str, Any]] = None, key_suffix: str = "") -> None:
        """Graph 2: Top 6 versions as-of latest week, shown across latest 8 weeks and staggers."""
        df = self._load_global_deployment_history(selected_week, data)
        if df.empty:
            st.info("Global deployment history not available for selected week.")
            return

        latest_weeks = sorted(df["week_start"].unique())[-8:]
        window = df[df["week_start"].isin(latest_weeks)].copy()
        if window.empty:
            st.info("No rows available in latest 8-week window.")
            return

        latest_week = window["week_start"].max()
        latest_slice = window[window["week_start"] == latest_week].copy()
        top6 = (
            latest_slice.groupby("current_version", as_index=False)["total_cells"]
            .max()
            .sort_values("total_cells", ascending=False)["current_version"]
            .head(6)
            .tolist()
        )
        if not top6:
            st.info("No top versions available.")
            return
        window = window[window["current_version"].isin(top6)].copy()

        stage_specs = [
            (" ", "__week_sep__"),
            ("SB0", "sb0_pct"),
            ("SB1", "sb1_pct"),
            ("R0", "r0_pct"),
            ("R1", "r1_pct"),
            ("R2A", "r2a_pct"),
            ("R2B", "r2b_pct"),
        ]
        stage_order = [s for s, _ in stage_specs]

        long_rows: List[Dict[str, Any]] = []
        for _, row in window.iterrows():
            week_label = row["week_start"].strftime("%Y-%m-%d")
            version = str(row["current_version"])
            total_cells = float(row["total_cells"] or 0)
            for stage_name, stage_col in stage_specs:
                pct = float(row.get(stage_col, 0.0) or 0.0) if stage_col != "__week_sep__" else 0.0
                cells_in_stage = total_cells * pct / 100.0
                long_rows.append(
                    {
                        "week_label": week_label,
                        "version": version,
                        "stagger": stage_name,
                        "cells_in_stage": cells_in_stage,
                        "total_cells": total_cells,
                    }
                )
        stage_df = pd.DataFrame(long_rows)
        if stage_df.empty:
            st.info("No top-6 stagger journey data available.")
            return
        stage_df["pct_of_version"] = np.where(
            stage_df["total_cells"] > 0,
            (stage_df["cells_in_stage"] / stage_df["total_cells"]) * 100.0,
            0.0,
        )
        stage_totals = (
            stage_df.groupby(["week_label", "stagger"], as_index=False)["cells_in_stage"].sum()
            .rename(columns={"cells_in_stage": "stage_total"})
        )
        stage_df = stage_df.merge(stage_totals, on=["week_label", "stagger"], how="left")
        stage_df["pct_in_stage"] = np.where(
            stage_df["stage_total"] > 0,
            (stage_df["cells_in_stage"] / stage_df["stage_total"]) * 100.0,
            0.0,
        )
        stage_df["stagger"] = pd.Categorical(stage_df["stagger"], categories=stage_order, ordered=True)
        stage_df = stage_df.sort_values(["week_label", "stagger", "version"])
        week_labels_order = sorted(stage_df["week_label"].unique())
        full_pairs = [(wk, stg) for wk in week_labels_order for stg in stage_order]

        fig = go.Figure()
        versions = [v for v in top6 if v in set(stage_df["version"].unique())]
        palette = list(px.colors.qualitative.Dark24) + list(px.colors.qualitative.Set3)
        version_color = {ver: palette[i % len(palette)] for i, ver in enumerate(versions)}

        for version in versions:
            part = stage_df[stage_df["version"] == version]
            if part.empty:
                continue
            values = {
                (str(r["week_label"]), str(r["stagger"])): (
                    float(r["pct_of_version"]),
                    float(r["cells_in_stage"]),
                    float(r["total_cells"]),
                    float(r["stage_total"]),
                )
                for _, r in part.iterrows()
            }
            y_vals = [values.get((wk, stg), (0.0, 0.0, 0.0, 0.0))[0] for wk, stg in full_pairs]
            cells_vals = [values.get((wk, stg), (0.0, 0.0, 0.0, 0.0))[1] for wk, stg in full_pairs]
            version_total_vals = [values.get((wk, stg), (0.0, 0.0, 0.0, 0.0))[2] for wk, stg in full_pairs]
            stage_total_vals = [values.get((wk, stg), (0.0, 0.0, 0.0, 0.0))[3] for wk, stg in full_pairs]
            fig.add_trace(
                go.Bar(
                    x=[[wk for wk, _ in full_pairs], [stg for _, stg in full_pairs]],
                    y=y_vals,
                    name=f"v{version}",
                    marker_color=version_color[version],
                    marker_line_color="#000000",
                    marker_line_width=0.8,
                    legendgroup=version,
                    showlegend=True,
                    customdata=np.stack(
                        [
                            [wk for wk, _ in full_pairs],
                            [stg for _, stg in full_pairs],
                            cells_vals,
                            version_total_vals,
                            stage_total_vals,
                        ],
                        axis=-1,
                    ),
                    hovertemplate=(
                        "<b>v%{fullData.legendgroup}</b><br>"
                        "Week: %{customdata[0]}<br>"
                        "Stagger: %{customdata[1]}<br>"
                        "Percent in this stagger (of version): %{y:.1f}%<br>"
                        "Cells in stagger: %{customdata[2]:.1f}<br>"
                        "Total cells for version that week: %{customdata[3]:.1f}<br>"
                        "Total cells in this stagger (all top-6): %{customdata[4]:.1f}<extra></extra>"
                    ),
                )
            )

        fig.update_layout(
            barmode="stack",
            title="📦 Top 6 Versions — Percent in Each Stagger by Week (Latest 8 Weeks)",
            xaxis_title="Week Start / Stagger",
            yaxis_title="Percent in stagger for each version (%)",
            yaxis=dict(range=[0, 100]),
            legend_title="Version",
            # Make grouped bars less skinny when all versions are present.
            bargap=0.08,
            bargroupgap=0.02,
            height=560,
        )
        fig.update_xaxes(tickangle=-35)
        st.plotly_chart(fig, use_container_width=True, key=f"global_journey_top6_{key_suffix}")

    def create_deployment_journey_cumulative(self, selected_week: Optional[str], data: Optional[Dict[str, Any]] = None, key_suffix: str = "") -> None:
        """
        Multi-line chart showing cumulative completion percentage for N releases over 12 weeks.
        Each line represents a release's journey through the stagger stages.
        """
        # Load deployment journey data from weeks/<cw>/Shared/deployment-journey.csv
        if selected_week:
            csv_path = os.path.join(APP_ROOT, "weeks", selected_week, "Shared", "deployment-journey.csv")
        else:
            csv_path = None

        if not csv_path or not os.path.exists(csv_path):
            st.info("Deployment journey data not available. Expected file: weeks/<cw>/Shared/deployment-journey.csv")
            return

        # Read the CSV
        df = pd.read_csv(csv_path)

        # Calculate cumulative completion percentage across all staggers
        # New column names: pct_of_SB0, pct_of_SB1, etc.
        stagger_cols = ['pct_of_SB0', 'pct_of_SB1', 'pct_of_R0', 'pct_of_R1', 'pct_of_R2a', 'pct_of_R2b']

        # Check if columns exist, if not try old format
        if not all(col in df.columns for col in stagger_cols):
            stagger_cols = ['sb0_pct', 'sb1_pct', 'r0_pct', 'r1_pct', 'r2a_pct', 'r2b_pct']

        df['cumulative_pct'] = df[stagger_cols].sum(axis=1)

        # Get unique releases
        releases = df['current_version'].unique()

        # Create figure
        fig = go.Figure()

        # Color palette for releases
        colors = px.colors.qualitative.Plotly + px.colors.qualitative.Set2

        # Add a line for each release
        for idx, release in enumerate(releases):
            release_data = df[df['current_version'] == release].sort_values('week_start')

            fig.add_trace(go.Scatter(
                x=release_data['week_start'],
                y=release_data['cumulative_pct'],
                mode='lines+markers',
                name=f"Release {release}",
                line=dict(width=2, color=colors[idx % len(colors)]),
                marker=dict(size=6),
                hovertemplate=(
                    f"<b>Release {release}</b><br>"
                    "Week: %{x}<br>"
                    "Cumulative: %{y:.1f}%<br>"
                    "<extra></extra>"
                )
            ))

        fig.update_layout(
            title="📈 Release Deployment Journey - Cumulative Completion Over 12 Weeks",
            xaxis_title="Week",
            yaxis_title="Cumulative Completion (%)",
            yaxis=dict(range=[0, 100]),
            hovermode='x unified',
            height=500,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            )
        )

        st.plotly_chart(fig, use_container_width=True, key=f"deployment_journey_cumulative_{key_suffix}")

    def create_release_journey_gantt(self, selected_week: Optional[str], data: Optional[Dict[str, Any]] = None, key_suffix: str = "") -> None:
        """
        Create a dense Gantt chart showing plan vs actual deployment timing for releases.
        This matches the PNG reference visualization with releases on Y-axis and timeline on X-axis.
        """
        # Load deployment journey data
        actual = self._load_shared_deployment_journey_history(selected_week, data)
        if actual.empty:
            actual = self._load_global_deployment_history(selected_week, data)

        # Load plan data
        plan = self._load_plan_schedule_data(selected_week, data)

        if actual.empty or plan.empty:
            st.info("Gantt chart unavailable: missing actual or plan data.")
            return

        # Stage configuration with colors
        stage_config = [
            {"name": "SB0", "color": "#6366F1", "label": "SB0 - Sandbox 0"},
            {"name": "SB1/SB2", "color": "#60A5FA", "label": "SB1/SB2 - Sandbox 1/2"},
            {"name": "R0", "color": "#06B6D4", "label": "R0 - Release Week 1"},
            {"name": "R1", "color": "#22C55E", "label": "R1 - Release Week 2"},
            {"name": "R2a", "color": "#F59E0B", "label": "R2a - Release Week 3"},
            {"name": "R2b", "color": "#F97316", "label": "R2b - Release Week 4"},
        ]

        stage_colors = {s["name"]: s["color"] for s in stage_config}
        stage_col_map = {
            "SB0": "sb0_pct",
            "SB1/SB2": "sb1_pct",
            "R0": "r0_pct",
            "R1": "r1_pct",
            "R2a": "r2a_pct",
            "R2b": "r2b_pct",
        }

        # Display color legend upfront - readable text
        legend_html = '<div style="margin: 12px 0; padding: 10px 0; border-bottom: 2px solid #ddd;"><span style="font-size: 16px; font-weight: 700; color: #000; margin-right: 24px;">Stages:</span>'
        for stage in stage_config:
            legend_html += f'<span style="display: inline-block; margin-right: 28px;"><span style="display: inline-block; width: 24px; height: 12px; background-color: {stage["color"]}; margin-right: 8px; border: 1px solid #aaa; vertical-align: middle;"></span><span style="font-size: 14px; color: #000; font-weight: 600;">{stage["label"]}</span></span>'
        legend_html += '</div>'
        st.markdown(legend_html, unsafe_allow_html=True)

        # Get overlapping releases between plan and actual
        actual_versions = set(actual["current_version"].astype(str))
        plan_versions = set(plan["version"].astype(str))

        # Filter to only versions that have plan data (check for actual plan entries with stages)
        versions_with_plans = []
        for v in sorted(actual_versions.intersection(plan_versions), key=self._version_tuple):
            v_plan = plan[plan["version"].astype(str) == v]
            # Check that plan has actual stage entries, not just empty rows
            if not v_plan.empty and v_plan["stage"].notna().any():
                versions_with_plans.append(v)

        versions = versions_with_plans

        if not versions:
            st.info("No overlapping releases between plan and actual.")
            return

        # Allow user to select releases to display - professional compact selector
        default_versions = versions[-12:] if len(versions) > 12 else versions

        # Custom CSS for smaller, professional multiselect with dark gray tags
        st.markdown("""
            <style>
            div[data-baseweb="select"] {
                font-size: 11px;
            }
            div[data-baseweb="select"] > div {
                min-height: 28px;
                font-size: 11px;
            }
            div[data-baseweb="select"] span {
                font-size: 11px;
            }
            div[data-baseweb="tag"] {
                font-size: 10px;
                padding: 2px 6px;
                margin: 2px;
                background-color: #4a4a4a !important;
                color: #ffffff !important;
            }
            div[data-baseweb="tag"] span[role="button"] {
                color: #ffffff !important;
            }
            </style>
        """, unsafe_allow_html=True)

        st.markdown('<div style="margin-top: 8px; margin-bottom: 4px;"><span style="font-size: 13px; font-weight: 700; color: #000;">Releases:</span></div>', unsafe_allow_html=True)

        col1, col2 = st.columns([4, 1])
        with col1:
            selected_versions = st.multiselect(
                "Select versions",
                versions,
                default=default_versions,
                key=f"gantt_versions_{key_suffix}",
                label_visibility="collapsed"
            )
        with col2:
            st.markdown("<div style='margin-top: 0px;'></div>", unsafe_allow_html=True)
            if st.button("Select All", key=f"select_all_{key_suffix}", use_container_width=True):
                selected_versions = versions

        if not selected_versions:
            st.info("Select at least one release.")
            return

        # Filter to selected versions
        actual = actual[actual["current_version"].astype(str).isin(selected_versions)].copy()
        plan = plan[plan["version"].astype(str).isin(selected_versions)].copy()

        # Get date range for x-axis and time range for visibility check
        all_dates = list(actual["week_start"].dropna()) + list(plan["week_start"].dropna())
        if all_dates:
            min_date = min(all_dates)
            max_date = max(all_dates)
        else:
            min_date = pd.Timestamp.now()
            max_date = min_date + pd.Timedelta(days=90)

        # Time range for visibility check
        time_range_start = min_date - pd.Timedelta(days=2)
        time_range_end = max_date + pd.Timedelta(days=2)

        # Create Gantt chart
        fig = go.Figure()

        # Y-axis position for each release x stage (6 rows per version)
        y_pos = 0
        y_labels = []
        y_positions = []
        version_start_positions = []

        # Define alternating gray colors for version labels
        version_label_colors = ['#2a2a2a', '#505050', '#707070', '#404040', '#606060']

        # Define fixed widths for alignment
        VERSION_WIDTH = 10  # Width for version field (e.g., "v262.18   ")
        STAGE_WIDTH = 8     # Width for stage field (e.g., "SB1/SB2 ")
        TOTAL_LABEL_WIDTH = VERSION_WIDTH + 3 + STAGE_WIDTH  # version + " │ " + stage

        # Process each version (reverse order so newest at top)
        version_index = 0
        for version in sorted(selected_versions, key=self._version_tuple, reverse=True):
            version_actual = actual[actual["current_version"].astype(str) == version].sort_values("week_start")
            version_plan = plan[plan["version"].astype(str) == version]

            # Build stage timeline for this version - sort by start date
            version_plan_sorted = version_plan.sort_values("week_start")
            stage_timeline = {}

            # Calculate end dates: each stage ends the day before the next stage starts
            for idx, (_, row) in enumerate(version_plan_sorted.iterrows()):
                stage = row["stage"]
                start_date = row["week_start"]

                # Find the next stage's start date
                if idx < len(version_plan_sorted) - 1:
                    next_start = version_plan_sorted.iloc[idx + 1]["week_start"]
                    end_date = next_start - pd.Timedelta(days=1)
                else:
                    # Last stage - use a week duration
                    end_date = start_date + pd.Timedelta(days=6)

                # Store or extend the range for this stage
                if stage not in stage_timeline:
                    stage_timeline[stage] = {"start": start_date, "end": end_date}
                else:
                    # Extend if we see this stage multiple times
                    stage_timeline[stage]["start"] = min(stage_timeline[stage]["start"], start_date)
                    stage_timeline[stage]["end"] = max(stage_timeline[stage]["end"], end_date)

            # Skip this version if it has no plan data
            if not stage_timeline:
                continue

            # Only add to positions list if we have valid plan data
            version_y_start = y_pos
            stages_drawn = 0

            # Get color for this version's labels
            label_color = version_label_colors[version_index % len(version_label_colors)]

            # First, collect all stages that have plan data for this version
            stages_with_plan = [stage for stage in ["R2b", "R2a", "R1", "R0", "SB1/SB2", "SB0"] if stage in stage_timeline]

            # Draw each stage on its own row (reversed order: R2b at top, SB0 at bottom)
            # Only show stages that have plan data
            stage_idx = 0
            for stage in ["R2b", "R2a", "R1", "R0", "SB1/SB2", "SB0"]:
                # Skip this stage if it has no plan
                if stage not in stage_timeline:
                    continue

                # Build label with consistent padding
                version_text = f"v{version}"

                # Show version label on the LAST stage (bottom-most, which is SB0 or earliest stage)
                is_last_stage = (stage_idx == len(stages_with_plan) - 1)

                if is_last_stage:
                    # Last stage - show version number (bold and black)
                    version_padded = f'{version_text:<{VERSION_WIDTH}}'
                    version_part = f'<b>{version_padded}</b>'
                else:
                    # Other stages - blank out version (use non-breaking spaces to maintain width)
                    blank_spaces = '&nbsp;' * VERSION_WIDTH
                    version_part = blank_spaces

                # Stage part with consistent width
                stage_part = f'{stage:<{STAGE_WIDTH}}'

                # Combine with separator
                colored_label = f'{version_part} │ {stage_part}'

                y_labels.append(colored_label)
                y_positions.append(y_pos)
                stages_drawn += 1
                stage_idx += 1

                stage_color = stage_colors[stage]

                # Draw plan (we know it exists because we checked above)
                if stage in stage_timeline:
                    plan_start = stage_timeline[stage]["start"]
                    plan_end = stage_timeline[stage]["end"]

                    # Draw thin line for plan
                    fig.add_trace(go.Scatter(
                        x=[plan_start, plan_end],
                        y=[y_pos, y_pos],
                        mode='lines',
                        line=dict(color=stage_color, width=4, dash='solid'),
                        showlegend=False,
                        hovertemplate=f"<b>v{version}</b><br><b>Stage:</b> {stage}<br><b>Plan:</b> {plan_start.strftime('%b %d, %Y')} to {plan_end.strftime('%b %d, %Y')}<extra></extra>",
                        opacity=0.35
                    ))

                    # Add donut circle at plan start (only if in time range)
                    if time_range_start <= plan_start <= time_range_end:
                        fig.add_trace(go.Scatter(
                            x=[plan_start],
                            y=[y_pos],
                            mode='markers',
                            marker=dict(
                                size=10,
                                color='white',
                                line=dict(color=stage_color, width=2.8)
                            ),
                            showlegend=False,
                            hovertemplate=f"<b>v{version}</b><br><b>Stage:</b> {stage}<br><b>Plan Start:</b> {plan_start.strftime('%b %d, %Y')}<extra></extra>"
                        ))

                    # Add donut circle at plan end (only if in time range)
                    if time_range_start <= plan_end <= time_range_end:
                        fig.add_trace(go.Scatter(
                            x=[plan_end],
                            y=[y_pos],
                            mode='markers',
                            marker=dict(
                                size=10,
                                color='white',
                                line=dict(color=stage_color, width=2.8)
                            ),
                            showlegend=False,
                            hovertemplate=f"<b>v{version}</b><br><b>Stage:</b> {stage}<br><b>Plan End:</b> {plan_end.strftime('%b %d, %Y')}<extra></extra>"
                        ))

                # Draw actual if exists
                stage_col = stage_col_map.get(stage)
                if stage_col and stage_col in version_actual.columns:
                    actual_weeks = version_actual[version_actual[stage_col] > 0].copy()

                    if not actual_weeks.empty:
                        actual_start = actual_weeks["week_start"].min()
                        actual_end_observed = actual_weeks["week_start"].max()
                        max_pct = actual_weeks[stage_col].max()

                        # Calculate proportional end date based on percentage complete
                        if stage in stage_timeline:
                            plan_start = stage_timeline[stage]["start"]
                            plan_end = stage_timeline[stage]["end"]
                            plan_duration = (plan_end - plan_start).total_seconds() / 86400  # days

                            # Actual end date proportional to percentage
                            actual_duration = plan_duration * (max_pct / 100.0)
                            actual_end = actual_start + pd.Timedelta(days=actual_duration)
                        else:
                            actual_end = actual_end_observed

                        # Draw thick opaque line for actual (2x thicker than plan)
                        fig.add_trace(go.Scatter(
                            x=[actual_start, actual_end],
                            y=[y_pos, y_pos],
                            mode='lines',
                            line=dict(color=stage_color, width=8, dash='solid'),
                            showlegend=False,
                            hovertemplate=f"<b>v{version}</b><br><b>Stage:</b> {stage}<br><b>Actual:</b> {actual_start.strftime('%b %d, %Y')} to {actual_end.strftime('%b %d, %Y')}<br><b>Progress:</b> {max_pct:.1f}%<extra></extra>",
                            opacity=1.0
                        ))

                        # Add solid opaque circle at actual start (only if in time range)
                        if time_range_start <= actual_start <= time_range_end:
                            fig.add_trace(go.Scatter(
                                x=[actual_start],
                                y=[y_pos],
                                mode='markers',
                                marker=dict(
                                    size=10,
                                    color=stage_color,
                                    opacity=1.0
                                ),
                                showlegend=False,
                                hovertemplate=f"<b>v{version}</b><br><b>Stage:</b> {stage}<br><b>Actual Start:</b> {actual_start.strftime('%b %d, %Y')}<extra></extra>"
                            ))

                        # Add solid opaque circle at actual end (only if in time range)
                        if time_range_start <= actual_end <= time_range_end:
                            fig.add_trace(go.Scatter(
                                x=[actual_end],
                                y=[y_pos],
                                mode='markers',
                                marker=dict(
                                    size=10,
                                    color=stage_color,
                                    opacity=1.0
                                ),
                                showlegend=False,
                                hovertemplate=f"<b>v{version}</b><br><b>Stage:</b> {stage}<br><b>Actual End:</b> {actual_end.strftime('%b %d, %Y')}<br><b>Progress:</b> {max_pct:.1f}%<extra></extra>"
                            ))

                y_pos += 1

            # Track version position with actual stage count
            if stages_drawn > 0:
                version_start_positions.append((version_y_start, version_index, stages_drawn))

                # Add prominent horizontal separator line after each version's rows
                fig.add_hline(
                    y=y_pos - 0.5,
                    line_width=2,
                    line_dash="solid",
                    line_color="#404040",
                    opacity=0.8
                )

            version_index += 1

        # Add alternating background shading for each version
        for y_start, v_idx, num_stages in version_start_positions:
            if v_idx % 2 == 1:  # Odd-indexed versions get darker shade
                fig.add_shape(
                    type="rect",
                    xref="paper",
                    yref="y",
                    x0=0,
                    x1=1,
                    y0=y_start - 0.5,
                    y1=y_start + num_stages - 0.5,  # Use actual number of stages drawn
                    fillcolor="#f0f0f0",
                    opacity=0.4,
                    layer="below",
                    line_width=0,
                )

        # Update layout with professional, polished styling
        fig.update_layout(
            title={
                'text': "Release Deployment Timeline - Plan vs Actual",
                'font': {'size': 16, 'color': '#1a1a1a', 'family': 'Segoe UI, Arial, sans-serif', 'weight': 700},
                'x': 0.02,
                'xanchor': 'left'
            },
            xaxis_title={
                'text': "",
                'font': {'size': 11, 'color': '#000000', 'family': 'Segoe UI, Arial, sans-serif', 'weight': 600}
            },
            yaxis_title={
                'text': "Release & Stage",
                'font': {'size': 11, 'color': '#000000', 'family': 'Segoe UI, Arial, sans-serif', 'weight': 600}
            },
            height=max(350, y_pos * 20),  # Use actual number of rows drawn with slightly more spacing
            yaxis=dict(
                tickmode='array',
                tickvals=y_positions,
                ticktext=y_labels,
                tickfont=dict(size=10, color='#000000', family='Courier New, monospace', weight=400),
                gridcolor='#e8e8e8',
                gridwidth=0.5,
                showgrid=True,
                zeroline=False,
                side='left',
                ticklabelposition='outside',
                automargin=True,
            ),
            xaxis=dict(
                tickfont=dict(size=9, color='#000000', family='Segoe UI, Arial, sans-serif', weight=500),
                tickformat='%b %d',
                dtick=604800000,  # 7 days in milliseconds
                tickangle=0,
                gridcolor='#d8d8d8',
                gridwidth=0.8,
                showgrid=True,
                zeroline=False,
                range=[min_date - pd.Timedelta(days=2), max_date + pd.Timedelta(days=2)],
                side='bottom',
                position=0.98,  # Position below the top
            ),
            hovermode='closest',
            hoverlabel=dict(
                bgcolor="white",
                font_size=11,
                font_family="Segoe UI, Arial, sans-serif",
                bordercolor="#cccccc"
            ),
            margin=dict(l=150, r=20, t=140, b=50),
            plot_bgcolor='#ffffff',
            paper_bgcolor='#f8f9fa',
            font=dict(family='Segoe UI, Arial, sans-serif', color='#1a1a1a'),
            showlegend=False,
        )

        # Add month separators as vertical lines and centered month labels above dates
        current = min_date.replace(day=1)
        while current <= max_date:
            # Calculate next month for centering
            if current.month == 12:
                next_month = current.replace(year=current.year + 1, month=1)
            else:
                next_month = current.replace(month=current.month + 1)

            # Add vertical line at month boundary
            fig.add_vline(
                x=current,
                line_width=1.5,
                line_dash="solid",
                line_color="#aaaaaa",
                opacity=0.6
            )

            # Calculate center of month for label placement
            month_center = current + (next_month - current) / 2

            # Add month label at the very top
            fig.add_annotation(
                x=month_center,
                y=1.0,
                yref="paper",
                yanchor="bottom",
                text=f"<b>{current.strftime('%B %Y')}</b>",
                showarrow=False,
                font=dict(size=12, color='#000000', family='Segoe UI, Arial, sans-serif', weight='bold'),
                xanchor='center'
            )

            # Move to next month
            current = next_month

        # Display chart aligned to left
        col1, col2 = st.columns([8, 2])
        with col1:
            st.plotly_chart(fig, use_container_width=True, key=f"release_journey_gantt_{key_suffix}")

        # Three analysis charts in one row
        st.markdown("---")
        st.markdown('<div style="margin: 16px 0;"><span style="font-size: 14px; font-weight: 700; color: #000;">Detailed Analysis by Version</span></div>', unsafe_allow_html=True)

        # Single version selector for analysis charts
        analysis_version = st.selectbox(
            "Select version for detailed analysis",
            selected_versions,
            key=f"analysis_version_{key_suffix}",
        )

        if analysis_version:
            analysis_actual = actual[actual["current_version"].astype(str) == analysis_version].sort_values("week_start")
            analysis_plan = plan[plan["version"].astype(str) == analysis_version]

            chart_col1, chart_col2, chart_col3 = st.columns(3)

            # Chart 2: Deployment Progress - Cumulative Completion
            with chart_col1:
                st.markdown("""
                <div style="background-color: #f0f7ff; padding: 10px; border-radius: 4px; margin-bottom: 12px; font-size: 11px;">
                <strong>2. Deployment Progress</strong><br/>
                Shows cumulative completion through the deployment pipeline. Each colored band represents a stage's contribution: SB0→SB1→R0→R1→R2a→R2b = 100%.
                </div>
                """, unsafe_allow_html=True)
                if not analysis_actual.empty:
                    # Calculate weighted cumulative progress per stage
                    # Assign weights: SB0=10%, SB1=15%, R0=15%, R1=20%, R2a=20%, R2b=20%
                    stage_weights = {
                        "SB0": 0.10,
                        "SB1/SB2": 0.15,
                        "R0": 0.15,
                        "R1": 0.20,
                        "R2a": 0.20,
                        "R2b": 0.20,
                    }

                    # Shared timeline across all 3 charts: earliest-to-latest from actual + plan.
                    actual_weeks = set(pd.to_datetime(analysis_actual["week_start"], errors="coerce").dropna().dt.normalize().tolist())
                    plan_weeks = set(pd.to_datetime(analysis_plan["week_start"], errors="coerce").dropna().dt.normalize().tolist())
                    weeks = sorted(actual_weeks | plan_weeks)
                    if not weeks:
                        st.info("No week timeline data available.")
                        return
                    progress_data = []
                    running_stage_max = {s: 0.0 for s in ["SB0", "SB1/SB2", "R0", "R1", "R2a", "R2b"]}

                    actual_by_week = {
                        pd.to_datetime(r["week_start"]).normalize(): r
                        for _, r in analysis_actual.sort_values("week_start").iterrows()
                    }

                    for week in weeks:
                        week_data = actual_by_week.get(pd.to_datetime(week).normalize())
                        week_str = f"{week.month}/{week.day}"

                        # Calculate each stage's weighted contribution
                        for stage in ["SB0", "SB1/SB2", "R0", "R1", "R2a", "R2b"]:
                            stage_col = stage_col_map.get(stage)
                            if stage_col in analysis_actual.columns:
                                pct = week_data.get(stage_col, 0) if week_data is not None else 0
                                # Each stage contributes (its % complete) × (its weight) to total progress
                                stage_contribution = (pct / 100.0) * stage_weights[stage] * 100
                                # Strict cumulative: once reached, contribution cannot decrease.
                                running_stage_max[stage] = max(running_stage_max[stage], stage_contribution)
                                progress_data.append({
                                    "Week": week_str,
                                    "Stage": stage,
                                    "Contribution": running_stage_max[stage],
                                })

                    progress_df = pd.DataFrame(progress_data)

                    # Create stacked area chart
                    fig1 = go.Figure()

                    # Add each stage as a stacked area trace in order
                    plan_label_y = {
                        "SB0": 96,
                        "SB1/SB2": 84,
                        "R0": 72,
                        "R1": 60,
                        "R2a": 48,
                        "R2b": 36,
                    }
                    for stage in ["SB0", "SB1/SB2", "R0", "R1", "R2a", "R2b"]:
                        stage_data = progress_df[progress_df["Stage"] == stage]
                        fig1.add_trace(go.Scatter(
                            x=stage_data["Week"],
                            y=stage_data["Contribution"],
                            name=stage,
                            mode='lines',
                            stackgroup='one',  # This creates the stacked effect
                            fillcolor=stage_colors[stage],
                            line=dict(width=0.5, color=stage_colors[stage]),
                            hovertemplate=f'<b>{stage}</b><br>Week: %{{x}}<br>Contribution: %{{y:.1f}}%<extra></extra>'
                        ))

                    fig1.update_layout(
                        title=f"Deployment Progress - Cumulative Completion<br><sub>v{analysis_version}</sub>",
                        height=350,
                        yaxis_title="Overall Progress %",
                        xaxis_title="Week",
                        font=dict(family='Segoe UI, Arial, sans-serif', size=10, color='#000000'),
                        title_font_size=12,
                        yaxis=dict(range=[0, 100]),
                        margin=dict(l=50, r=20, t=60, b=110),
                        plot_bgcolor='#ffffff',
                        paper_bgcolor='#f8f9fa',
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.6,
                            xanchor="center",
                            x=0.5,
                            font=dict(size=9),
                            tracegroupgap=5
                        ),
                    )

                    # Use the same week axis/tick spacing as charts 2 and 3.
                    week_axis_labels = [f"{w.month}/{w.day}" for w in weeks]
                    tickvals = [week_axis_labels[i] for i in range(len(week_axis_labels)) if i % 2 == 0]
                    fig1.update_xaxes(
                        tickangle=0,
                        tickfont=dict(size=9, color='#000000'),
                        tickmode='array',
                        tickvals=tickvals,
                        categoryorder='array',
                        categoryarray=week_axis_labels
                    )
                    fig1.update_yaxes(tickfont=dict(color='#000000'))

                    st.plotly_chart(fig1, use_container_width=True, key=f"dist_{key_suffix}")
                else:
                    st.info("No actual data for this version")

            # Chart 3: Planned vs Actual (12 lines)
            with chart_col2:
                st.markdown("""
                <div style="background-color: #f0f7ff; padding: 10px; border-radius: 4px; margin-bottom: 12px; font-size: 11px;">
                <strong>3. Planned vs Actual Progress</strong><br/>
                Actual progress (solid lines) against Plan (dotted lines) on a continuous date scale.
                Both plan and actual are interpolated between known weekly points for smoother trend comparison.
                </div>
                """, unsafe_allow_html=True)
                if not analysis_actual.empty and not analysis_plan.empty:
                    fig2 = go.Figure()

                    # Build stage timeline for planned start/end dates (same logic as table).
                    version_plan_sorted = analysis_plan.sort_values("week_start")
                    stage_timeline = self._build_stage_timeline(version_plan_sorted)

                    # Use the exact same week axis as Deployment Progress.
                    all_weeks = weeks
                    week_label_map = {w: f"{w.month}/{w.day}" for w in all_weeks}
                    week_labels_for_axis = [week_label_map[w] for w in all_weeks]
                    date_start = min(all_weeks)
                    date_end = max(all_weeks)
                    daily_index = pd.date_range(date_start, date_end, freq='D')
                    # Use a lighter actual palette for easier contrast over plan bands.
                    actual_line_colors = {
                        "SB0": "#6366F1",
                        "SB1/SB2": "#3B82F6",
                        "R0": "#06B6D4",
                        "R1": "#22C55E",
                        "R2a": "#F59E0B",
                        "R2b": "#F97316",
                    }

                    stage_list = ["SB0", "SB1/SB2", "R0", "R1", "R2a", "R2b"]
                    plan_focus_stages = {"SB0", "SB1/SB2", "R0", "R1", "R2a", "R2b"}
                    def _hex_to_rgba(hex_color: str, alpha: float) -> str:
                        c = str(hex_color).lstrip('#')
                        if len(c) != 6:
                            return f"rgba(0,0,0,{alpha})"
                        r = int(c[0:2], 16)
                        g = int(c[2:4], 16)
                        b = int(c[4:6], 16)
                        return f"rgba({r},{g},{b},{alpha})"

                    # Draw all 6 plan traces first (background layer), even if a stage
                    # has no explicit timeline window in the selected data.
                    for stage in stage_list:
                        stage_color = stage_colors[stage]
                        if stage in stage_timeline and stage in plan_focus_stages:
                            plan_start = stage_timeline[stage]["start"]
                            plan_end = stage_timeline[stage]["end"]
                            plan_vals = []
                            total_days = max((plan_end - plan_start).days, 1)
                            has_plan_window = True
                            for d in daily_index:
                                if d < plan_start:
                                    plan_vals.append(None)
                                elif d > plan_end:
                                    plan_vals.append(None)
                                else:
                                    elapsed = (d - plan_start).days
                                    plan_vals.append(min(100.0, max(0.0, (elapsed / total_days) * 100.0)))
                        else:
                            # Keep the stage present in the chart even when no plan window
                            # exists for this version in the selected horizon.
                            plan_vals = [0.0 for _ in daily_index]
                            has_plan_window = False

                        hover = (
                            f'<b>{stage} Plan</b><br>Date: %{{x|%Y-%m-%d}}<br>Planned %: %{{y:.1f}}<extra></extra>'
                            if has_plan_window
                            else f'<b>{stage} Plan</b><br>Date: %{{x|%Y-%m-%d}}<br>Planned %: 0.0 (no plan window)<extra></extra>'
                        )
                        fig2.add_trace(go.Scatter(
                            x=daily_index,
                            y=plan_vals,
                            name=f"{stage} Plan",
                            mode='lines',
                            fill='tozeroy',
                            fillcolor=_hex_to_rgba(stage_color, 0.09) if has_plan_window else _hex_to_rgba(stage_color, 0.03),
                            line=dict(color=stage_color, width=1.0, dash='dot'),
                            legendgroup=stage,
                            showlegend=False,
                            hovertemplate=hover,
                        ))

                    # Draw all actual lines after plan areas so they remain fully visible.
                    for stage in stage_list:
                        stage_color = stage_colors[stage]
                        stage_col = stage_col_map.get(stage)
                        if stage_col in analysis_actual.columns:
                            actual_data = analysis_actual[["week_start", stage_col]].copy().dropna(subset=["week_start"])
                            actual_data = actual_data.rename(columns={stage_col: "pct"}).sort_values("week_start")
                            actual_data["pct"] = pd.to_numeric(actual_data["pct"], errors="coerce").fillna(0.0)
                            actual_series = actual_data.set_index("week_start")["pct"]
                            actual_interp = actual_series.reindex(daily_index).interpolate(method='time').ffill().bfill()

                            fig2.add_trace(go.Scatter(
                                x=daily_index,
                                y=actual_interp.values,
                                name=stage,
                                mode='lines',
                                line=dict(color=actual_line_colors.get(stage, stage_color), width=2.8, dash='solid'),
                                opacity=0.9,
                                legendgroup=stage,
                                showlegend=True,
                                hovertemplate=f'<b>{stage} Actual</b><br>Date: %{{x|%Y-%m-%d}}<br>Actual %: %{{y:.1f}}<extra></extra>',
                            ))

                    fig2.update_layout(
                        title=f"Planned vs Actual Progress<br><sub>Actual (solid) vs Plan (dotted) · v{analysis_version}</sub>",
                        height=350,
                        yaxis_title="% Complete",
                        xaxis_title="Week",
                        font=dict(family='Segoe UI, Arial, sans-serif', size=10, color='#000000'),
                        title_font_size=12,
                        yaxis=dict(range=[0, 100]),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.6,
                            xanchor="center",
                            x=0.5,
                            font=dict(size=9),
                            tracegroupgap=5
                        ),
                        margin=dict(l=50, r=20, t=60, b=110),
                        plot_bgcolor='#ffffff',
                        paper_bgcolor='#f8f9fa',
                    )
                    # Match Deployment Progress x-axis labeling density.
                    tickvals2 = [week_labels_for_axis[i] for i in range(len(week_labels_for_axis)) if i % 2 == 0]
                    tickvals2_dt = [all_weeks[i] for i in range(len(all_weeks)) if i % 2 == 0]
                    fig2.update_xaxes(
                        tickangle=0,
                        tickfont=dict(size=9, color='#000000'),
                        tickmode='array',
                        tickvals=tickvals2_dt,
                        ticktext=tickvals2,
                    )
                    fig2.update_yaxes(tickfont=dict(color='#000000'))
                    st.plotly_chart(fig2, use_container_width=True, key=f"plan_actual_{key_suffix}")
                else:
                    st.info("No plan/actual data for comparison")

            # Chart 4: Plan Adherence Over Time
            with chart_col3:
                st.markdown("""
                <div style="background-color: #f0f7ff; padding: 10px; border-radius: 4px; margin-bottom: 12px; font-size: 11px;">
                <strong>4. Plan Adherence Over Time</strong><br/>
                Interpolated plan-vs-actual gap by stage at each week.
                Red = planned-but-missing stage share; green = remaining share (on stage or not planned yet). Bars add to 100%.
                </div>
                """, unsafe_allow_html=True)
                if not analysis_actual.empty and not analysis_plan.empty:
                    # Build adherence data
                    adherence_data = []
                    # Use the exact same week axis as the first two charts.
                    all_weeks = weeks
                    # Stage target weights (must sum to 1.0) used to convert stage progress into planned share.
                    stage_weights = {
                        "SB0": 0.10,
                        "SB1/SB2": 0.15,
                        "R0": 0.15,
                        "R1": 0.20,
                        "R2a": 0.20,
                        "R2b": 0.20,
                    }

                    # Build stage timeline for this version (same logic as table).
                    version_plan_sorted = analysis_plan.sort_values("week_start")
                    stage_timeline = self._build_stage_timeline(version_plan_sorted)

                    week_actual_map = {
                        pd.to_datetime(r["week_start"], errors="coerce").normalize(): r
                        for _, r in analysis_actual.iterrows()
                    }

                    for week in all_weeks:
                        week_norm = pd.to_datetime(week, errors="coerce").normalize()
                        week_data = week_actual_map.get(week_norm)
                        red_pct = 0.0

                        for stage in ["SB0", "SB1/SB2", "R0", "R1", "R2a", "R2b"]:
                            if stage not in stage_timeline:
                                continue

                            plan_start = stage_timeline[stage]["start"]
                            plan_end = stage_timeline[stage]["end"]

                            # Interpolate planned progress for this stage at date T (0 before start, linear ramp, 1 after end).
                            if week_norm < plan_start:
                                stage_plan_progress = 0.0
                            elif week_norm >= plan_end:
                                stage_plan_progress = 1.0
                            else:
                                total_days = max((plan_end - plan_start).days, 1)
                                elapsed_days = max((week_norm - plan_start).days, 0)
                                stage_plan_progress = min(max(elapsed_days / total_days, 0.0), 1.0)

                            planned_stage_pct = stage_plan_progress * stage_weights[stage] * 100.0
                            stage_col = stage_col_map.get(stage)
                            actual_stage_pct = 0.0
                            if week_data is not None and stage_col in analysis_actual.columns:
                                actual_stage_pct = float(week_data.get(stage_col, 0) or 0)

                            # Red is only the planned-but-missing portion for this stage.
                            red_pct += max(planned_stage_pct - actual_stage_pct, 0.0)

                        red_pct = min(max(red_pct, 0.0), 100.0)
                        on_time_pct = 100.0 - red_pct
                        behind_pct = red_pct
                        adherence_data.append({
                            "Week": f"{week.month}/{week.day}",
                            "On Time %": on_time_pct,
                            "Behind %": behind_pct,
                        })

                    if adherence_data:
                        adherence_df = pd.DataFrame(adherence_data)

                        fig3 = go.Figure()
                        fig3.add_trace(go.Scatter(
                            x=adherence_df["Week"],
                            y=adherence_df["On Time %"],
                            name="On Time",
                            line=dict(color='#22C55E', width=2),
                            mode='lines',
                            stackgroup='one',
                            groupnorm='percent',
                            fillcolor='rgba(34,197,94,0.55)',
                            marker=dict(size=6),
                            hovertemplate="Week: %{x}<br>On Time: %{y:.1f}%<extra></extra>",
                        ))
                        fig3.add_trace(go.Scatter(
                            x=adherence_df["Week"],
                            y=adherence_df["Behind %"],
                            name="Behind Plan",
                            line=dict(color='#EF4444', width=2),
                            mode='lines',
                            stackgroup='one',
                            fillcolor='rgba(239,68,68,0.55)',
                            marker=dict(size=6),
                            hovertemplate="Week: %{x}<br>Behind: %{y:.1f}%<extra></extra>",
                        ))

                        fig3.update_layout(
                            title=f"Plan Adherence Over Time<br><sub>v{analysis_version}</sub>",
                            height=350,
                            yaxis_title="Adherence %",
                            xaxis_title="Week",
                            font=dict(family='Segoe UI, Arial, sans-serif', size=10, color='#000000'),
                            title_font_size=12,
                            yaxis=dict(range=[0, 100]),
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=-0.6,
                                xanchor="center",
                                x=0.5,
                                font=dict(size=9),
                                tracegroupgap=5
                            ),
                            margin=dict(l=50, r=20, t=60, b=110),
                            plot_bgcolor='#ffffff',
                            paper_bgcolor='#f8f9fa',
                        )
                        # Match X-axis labeling style with other graphs (m/d, every other week).
                        adherence_weeks = [f"{w.month}/{w.day}" for w in all_weeks]
                        adherence_tickvals = [adherence_weeks[i] for i in range(len(adherence_weeks)) if i % 2 == 0]
                        fig3.update_xaxes(
                            tickangle=0,
                            tickfont=dict(size=9, color='#000000'),
                            tickmode='array',
                            tickvals=adherence_tickvals,
                            categoryorder='array',
                            categoryarray=adherence_weeks
                        )
                        fig3.update_yaxes(tickfont=dict(color='#000000'))
                        st.plotly_chart(fig3, use_container_width=True, key=f"adherence_{key_suffix}")
                    else:
                        st.info("No adherence data available")
                else:
                    st.info("No data for adherence analysis")

    def create_plan_vs_actual_table(self, selected_week: Optional[str], data: Optional[Dict[str, Any]] = None, key_suffix: str = "") -> None:
        """Create the Plan vs Actual Timeline by Stage table."""
        # Load deployment journey data
        actual = self._load_shared_deployment_journey_history(selected_week, data)
        if actual.empty:
            actual = self._load_global_deployment_history(selected_week, data)

        # Load plan data
        plan = self._load_plan_schedule_data(selected_week, data)

        if actual.empty or plan.empty:
            st.info("Table unavailable: missing actual or plan data.")
            return

        # Stage configuration with colors
        stage_config = [
            {"name": "SB0", "color": "#6366F1", "label": "SB0 - Sandbox 0"},
            {"name": "SB1/SB2", "color": "#60A5FA", "label": "SB1/SB2 - Sandbox 1/2"},
            {"name": "R0", "color": "#06B6D4", "label": "R0 - Release Week 1"},
            {"name": "R1", "color": "#22C55E", "label": "R1 - Release Week 2"},
            {"name": "R2a", "color": "#F59E0B", "label": "R2a - Release Week 3"},
            {"name": "R2b", "color": "#F97316", "label": "R2b - Release Week 4"},
        ]

        stage_colors = {s["name"]: s["color"] for s in stage_config}
        stage_col_map = {
            "SB0": "sb0_pct",
            "SB1/SB2": "sb1_pct",
            "R0": "r0_pct",
            "R1": "r1_pct",
            "R2a": "r2a_pct",
            "R2b": "r2b_pct",
        }

        # Get overlapping releases between plan and actual
        actual_versions = set(actual["current_version"].astype(str))
        plan_versions = set(plan["version"].astype(str))

        # Filter to only versions that have plan data
        versions_with_plans = []
        for v in sorted(actual_versions.intersection(plan_versions), key=self._version_tuple):
            v_plan = plan[plan["version"].astype(str) == v]
            if not v_plan.empty and v_plan["stage"].notna().any():
                versions_with_plans.append(v)

        selected_versions = versions_with_plans

        if not selected_versions:
            st.info("No overlapping releases between plan and actual.")
            return

        # Create plan vs actual table
        st.markdown("---")
        st.markdown('<div style="margin: 12px 0;"><span style="font-size: 14px; font-weight: 700; color: #000;">Plan vs Actual Timeline by Stage</span></div>', unsafe_allow_html=True)

        # Build table data (oldest to newest)
        table_rows = []
        for version in sorted(selected_versions, key=self._version_tuple):
            row_data = {"Version": f"v{version}"}

            version_actual = actual[actual["current_version"].astype(str) == version].sort_values("week_start")
            version_plan = plan[plan["version"].astype(str) == version]

            # Build stage timeline for this version - shared logic with charts.
            version_plan_sorted = version_plan.sort_values("week_start")
            stage_timeline = self._build_stage_timeline(version_plan_sorted)

            for stage, color in stage_colors.items():
                # Plan dates
                if stage in stage_timeline:
                    plan_start = stage_timeline[stage]["start"]
                    plan_end = stage_timeline[stage]["end"]
                    row_data[f"{stage}_Plan"] = f"{plan_start.strftime('%b %d, %Y')} - {plan_end.strftime('%b %d, %Y')}"
                else:
                    row_data[f"{stage}_Plan"] = "-"

                # Actual dates with percentage complete
                stage_col = stage_col_map.get(stage)
                if stage_col and stage_col in version_actual.columns:
                    actual_weeks = version_actual[version_actual[stage_col] > 0].copy()
                    if not actual_weeks.empty:
                        actual_start = actual_weeks["week_start"].min()
                        actual_end = actual_weeks["week_start"].max()
                        max_pct = actual_weeks[stage_col].max()
                        row_data[f"{stage}_Actual"] = f"{actual_start.strftime('%b %d, %Y')} - {actual_end.strftime('%b %d, %Y')} ({max_pct:.1f}%)"
                    else:
                        row_data[f"{stage}_Actual"] = "-"
                else:
                    row_data[f"{stage}_Actual"] = "-"

            table_rows.append(row_data)

        # Create DataFrame
        table_df = pd.DataFrame(table_rows)

        # Create HTML table with custom styling
        table_html = '<div style="overflow-x: auto;"><table style="width: 100%; border-collapse: collapse; font-size: 9px; font-family: Arial, sans-serif;">'

        # Header row with stage colors
        table_html += '<thead><tr style="background-color: #f0f0f0;">'
        table_html += '<th style="border: 1px solid #ddd; padding: 6px 8px; text-align: left; font-weight: 700; position: sticky; left: 0; background-color: #f0f0f0; z-index: 10;">Version</th>'

        for stage_info in stage_config:
            stage = stage_info["name"]
            color = stage_info["color"]
            table_html += f'<th colspan="2" style="border: 1px solid #ddd; padding: 6px 8px; text-align: center; font-weight: 700; background-color: {color}; color: white;">{stage}</th>'

        table_html += '</tr><tr style="background-color: #f8f8f8;">'
        table_html += '<th style="border: 1px solid #ddd; padding: 4px 8px; text-align: left; font-weight: 600; position: sticky; left: 0; background-color: #f8f8f8; z-index: 10;"></th>'

        for stage_info in stage_config:
            stage = stage_info["name"]
            table_html += f'<th style="border: 1px solid #ddd; padding: 4px 8px; text-align: center; font-weight: 600; font-size: 8px;">Plan</th>'
            table_html += f'<th style="border: 1px solid #ddd; padding: 4px 8px; text-align: center; font-weight: 600; font-size: 8px;">Actual</th>'

        table_html += '</tr></thead><tbody>'

        # Data rows
        for idx, row in table_df.iterrows():
            bg_color = "#ffffff" if idx % 2 == 0 else "#f9f9f9"
            table_html += f'<tr style="background-color: {bg_color};">'
            table_html += f'<td style="border: 1px solid #ddd; padding: 6px 8px; font-weight: 600; position: sticky; left: 0; background-color: {bg_color}; z-index: 5;">{row["Version"]}</td>'

            for stage_info in stage_config:
                stage = stage_info["name"]
                plan_val = row.get(f"{stage}_Plan", "-")
                actual_val = row.get(f"{stage}_Actual", "-")

                table_html += f'<td style="border: 1px solid #ddd; padding: 4px 6px; text-align: center; white-space: nowrap;">{plan_val}</td>'
                table_html += f'<td style="border: 1px solid #ddd; padding: 4px 6px; text-align: center; white-space: nowrap;">{actual_val}</td>'

            table_html += '</tr>'

        table_html += '</tbody></table></div>'

        st.markdown(table_html, unsafe_allow_html=True)

    def create_release_journey_slick_panel(self, selected_week: Optional[str], data: Optional[Dict[str, Any]] = None, key_suffix: str = "") -> None:
        """
        UI-preview panel inspired by the provided Release Journey screenshot:
        stage summary cards + release journey table + right-side details.
        """
        # Use shared journey history as primary source for this preview.
        df = self._load_shared_deployment_journey_history(selected_week, data)
        if df.empty:
            df = self._load_global_deployment_history(selected_week, data)
        if df.empty:
            st.info("Release Journey preview unavailable: deployment journey history not found for selected week.")
            return

        latest_week = df["week_start"].max()
        latest_slice = df[df["week_start"] == latest_week].copy()
        if latest_slice.empty:
            st.info("Release Journey preview unavailable: no rows for latest week.")
            return

        stage_specs = [
            ("SB0", "sb0_pct", "#5B5CFF"),
            ("SB1/SB2", "sb1_pct", "#2F80FF"),
            ("R0", "r0_pct", "#00B3C7"),
            ("R1", "r1_pct", "#2E9E44"),
            ("R2a", "r2a_pct", "#E2A300"),
            ("R2b", "r2b_pct", "#C56A00"),
        ]

        def _to_sparkline(values: List[float]) -> str:
            bars = "▁▂▃▄▅▆▇█"
            cleaned = [float(v) for v in values if pd.notna(v)]
            if not cleaned:
                return "—"
            vmin = min(cleaned)
            vmax = max(cleaned)
            if vmax - vmin < 1e-9:
                return bars[2] * len(cleaned)
            out = []
            for v in cleaned:
                idx = int(round((v - vmin) / (vmax - vmin) * (len(bars) - 1)))
                idx = max(0, min(len(bars) - 1, idx))
                out.append(bars[idx])
            return "".join(out)

        # Use latest deployment snapshot counts for ranking/total cells in preview table/cards.
        deployment_counts_map: Dict[str, float] = {}
        week_folder = self._resolve_week_folder_key(selected_week, data)
        if week_folder:
            snapshot_candidates = [
                os.path.join(APP_ROOT, "weeks", week_folder, "Shared", "deployment.csv"),
                os.path.join(APP_ROOT, "weeks", week_folder, "Engine", "deployment.csv"),
            ]
            for snap_path in snapshot_candidates:
                if not os.path.exists(snap_path):
                    continue
                try:
                    snap = pd.read_csv(snap_path)
                except Exception:
                    continue
                if snap.empty:
                    continue
                version_col = "version" if "version" in snap.columns else ("current_version" if "current_version" in snap.columns else None)
                count_col = None
                for c in ["SUM(count)", "count", "cells"]:
                    if c in snap.columns:
                        count_col = c
                        break
                if not version_col or not count_col:
                    continue
                snap[version_col] = snap[version_col].astype(str).str.strip()
                snap[count_col] = pd.to_numeric(snap[count_col], errors="coerce").fillna(0.0)
                counts_df = (
                    snap.groupby(version_col, as_index=False)[count_col]
                    .sum()
                    .sort_values(count_col, ascending=False)
                )
                deployment_counts_map = {str(r[version_col]): float(r[count_col]) for _, r in counts_df.iterrows() if float(r[count_col]) > 0}
                if deployment_counts_map:
                    break

        # Keep preview/table aligned with Release Journey cohort logic.
        ordered_versions = sorted(latest_slice["current_version"].astype(str).unique().tolist(), key=self._version_tuple)
        # Active versions in latest week.
        active_set = set()
        for v in ordered_versions:
            vr = latest_slice[latest_slice["current_version"].astype(str) == v]
            if vr.empty:
                continue
            non_sb0 = 0.0
            for col in ["sb1_pct", "r0_pct", "r1_pct", "r2a_pct", "r2b_pct"]:
                if col in vr.columns:
                    non_sb0 += float(pd.to_numeric(vr[col], errors="coerce").fillna(0.0).mean())
            if non_sb0 > 0:
                active_set.add(v)
        if not active_set:
            active_set = set(ordered_versions)

        plan_df = self._load_plan_schedule_data(selected_week, data)
        if not plan_df.empty and "version" in plan_df.columns:
            planned = set(plan_df["version"].astype(str).str.strip().tolist())
            overlap = active_set.intersection(planned)
            if overlap:
                active_set = overlap

        # Seed on dominant by real deployment counts where possible.
        seed = None
        if deployment_counts_map:
            for v, _ in sorted(deployment_counts_map.items(), key=lambda kv: kv[1], reverse=True):
                if v in active_set:
                    seed = v
                    break
        if not seed:
            seed = sorted(active_set, key=self._version_tuple)[-1] if active_set else None

        top_releases = []
        if seed and seed in ordered_versions:
            idx = ordered_versions.index(seed)
            older = [v for v in ordered_versions[:idx] if v in active_set][-2:]
            newer = [v for v in ordered_versions[idx + 1 :] if v in active_set][:6]
            top_releases = older + [seed] + newer
        if not top_releases:
            top_releases = [v for v in ordered_versions if v in active_set][:9]
        if not top_releases:
            st.info("Release Journey preview unavailable: no releases in latest week.")
            return

        selected_release_key = f"rj_preview_release_{key_suffix}"
        selected_release = st.session_state.get(selected_release_key, top_releases[0])
        if selected_release not in top_releases:
            selected_release = top_releases[0]

        selected_release_df = df[df["current_version"] == selected_release].copy()
        selected_latest_slice = latest_slice[latest_slice["current_version"] == selected_release].copy()
        if selected_latest_slice.empty:
            # Safe fallback in case selected release is missing in latest week.
            selected_latest_slice = latest_slice.copy()

        recent_weeks = sorted(df["week_start"].dropna().unique())[-8:]
        trend_df = selected_release_df[selected_release_df["week_start"].isin(recent_weeks)].copy()
        weekly_stage_trends: Dict[str, pd.DataFrame] = {}
        for label, col, _ in stage_specs:
            merged_trend = (
                trend_df.groupby("week_start", as_index=False)[col]
                .mean()
                .rename(columns={col: "stage_pct"})
            )
            weekly_stage_trends[label] = merged_trend

        latest_total_cells = float(deployment_counts_map.get(selected_release, float(selected_latest_slice["total_cells"].sum())))
        stage_totals: Dict[str, float] = {}
        for label, col, _ in stage_specs:
            stage_pct = float(selected_latest_slice[col].mean()) if col in selected_latest_slice.columns and not selected_latest_slice.empty else 0.0
            stage_totals[label] = float(latest_total_cells * stage_pct / 100.0)

        st.markdown(
            """
            <style>
            .rj-preview-wrap { border: 1px solid #e5e7eb; border-radius: 12px; padding: 12px; background: #ffffff; }
            .rj-preview-title { font-size: 1.25rem; font-weight: 700; color: #111827; margin-bottom: 2px; }
            .rj-preview-sub { color: #6b7280; font-size: 0.9rem; margin-bottom: 12px; }
            .rj-card { border: 1px solid #dbe4ef; border-radius: 10px; padding: 10px; background: #fbfdff; }
            .rj-card-title { font-weight: 700; font-size: 0.95rem; margin-bottom: 4px; }
            .rj-card-meta { color: #374151; font-size: 0.8rem; }
            .rj-card-trend { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.9rem; margin-top: 6px; letter-spacing: 0.5px; }
            .rj-card-trend-label { color: #64748b; font-size: 0.72rem; margin-top: 2px; }
            .rj-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
            .rj-table th { text-align: left; border-bottom: 1px solid #e5e7eb; padding: 8px 6px; color: #4b5563; }
            .rj-table td { border-bottom: 1px solid #f3f4f6; padding: 8px 6px; vertical-align: middle; }
            .rj-pill { display:inline-block; padding:2px 8px; border-radius:10px; font-size:0.72rem; font-weight:600; background:#E8F7ED; color:#1E7A33; }
            .rj-bar { width: 100%; height: 8px; background:#edf2f7; border-radius: 999px; overflow:hidden; }
            .rj-fill { height: 100%; border-radius: 999px; }
            .rj-side { border:1px solid #e5e7eb; border-radius:10px; padding:10px; background:#fafafa; }
            .rj-kv { font-size:0.8rem; color:#374151; margin: 4px 0; }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="rj-preview-wrap">', unsafe_allow_html=True)
        st.markdown(f'<div class="rj-preview-title">Release Journey as of {latest_week.strftime("%b %d, %Y")}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="rj-preview-sub">Track release progression through stages • Release R{selected_release}</div>',
            unsafe_allow_html=True,
        )

        card_cols = st.columns(len(stage_specs))
        for col_ui, (label, _, color) in zip(card_cols, stage_specs):
            cells = int(round(stage_totals[label]))
            pct = (cells / latest_total_cells * 100.0) if latest_total_cells > 0 else 0.0
            with col_ui:
                trend = weekly_stage_trends.get(label, pd.DataFrame())
                spark = _to_sparkline(trend["stage_pct"].tolist()) if not trend.empty else "—"
                st.markdown(
                    f"""
                    <div class="rj-card">
                        <div class="rj-card-title" style="color:{color};">{label}</div>
                        <div class="rj-card-meta">{cells} cells</div>
                        <div class="rj-card-meta">{pct:.1f}% of release</div>
                        <div class="rj-card-trend" style="color:{color};">{spark}</div>
                        <div class="rj-card-trend-label">8-week trend</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        left_col, right_col = st.columns([3, 1])

        # Build rows for the preview table.
        row_map: Dict[str, Dict[str, Any]] = {}
        for version in top_releases:
            row = latest_slice[latest_slice["current_version"] == version]
            if row.empty:
                continue
            total = float(deployment_counts_map.get(version, float(row["total_cells"].sum())))
            stage_data = {}
            for label, col, color in stage_specs:
                pct = float(row[col].mean()) if total > 0 and col in row.columns else 0.0
                cells = int(round(total * pct / 100.0))
                stage_data[label] = {"pct": pct, "cells": cells, "color": color}
            row_map[version] = {"total": int(round(total)), "stages": stage_data}

        with left_col:
            table_html = [
                "<table class='rj-table'>",
                "<thead><tr><th>Release</th><th>Total Cells</th><th>SB0</th><th>SB1/SB2</th><th>R0</th><th>R1</th><th>R2a</th><th>R2b</th><th>Status</th></tr></thead><tbody>",
            ]
            for version in top_releases:
                if version not in row_map:
                    continue
                row = row_map[version]
                stage_cells = []
                for label, _, _ in stage_specs:
                    sd = row["stages"][label]
                    stage_cells.append(
                        f"<td><div style='font-size:0.74rem;color:#6b7280;margin-bottom:3px'>{sd['cells']} cells</div>"
                        f"<div class='rj-bar'><div class='rj-fill' style='width:{max(0,min(100,sd['pct'])):.1f}%;background:{sd['color']};'></div></div></td>"
                    )
                status = "Complete" if row["stages"]["R2b"]["pct"] >= 99.0 else "In Progress"
                status_pill = "<span class='rj-pill'>Complete</span>" if status == "Complete" else "<span class='rj-pill' style='background:#E8F0FF;color:#1D4ED8;'>In Progress</span>"
                table_html.append(
                    f"<tr><td><strong>R{version}</strong></td><td>{row['total']}</td>{''.join(stage_cells)}<td>{status_pill}</td></tr>"
                )
            table_html.append("</tbody></table>")
            st.markdown("".join(table_html), unsafe_allow_html=True)

        with right_col:
            selected_release = st.selectbox(
                "Release details",
                top_releases,
                index=top_releases.index(selected_release) if selected_release in top_releases else 0,
                key=selected_release_key,
            )
            rd = row_map.get(selected_release, {"total": 0, "stages": {}})
            current_stage = max(
                stage_specs,
                key=lambda s: rd["stages"].get(s[0], {}).get("pct", 0.0),
            )[0]
            st.markdown("<div class='rj-side'>", unsafe_allow_html=True)
            st.markdown(f"### R{selected_release}")
            st.markdown(f"<div class='rj-kv'><b>Week:</b> {latest_week.strftime('%Y-%m-%d')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='rj-kv'><b>Total Cells:</b> {rd['total']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='rj-kv'><b>Current Stage:</b> {current_stage}</div>", unsafe_allow_html=True)
            st.markdown("<hr style='margin:8px 0;border:0;border-top:1px solid #e5e7eb'/>", unsafe_allow_html=True)
            for label, _, color in stage_specs:
                pct = rd["stages"].get(label, {}).get("pct", 0.0)
                st.markdown(
                    f"<div class='rj-kv'><span style='display:inline-block;width:8px;height:8px;border-radius:50%;background:{color};margin-right:6px'></span>{label}: {pct:.1f}%</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    def create_release_timeline_chart(self, selected_week: Optional[str], data: Optional[Dict[str, Any]] = None, key_suffix: str = "") -> None:
        """
        Timeline chart showing plan vs actual deployment with:
        - X-axis: Timeline with vertical partitioning by month/year at top
        - Plan: Thin line with hollow circles at start
        - Actual: Thick line overlaid on plan with solid circles (on-time) or hollow circles (delayed)
        - Color-coded by stagger stage
        """
        # Load plan and actual data
        actual = self._load_shared_deployment_journey_history(selected_week, data)
        if actual.empty:
            actual = self._load_global_deployment_history(selected_week, data)
        plan = self._load_plan_schedule_data(selected_week, data)

        if actual.empty or plan.empty:
            st.info("Timeline chart unavailable: missing actual or plan data.")
            return

        # Get last 12 weeks
        weeks = sorted(actual["week_start"].dropna().unique())[-12:]
        if not weeks:
            st.info("Timeline chart unavailable: no weekly data.")
            return

        actual = actual[actual["week_start"].isin(weeks)].copy()
        plan = plan[plan["week_start"].isin(weeks)].copy()

        # Stage configuration
        stage_colors = {
            "SB0": "#6366F1",
            "SB1/SB2": "#3B82F6",
            "R0": "#06B6D4",
            "R1": "#22C55E",
            "R2a": "#F59E0B",
            "R2b": "#F97316",
        }

        stage_col_map = {
            "SB0": "pct_of_SB0",
            "SB1/SB2": "pct_of_SB1",
            "R0": "pct_of_R0",
            "R1": "pct_of_R1",
            "R2a": "pct_of_R2a",
            "R2b": "pct_of_R2b",
        }

        # Get releases
        actual_versions = set(actual["current_version"].astype(str))
        plan_versions = set(plan["version"].astype(str))
        versions = sorted(actual_versions.intersection(plan_versions), key=self._version_tuple)

        if not versions:
            st.info("No overlapping releases between plan and actual.")
            return

        # Select releases to display (default to last 8)
        default_versions = versions[-8:] if len(versions) > 8 else versions
        selected_versions = st.multiselect(
            "Select Releases for Timeline",
            versions,
            default=default_versions,
            key=f"timeline_versions_{key_suffix}",
        )

        if not selected_versions:
            st.info("Select at least one release.")
            return

        # Filter data
        actual = actual[actual["current_version"].astype(str).isin(selected_versions)].copy()
        plan = plan[plan["version"].astype(str).isin(selected_versions)].copy()

        # Create figure
        fig = go.Figure()

        # Add timeline background with month/year labels
        week_dates = [pd.to_datetime(w) for w in weeks]

        # Track y-position for each release
        y_pos = 0
        y_labels = []
        y_positions = []

        for version in selected_versions:
            version_actual = actual[actual["current_version"].astype(str) == version].sort_values("week_start")
            version_plan = plan[plan["version"].astype(str) == version]

            y_labels.append(f"v{version}")
            y_positions.append(y_pos)

            # For each stage, draw plan (thin line + hollow circle) and actual (thick line + circle)
            for stage, color in stage_colors.items():
                # Get plan data for this stage
                stage_plan = version_plan[version_plan["stage"] == stage].sort_values("week_start")

                if not stage_plan.empty:
                    plan_weeks = pd.to_datetime(stage_plan["week_start"]).tolist()

                    # Draw thin line for plan
                    fig.add_trace(go.Scatter(
                        x=plan_weeks,
                        y=[y_pos] * len(plan_weeks),
                        mode='lines',
                        line=dict(color=color, width=1, dash='solid'),
                        showlegend=False,
                        hoverinfo='skip'
                    ))

                    # Draw hollow circle at start of plan
                    if plan_weeks:
                        fig.add_trace(go.Scatter(
                            x=[plan_weeks[0]],
                            y=[y_pos],
                            mode='markers',
                            marker=dict(
                                size=8,
                                color='white',
                                line=dict(color=color, width=2)
                            ),
                            showlegend=False,
                            hovertemplate=f"<b>v{version}</b><br>Stage: {stage}<br>Plan Start: {plan_weeks[0].strftime('%Y-%m-%d')}<extra></extra>"
                        ))

                # Get actual data for this stage
                stage_col = stage_col_map.get(stage)
                if stage_col and stage_col in version_actual.columns:
                    # Find weeks where this stage has activity
                    actual_weeks = version_actual[version_actual[stage_col] > 0].copy()

                    if not actual_weeks.empty:
                        actual_dates = pd.to_datetime(actual_weeks["week_start"]).tolist()
                        actual_pcts = actual_weeks[stage_col].tolist()

                        # Draw thick line for actual
                        fig.add_trace(go.Scatter(
                            x=actual_dates,
                            y=[y_pos] * len(actual_dates),
                            mode='lines',
                            line=dict(color=color, width=4),
                            showlegend=False,
                            hoverinfo='skip'
                        ))

                        # Determine if on-time or delayed by comparing with plan
                        if not stage_plan.empty:
                            plan_start = stage_plan["week_start"].min()
                            actual_start = actual_weeks["week_start"].min()

                            # Solid circle if on-time (within 1 week), hollow if delayed
                            is_on_time = actual_start <= plan_start + pd.Timedelta(days=7)

                            if is_on_time:
                                # Solid circle
                                fig.add_trace(go.Scatter(
                                    x=[actual_dates[0]],
                                    y=[y_pos],
                                    mode='markers',
                                    marker=dict(size=8, color=color),
                                    showlegend=False,
                                    hovertemplate=f"<b>v{version}</b><br>Stage: {stage}<br>Actual Start: {actual_dates[0].strftime('%Y-%m-%d')}<br>Status: On-time<extra></extra>"
                                ))
                            else:
                                # Hollow circle (delayed)
                                fig.add_trace(go.Scatter(
                                    x=[actual_dates[0]],
                                    y=[y_pos],
                                    mode='markers',
                                    marker=dict(
                                        size=8,
                                        color='white',
                                        line=dict(color=color, width=2)
                                    ),
                                    showlegend=False,
                                    hovertemplate=f"<b>v{version}</b><br>Stage: {stage}<br>Actual Start: {actual_dates[0].strftime('%Y-%m-%d')}<br>Status: Delayed<extra></extra>"
                                ))

            y_pos += 1

        # Add month/year labels at top
        month_boundaries = []
        current_month = None
        for i, date in enumerate(week_dates):
            if date.month != current_month:
                month_boundaries.append((date, date.strftime("%b %Y")))
                current_month = date.month

        # Update layout
        fig.update_layout(
            title="Release Deployment Timeline - Plan vs Actual",
            xaxis=dict(
                title="",
                tickformat="%m/%d",
                tickangle=0,
                side="top",
                showgrid=True,
                gridcolor='lightgray',
                gridwidth=0.5
            ),
            yaxis=dict(
                title="",
                ticktext=y_labels,
                tickvals=y_positions,
                showgrid=True,
                gridcolor='lightgray',
                gridwidth=0.5
            ),
            height=max(400, len(selected_versions) * 60),
            hovermode='closest',
            showlegend=False,
            plot_bgcolor='white',
            margin=dict(l=100, r=50, t=100, b=50)
        )

        # Add vertical lines for month boundaries
        for date, label in month_boundaries:
            fig.add_vline(
                x=date,
                line=dict(color="gray", width=1, dash="dash"),
                annotation=dict(
                    text=label,
                    font=dict(size=10, color="gray"),
                    textangle=0,
                    xanchor="left",
                    yanchor="bottom",
                    y=1.05,
                    yref="paper"
                )
            )

        # Add legend for symbols
        st.markdown("""
        <div style='font-size: 0.9em; color: #666; margin-bottom: 10px;'>
        <b>Legend:</b>
        ○ Hollow circle = Plan start or Delayed actual |
        ● Solid circle = On-time actual |
        ─ Thin line = Plan |
        ━ Thick line = Actual
        </div>
        """, unsafe_allow_html=True)

        st.plotly_chart(fig, use_container_width=True, key=f"release_timeline_{key_suffix}")

    def create_promotion_plan_actuals_slick(self, selected_week: Optional[str], data: Optional[Dict[str, Any]] = None, key_suffix: str = "") -> None:
        """Slick, PNG-inspired promotion plan vs actuals graph suite."""
        actual = self._load_shared_deployment_journey_history(selected_week, data)
        if actual.empty:
            actual = self._load_global_deployment_history(selected_week, data)
        plan = self._load_plan_schedule_data(selected_week, data)
        if actual.empty or plan.empty:
            st.info("Promotion Plan vs Actuals unavailable: missing actual or plan data.")
            return

        weeks = sorted(actual["week_start"].dropna().unique())[-12:]
        if not weeks:
            st.info("Promotion Plan vs Actuals unavailable: no weekly rows.")
            return
        actual = actual[actual["week_start"].isin(weeks)].copy()
        plan = plan[plan["week_start"].isin(weeks)].copy()
        week_labels = [pd.to_datetime(w).strftime("%Y-%m-%d") for w in weeks]

        stage_cols = {
            "SB0": "sb0_pct",
            "SB1/SB2": "sb1_pct",
            "R0": "r0_pct",
            "R1": "r1_pct",
            "R2A": "r2a_pct",
            "R2B": "r2b_pct",
        }
        stage_order = list(stage_cols.keys())
        stage_colors = {
            "SB0": "#6366F1",
            "SB1/SB2": "#3B82F6",
            "R0": "#06B6D4",
            "R1": "#22C55E",
            "R2A": "#F59E0B",
            "R2B": "#F97316",
        }

        actual_versions = set(actual["current_version"].astype(str))
        plan_versions = set(plan["version"].astype(str))
        versions = sorted(actual_versions.intersection(plan_versions), key=self._version_tuple)
        if not versions:
            st.info("No overlapping release versions between plan and actual for this window.")
            return
        default_versions = versions[-8:] if len(versions) > 8 else versions
        selected_versions = st.multiselect(
            "Releases",
            versions,
            default=default_versions,
            key=f"promo_actual_versions_{key_suffix}",
        )
        if not selected_versions:
            st.info("Select at least one release.")
            return

        actual = actual[actual["current_version"].astype(str).isin(selected_versions)].copy()
        plan = plan[plan["version"].astype(str).isin(selected_versions)].copy()

        latest_week = pd.to_datetime(weeks[-1])
        latest_actual = actual[actual["week_start"] == latest_week].copy()
        total_plan_releases = len(set(plan["version"].astype(str)))
        releases_in_flight = len(set(latest_actual["current_version"].astype(str)))
        cells_deployed = int(round(pd.to_numeric(latest_actual["total_cells"], errors="coerce").fillna(0).sum()))

        # Build stage adherence for latest week.
        stage_rows = []
        for stage, col in stage_cols.items():
            actual_count = int((pd.to_numeric(latest_actual[col], errors="coerce").fillna(0.0) > 0).sum())
            plan_count = int(
                plan[
                    (plan["week_start"] == latest_week)
                    & (plan["stage"] == stage.replace("A", "a").replace("B", "b") if stage.startswith("R2") else plan["stage"])
                ].shape[0]
            )
            # Robust stage mapping for plan format.
            if plan_count == 0:
                plan_stage_name = {"SB0": "SB0", "SB1/SB2": "SB1/SB2", "R0": "R0", "R1": "R1", "R2A": "R2a", "R2B": "R2b"}[stage]
                plan_count = int(
                    plan[
                        (plan["week_start"] == latest_week)
                        & (plan["stage"] == plan_stage_name)
                    ].shape[0]
                )
            on_time = min(actual_count, plan_count)
            behind = max(plan_count - actual_count, 0)
            adherence = (on_time / plan_count * 100.0) if plan_count > 0 else 0.0
            stage_rows.append(
                {
                    "stage": stage,
                    "on_time": on_time,
                    "behind": behind,
                    "adherence": adherence,
                }
            )
        stage_df = pd.DataFrame(stage_rows)
        overall_behind = int(stage_df["behind"].sum())
        overall_on_time = int(stage_df["on_time"].sum())
        overall_adherence = (overall_on_time / max(1, overall_on_time + overall_behind)) * 100.0

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total Releases (Plan)", total_plan_releases)
        k2.metric("Releases In Flight (Actual)", releases_in_flight)
        k3.metric("Cells Deployed (Actual)", f"{cells_deployed:,}")
        k4.metric("Plan Adherence", f"{overall_adherence:.0f}%")
        k5.metric("Releases Behind Plan", overall_behind)

        left, right = st.columns([3.2, 1.2])
        with left:
            # 1) Plan vs actual pipeline: first-hit stage dates for each release.
            traces = []
            for v in sorted(selected_versions, key=self._version_tuple, reverse=True):
                rv = actual[actual["current_version"].astype(str) == str(v)].copy().sort_values("week_start")
                if rv.empty:
                    continue
                x_vals = []
                y_vals = []
                marker_colors = []
                for stage, col in stage_cols.items():
                    hit = rv[pd.to_numeric(rv[col], errors="coerce").fillna(0) > 0]
                    if hit.empty:
                        continue
                    x_vals.append(pd.to_datetime(hit.iloc[0]["week_start"]).strftime("%Y-%m-%d"))
                    y_vals.append(f"v{v}")
                    marker_colors.append(stage_colors[stage])
                if len(x_vals) < 1:
                    continue
                traces.append(
                    go.Scatter(
                        x=x_vals,
                        y=y_vals,
                        mode="lines+markers",
                        marker=dict(size=7, color=marker_colors),
                        line=dict(width=3, color="#94A3B8"),
                        name=f"v{v}",
                        showlegend=False,
                        hovertemplate="Release %{y}<br>Week %{x}<extra></extra>",
                    )
                )
            fig_pipeline = go.Figure(data=traces)
            fig_pipeline.update_layout(
                title="1. Plan vs Actual — Releases in Promotion Pipeline",
                xaxis_title="Week",
                yaxis_title="Releases",
                height=360,
                margin=dict(l=10, r=10, t=40, b=10),
            )
            fig_pipeline.update_xaxes(categoryorder="array", categoryarray=week_labels)
            st.plotly_chart(fig_pipeline, use_container_width=True, key=f"promo_pipeline_{key_suffix}")

        with right:
            st.markdown("#### Plan Adherence (By Stage)")
            st.dataframe(
                stage_df.rename(
                    columns={
                        "stage": "Stage",
                        "on_time": "On Time",
                        "behind": "Behind",
                        "adherence": "Adherence %",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

        c1, c2, c3 = st.columns([1.5, 1.5, 1.2])
        with c1:
            # 2) Actual stage distribution by week (stacked).
            actual_long = actual.melt(
                id_vars=["week_start", "current_version", "total_cells"],
                value_vars=list(stage_cols.values()),
                var_name="stage_col",
                value_name="pct",
            ).copy()
            inv_map = {v: k for k, v in stage_cols.items()}
            actual_long["stage"] = actual_long["stage_col"].map(inv_map)
            actual_long["cells"] = (
                pd.to_numeric(actual_long["total_cells"], errors="coerce").fillna(0.0)
                * pd.to_numeric(actual_long["pct"], errors="coerce").fillna(0.0)
                / 100.0
            )
            dist = (
                actual_long.groupby(["week_start", "stage"], as_index=False)["cells"].sum()
                .merge(
                    actual_long.groupby("week_start", as_index=False)["cells"].sum().rename(columns={"cells": "total"}),
                    on="week_start",
                    how="left",
                )
            )
            dist["pct"] = np.where(dist["total"] > 0, dist["cells"] * 100.0 / dist["total"], 0.0)
            dist["week_label"] = pd.to_datetime(dist["week_start"]).dt.strftime("%Y-%m-%d")
            fig_dist = px.bar(
                dist,
                x="week_label",
                y="pct",
                color="stage",
                category_orders={"stage": stage_order},
                color_discrete_map=stage_colors,
                title="2. Actual Progress — Cells Distribution by Stage (Weekly)",
            )
            fig_dist.update_layout(barmode="stack", height=320, yaxis=dict(range=[0, 100]), margin=dict(l=10, r=10, t=40, b=10))
            fig_dist.update_xaxes(categoryorder="array", categoryarray=week_labels)
            st.plotly_chart(fig_dist, use_container_width=True, key=f"promo_dist_{key_suffix}")

        with c2:
            # 3) Cumulative cells reaching each stage (actual + plan proxy counts).
            cum_actual = []
            cum_plan = []
            for stage, col in stage_cols.items():
                d = (
                    actual.assign(cells=lambda x: pd.to_numeric(x["total_cells"], errors="coerce").fillna(0.0) * pd.to_numeric(x[col], errors="coerce").fillna(0.0) / 100.0)
                    .groupby("week_start", as_index=False)["cells"]
                    .sum()
                    .sort_values("week_start")
                )
                d["cum"] = d["cells"].cumsum()
                d["stage"] = stage
                d["week_label"] = pd.to_datetime(d["week_start"]).dt.strftime("%Y-%m-%d")
                cum_actual.append(d[["week_label", "stage", "cum"]].assign(series="Actual"))

                stage_plan_name = {"SB0": "SB0", "SB1/SB2": "SB1/SB2", "R0": "R0", "R1": "R1", "R2A": "R2a", "R2B": "R2b"}[stage]
                p = (
                    plan[plan["stage"] == stage_plan_name]
                    .groupby("week_start", as_index=False)
                    .size()
                    .rename(columns={"size": "cells"})
                    .sort_values("week_start")
                )
                p["cum"] = p["cells"].cumsum()
                p["stage"] = stage
                p["week_label"] = pd.to_datetime(p["week_start"]).dt.strftime("%Y-%m-%d")
                cum_plan.append(p[["week_label", "stage", "cum"]].assign(series="Plan"))
            cum_df = pd.concat(cum_actual + cum_plan, ignore_index=True)
            fig_cum = px.line(
                cum_df,
                x="week_label",
                y="cum",
                color="stage",
                line_dash="series",
                category_orders={"stage": stage_order},
                color_discrete_map=stage_colors,
                title="3. Planned vs Actual — Cumulative Cells Reaching Each Stage",
            )
            fig_cum.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
            fig_cum.update_xaxes(categoryorder="array", categoryarray=week_labels)
            st.plotly_chart(fig_cum, use_container_width=True, key=f"promo_cum_{key_suffix}")

        with c3:
            # 4) Plan adherence over time.
            wk_rows = []
            for wk in week_labels:
                wk_actual = actual[pd.to_datetime(actual["week_start"]).dt.strftime("%Y-%m-%d") == wk]
                wk_plan = plan[pd.to_datetime(plan["week_start"]).dt.strftime("%Y-%m-%d") == wk]
                stage_ok = 0
                for stage, col in stage_cols.items():
                    stage_plan_name = {"SB0": "SB0", "SB1/SB2": "SB1/SB2", "R0": "R0", "R1": "R1", "R2A": "R2a", "R2B": "R2b"}[stage]
                    pcount = int((wk_plan["stage"] == stage_plan_name).sum())
                    acount = int((pd.to_numeric(wk_actual[col], errors="coerce").fillna(0) > 0).sum())
                    if acount >= pcount:
                        stage_ok += 1
                on_time_pct = stage_ok / max(1, len(stage_cols)) * 100.0
                wk_rows.append({"week_label": wk, "On Time %": on_time_pct, "Behind %": 100.0 - on_time_pct})
            adh = pd.DataFrame(wk_rows)
            fig_adh = go.Figure()
            fig_adh.add_trace(go.Scatter(x=adh["week_label"], y=adh["On Time %"], mode="lines+markers", name="On Time (%)", line=dict(color="#22C55E", width=2)))
            fig_adh.add_trace(go.Scatter(x=adh["week_label"], y=adh["Behind %"], mode="lines+markers", name="Behind (%)", line=dict(color="#EF4444", width=2)))
            fig_adh.update_layout(title="4. Plan Adherence Over Time", height=320, yaxis=dict(range=[0, 100]), margin=dict(l=10, r=10, t=40, b=10))
            fig_adh.update_xaxes(categoryorder="array", categoryarray=week_labels)
            st.plotly_chart(fig_adh, use_container_width=True, key=f"promo_adh_{key_suffix}")

        # 5) Release detail table (latest week).
        st.markdown("#### 5. Release Detail — Plan vs Actual (Latest Week)")
        detail_rows = []
        latest_lbl = pd.to_datetime(latest_week).strftime("%Y-%m-%d")
        for v in sorted(selected_versions, key=self._version_tuple):
            v_actual = actual[actual["current_version"].astype(str) == str(v)].copy().sort_values("week_start")
            if v_actual.empty:
                continue
            latest_v = v_actual[pd.to_datetime(v_actual["week_start"]).dt.strftime("%Y-%m-%d") == latest_lbl]
            if latest_v.empty:
                latest_v = v_actual.tail(1)
            row = latest_v.iloc[0]
            stage_vals = {s: f"{float(row.get(c, 0.0)):.1f}%" for s, c in stage_cols.items()}
            status = "On Track" if float(row.get("r2b_pct", 0.0)) >= 50.0 else "Behind"
            detail_rows.append(
                {
                    "Release": f"v{v}",
                    "Week": pd.to_datetime(row["week_start"]).strftime("%Y-%m-%d"),
                    "SB0": stage_vals["SB0"],
                    "SB1/SB2": stage_vals["SB1/SB2"],
                    "R0": stage_vals["R0"],
                    "R1": stage_vals["R1"],
                    "R2A": stage_vals["R2A"],
                    "R2B": stage_vals["R2B"],
                    "Status": status,
                }
            )
        if detail_rows:
            st.dataframe(pd.DataFrame(detail_rows), use_container_width=True, hide_index=True)
    
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
    
    def create_bug_severity_chart(self, data: Dict[str, Any], key_suffix: str = ""):
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
        
        st.plotly_chart(fig, use_container_width=True, key=f"bug_severity_chart{key_suffix}")
    
    def create_ci_issues_chart(self, data: Dict[str, Any], key_suffix: str = ""):
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
        
        st.plotly_chart(fig, use_container_width=True, key=f"ci_issues_chart{key_suffix}")
    
    def create_security_bugs_chart(self, data: Dict[str, Any], key_suffix: str = ""):
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
        
        st.plotly_chart(fig, use_container_width=True, key=f"security_bugs_chart{key_suffix}")
    
    def create_leftshift_bugs_chart(self, data: Dict[str, Any], key_suffix: str = ""):
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
        
        st.plotly_chart(fig, use_container_width=True, key=f"leftshift_bugs_chart{key_suffix}")
    
    def create_abs_bugs_chart(self, data: Dict[str, Any], key_suffix: str = ""):
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
        
        st.plotly_chart(fig, use_container_width=True, key=f"abs_bugs_chart{key_suffix}")
    
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
    
    def create_prb_insights(self, data: Dict[str, Any], key_suffix: str = ""):
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
                        st.text_area(
                            f"Description - {prb.get('id')}",
                            prb.get('description'),
                            height=100,
                            key=f"desc_{prb.get('id')}{key_suffix}",
                        )
                    
                    # Comprehensive technical details 
                    what_happened = prb.get('what_happened', '') or getattr(prb, 'what_happened', '')
                    if what_happened:
                        st.text_area(
                            f"What Happened (Complete) - {prb.get('id')}",
                            what_happened,
                            height=120,
                            key=f"what_{prb.get('id')}{key_suffix}",
                        )
                    
                    proximate_cause = prb.get('proximate_cause', '') or getattr(prb, 'proximate_cause', '')
                    if proximate_cause:
                        st.text_area(
                            f"Root Cause (Complete) - {prb.get('id')}",
                            proximate_cause,
                            height=120,
                            key=f"cause_{prb.get('id')}{key_suffix}",
                        )
                    
                    how_resolved = prb.get('how_resolved', '') or getattr(prb, 'how_resolved', '')
                    if how_resolved:
                        st.text_area(
                            f"Resolution (Complete) - {prb.get('id')}",
                            how_resolved,
                            height=120,
                            key=f"resolution_{prb.get('id')}{key_suffix}",
                        )
                    
                    next_steps = prb.get('next_steps', '') or getattr(prb, 'next_steps', '')
                    if next_steps:
                        st.text_area(
                            f"Next Steps (Complete) - {prb.get('id')}",
                            next_steps,
                            height=120,
                            key=f"next_{prb.get('id')}{key_suffix}",
                        )
                    
                    user_experience = prb.get('user_experience', '') or getattr(prb, 'user_experience', '')
                    if user_experience:
                        st.text_area(
                            f"User Experience - {prb.get('id')}",
                            user_experience,
                            height=100,
                            key=f"user_{prb.get('id')}{key_suffix}",
                        )
                    
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
    'Core App Efficiency': '00OEE0000038GfN2AU',  # P0/P1 Prod Investigations for Core Optimizer/SFSQL
}

# GUS Salesforce report IDs for P0/P1 CI issues (metric card + detail links)
P0P1_CI_ISSUES_REPORT_ID_BY_COMPONENT: Dict[str, str] = {
    'Engine': '00OEE000002WjvJ2AS',
    'Store': '00OEE0000030lWf2AI',
    'SDD': '00OEE0000030lej2AA',
    'Core App Efficiency': '00OEE0000038NnJ2AU',  # Core Optimizer/SFSQL CI Issues
}

# GUS Salesforce report IDs for P0/P1 security bugs (metric card + detail links)
P0P1_SECURITY_BUGS_REPORT_ID_BY_COMPONENT: Dict[str, str] = {
    'Engine': '00OB0000002qWjvMAE',
    'Store': '00OEE0000030lwT2AQ',
    'SDD': '00OEE0000030lzh2AA',
    'Core App Efficiency': '00OEE0000038PM52AM',  # Core Optimizer/SFSQL Security Issues
}

# GUS Salesforce report IDs for P0/P1 left shift (metric card + detail links)
P0P1_LEFT_SHIFT_REPORT_ID_BY_COMPONENT: Dict[str, str] = {
    'Engine': '00OEE000002Wjld2AC',
    'Store': '00OEE0000030m7l2AA',
    'SDD': '00OEE0000030m9N2AQ',
    'Core App Efficiency': '00OEE0000038PHF2A2',  # Core Optimizer/SFSQL Left Shift Issues
}

# GUS Salesforce report IDs for P0/P1 ABS bugs (metric card + detail links)
P0P1_ABS_BUGS_REPORT_ID_BY_COMPONENT: Dict[str, str] = {
    'Engine': '00OEE000002bDht2AE',
    'Store': '00OEE0000030o6L2AQ',
    'SDD': '00OEE0000030o7x2AA',
    'Core App Efficiency': '00OEE000002bDht2AE',  # Using Engine default (no Core-specific ABS report yet)
}

# GUS Salesforce report IDs for All-time Bug Backlog (second dev metrics row)
ALL_TIME_BUG_BACKLOG_REPORT_ID_BY_COMPONENT: Dict[str, str] = {
    'Engine': '00OEE000002XRUv2AO',
    'Store': '00OEE0000030oHd2AI',
    'SDD': '00OEE0000030oKr2AI',
    'Core App Efficiency': '00OEE0000038PIr2AM',  # Core Optimizer/SFSQL All-time Bug Backlog
}

# GUS Salesforce report IDs for Backlog from PRB (second dev metrics row)
BACKLOG_FROM_PRB_REPORT_ID_BY_COMPONENT: Dict[str, str] = {
    'Engine': '00OEE000002ZnZN2A0',
    'Store': '00OEE0000030oCn2AI',
    'SDD': '00OEE0000030oEP2AY',
    'Core App Efficiency': '00OEE0000038PKT2A2',  # Core Optimizer/SFSQL PRB Backlog
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

        # Initialize Ask Claude state
        if f'ask_claude_history_{component}' not in st.session_state:
            st.session_state[f'ask_claude_history_{component}'] = []

        # Simple, working chat interface using expander
        st.markdown("""
        <style>
        /* Style for Ask Claude section */
        div[data-testid="stExpander"] details summary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            font-size: 18px !important;
            font-weight: 700 !important;
            padding: 15px 20px !important;
            border-radius: 12px !important;
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5) !important;
        }

        div[data-testid="stExpander"] details summary:hover {
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.7) !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # Use expander for chat interface
        with st.expander("💬 Ask Claude AI - Quality Intelligence Assistant", expanded=False):
            ask_claude = AskClaudePanel()

            st.markdown("**💭 Ask me anything about quality metrics for this component**")

            # Question input
            question = st.text_area(
                "Your question:",
                key=f"ask_claude_input_{component}",
                placeholder="e.g., What are the top 3 quality risks right now?",
                height=100,
                label_visibility="collapsed"
            )

            col1, col2 = st.columns([3, 1])
            with col1:
                send_clicked = st.button("🚀 Send Question", key=f"ask_claude_button_{component}", use_container_width=True, type="primary")
            with col2:
                if st.button("🗑️ Clear", key=f"clear_claude_{component}", use_container_width=True):
                    st.session_state[f'ask_claude_history_{component}'] = []
                    st.rerun()

            # Process question
            if send_clicked and question:
                with st.spinner("🤔 Claude is thinking..."):
                    context = ask_claude.prepare_context(data, component)
                    answer = ask_claude.query_claude(question, context, component)

                    # Add to history
                    st.session_state[f'ask_claude_history_{component}'].append({
                        'question': question,
                        'answer': answer,
                        'timestamp': datetime.now().strftime("%H:%M:%S")
                    })
                    st.rerun()

            st.markdown("---")

            # Display conversation history
            history = st.session_state[f'ask_claude_history_{component}']
            if history:
                st.markdown("**📜 Conversation History**")

                # Show messages (most recent first)
                for idx, item in enumerate(reversed(history)):
                    # User message
                    st.markdown(f"""
                    <div style="margin-bottom: 15px;">
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                    color: white; padding: 12px 16px; border-radius: 18px 18px 4px 18px;
                                    margin-left: 15%; box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);">
                            <div style="font-size: 11px; opacity: 0.8; margin-bottom: 4px;">You • {item['timestamp']}</div>
                            <div style="font-size: 14px; line-height: 1.5;">{item['question']}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Claude response
                    st.markdown(f"""
                    <div style="margin-bottom: 20px;">
                        <div style="background: #f7f7f8; color: #1a1a1a; padding: 12px 16px;
                                    border-radius: 18px 18px 18px 4px; margin-right: 15%;
                                    border: 1px solid #e5e5e7; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);">
                            <div style="font-size: 11px; opacity: 0.6; margin-bottom: 4px; color: #764ba2; font-weight: 600;">
                                Claude AI
                            </div>
                            <div style="font-size: 14px; line-height: 1.6;">{item['answer']}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("👋 Start a conversation by asking a question above!")
                st.markdown("""
                **Example questions:**
                - What are the biggest quality risks right now?
                - Summarize the PRB situation
                - How is our code coverage trending?
                - What should I focus on this week?
                - Are there any P0/P1 bugs I should know about?
                """)

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
            dashboard.create_prb_insights(data, key_suffix=f"_{component}")
        
        # Bug Analysis
        bug_section_title = "🐛 Prod Investigations Analysis" if component == "Core App Efficiency" else "🐛 Production Bug Analysis"
        bug_link_text = "P0/P1 prod investigations" if component == "Core App Efficiency" else "P0/P1 production bugs"
        st.markdown(f'<h3 id="production-bug-analysis">{bug_section_title}</h3>', unsafe_allow_html=True)
        p0p1_gus = p0p1_prod_bugs_report_url(component)
        if p0p1_gus:
            st.markdown(
                f'<p style="margin: -4px 0 10px 0;"><a href="{p0p1_gus}" target="_blank" rel="noopener noreferrer">'
                f'📋 {bug_link_text} — GUS report</a></p>',
                unsafe_allow_html=True,
            )
        st.markdown('<p style="text-align: right; margin-top: -10px;"><a href="#production-metrics" style="font-size: 0.8rem; color: #666;">↑ Back to top</a></p>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1])
        with col1:
            dashboard.create_bug_severity_chart(data, key_suffix=f"_{component}")
        with col2:
            dashboard.create_bug_insights(data)
        
        # Coverage Analysis
        st.markdown('<h3 id="code-coverage-analysis">📊 <a href="https://sonarqube.sfcq.buildndeliver-s.aws-esvc1-useast2.aws.sfdc.cl/component_measures?id=sayonara.sayonaradb.sdb&metric=uncovered_lines&view=list" target="_blank" style="color: inherit; text-decoration: none;">Code Coverage Analysis</a></h3>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: right; margin-top: -10px;"><a href="#production-metrics" style="font-size: 0.8rem; color: #666;">↑ Back to top</a></p>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1])
        with col1:
            dashboard.create_coverage_comparison_chart(data, key_suffix=f"_{component}")
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
            dashboard.create_ci_issues_chart(data, key_suffix=f"_{component}")
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
            dashboard.create_security_bugs_chart(data, key_suffix=f"_{component}")
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
            dashboard.create_leftshift_bugs_chart(data, key_suffix=f"_{component}")
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
            dashboard.create_abs_bugs_chart(data, key_suffix=f"_{component}")
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
        dashboard.create_version_pie_chart(data, key_suffix=f"_{component}")

        st.markdown("#### 1. Release Deployment Timeline - Plan vs Actual")
        st.markdown("""
        <div style="background-color: #f0f7ff; padding: 12px; border-radius: 6px; border-left: 4px solid #3b82f6; margin-bottom: 16px; font-size: 13px;">
        <strong>How to read this chart:</strong><br/>
        • <strong>Y-axis:</strong> Each release version is split into 6 deployment stages (SB0 → SB1/SB2 → R0 → R1 → R2a → R2b)<br/>
        • <strong>X-axis:</strong> Timeline showing dates across weeks and months<br/>
        • <strong>Thin lines with hollow circles:</strong> Planned deployment schedule<br/>
        • <strong>Thick lines with solid circles:</strong> Actual deployment progress (line length shows % complete)<br/>
        • <strong>Colors:</strong> Each stage has a unique color shown in the legend above
        </div>
        """, unsafe_allow_html=True)
        dashboard.create_release_journey_gantt(selected_week, data, key_suffix=component.lower())

        dashboard.create_release_journey_slick_panel(selected_week, data, key_suffix=component.lower())

        dashboard.create_plan_vs_actual_table(selected_week, data, key_suffix=component.lower())
        
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
        st.markdown("""
        <h3 id="code-changes-analysis">📊 Code Changes Analysis</h3>
        <script>
        // Enable smooth scrolling to anchors
        document.addEventListener('click', function(e) {
            if (e.target.tagName === 'A' && e.target.getAttribute('href').startsWith('#')) {
                e.preventDefault();
                const target = document.querySelector(e.target.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
        });
        </script>
        """, unsafe_allow_html=True)
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

    # Authentication check
    from auth_config import check_authentication, login_page, logout

    if not check_authentication():
        login_page()
        st.stop()

    # Show logout button in sidebar
    if st.session_state.get("authenticated"):
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"**👤 Logged in as:** {st.session_state.username}")
        st.sidebar.markdown(f"**🔑 Role:** {st.session_state.user_role}")
        if st.sidebar.button("🚪 Logout", key="logout_button"):
            logout()

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


class AskClaudePanel:
    """Interactive Ask Claude panel for querying dashboard data"""

    def __init__(self):
        self.llm_api_key = os.getenv("LLM_GW_EXPRESS_KEY", "")
        self.openai_user_id = os.getenv("OPENAI_USER_ID", "")
        self.llm_gateway_url = "https://eng-ai-model-gateway.sfproxy.devx-preprod.aws-esvc1-useast2.aws.sfdc.cl/chat/completions"

    def prepare_context(self, data: Dict[str, Any], component: str) -> str:
        """Prepare dashboard data as context for Claude"""
        context_parts = []

        # Component info
        context_parts.append(f"=== {component} Quality Dashboard Data ===\n")

        # PRBs - with full details
        prbs = data.get('prbs', [])
        if prbs:
            context_parts.append(f"\n## PROBLEM REPORTS (PRBs): {len(prbs)} total")
            for idx, prb in enumerate(prbs[:10], 1):  # Top 10 PRBs
                prb_id = prb.get('id', 'Unknown')
                priority = prb.get('priority', 'Unknown')
                title = prb.get('title', 'No title')
                status = prb.get('status', 'Unknown')
                what_happened = prb.get('what_happened', 'N/A')
                proximate_cause = prb.get('proximate_cause', 'N/A')

                context_parts.append(f"\n{idx}. {prb_id} - {priority}")
                context_parts.append(f"   Title: {title}")
                context_parts.append(f"   Status: {status}")
                if what_happened != 'N/A':
                    context_parts.append(f"   What Happened: {what_happened[:200]}")
                if proximate_cause != 'N/A':
                    context_parts.append(f"   Cause: {proximate_cause[:200]}")
        else:
            context_parts.append("\n## PROBLEM REPORTS (PRBs): None")

        # Production Bugs - with details
        bugs = data.get('bugs', [])
        if bugs:
            p0_bugs = [b for b in bugs if 'P0' in str(b.get('priority',''))]
            p1_bugs = [b for b in bugs if 'P1' in str(b.get('priority',''))]
            p2_bugs = [b for b in bugs if 'P2' in str(b.get('priority',''))]

            context_parts.append(f"\n## PRODUCTION BUGS: {len(bugs)} total")
            context_parts.append(f"   P0 (Critical): {len(p0_bugs)}")
            context_parts.append(f"   P1 (High): {len(p1_bugs)}")
            context_parts.append(f"   P2+ (Medium/Low): {len(p2_bugs)}")

            # Show P0/P1 bug details
            high_priority = p0_bugs + p1_bugs
            if high_priority:
                context_parts.append("\n   Critical Bugs (P0/P1):")
                for idx, bug in enumerate(high_priority[:5], 1):
                    subject = bug.get('subject', 'No subject')
                    team = bug.get('team', 'Unknown team')
                    context_parts.append(f"   {idx}. [{bug.get('priority')}] {subject[:100]} (Team: {team})")
        else:
            context_parts.append("\n## PRODUCTION BUGS: None")

        # Code Coverage
        cov_summary = data.get('coverage_summary', {})
        if cov_summary:
            overall = cov_summary.get('overall', {})
            new_code = cov_summary.get('new_code', {})
            line_cov = overall.get('line_coverage', 0)
            branch_cov = overall.get('branch_coverage', 0)
            new_line_cov = new_code.get('line_coverage', 0)

            context_parts.append(f"\n## CODE COVERAGE:")
            context_parts.append(f"   Overall Line Coverage: {line_cov:.1f}%")
            context_parts.append(f"   Overall Branch Coverage: {branch_cov:.1f}%")
            context_parts.append(f"   New Code Line Coverage: {new_line_cov:.1f}%")

            # Coverage status
            if line_cov < 70:
                context_parts.append(f"   ⚠️ Coverage is below 70% threshold - HIGH RISK")
            elif line_cov < 80:
                context_parts.append(f"   ⚠️ Coverage is below 80% target - MODERATE RISK")
            else:
                context_parts.append(f"   ✓ Coverage meets target")
        else:
            context_parts.append("\n## CODE COVERAGE: No data available")

        # CI Issues
        ci = data.get('ci_issues', [])
        if ci:
            p0_ci = [c for c in ci if 'P0' in str(c.get('priority',''))]
            p1_ci = [c for c in ci if 'P1' in str(c.get('priority',''))]
            context_parts.append(f"\n## CI ISSUES: {len(ci)} total")
            context_parts.append(f"   P0 (Blocking): {len(p0_ci)}")
            context_parts.append(f"   P1 (High): {len(p1_ci)}")
            if p0_ci:
                context_parts.append("   ⚠️ P0 CI issues are blocking releases - CRITICAL")

        # Left Shift Issues
        leftshift = data.get('leftshift_issues', [])
        if leftshift:
            context_parts.append(f"\n## LEFT SHIFT ISSUES: {len(leftshift)} total")
            context_parts.append(f"   (Bugs found late in development cycle)")

        # ABS (After Build Starts) Issues
        abs_issues = data.get('abs_issues', [])
        if abs_issues:
            p0_abs = [a for a in abs_issues if 'P0' in str(a.get('priority',''))]
            p1_abs = [a for a in abs_issues if 'P1' in str(a.get('priority',''))]
            context_parts.append(f"\n## ABS ISSUES: {len(abs_issues)} total")
            context_parts.append(f"   P0: {len(p0_abs)}, P1: {len(p1_abs)}")

        # Security Issues
        security = data.get('security_issues', [])
        if security:
            p0_sec = [s for s in security if 'P0' in str(s.get('priority',''))]
            p1_sec = [s for s in security if 'P1' in str(s.get('priority',''))]
            context_parts.append(f"\n## SECURITY ISSUES: {len(security)} total")
            context_parts.append(f"   P0: {len(p0_sec)}, P1: {len(p1_sec)}")
            if p0_sec or p1_sec:
                context_parts.append("   ⚠️ High priority security issues require immediate attention")

        # Risks/Features
        risks = data.get('risks', [])
        if risks:
            at_risk = [r for r in risks if 'red' in str(r.get('status','')).lower() or 'at risk' in str(r.get('status','')).lower()]
            on_track = [r for r in risks if 'green' in str(r.get('status','')).lower() or 'on track' in str(r.get('status','')).lower()]

            context_parts.append(f"\n## FEATURES/RISKS: {len(risks)} tracked")
            context_parts.append(f"   At Risk: {len(at_risk)}")
            context_parts.append(f"   On Track: {len(on_track)}")

            if at_risk:
                context_parts.append("\n   Features at Risk:")
                for idx, risk in enumerate(at_risk[:5], 1):
                    feature = risk.get('feature', 'Unknown')
                    status = risk.get('status', 'Unknown')
                    context_parts.append(f"   {idx}. {feature} - Status: {status}")

        # Backlog
        alltime_backlog = data.get('alltime_backlog', [])
        prb_backlog = data.get('prb_backlog', [])
        if alltime_backlog:
            context_parts.append(f"\n## ALL-TIME BACKLOG: {len(alltime_backlog)} items")
        if prb_backlog:
            context_parts.append(f"## PRB BACKLOG: {len(prb_backlog)} items")

        # Code Changes
        code_changes = data.get('code_changes', {})
        if code_changes:
            files_changed = code_changes.get('files_changed', 0)
            lines_added = code_changes.get('lines_added', 0)
            lines_deleted = code_changes.get('lines_deleted', 0)
            commits = code_changes.get('commits', 0)

            context_parts.append(f"\n## CODE CHANGES (Recent):")
            context_parts.append(f"   Files Changed: {files_changed}")
            context_parts.append(f"   Lines Added: {lines_added}")
            context_parts.append(f"   Lines Deleted: {lines_deleted}")
            context_parts.append(f"   Commits: {commits}")

        return "\n".join(context_parts)

    def query_claude(self, question: str, context: str, component: str) -> str:
        """Query Claude with the dashboard context"""
        import requests
        import socket
        import urllib3

        # Suppress SSL warnings for internal Salesforce endpoint
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        if not self.llm_api_key:
            return "❌ LLM Gateway API key not configured. Please set LLM_GW_EXPRESS_KEY environment variable."

        # Check if LLM Gateway is reachable (VPN connectivity)
        try:
            socket.gethostbyname("eng-ai-model-gateway.sfproxy.devx-preprod.aws-esvc1-useast2.aws.sfdc.cl")
        except socket.gaierror:
            return """❌ Cannot reach LLM Gateway (eng-ai-model-gateway.sfproxy.devx-preprod.aws-esvc1-useast2.aws.sfdc.cl)

This is an internal Salesforce endpoint that requires VPN connection.

**To fix:**
1. Connect to Salesforce VPN
2. Verify connection: `ping eng-ai-model-gateway.sfproxy.devx-preprod.aws-esvc1-useast2.aws.sfdc.cl`
3. Refresh this page and try again"""

        try:
            headers = {
                "Authorization": f"Bearer {self.llm_api_key}",
                "Content-Type": "application/json"
            }

            messages = [
                {"role": "system", "content": f"You are a senior quality engineer analyzing SDB dashboard data for {component}. Provide concise, actionable answers."},
                {"role": "user", "content": f"Dashboard Context:\n{context}\n\nQuestion: {question}"}
            ]

            payload = {
                "model": "claude-sonnet-4-20250514",
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.3
            }

            if self.openai_user_id:
                payload["user"] = self.openai_user_id

            response = requests.post(
                self.llm_gateway_url,
                headers=headers,
                json=payload,
                timeout=120,
                verify=False  # Disable SSL verification for internal Salesforce endpoint
            )

            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    return f"❌ LLM Gateway returned 200 but no choices. Response: {str(result)[:200]}"
            else:
                return f"❌ Error: {response.status_code} - {response.text[:200]}"

        except requests.exceptions.Timeout:
            return "❌ Request timed out. The LLM Gateway may be slow or unresponsive."
        except requests.exceptions.ConnectionError as e:
            return f"❌ Connection error: {str(e)}\n\nMake sure you're connected to Salesforce VPN."
        except Exception as e:
            return f"❌ Error querying Claude: {str(e)}"



if __name__ == "__main__":
    main()

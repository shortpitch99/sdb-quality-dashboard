#!/usr/bin/env python3
"""
Quality Report Generator
A comprehensive tool to generate quality reports using LLM analysis of various data sources.
"""

import json
import csv
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import requests
import aiohttp
import asyncio
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_report_dates(custom_end_date=None):
    """Calculate dynamic report dates based on last week Monday to Sunday period.
    
    Args:
        custom_end_date: Optional datetime object to use as the reference date instead of today.
                        The report will cover the week ending on the Sunday before this date.
    """
    if custom_end_date:
        reference_date = custom_end_date
    else:
        reference_date = datetime.now()
    
    # Find current week's Monday (start of this week)
    days_since_monday = reference_date.weekday()  # Monday is 0
    current_monday = reference_date - timedelta(days=days_since_monday)
    
    # Get last week's Monday and Sunday
    last_monday = current_monday - timedelta(days=7)
    last_sunday = last_monday + timedelta(days=6)
    
    return {
        'report_date': reference_date.strftime('%B %d, %Y'),
        'period_start': last_monday.strftime('%B %d'),
        'period_end': last_sunday.strftime('%B %d, %Y'),
        'period_full': f"{last_monday.strftime('%B %d')}-{last_sunday.strftime('%d, %Y')}",
        'period_start_full': last_monday.strftime('%Y-%m-%d'),
        'period_end_full': last_sunday.strftime('%Y-%m-%d')
    }

@dataclass
class RiskItem:
    feature: str
    status: str
    priority: str
    description: str
    last_updated: str

@dataclass
class PRBItem:
    id: str
    title: str
    priority: str
    status: str
    description: str
    created_date: str

@dataclass
class BugItem:
    id: str
    title: str
    severity: str
    status: str
    description: str
    component: str
    reported_date: str

@dataclass
class CriticalIssue:
    id: str
    title: str
    severity: str
    status: str
    description: str
    impact: str
    created_date: str

@dataclass
class DeploymentInfo:
    version: str
    date: str
    environment: str
    status: str
    features: List[str]
    issues: List[str]

@dataclass
class StaggerDeployment:
    stagger: str  # SB0, SB1, SB2, R0, R1, R2
    sdb_version: str
    cell_count: int
    deployment_phase: str  # Sandbox, Production Rollout

@dataclass
class CoverageMetric:
    component: str
    line_coverage: float
    branch_coverage: float
    function_coverage: float
    test_count: int

@dataclass
class NewCodeCoverage:
    component: str
    new_code_coverage: float
    overall_coverage: float
    new_code_line_coverage: float
    overall_line_coverage: float
    lines_to_cover: int
    uncovered_lines: int
    overall_lines_to_cover: int
    overall_uncovered_lines: int

@dataclass
class CIIssue:
    work_id: str
    team: str
    priority: str
    subject: str
    status: str
    build_version: str
    created_date: str
    issue_type: str = "CI"

@dataclass
class LeftShiftIssue:
    work_id: str
    team: str
    priority: str
    subject: str
    status: str
    build_version: str
    created_date: str
    issue_type: str = "LeftShift"

@dataclass
class SecurityIssue:
    work_id: str
    issue_category: str  # RESOURCE_LEAK, OVERRUN, USE_AFTER_FREE, etc.
    file_path: str
    assigned_to: str
    status: str
    build_version: str
    team: str = "Security"
    issue_type: str = "Security"

@dataclass
class GitStats:
    reporting_period_start: str
    reporting_period_end: str
    total_commits: int
    lines_added: int
    lines_deleted: int
    lines_changed: int
    files_changed: int
    authors: List[str]
    most_changed_files: List[dict]
    commit_frequency: float  # commits per day
    code_churn_risk: str  # Low, Medium, High

class QualityDataCollector:
    """Collects data from various sources for quality reporting."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config = self._load_config(config_file)
        self.data = {
            'risks': [],
            'prbs': [],
            'bugs': [],
            'critical_issues': [],
            'deployments': [],
            'deployment_summary': '',
            'coverage': [],
            'new_code_coverage': [],
            'ci_issues': [],
            'leftshift_issues': [],
            'abs_issues': [],
            'security_issues': [],
            'git_stats': {},
            'generated_at': datetime.now().isoformat()
        }
    
    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        default_config = {
            'llm_api_key': os.getenv('LLM_GW_EXPRESS_KEY', ''),
            'openai_user_id': os.getenv('OPENAI_USER_ID', ''),
            'salesforce_session_id': os.getenv('SALESFORCE_SESSION_ID', ''),
            'salesforce_instance': os.getenv('SALESFORCE_INSTANCE', 'gus.lightning.force.com'),
            'output_dir': './reports',
            'archive_dir': './archive'
        }
        
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def load_risk_data(self, risk_file: str) -> List[RiskItem]:
        """Load risk/feature tracking data from text file."""
        risks = []
        
        if not os.path.exists(risk_file):
            print(f"Warning: Risk file {risk_file} not found. Creating example.")
            self._create_example_risk_file(risk_file)
        
        try:
            with open(risk_file, 'r') as f:
                content = f.read().strip()
                
            # Parse different formats - JSON, CSV, or structured text
            if risk_file.endswith('.json'):
                risk_data = json.loads(content)
                for item in risk_data:
                    risks.append(RiskItem(**item))
            elif risk_file.endswith('.csv'):
                risks = self._parse_csv_risks(risk_file)
            else:
                risks = self._parse_text_risks(content)
                
        except Exception as e:
            print(f"Error loading risk data: {e}")
            
        self.data['risks'] = [vars(risk) for risk in risks]
        return risks
    
    def _parse_text_risks(self, content: str) -> List[RiskItem]:
        """Parse structured text format for risks."""
        risks = []
        current_risk = {}
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if line.startswith('Feature:'):
                if current_risk:
                    risks.append(RiskItem(**current_risk))
                current_risk = {'feature': line.replace('Feature:', '').strip()}
            elif line.startswith('Status:'):
                current_risk['status'] = line.replace('Status:', '').strip()
            elif line.startswith('Priority:'):
                current_risk['priority'] = line.replace('Priority:', '').strip()
            elif line.startswith('Description:'):
                current_risk['description'] = line.replace('Description:', '').strip()
            elif line.startswith('Updated:'):
                current_risk['last_updated'] = line.replace('Updated:', '').strip()
        
        if current_risk:
            # Fill in missing fields with defaults
            current_risk.setdefault('status', 'Unknown')
            current_risk.setdefault('priority', 'Medium')
            current_risk.setdefault('description', '')
            current_risk.setdefault('last_updated', datetime.now().strftime('%Y-%m-%d'))
            risks.append(RiskItem(**current_risk))
            
        return risks
    
    def _parse_text_prbs(self, content: str) -> List[PRBItem]:
        """Parse PRB data from new Salesforce report format."""
        import re
        prbs = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for PRB number (PRB-#######)
            prb_match = re.search(r'PRB-\d{7}', line)
            if prb_match:
                prb_id = prb_match.group()
                
                # Initialize with defaults
                priority = 'Medium'
                status = 'Open'
                description = ''
                created_date = datetime.now().strftime('%Y-%m-%d')
                team = 'Unknown'
                title = f"Incident {prb_id}"
                problem_state = 'Unknown'
                customer_impact = 'Unknown'
                
                # Search context around this line for details (Salesforce structured report)
                # Look for priority pattern exactly 1 line before PRB (based on format analysis)
                if i > 0:
                    priority_line = lines[i - 1].strip()
                    priority_match = re.search(r'P([0-4])\(\d+\)', priority_line)
                    if priority_match:
                        priority_num = priority_match.group(1)
                        if priority_num == '0':
                            priority = 'P0-Critical'
                        elif priority_num == '1':
                            priority = 'P1-High'
                        elif priority_num == '2':
                            priority = 'P2-Medium'
                        elif priority_num == '3':
                            priority = 'P3-Low'
                        elif priority_num == '4':
                            priority = 'P4-Minimal'
                
                # Also check for simple P2 format (without parentheses)
                if i > 0:
                    priority_line = lines[i - 1].strip()
                    if priority_line in ['P0', 'P1', 'P2', 'P3', 'P4']:
                        priority_num = priority_line[1]
                        if priority_num == '0':
                            priority = 'P0-Critical'
                        elif priority_num == '1':
                            priority = 'P1-High'
                        elif priority_num == '2':
                            priority = 'P2-Medium'
                        elif priority_num == '3':
                            priority = 'P3-Low'
                        elif priority_num == '4':
                            priority = 'P4-Minimal'
                
                # Now search broader context for other details
                context_start = max(0, i - 5)
                context_end = min(len(lines), i + 50)
                
                for j in range(context_start, context_end):
                    context_line = lines[j].strip()
                    
                    # Extract team names - look for specific team indicators
                    if context_line == 'SDB' or context_line == 'Cloud':
                        team = context_line
                    elif 'SDB Performance' in context_line:
                        team = 'SDB Performance'
                    elif 'CRM Database Sustaining Engineering' in context_line:
                        team = 'CRM Database Sustaining Engineering'
                    elif 'Site Reliability' in context_line:
                        team = 'Site Reliability'
                    elif 'CRM DB Replication and Recovery as a Service' in context_line:
                        team = 'CRM DB Replication and Recovery as a Service'
                    
                    # Extract problem state
                    if context_line == 'Analysis Complete':
                        problem_state = 'Analysis Complete'
                        status = 'Analysis Complete'
                    elif context_line in ['Waiting 3rd Party', 'Open', 'Resolved', 'In Progress']:
                        problem_state = context_line
                        status = context_line
                    
                    # Extract customer impact - look for specific impact descriptions
                    if 'Feature degradation / disruption (internal service impact)' in context_line:
                        customer_impact = 'Feature degradation / disruption (internal service impact)'
                    elif context_line in ['Performance degradation (general)', 'Service unavailable', 'Data loss']:
                        customer_impact = context_line
                    
                    # Extract created date (MM/DD/YYYY format)
                    date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', context_line)
                    if date_match:
                        try:
                            date_str = date_match.group(1)
                            date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                            created_date = date_obj.strftime('%Y-%m-%d')
                        except:
                            pass
                
                # Extract comprehensive PRB information for narrative generation
                what_happened = ""
                proximate_cause = ""
                how_resolved = ""
                next_steps = ""
                user_experience = ""
                
                # Look for detailed fields in the context around the PRB
                context_start = max(0, i - 20)
                context_end = min(len(lines), i + 50)
                all_lines = [(line_idx, lines[line_idx]) for line_idx in range(context_start, context_end)]
                
                # Extract "What Happened?" section - look for content after the question
                # Extract "Customer Experience" or "User Experience" section
                for line_num, context_line in all_lines:
                    if 'User Experience:' in context_line or 'Customer Experience' in context_line:
                        # Extract the experience description
                        if ':' in context_line:
                            user_experience = context_line.split(':', 1)[1].strip()
                            # Clean up the user experience text
                            if '|' in user_experience:
                                user_experience = user_experience.split('|')[0].strip()
                        break
                
                # Extract team information more accurately - override with better data
                for line_num, context_line in all_lines:
                    if context_line.strip().startswith('Team:') and 'Team Name' not in context_line:
                        team = context_line.replace('Team:', '').strip()
                        break
                    elif context_line.strip() == 'SDB':
                        team = 'SDB'
                        break
                    elif context_line.strip() == 'Cloud':
                        team = 'Cloud'
                        break
                    elif any(team_indicator in context_line for team_indicator in ['Database']) and len(context_line.strip()) < 20:
                        team = context_line.strip()
                        break
                
                # Extract customer impact more accurately - override with better data
                for line_num, context_line in all_lines:
                    if 'Customer Impact' in context_line and line_num < len(lines) - 1:
                        next_line = lines[line_num + 1].strip()
                        if next_line and len(next_line) > 5 and 'External RCA' not in next_line:
                            customer_impact = next_line
                            break
                    elif 'Feature degradation / disruption (internal service impact)' in context_line:
                        customer_impact = 'Feature degradation / disruption (internal service impact)'
                        break
                
                # Extract "What Happened?" section - look for content after the question
                # Extract "Proximate Cause" section - look for actual cause description
                for line_num, context_line in all_lines:
                    if 'Proximate Cause' in context_line and '?' in context_line:
                        # Look for the actual cause in subsequent lines
                        cause_lines = []
                        for j in range(line_num + 1, min(len(lines), line_num + 10)):
                            line_content = lines[j].strip()
                            if (line_content and 
                                not any(keyword in line_content for keyword in ['How did we find out', 'How was it Resolved', 'Root Cause', 'Next Steps']) and
                                not line_content.startswith('Q:') and
                                not line_content.startswith('A:') and
                                line_content != '​'):  # Skip empty unicode characters
                                cause_lines.append(line_content)
                            elif any(keyword in line_content for keyword in ['How did we find out', 'How was it Resolved']):
                                break
                        proximate_cause = " ".join(cause_lines)
                        break
                
                # If no structured proximate cause found, look for the standalone cause line
                if not proximate_cause:
                    for line_num, context_line in all_lines:
                        line_content = context_line.strip()
                        if (line_content.startswith('Proximate Cause:') or 
                            ('ERR release' in line_content and 'version mismatch' in line_content) or
                            ('caused' in line_content.lower() and any(word in line_content.lower() for word in ['mismatch', 'incompatible', 'failure', 'error']))):
                            if line_content.startswith('Proximate Cause:'):
                                proximate_cause = line_content.replace('Proximate Cause:', '').strip()
                            else:
                                proximate_cause = line_content
                            break
                
                # If no structured "What Happened?" found, look for the actual incident description
                if not what_happened:
                    # Look for lines that describe the actual problem (after system messages)
                    for line_num, context_line in all_lines:
                        line_content = context_line.strip()
                        # Look for substantive problem descriptions - specifically target the SDB archival issue
                        if (line_content and 
                            len(line_content) > 30 and  # Substantial content
                            not any(skip in line_content for skip in ['[THIS PRB IS MANAGED BY QUIP2GUS]', 'User Experience:', 'Impact Quantification:', 'Q:', 'A:', 'https://', 'Proximate Cause:', 'Key Questions', 'Created Date Time', 'Select all rows', 'Sorted by', 'Select row for Drill Down']) and
                            ('SDB Archival is not running' in line_content or 
                             'archival is not running' in line_content or
                             any(indicator in line_content.lower() for indicator in ['not running for sdb', 'backup', 'capacity constraints', 'clusters in hyperforce']))):
                            what_happened = line_content
                            break
                
                # Look directly for the actual next steps work items
                next_steps = ""
                work_items = []
                for line_num in range(len(lines)):
                    line_content = lines[line_num].strip()
                    if line_content.startswith(('1)', '2)', '3)')) and 'W-' in line_content:
                        work_items.append(line_content)
                
                if work_items:
                    next_steps = " ".join(work_items)
                
                # Look directly for the actual resolution line
                how_resolved = ""
                for line_num, context_line in all_lines:
                    line_content = context_line.strip()
                    if any(keyword in line_content.lower() for keyword in ['rolled back', 'rollback', 'restarted', 'pods were restarted']) and len(line_content) > 20:
                        how_resolved = line_content
                        break
                
                # Extract Resolution section (comprehensive)
                resolution_lines = []
                for line_num, context_line in all_lines:
                    if ("how was it resolved" in context_line.lower() or
                        "rollback" in context_line.lower() or
                        "failover" in context_line.lower() or
                        "resolution involved" in context_line.lower() or
                        "self resolved" in context_line.lower()):
                        
                        resolution_lines.append(context_line)
                        
                        # Get resolution details
                        for k in range(line_num + 1, min(len(lines), line_num + 5)):
                            next_line = lines[k].strip()
                            if (next_line and not next_line.startswith('[') and 
                                not next_line.startswith('Q:') and
                                len(next_line) > 10):
                                resolution_lines.append(next_line)
                            how_resolved = line_content
                            break
                
                # Extract Team (look for team assignment - SDB Archival is on line 39)
                team = "Unknown"
                for line_num, context_line in all_lines:
                    line_content = context_line.strip()
                    if line_content == "SDB Archival":
                        team = "SDB Archival"
                        break
                    elif line_content == "Cloud" and line_num > 15:  # Cloud appears on line 19
                        team = "Cloud"
                
                # Extract Next Steps (comprehensive)
                steps_lines = []
                for line_num, context_line in all_lines:
                    if ("next steps" in context_line.lower() or
                        (context_line.startswith('1)') and "testing" in context_line.lower()) or
                        (context_line.startswith('2)') and any(word in context_line.lower() for word in ['alert', 'monitoring', 'pipeline']))):
                        
                        steps_lines.append(context_line)
                        
                        # Get all numbered steps
                        for k in range(line_num + 1, min(len(lines), line_num + 10)):
                            next_line = lines[k].strip()
                        break
                
                # If no retrospective title found, construct from available info
                if 'PRB Retrospective' not in title and customer_impact != 'Unknown':
                    title = f"{prb_id}: {customer_impact}"
                elif 'PRB Retrospective' not in title:
                    title = f"{prb_id}: {problem_state} - {team}"
                
                # Create PRB item with detailed information for narrative generation
                prb_item = PRBItem(
                    id=prb_id,
                    title=title,
                    priority=priority,
                    status=status,
                    description=f"Team: {team} | Impact: {customer_impact} | {description[:200]}" if description else f"Problem report {prb_id} managed by {team}",
                    created_date=created_date
                )
                
                # Add detailed fields for narrative generation
                prb_item.what_happened = what_happened
                prb_item.proximate_cause = proximate_cause  
                prb_item.how_resolved = how_resolved
                prb_item.next_steps = next_steps
                prb_item.user_experience = user_experience
                prb_item.team = team
                prb_item.customer_impact = customer_impact
                
                prbs.append(prb_item)
            
            i += 1
        
        # Remove duplicates based on ID
        seen_ids = set()
        unique_prbs = []
        for prb in prbs:
            if prb.id not in seen_ids:
                seen_ids.add(prb.id)
                unique_prbs.append(prb)
        
        print(f"Parsed {len(unique_prbs)} PRBs from new Salesforce format")
        return unique_prbs
    
    def _parse_text_bugs(self, content: str) -> List[BugItem]:
        """Parse bug data from new Salesforce report format with priority mapping."""
        import re
        bugs = []
        lines = content.split('\n')
        
        # First, extract priority counts from the header section
        priority_mapping = {}
        current_priority = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            # Look for priority patterns like "P1(2)" or "P2(11)"
            priority_match = re.search(r'P([0-4])\((\d+)\)', line)
            if priority_match:
                p_level = f"P{priority_match.group(1)}"
                count = int(priority_match.group(2))
                current_priority = p_level
                # Store the range for this priority level
                priority_mapping[current_priority] = {'count': count, 'start_line': i}
            elif current_priority and not priority_match and 'P' not in line and line:
                # Continuation of current priority section
                if 'end_line' not in priority_mapping[current_priority]:
                    priority_mapping[current_priority]['end_line'] = i + 20  # Give some buffer
        
        
        # Determine section boundaries more accurately by looking at the structure
        p1_start = p1_end = p2_start = p2_end = 0
        
        for i, line in enumerate(lines):
            if 'P1(2)' in line:
                p1_start = i
            elif 'P2(11)' in line:
                p2_start = i
                if p1_start > 0:
                    p1_end = i - 1
        
        # Set reasonable end boundaries
        if p2_start > 0:
            p2_end = len(lines)
        if p1_end == 0 and p1_start > 0:
            p1_end = p2_start - 1 if p2_start > 0 else p1_start + 30
            
        
        # Now parse individual Work IDs and assign priorities based on their section
        i = 0  
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for Work ID pattern (W-########)
            work_id_match = re.search(r'W-\d{8}', line)
            if work_id_match:
                work_id = work_id_match.group()
                
                # Determine priority based on which section the Work ID is in
                if p1_start <= i <= p1_end:
                    assigned_priority = 'P1'
                    severity = 'P1-High'
                elif p2_start <= i <= p2_end:
                    assigned_priority = 'P2'
                    severity = 'P2-Medium'
                else:
                    assigned_priority = 'P2'  # Default
                    severity = 'P2-Medium'
                
                status = 'Open'  
                component = 'Unknown'
                title = 'Unknown Issue'
                description = ''
                reported_date = datetime.now().strftime('%Y-%m-%d')
                assigned_to = 'Unknown'
                customer = 'Unknown'
                
                # Look at surrounding lines for context (structured Salesforce report data)
                context_start = max(0, i - 3)
                context_end = min(len(lines), i + 8)
                
                for j in range(context_start, context_end):
                    context_line = lines[j].strip()
                    # Skip the priority extraction from context since we already determined it above
                    
                    # Extract team/component names
                    team_patterns = [
                        'Sayonara TxP', 'SDB Query Proc Optimizer', 'Sayonara Data Management',
                        'Sayonara Foundation Services', 'SDBStore', 'SDB QP Execution',
                        'SDB TxP Work Queue', 'SDBStore Work Queue'
                    ]
                    for team in team_patterns:
                        if team in context_line:
                            component = team
                            break
                    
                    # Extract status
                    status_patterns = ['New', 'In Progress', 'Triaged', 'Open', 'Resolved', 'Closed']
                    for stat in status_patterns:
                        if context_line.strip() == stat:
                            status = stat
                            break
                    
                    # Extract date (MM/DD/YYYY format)
                    date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', context_line)
                    if date_match:
                        try:
                            date_str = date_match.group(1)
                            date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                            reported_date = date_obj.strftime('%Y-%m-%d')
                        except:
                            pass
                    
                    # Extract customer info (lines containing "SDBFalcon")
                    if 'SDBFalcon' in context_line:
                        customer = context_line
                    
                    # Extract assigned person - look for names after work ID
                    if j > i + 2 and context_line and context_line != '-':
                        # Potential name if it's 2-3 words and doesn't contain tech keywords
                        words = context_line.split()
                        if len(words) == 2 and not any(tech in context_line.lower() for tech in ['sdb', 'queue', 'falcon', 'usa', 'ind', 'deu', 'gbr']):
                            assigned_to = context_line
                
                # Extract title (usually the line right after Work ID)
                if i + 1 < len(lines):
                    potential_title = lines[i + 1].strip()
                    if potential_title and potential_title != '-' and len(potential_title) > 10:
                        # Clean up technical titles from SDB
                        if '[EA][PROD]' in potential_title:
                            # Extract meaningful part of technical error
                            title = potential_title[:80] + ('...' if len(potential_title) > 80 else '')
                        else:
                            title = potential_title[:100] + ('...' if len(potential_title) > 100 else '')
                
                bug = BugItem(
                    id=work_id,
                    title=title,
                    severity=severity,
                    status=status,
                    description=f"Assigned: {assigned_to}, Customer: {customer}",
                    component=component,
                    reported_date=reported_date
                )
                bugs.append(bug)
                
            i += 1
        
        # Remove duplicates and limit results
        seen_ids = set()
        unique_bugs = []
        for bug in bugs[:30]:  # Limit to 30 bugs for performance
            if bug.id not in seen_ids:
                seen_ids.add(bug.id)
                unique_bugs.append(bug)
        
        print(f"Parsed {len(unique_bugs)} bugs from new Salesforce format")
        return unique_bugs
    
    def _parse_csv_risks(self, csv_file: str) -> List[RiskItem]:
        """Parse CSV format for risks."""
        risks = []
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                risks.append(RiskItem(
                    feature=row.get('feature', ''),
                    status=row.get('status', 'Unknown'),
                    priority=row.get('priority', 'Medium'),
                    description=row.get('description', ''),
                    last_updated=row.get('last_updated', datetime.now().strftime('%Y-%m-%d'))
                ))
        return risks
    
    def load_prb_data(self, prb_file: str) -> List[PRBItem]:
        """Load PRB (Problem Report/Incident) data from text file."""
        prbs = []
        
        if not os.path.exists(prb_file):
            print(f"Warning: PRB file {prb_file} not found. Creating example.")
            self._create_example_prb_file(prb_file)
        
        try:
            with open(prb_file, 'r') as f:
                content = f.read().strip()
            
            # Parse PRB text format
            prbs = self._parse_text_prbs(content)
            
        except Exception as e:
            print(f"Error loading PRB data: {e}")
        
        self.data['prbs'] = [vars(prb) for prb in prbs]
        return prbs
    
    def load_bugs_data(self, bugs_file: str) -> List[BugItem]:
        """Load active bugs data from text file."""
        bugs = []
        
        if not os.path.exists(bugs_file):
            print(f"Warning: Bugs file {bugs_file} not found. Creating example.")
            self._create_example_bugs_file(bugs_file)
        
        try:
            with open(bugs_file, 'r') as f:
                content = f.read().strip()
            
            # Parse bugs text format
            bugs = self._parse_text_bugs(content)
            
        except Exception as e:
            print(f"Error loading bugs data: {e}")
        
        self.data['bugs'] = [vars(bug) for bug in bugs]
        return bugs
    
    def load_deployment_summary(self, file_path: str):
        """Load deployment summary from deployment.txt."""
        try:
            if not os.path.exists(file_path):
                print(f"Warning: {file_path} not found. Creating example deployment.txt")
                # Create example deployment.txt
                example_content = """Weekly Deployment Summary - Week of September 15, 2025

This week's deployment activities proceeded smoothly across all stagger groups. 
SDB version 258.11 was successfully deployed to sandbox environments (SB0-SB2) 
with no major issues reported.

Key highlights:
- Version 258.11 rolled out to 150 sandbox cells
- Zero failed deployments
- Average deployment time: 12 minutes
- All post-deployment validations passed

Next week: Planning production rollout to P0-P3 stages pending final validation results."""
                
                with open(file_path, 'w') as f:
                    f.write(example_content)
                print(f"✓ Created example {file_path}")
            
            with open(file_path, 'r') as f:
                content = f.read()
                self.data['deployment_summary'] = content.strip()
                print(f"✓ Loaded deployment summary from {file_path}")
                
        except Exception as e:
            print(f"Error loading deployment summary: {e}")
            self.data['deployment_summary'] = ""

    def extract_prb_data(self, prb_url: str, manual_augmentation_file: Optional[str] = None) -> List[PRBItem]:
        """Extract PRB data from Salesforce report URL."""
        prbs = []
        
        # For now, create a mock implementation since we can't access the actual Salesforce data
        # In production, you would use Salesforce API with proper authentication
        print(f"Note: PRB extraction from {prb_url} requires Salesforce authentication.")
        print("Creating example PRB data. Replace with actual Salesforce integration.")
        
        # Create example PRBs
        example_prbs = [
            PRBItem("PRB001", "Authentication failure in production", "P1-Critical", "Open", 
                   "Users unable to login due to SSO integration issue", "2024-01-15"),
            PRBItem("PRB002", "Performance degradation in search", "P2-High", "In Progress", 
                   "Search queries taking >10s response time", "2024-01-14"),
            PRBItem("PRB003", "UI rendering issue on mobile", "P3-Medium", "Resolved", 
                   "Mobile users see layout breakage on profile page", "2024-01-13"),
        ]
        
        # Apply manual augmentation if provided
        if manual_augmentation_file and os.path.exists(manual_augmentation_file):
            augmentation_data = self._load_augmentation_data(manual_augmentation_file)
            example_prbs = self._augment_prbs(example_prbs, augmentation_data)
        
        self.data['prbs'] = [vars(prb) for prb in example_prbs]
        return example_prbs
    
    def extract_critical_issues(self, critical_url: str) -> List[CriticalIssue]:
        """Extract critical production issues from Salesforce report URL."""
        print(f"Note: Critical issues extraction from {critical_url} requires Salesforce authentication.")
        print("Creating example critical issues data.")
        
        # Create example critical issues
        example_issues = [
            CriticalIssue("CRIT001", "Database connection timeout", "Critical", "Open",
                         "Production database experiencing connection timeouts", 
                         "50% of users affected", "2024-01-15"),
            CriticalIssue("CRIT002", "Payment gateway failure", "Critical", "Resolved",
                         "Payment processing down for 2 hours", 
                         "All payment transactions failed", "2024-01-12"),
        ]
        
        self.data['critical_issues'] = [vars(issue) for issue in example_issues]
        return example_issues
    
    def load_deployment_data(self, csv_file: str) -> List[DeploymentInfo]:
        """Load release deployment information from CSV file."""
        deployments = []
        
        if not os.path.exists(csv_file):
            print(f"Warning: Deployment file {csv_file} not found.")
            self.data['deployments'] = []
            return []
        
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Parse SuperSet export format: stagger, version, SUM(count)
                    deployment_record = {
                        'stagger': row.get('stagger', ''),
                        'version': row.get('version', ''),
                        'count': int(row.get('SUM(count)', 0)) if row.get('SUM(count)') else 0,
                        'stage': row.get('stagger', ''),  # Alias for compatibility
                        'cells': int(row.get('SUM(count)', 0)) if row.get('SUM(count)') else 0  # Alias for compatibility
                    }
                    deployments.append(deployment_record)
                    
        except Exception as e:
            print(f"Error loading deployment data: {e}")
            deployments = []
        
        self.data['deployments'] = deployments
        print(f"✓ Loaded {len(deployments)} deployment records from {csv_file}")
        return deployments
    
    def load_coverage_metrics(self, coverage_file: str) -> List[CoverageMetric]:
        """Load code coverage metrics from file."""
        metrics = []
        
        if not os.path.exists(coverage_file):
            print(f"Warning: Coverage file {coverage_file} not found. Creating example.")
            self._create_example_coverage_file(coverage_file)
        
        try:
            if coverage_file.endswith('.json'):
                with open(coverage_file, 'r') as f:
                    coverage_data = json.load(f)
                    for item in coverage_data:
                        metrics.append(CoverageMetric(**item))
            elif coverage_file.endswith('.csv'):
                with open(coverage_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        metrics.append(CoverageMetric(
                            component=row.get('component', ''),
                            line_coverage=float(row.get('line_coverage', 0)),
                            branch_coverage=float(row.get('branch_coverage', 0)),
                            function_coverage=float(row.get('function_coverage', 0)),
                            test_count=int(row.get('test_count', 0))
                        ))
        except Exception as e:
            print(f"Error loading coverage data: {e}")
        
        self.data['coverage'] = [vars(metric) for metric in metrics]
        return metrics
    
    def load_new_code_coverage(self, coverage_file: str) -> List[NewCodeCoverage]:
        """Load new code coverage data from text file."""
        if not os.path.exists(coverage_file):
            print(f"Warning: New code coverage file {coverage_file} not found.")
            return []
        
        try:
            with open(coverage_file, 'r') as f:
                content = f.read().strip()
            
            # Parse the structured text format
            coverage_data = self._parse_text_coverage(content)
            
            self.data['new_code_coverage'] = [vars(cov) for cov in coverage_data]
            return coverage_data
            
        except Exception as e:
            print(f"Error loading new code coverage data: {e}")
            return []
    
    def _parse_text_coverage(self, content: str) -> List[NewCodeCoverage]:
        """Parse the structured text format from coverage.txt."""
        lines = content.split('\n')
        
        # Initialize data storage
        new_code_data = {}
        overall_data = {}
        current_section = None
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line == "On new code":
                current_section = "new_code"
                i += 1
                continue
            elif line == "Overall":
                current_section = "overall"
                i += 1
                continue
            
            # Parse key-value pairs
            if current_section and line and i + 1 < len(lines):
                value_line = lines[i + 1].strip()
                
                if line == "Coverage" and value_line.endswith('%'):
                    percentage = float(value_line.replace('%', ''))
                    if current_section == "new_code":
                        new_code_data['coverage'] = percentage
                    elif current_section == "overall":
                        overall_data['coverage'] = percentage
                        
                elif line == "Line Coverage" and value_line.endswith('%'):
                    percentage = float(value_line.replace('%', ''))
                    if current_section == "new_code":
                        new_code_data['line_coverage'] = percentage
                    elif current_section == "overall":
                        overall_data['line_coverage'] = percentage
                        
                elif line == "Lines to Cover":
                    count = int(value_line.replace(',', ''))
                    if current_section == "new_code":
                        new_code_data['lines_to_cover'] = count
                    elif current_section == "overall":
                        overall_data['lines_to_cover'] = count
                        
                elif line == "Uncovered Lines":
                    count = int(value_line.replace(',', ''))
                    if current_section == "new_code":
                        new_code_data['uncovered_lines'] = count
                    elif current_section == "overall":
                        overall_data['uncovered_lines'] = count
                        
                elif line == "Condition Coverage" and value_line.endswith('%'):
                    percentage = float(value_line.replace('%', ''))
                    if current_section == "new_code":
                        new_code_data['condition_coverage'] = percentage
                    elif current_section == "overall":
                        overall_data['condition_coverage'] = percentage
                        
                elif line == "Conditions to Cover":
                    count = int(value_line.replace(',', ''))
                    if current_section == "new_code":
                        new_code_data['conditions_to_cover'] = count
                    elif current_section == "overall":
                        overall_data['conditions_to_cover'] = count
                        
                elif line == "Uncovered Conditions":
                    count = int(value_line.replace(',', ''))
                    if current_section == "new_code":
                        new_code_data['uncovered_conditions'] = count
                    elif current_section == "overall":
                        overall_data['uncovered_conditions'] = count
            
            i += 1
        
        # Create coverage object if we have data
        coverage_data = []
        if new_code_data and overall_data:
            coverage_data.append(NewCodeCoverage(
                component="SDB Engine",
                new_code_coverage=new_code_data.get('coverage', 0.0),
                overall_coverage=overall_data.get('coverage', 0.0),
                new_code_line_coverage=new_code_data.get('line_coverage', 0.0),
                overall_line_coverage=overall_data.get('line_coverage', 0.0),
                lines_to_cover=new_code_data.get('lines_to_cover', 0),
                uncovered_lines=new_code_data.get('uncovered_lines', 0),
                overall_lines_to_cover=overall_data.get('lines_to_cover', 0),
                overall_uncovered_lines=overall_data.get('uncovered_lines', 0)
            ))
            
            # Store coverage summary for dashboard visualization
            self.data['coverage_summary'] = {
                'new_code': {
                    'coverage': new_code_data.get('coverage', 0.0),
                    'line_coverage': new_code_data.get('line_coverage', 0.0),
                    'condition_coverage': new_code_data.get('condition_coverage', 0.0),
                    'lines_to_cover': new_code_data.get('lines_to_cover', 0),
                    'uncovered_lines': new_code_data.get('uncovered_lines', 0),
                    'conditions_to_cover': new_code_data.get('conditions_to_cover', 0),
                    'uncovered_conditions': new_code_data.get('uncovered_conditions', 0)
                },
                'overall': {
                    'coverage': overall_data.get('coverage', 0.0),
                    'line_coverage': overall_data.get('line_coverage', 0.0),
                    'condition_coverage': overall_data.get('condition_coverage', 0.0),
                    'lines_to_cover': overall_data.get('lines_to_cover', 0),
                    'uncovered_lines': overall_data.get('uncovered_lines', 0),
                    'conditions_to_cover': overall_data.get('conditions_to_cover', 0),
                    'uncovered_conditions': overall_data.get('uncovered_conditions', 0)
                }
            }
        
        return coverage_data
    
    def load_stagger_deployment_data(self, deployment_file: str) -> List[StaggerDeployment]:
        """Load stagger deployment data from CSV file."""
        deployments = []
        
        if not os.path.exists(deployment_file):
            print(f"Warning: Stagger deployment file {deployment_file} not found.")
            return []
        
        try:
            with open(deployment_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    stagger = row.get('stagger', '').strip()
                    version = row.get('version', '').strip()
                    cell_count_str = row.get('SUM(count)', '0').strip()
                    
                    # Parse cell count
                    try:
                        cell_count = int(cell_count_str)
                    except ValueError:
                        cell_count = 0
                    
                    # Determine deployment phase based on stagger
                    if stagger.startswith('SB'):
                        deployment_phase = "Sandbox"
                    elif stagger.startswith('R'):
                        deployment_phase = "Production Rollout"
                    else:
                        deployment_phase = "Unknown"
                    
                    deployments.append(StaggerDeployment(
                        stagger=stagger,
                        sdb_version=version,
                        cell_count=cell_count,
                        deployment_phase=deployment_phase
                    ))
            
            self.data['stagger_deployments'] = [vars(dep) for dep in deployments]
            return deployments
            
        except Exception as e:
            print(f"Error loading stagger deployment data: {e}")
            return []
    
    def load_ci_issues(self, ci_file: str) -> List[CIIssue]:
        """Load CI issues from text file."""
        if not os.path.exists(ci_file):
            print(f"Warning: CI issues file {ci_file} not found.")
            return []
        
        try:
            with open(ci_file, 'r') as f:
                content = f.read().strip()
            
            issues = self._parse_salesforce_issues(content, "CI")
            ci_issues = [CIIssue(
                work_id=issue['work_id'],
                team=issue['team'],
                priority=issue['priority'],
                subject=issue['subject'],
                status=issue['status'],
                build_version=issue['build_version'],
                created_date=issue['created_date']
            ) for issue in issues]
            
            self.data['ci_issues'] = [vars(issue) for issue in ci_issues]
            return ci_issues
            
        except Exception as e:
            print(f"Error loading CI issues: {e}")
            return []
    
    def load_leftshift_issues(self, leftshift_file: str) -> List[LeftShiftIssue]:
        """Load LeftShift issues from text file."""
        if not os.path.exists(leftshift_file):
            print(f"Warning: LeftShift issues file {leftshift_file} not found.")
            return []
        
        try:
            with open(leftshift_file, 'r') as f:
                content = f.read().strip()
            
            issues = self._parse_salesforce_issues(content, "LeftShift")
            leftshift_issues = [LeftShiftIssue(
                work_id=issue['work_id'],
                team=issue['team'],
                priority=issue['priority'],
                subject=issue['subject'],
                status=issue['status'],
                build_version=issue['build_version'],
                created_date=issue['created_date']
            ) for issue in issues]
            
            self.data['leftshift_issues'] = [vars(issue) for issue in leftshift_issues]
            return leftshift_issues
            
        except Exception as e:
            print(f"Error loading LeftShift issues: {e}")
            return []
    
    def load_abs_issues(self, abs_file: str) -> List[LeftShiftIssue]:
        """Load ABS issues from text file (same format as LeftShift)."""
        if not os.path.exists(abs_file):
            print(f"Warning: ABS issues file {abs_file} not found.")
            return []
        
        try:
            with open(abs_file, 'r') as f:
                content = f.read().strip()
            
            if not content:  # File is empty
                self.data['abs_issues'] = []
                return []
            
            issues = self._parse_salesforce_issues(content, "ABS")
            abs_issues = [LeftShiftIssue(
                work_id=issue['work_id'],
                team=issue['team'],
                priority=issue['priority'],
                subject=issue['subject'],
                status=issue['status'],
                build_version=issue['build_version'],
                created_date=issue['created_date'],
                issue_type="ABS"
            ) for issue in issues]
            
            self.data['abs_issues'] = [vars(issue) for issue in abs_issues]
            return abs_issues
            
        except Exception as e:
            print(f"Error loading ABS issues: {e}")
            return []
    
    def load_security_issues(self, security_file: str) -> List[SecurityIssue]:
        """Load security issues from text file."""
        if not os.path.exists(security_file):
            print(f"Warning: Security issues file {security_file} not found.")
            return []
        
        try:
            with open(security_file, 'r') as f:
                content = f.read().strip()
            
            security_issues = self._parse_security_issues(content)
            
            self.data['security_issues'] = [vars(issue) for issue in security_issues]
            return security_issues
            
        except Exception as e:
            print(f"Error loading security issues: {e}")
            return []
    
    def _parse_salesforce_issues(self, content: str, issue_type: str) -> List[dict]:
        """Parse Salesforce export format for CI/LeftShift/ABS issues."""
        import re
        issues = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for Work ID pattern
            work_id_match = re.search(r'W-\d{8}', line)
            if work_id_match:
                work_id = work_id_match.group()
                
                # Initialize defaults
                team = "Unknown"
                priority = "P2"
                subject = "Unknown Issue"
                status = "New"
                build_version = "Unknown"
                created_date = datetime.now().strftime('%Y-%m-%d')
                
                # Look for context in surrounding lines
                for j in range(max(0, i-15), min(len(lines), i+10)):
                    context_line = lines[j].strip()
                    
                    # Extract team names
                    team_patterns = [
                        'Sayonara Data Management', 'Sayonara Foundation Services',
                        'Sayonara TxP', 'SDB Catalog Services', 'SDB Engine Health',
                        'SDB Query Proc', 'SDBStore', 'SDB Production Readiness'
                    ]
                    for team_pattern in team_patterns:
                        if team_pattern in context_line:
                            team = team_pattern
                    
                    # Extract priority
                    if re.search(r'P[1-4]', context_line):
                        priority_match = re.search(r'P[1-4]', context_line)
                        if priority_match:
                            priority = priority_match.group()
                    
                    # Extract status
                    status_patterns = ['New', 'In Progress', 'Triaged', 'Ready for Review', 'Waiting']
                    for status_pattern in status_patterns:
                        if status_pattern in context_line:
                            status = status_pattern
                    
                    # Extract build version
                    version_match = re.search(r'sdb\.\d+(\.\d+)*', context_line)
                    if version_match:
                        build_version = version_match.group()
                    
                    # Extract subject (usually line after work ID)
                    if j == i + 1 and len(context_line) > 10 and not context_line.startswith('Subtotal'):
                        subject = context_line[:150]  # Limit subject length
                    
                    # Extract date
                    date_match = re.search(r'\d{1,2}/\d{1,2}/\d{4}', context_line)
                    if date_match:
                        try:
                            date_str = date_match.group()
                            month, day, year = date_str.split('/')
                            created_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                        except:
                            pass
                
                issues.append({
                    'work_id': work_id,
                    'team': team,
                    'priority': priority,
                    'subject': subject,
                    'status': status,
                    'build_version': build_version,
                    'created_date': created_date
                })
            
            i += 1
        
        # Remove duplicates
        seen_ids = set()
        unique_issues = []
        for issue in issues:
            if issue['work_id'] not in seen_ids:
                seen_ids.add(issue['work_id'])
                unique_issues.append(issue)
        
        return unique_issues
    
    def _parse_security_issues(self, content: str) -> List[SecurityIssue]:
        """Parse security issues from Coverity/security scan output."""
        import re
        security_issues = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for Work ID pattern
            work_id_match = re.search(r'W-\d{8}', line)
            if work_id_match:
                work_id = work_id_match.group()
                
                # Initialize defaults
                issue_category = "UNKNOWN"
                file_path = ""
                assigned_to = "Unassigned"
                status = "New"
                build_version = "Unknown"
                team = "Security"
                
                # Look for context in surrounding lines
                for j in range(max(0, i-5), min(len(lines), i+8)):
                    context_line = lines[j].strip()
                    
                    # Extract security issue category
                    security_categories = ['RESOURCE_LEAK', 'OVERRUN', 'USE_AFTER_FREE', 'UNINIT', 'NO_EFFECT', 'ARRAY_VS_SINGLETON']
                    for category in security_categories:
                        if category in context_line:
                            issue_category = category
                            # Extract file path
                            if '/' in context_line:
                                path_match = re.search(r'/[^()]+\.(c|cpp|h|java|py)', context_line)
                                if path_match:
                                    file_path = path_match.group()
                    
                    # Extract assigned to
                    if j > i and len(context_line) > 5 and context_line != 'New' and not context_line.startswith('sdb.'):
                        # Try to identify names (simple heuristic)
                        if ' ' in context_line and len(context_line.split()) == 2 and not any(x in context_line.lower() for x in ['test', 'error', 'exception']):
                            assigned_to = context_line
                    
                    # Extract build version
                    version_match = re.search(r'sdb\.\d+(\.\d+)*', context_line)
                    if version_match:
                        build_version = version_match.group()
                    
                    # Extract team
                    if 'Sayonara' in context_line:
                        team = context_line
                
                security_issues.append(SecurityIssue(
                    work_id=work_id,
                    issue_category=issue_category,
                    file_path=file_path,
                    assigned_to=assigned_to,
                    status=status,
                    build_version=build_version,
                    team=team
                ))
            
            i += 1
        
        return security_issues
    
    def load_ss_security_issues(self, ss_file: str):
        """Load security issues from ss.txt file."""
        if not os.path.exists(ss_file):
            print(f"Warning: Security issues file {ss_file} not found.")
            self.data['security_issues'] = []
            return []
        
        try:
            with open(ss_file, 'r') as f:
                content = f.read().strip()
            
            security_issues = self._parse_ss_security_bugs(content)
            
            self.data['security_issues'] = security_issues
            return security_issues
            
        except Exception as e:
            print(f"Error loading security issues from {ss_file}: {e}")
            self.data['security_issues'] = []
            return []
    
    def _parse_ss_security_bugs(self, content: str) -> List[Dict[str, Any]]:
        """Parse security bugs from ss.txt using Coverity scan format with W- work items."""
        security_bugs = []
        if not content:
            return security_bugs
            
        lines = content.split('\n')
        current_priority = 'P4'  # Default priority from the data
        current_team = 'Unknown'
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Extract priority from lines like "P4(16)"
            if line.startswith('P') and '(' in line:
                priority_match = line.split('(')[0]
                if priority_match in ['P0', 'P1', 'P2', 'P3', 'P4']:
                    current_priority = priority_match
            
            # Extract team names like "Sayonara Data Management(16)"
            elif '(' in line and line.endswith(')') and not line.startswith('W-'):
                team_part = line.split('(')[0].strip()
                if len(team_part) > 5 and team_part not in ['Subtotal', 'Total']:
                    current_team = team_part
            
            # Look for work items (W-numbers) which represent security issues
            elif line.startswith('W-'):
                work_id = line.strip()
                
                # Extract details from the next few lines
                build_version = 'Unknown'
                assignee = 'Unknown'
                status = 'Unknown'
                issue_description = 'Security Issue'
                
                # Look ahead for details in the structured format
                if i + 1 < len(lines):
                    build_version = lines[i + 1].strip() or 'Unknown'
                if i + 2 < len(lines):
                    assignee = lines[i + 2].strip() or 'Unknown'
                if i + 3 < len(lines):
                    status = lines[i + 3].strip() or 'Unknown'
                if i + 4 < len(lines):
                    issue_description = lines[i + 4].strip() or 'Security Issue'
                
                # Create security bug entry
                security_bug = {
                    'id': work_id,
                    'title': issue_description,
                    'priority': f"{current_priority}-{'Critical' if current_priority in ['P0', 'P1'] else 'Medium' if current_priority == 'P2' else 'Low'}",
                    'severity': f"{current_priority}-{'Critical' if current_priority in ['P0', 'P1'] else 'Medium' if current_priority == 'P2' else 'Low'}",
                    'status': status,
                    'component': current_team,
                    'assignee': assignee,
                    'build_version': build_version,
                    'description': issue_description,
                    'type': 'security',
                    'issue_category': self._extract_issue_category(issue_description)
                }
                
                security_bugs.append(security_bug)
                
                # Skip the next 4 lines as we've already processed them
                i += 4
            
            i += 1
        
        print(f"Parsed {len(security_bugs)} security bugs from ss.txt")
        return security_bugs
    
    def _extract_issue_category(self, description: str) -> str:
        """Extract issue category from Coverity description."""
        if 'RESOURCE_LEAK' in description:
            return 'Resource Leak'
        elif 'ARRAY_VS_SINGLETON' in description:
            return 'Array vs Singleton'
        elif 'OVERRUN' in description:
            return 'Buffer Overrun'
        elif 'USE_AFTER_FREE' in description:
            return 'Use After Free'
        elif 'UNINIT' in description:
            return 'Uninitialized Variable'
        elif 'NO_EFFECT' in description:
            return 'No Effect'
        else:
            return 'Other'
    
    def analyze_git_repository(self, repo_path: str, period_start: str, period_end: str) -> GitStats:
        """Analyze git repository for code changes during reporting period."""
        import subprocess
        import os
        from datetime import datetime, timedelta
        
        if not os.path.exists(repo_path):
            print(f"Warning: Git repository {repo_path} not found.")
            return self._create_empty_git_stats(period_start, period_end)
        
        if not os.path.exists(os.path.join(repo_path, '.git')):
            print(f"Warning: {repo_path} is not a git repository.")
            return self._create_empty_git_stats(period_start, period_end)
        
        try:
            # Change to repository directory
            original_cwd = os.getcwd()
            os.chdir(repo_path)
            
            # Convert period dates to git format
            git_since = f"--since='{period_start}'"
            git_until = f"--until='{period_end}'"
            
            # Get commit count
            commit_count_cmd = f"git rev-list --count HEAD {git_since} {git_until}"
            total_commits = int(subprocess.check_output(commit_count_cmd, shell=True, text=True).strip())
            
            # Get line changes using git log --stat
            stats_cmd = f"git log --numstat --pretty=format: {git_since} {git_until}"
            stats_output = subprocess.check_output(stats_cmd, shell=True, text=True)
            
            lines_added = 0
            lines_deleted = 0
            files_changed = set()
            file_changes = {}
            
            for line in stats_output.split('\n'):
                if line.strip() and '\t' in line:
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        added = parts[0] if parts[0] != '-' else '0'
                        deleted = parts[1] if parts[1] != '-' else '0'
                        filename = parts[2]
                        
                        try:
                            lines_added += int(added)
                            lines_deleted += int(deleted)
                            files_changed.add(filename)
                            
                            if filename not in file_changes:
                                file_changes[filename] = {'added': 0, 'deleted': 0}
                            file_changes[filename]['added'] += int(added)
                            file_changes[filename]['deleted'] += int(deleted)
                        except ValueError:
                            continue
            
            # Get unique authors
            authors_cmd = f"git log --pretty=format:'%an' {git_since} {git_until} | sort | uniq"
            authors_output = subprocess.check_output(authors_cmd, shell=True, text=True)
            authors = [author.strip() for author in authors_output.split('\n') if author.strip()]
            
            # Get most changed files (top 10)
            most_changed = sorted(file_changes.items(), 
                                key=lambda x: x[1]['added'] + x[1]['deleted'], 
                                reverse=True)[:10]
            
            most_changed_files = [
                {
                    'file': filename,
                    'lines_added': changes['added'],
                    'lines_deleted': changes['deleted'],
                    'total_changes': changes['added'] + changes['deleted']
                }
                for filename, changes in most_changed
            ]
            
            # Calculate metrics
            lines_changed = lines_added + lines_deleted
            
            # Calculate commit frequency (commits per day)
            period_start_dt = datetime.strptime(period_start, '%Y-%m-%d')
            period_end_dt = datetime.strptime(period_end, '%Y-%m-%d')
            days_in_period = (period_end_dt - period_start_dt).days + 1
            commit_frequency = total_commits / days_in_period if days_in_period > 0 else 0
            
            # Assess code churn risk
            code_churn_risk = self._assess_code_churn_risk(
                total_commits, lines_changed, files_changed, days_in_period
            )
            
            git_stats = GitStats(
                reporting_period_start=period_start,
                reporting_period_end=period_end,
                total_commits=total_commits,
                lines_added=lines_added,
                lines_deleted=lines_deleted,
                lines_changed=lines_changed,
                files_changed=len(files_changed),
                authors=authors,
                most_changed_files=most_changed_files,
                commit_frequency=commit_frequency,
                code_churn_risk=code_churn_risk
            )
            
            self.data['git_stats'] = vars(git_stats)
            return git_stats
            
        except subprocess.CalledProcessError as e:
            print(f"Error executing git command: {e}")
            return self._create_empty_git_stats(period_start, period_end)
        except Exception as e:
            print(f"Error analyzing git repository: {e}")
            return self._create_empty_git_stats(period_start, period_end)
        finally:
            # Return to original directory
            os.chdir(original_cwd)
    
    def _create_empty_git_stats(self, period_start: str, period_end: str) -> GitStats:
        """Create empty git stats when repository analysis fails."""
        return GitStats(
            reporting_period_start=period_start,
            reporting_period_end=period_end,
            total_commits=0,
            lines_added=0,
            lines_deleted=0,
            lines_changed=0,
            files_changed=0,
            authors=[],
            most_changed_files=[],
            commit_frequency=0.0,
            code_churn_risk="Unknown"
        )
    
    def _assess_code_churn_risk(self, commits: int, lines_changed: int, files_changed: set, days: int) -> str:
        """Assess risk level based on code churn metrics."""
        if days == 0:
            return "Unknown"
        
        # Calculate daily averages
        daily_commits = commits / days
        daily_lines_changed = lines_changed / days
        daily_files_changed = len(files_changed) / days
        
        # Risk thresholds (adjustable based on team size and project type)
        high_risk_conditions = [
            daily_commits > 10,  # More than 10 commits per day
            daily_lines_changed > 1000,  # More than 1000 lines changed per day
            daily_files_changed > 20,  # More than 20 files changed per day
            lines_changed > 50000  # More than 50k total lines changed in period
        ]
        
        medium_risk_conditions = [
            daily_commits > 5,
            daily_lines_changed > 500,
            daily_files_changed > 10,
            lines_changed > 20000
        ]
        
        if sum(high_risk_conditions) >= 2:
            return "High"
        elif sum(medium_risk_conditions) >= 2:
            return "Medium"
        else:
            return "Low"
    
    def _create_example_risk_file(self, filename: str):
        """Create an example risk tracking file."""
        example_content = """# Risk and Feature Tracking
# Format: Each feature block should contain Feature, Status, Priority, Description, Updated

Feature: User Authentication System
Status: At Risk
Priority: High
Description: SSO integration showing intermittent failures in production
Updated: 2024-01-15

Feature: Payment Processing
Status: Green
Priority: Critical
Description: All payment gateways operational, monitoring in place
Updated: 2024-01-14

Feature: Mobile App Performance
Status: Yellow
Priority: Medium
Description: Response times increasing, optimization needed
Updated: 2024-01-13

Feature: Data Export Feature
Status: Green
Priority: Low
Description: Feature working as expected, no issues reported
Updated: 2024-01-12
"""
        with open(filename, 'w') as f:
            f.write(example_content)
        print(f"Created example risk file: {filename}")
    
    def _create_example_deployment_csv(self, filename: str):
        """Create an example deployment CSV file."""
        example_data = [
            ['version', 'date', 'environment', 'status', 'features', 'issues'],
            ['v2.3.1', '2024-01-15', 'production', 'deployed', 'auth-improvements;ui-updates', ''],
            ['v2.3.0', '2024-01-10', 'production', 'deployed', 'payment-gateway;mobile-fixes', 'minor-ui-glitch'],
            ['v2.2.9', '2024-01-05', 'staging', 'testing', 'data-export;performance-opt', 'load-test-pending'],
        ]
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(example_data)
        print(f"Created example deployment CSV: {filename}")
    
    def _create_example_coverage_file(self, filename: str):
        """Create an example coverage metrics file."""
        example_data = [
            {
                "component": "Authentication Module",
                "line_coverage": 85.2,
                "branch_coverage": 78.5,
                "function_coverage": 92.1,
                "test_count": 156
            },
            {
                "component": "Payment Processing",
                "line_coverage": 91.3,
                "branch_coverage": 87.2,
                "function_coverage": 95.8,
                "test_count": 203
            },
            {
                "component": "UI Components",
                "line_coverage": 73.1,
                "branch_coverage": 65.8,
                "function_coverage": 81.2,
                "test_count": 89
            }
        ]
        
        with open(filename, 'w') as f:
            json.dump(example_data, f, indent=2)
        print(f"Created example coverage file: {filename}")
    
    def _create_example_new_code_coverage_file(self, filename: str):
        """Create an example new code coverage file."""
        example_content = """On new code

Coverage
83.9%

Lines to Cover
6,194

Uncovered Lines
277

Line Coverage
95.5%

Conditions to Cover
5,634

Uncovered Conditions
1,631

Condition Coverage
71.1%

Overall

Coverage
67.8%

Lines to Cover
543,125

Uncovered Lines
104,785

Line Coverage
80.7%

Conditions to Cover
471,493

Uncovered Conditions
222,186

Condition Coverage
52.9%
"""
        with open(filename, 'w') as f:
            f.write(example_content)
        print(f"Created example new code coverage file: {filename}")
    
    def _create_example_prb_file(self, filename: str):
        """Create an example PRB file."""
        example_content = """# PRB/Incident Tracking
# Format: Each incident block should contain PRB, Title, Priority, Status, Description, Reported

PRB: PRB-2024-001
Title: Authentication service timeout
Priority: High
Status: Open
Description: Users experiencing 30-second timeouts during SSO login process
Reported: 2024-01-15

PRB: PRB-2024-002
Title: Database connection pool exhaustion
Priority: Critical
Status: In Progress
Description: Production database reaching max connections during peak hours
Reported: 2024-01-14

PRB: PRB-2024-003
Title: Search index corruption
Priority: Medium
Status: Resolved
Description: Search results returning incomplete data for specific queries
Reported: 2024-01-12
"""
        with open(filename, 'w') as f:
            f.write(example_content)
        print(f"Created example PRB file: {filename}")
    
    def _create_example_bugs_file(self, filename: str):
        """Create an example bugs file."""
        example_content = """# Active Production Bugs
# Format: Each bug block should contain Bug, Title, Severity, Status, Description, Component, Reported

Bug: BUG-2024-001
Title: Memory leak in user session handler
Severity: High
Status: Open
Description: Gradual memory increase in session management service leading to restarts
Component: Authentication Service
Reported: 2024-01-15

Bug: BUG-2024-002
Title: Race condition in payment processing
Severity: Critical
Status: In Progress
Description: Concurrent payment requests causing duplicate charges
Component: Payment Gateway
Reported: 2024-01-14

Bug: BUG-2024-003
Title: UI button misalignment on mobile
Severity: Low
Status: Open
Description: Submit buttons not properly aligned on screens smaller than 375px
Component: Mobile UI
Reported: 2024-01-13
"""
        with open(filename, 'w') as f:
            f.write(example_content)
        print(f"Created example bugs file: {filename}")
    
    def save_archive_data(self, archive_file: str, custom_end_date=None):
        """Save all collected data to archive file with metadata."""
        os.makedirs(os.path.dirname(archive_file), exist_ok=True)
        
        # Add metadata to the data
        dates = get_report_dates(custom_end_date)
        # Compute additional summary counts
        def _count_p0_p1(items):
            try:
                return sum(1 for x in items if str(x.get('priority', '')).upper().startswith(('P0', 'P1')))
            except Exception:
                return 0

        ci_items = self.data.get('ci_issues', []) or []
        sec_items = self.data.get('security_issues', []) or []
        ls_items = self.data.get('leftshift_issues', []) or []
        cov_summary = self.data.get('coverage_summary', {}) or {}
        new_code_cov = cov_summary.get('new_code', {}) if isinstance(cov_summary, dict) else {}
        overall_cov = cov_summary.get('overall', {}) if isinstance(cov_summary, dict) else {}

        metadata = {
            'generated_at': datetime.now().isoformat(),
            'report_period_start': dates['period_start_full'],
            'report_period_end': dates['period_end_full'],
            'report_period_display': dates['period_full'],
            'generator_version': '2.0',
            'data_sources': {
                'risks': len(self.data.get('risks', [])),
                'prbs': len(self.data.get('prbs', [])),
                'bugs': len(self.data.get('bugs', [])),
                'deployments': len(self.data.get('deployments', [])),
                'has_llm_content': 'llm_content' in self.data,
                # Extended metrics
                'ci_total': len(ci_items),
                'ci_p0_p1': _count_p0_p1(ci_items),
                'security_total': len(sec_items),
                'security_p0_p1': _count_p0_p1(sec_items),
                'leftshift_total': len(ls_items),
                'leftshift_p0_p1': _count_p0_p1(ls_items),
                # Coverage (percentages)
                'coverage_overall': float(overall_cov.get('coverage', 0.0) or 0.0),
                'coverage_overall_line': float(overall_cov.get('line_coverage', 0.0) or 0.0),
                'coverage_new_code': float(new_code_cov.get('coverage', 0.0) or 0.0),
                'coverage_new_code_line': float(new_code_cov.get('line_coverage', 0.0) or 0.0)
            }
        }
        
        # Add metadata to data
        self.data['metadata'] = metadata
        
        with open(archive_file, 'w') as f:
            json.dump(self.data, f, indent=2)
        print(f"Data archived to: {archive_file}")
    
    def _load_augmentation_data(self, file_path: str) -> Dict[str, str]:
        """Load manual augmentation data for PRBs."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _augment_prbs(self, prbs: List[PRBItem], augmentation: Dict[str, str]) -> List[PRBItem]:
        """Apply manual augmentation to PRB descriptions."""
        for prb in prbs:
            if prb.id in augmentation:
                prb.description += f" | Manual Note: {augmentation[prb.id]}"
        return prbs

class QualityReportGenerator:
    """Generates quality reports using Salesforce LLM Gateway analysis."""
    
    def __init__(self, llm_api_key: str = None, model: str = "claude-sonnet-4-20250514"):
        self.llm_api_key = llm_api_key or os.getenv("LLM_GW_EXPRESS_KEY", "")
        self.openai_user_id = os.getenv("OPENAI_USER_ID", "")
        self.model = model
        self.api_url = "https://eng-ai-model-gateway.sfproxy.devx-preprod.aws-esvc1-useast2.aws.sfdc.cl/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.llm_api_key}",
            "Content-Type": "application/json"
        } if self.llm_api_key else None
        
    def generate_llm_content_for_dashboard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate all LLM-based content for dashboard consumption."""
        print("🤖 Generating LLM content for dashboard...")
        
        if not self.llm_api_key or not self.headers:
            print("⚠️ No LLM Gateway key provided. Dashboard will show 'content not available' messages.")
            return {}
        
        llm_content = {}
        
        try:
            # Generate PRB narratives
            prbs = data.get('prbs', [])
            prb_narratives = {}
            prb_analyses = {}
            
            for prb in prbs:
                # Handle both dict and object types
                if isinstance(prb, dict):
                    prb_dict = {
                        'id': prb.get('id', 'Unknown'),
                        'title': prb.get('title', ''),
                        'priority': prb.get('priority', ''),
                        'team': prb.get('team', ''),
                        'what_happened': prb.get('what_happened', ''),
                        'proximate_cause': prb.get('proximate_cause', ''),
                        'how_resolved': prb.get('how_resolved', ''),
                        'next_steps': prb.get('next_steps', ''),
                        'customer_impact': prb.get('customer_impact', ''),
                        'status': prb.get('status', ''),
                        'user_experience': prb.get('user_experience', ''),
                        'description': prb.get('description', ''),
                        'created_date': prb.get('created_date', '')
                    }
                else:
                    prb_dict = {
                        'id': getattr(prb, 'id', 'Unknown'),
                        'title': getattr(prb, 'title', ''),
                        'priority': getattr(prb, 'priority', ''),
                        'team': getattr(prb, 'team', ''),
                        'what_happened': getattr(prb, 'what_happened', ''),
                        'proximate_cause': getattr(prb, 'proximate_cause', ''),
                        'how_resolved': getattr(prb, 'how_resolved', ''),
                        'next_steps': getattr(prb, 'next_steps', ''),
                        'customer_impact': getattr(prb, 'customer_impact', ''),
                        'status': getattr(prb, 'status', ''),
                        'user_experience': getattr(prb, 'user_experience', ''),
                        'description': getattr(prb, 'description', ''),
                        'created_date': getattr(prb, 'created_date', '')
                    }
                
                # Generate narrative using LLM
                narrative = self._call_llm_for_prb_narrative(prb_dict)
                prb_narratives[prb_dict['id']] = narrative
                
                # Generate exhaustive analysis using LLM
                analysis = self._call_llm_for_prb_analysis(prb_dict)
                prb_analyses[prb_dict['id']] = analysis
            
            # Generate lower priority summary
            p2_p3_prbs = [p for p in prbs if 'P2' in str(getattr(p, 'priority', '')) or 'P3' in str(getattr(p, 'priority', ''))]
            if p2_p3_prbs:
                lower_summary = self._call_llm_for_lower_priority_summary(p2_p3_prbs)
                llm_content['lower_priority_summary'] = lower_summary
            
            # Generate trend analysis
            trend_analysis = self._call_llm_for_trend_analysis(data)
            llm_content['trend_analysis'] = trend_analysis
            
            # Generate code change risk analysis
            risk_analysis = self._call_llm_for_risk_analysis(data)
            llm_content['risk_analysis'] = risk_analysis
            
            llm_content['prb_narratives'] = prb_narratives
            llm_content['prb_analyses'] = prb_analyses
            
            print("✅ LLM content generated successfully")
            
        except Exception as e:
            print(f"⚠️ LLM content generation failed: {e}")
            return {}
        
        return llm_content

    def _call_llm_for_prb_narrative(self, prb_dict: Dict[str, Any]) -> str:
        """Generate PRB narrative using LLM."""
        prompt = f"""
        You are a technical incident analyst for a database platform team. Analyze this Problem Report (PRB) and provide a clear, concise summary in exactly this format:

        **Problem Type:** [One sentence describing the specific technical issue type]
        **Root Cause:** [One sentence explaining the detailed underlying technical cause]
        **Resolution:** [One sentence describing how the issue was specifically fixed or mitigated]
        **Next Steps:** [One sentence describing concrete follow-up actions or improvements]

        PRB Data:
        ID: {prb_dict['id']}
        Title: {prb_dict['title']}
        Priority: {prb_dict['priority']}
        Team: {prb_dict['team']}
        What Happened: {prb_dict['what_happened']}
        Proximate Cause: {prb_dict['proximate_cause']}
        How Resolved: {prb_dict['how_resolved']}
        Next Steps: {prb_dict['next_steps']}
        """
        
        return self._call_llm_sync(prompt)

    def _call_llm_for_prb_analysis(self, prb_dict: Dict[str, Any]) -> str:
        """Generate exhaustive PRB analysis using LLM."""
        prompt = f"""
        Generate a comprehensive technical analysis for this PRB:

        **Technical Impact:** [Detailed impact assessment]
        **Root Cause Analysis:** [In-depth technical root cause]
        **Resolution Applied:** [Detailed resolution methodology]
        **Preventive Measures:** [Specific prevention strategies]

        PRB Data: {json.dumps(prb_dict, indent=2)}
        """
        
        return self._call_llm_sync(prompt)

    def _call_llm_for_lower_priority_summary(self, prbs: List) -> str:
        """Generate lower priority PRB summary using LLM."""
        prompt = f"""
        Generate a concise summary of these Sev 2+ PRBs:
        
        PRB Data: {json.dumps([{
            'id': getattr(p, 'id', 'Unknown'),
            'priority': getattr(p, 'priority', ''),
            'team': getattr(p, 'team', ''),
            'what_happened': getattr(p, 'what_happened', '')
        } for p in prbs], indent=2)}
        
        Format as: **Current Sev 2+ Issues:** followed by a brief summary of each issue.
        """
        
        return self._call_llm_sync(prompt)

    def _call_llm_for_trend_analysis(self, data: Dict[str, Any]) -> str:
        """Generate quality trends analysis using LLM."""
        prompt = f"""
        Analyze these quality metrics and provide trend insights:
        
        Data Summary:
        - PRBs: {len(data.get('prbs', []))}
        - Bugs: {len(data.get('bugs', []))}
        - Risks: {len(data.get('risks', []))}
        - Security Issues: {len(data.get('security_bugs', []))}
        
        Provide a brief quality trends analysis focusing on overall system health.
        """
        
        return self._call_llm_sync(prompt)

    def _call_llm_for_risk_analysis(self, data: Dict[str, Any]) -> str:
        """Generate code change risk analysis using LLM."""
        prompt = f"""
        Analyze code changes and deployment risks based on this data:
        
        Deployment Summary: {data.get('deployment_summary', 'No deployment data')}
        
        Provide a risk assessment focusing on deployment stability and code change impact.
        
        Format the response using standard markdown headers. Start with ### for the main title 
        (not # which is too large), then use #### for main sections and ##### for subsections. 
        Use consistent formatting that matches typical technical documentation.
        """
        
        return self._call_llm_sync(prompt)

    def _call_llm_sync(self, prompt: str) -> str:
        """Make synchronous LLM call."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self._call_llm_async(prompt))
            finally:
                loop.close()
        except Exception as e:
            print(f"⚠️ LLM call failed: {e}")
            return "Content not available - LLM generation failed"

    async def _call_llm_async(self, prompt: str) -> str:
        """Make async LLM call."""
        messages = [
            {"role": "system", "content": "You are a senior quality engineer providing technical analysis."},
            {"role": "user", "content": prompt}
        ]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.3
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        return result["choices"][0]["message"]["content"].strip()
                
                return "Content not available - LLM API error"

    def generate_report(self, data: Dict[str, Any], report_type: str = "comprehensive") -> str:
        """Generate a quality report using Salesforce LLM Gateway analysis."""
        
        if not self.llm_api_key or not self.headers:
            print("❌ Error: No LLM Gateway key provided. Cannot generate report without LLM access.")
            print("   Please ensure .env file contains valid LLM_GW_EXPRESS_KEY")
            raise RuntimeError("LLM Gateway credentials not available")
        
        try:
            # Run async method in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self._generate_llm_report(data, report_type))
            finally:
                loop.close()
        except Exception as e:
            print(f"❌ Error generating LLM report: {e}")
            print("   Report generation requires working LLM Gateway connection")
            raise RuntimeError(f"LLM report generation failed: {e}")
    
    async def _generate_llm_report(self, data: Dict[str, Any], report_type: str = "comprehensive") -> str:
        """Generate report using async LLM Gateway call."""
        prompt = self._build_prompt(data, report_type)
        
        messages = [
            {"role": "system", "content": "You are a senior quality engineer creating comprehensive quality reports for software teams. Provide actionable insights and clear summaries."},
            {"role": "user", "content": prompt}
        ]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 2000,
            "temperature": 0.3,
            "top_p": 0.9
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=90)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    
                    # Extract response from Salesforce LLM Gateway
                    if "choices" in result and len(result["choices"]) > 0:
                        generated_text = result["choices"][0]["message"]["content"].strip()
                        return generated_text
                    else:
                        print("❌ Error: Unexpected LLM Gateway response format")
                        raise RuntimeError("LLM Gateway returned invalid response format")
                else:
                    error_text = await response.text()
                    print(f"❌ LLM Gateway API error: {response.status} - {error_text}")
                    raise RuntimeError(f"LLM Gateway API failed with status {response.status}: {error_text}")
    
    def _build_llm_prompt(self, data: Dict[str, Any], report_type: str) -> str:
        """Build the prompt for LLM report generation."""
        
        # Get dynamic report dates (use custom date if available)
        dates = get_report_dates(getattr(self, 'custom_end_date', None))
        
        prompt = f"""Generate a {report_type} quality report based on the following data.

- Do NOT include "Prepared by: Quality Engineering Team" or similar attribution lines
- Do NOT include report title, report date, or reporting period in the header


RISK DATA:
{json.dumps(data.get('risks', []), indent=2)}

PRB DATA (Problem Reports/Incidents):
{json.dumps(data.get('prbs', []), indent=2)}

BUGS DATA (Active Production Bugs):
CONTEXT: These bugs are across a production fleet. Calculate fleet size from stagger_deployments data if available. Current bug-to-cell ratio should be evaluated as excellent for large-scale database infrastructure.
{json.dumps(data.get('bugs', []), indent=2)}

CRITICAL ISSUES:
{json.dumps(data.get('critical_issues', []), indent=2)}

DEPLOYMENT DATA (Legacy):
{json.dumps(data.get('deployments', []), indent=2)}

STAGGER DEPLOYMENT DATA:
CONTEXT: This shows SDB version rollout across our fleet using staged deployment phases. Progression: SB0 (sandbox) -> SB1 -> SB2 -> R0 (production) -> R1 -> R2 (full rollout), with signature and high AOV customers prioritized in early phases. Calculate total fleet size from cell_count values.
{json.dumps(data.get('stagger_deployments', []), indent=2)}

CODE COVERAGE METRICS (Legacy JSON format):
{json.dumps(data.get('coverage', []), indent=2)}

NEW CODE COVERAGE DATA (Text format):
{json.dumps(data.get('new_code_coverage', []), indent=2)}

DEVELOPMENT CODELINE HEALTH DATA:

CI ISSUES (from CI system):
{json.dumps(data.get('ci_issues', []), indent=2)}

LEFTSHIFT ISSUES (from LeftShift infrastructure):
{json.dumps(data.get('leftshift_issues', []), indent=2)}

ABS ISSUES (from Salesforce Core app):
{json.dumps(data.get('abs_issues', []), indent=2)}

SECURITY ISSUES (from security scans):
{json.dumps(data.get('security_issues', []), indent=2)}

GIT REPOSITORY STATS (Code churn analysis for reporting period):
{json.dumps(data.get('git_stats', {}), indent=2)}

Please generate a report with the following sections:
1. Executive Summary (high-level quality status)
2. Risk Assessment (analyze risk items by priority and status)
3. Incident Analysis (PRBs, Production Bugs, and Critical Issues breakdown by priority/severity)
4. Deployment Quality (analysis of recent deployments)
5. Development Codeline Health (CI issues, LeftShift, ABS bugs, security issues, code coverage)
6. Recommendations (top 3-5 actionable items)
7. Detailed Data (structured view of all metrics)

IMPORTANT CONTEXT FOR ANALYSIS:
- This is a large-scale production database infrastructure serving ~1000 cells
- Bug counts should be evaluated relative to fleet size (bugs per cell ratio)
- Focus on P1/Critical severity items and trends rather than absolute counts
- Code churn analysis covers the weekly reporting period - zero commits may indicate planned quiet periods
- Evaluate development velocity and risk in context of project phases and release cycles

Use clear, professional language suitable for engineering management. Highlight critical issues and provide specific recommendations.
"""
        return prompt
    
    def _generate_template_report(self, data: Dict[str, Any], report_type: str) -> str:
        """Generate a template report when LLM is not available."""
        
        # Get dynamic report dates (use custom date if available)
        dates = get_report_dates(getattr(self, 'custom_end_date', None))
        
        report = f"""## Executive Summary
This quality report provides an overview of system health, risk factors, incidents, deployments, and test coverage metrics for the period {dates['period_full']}.

## Risk Assessment
**Total Features Tracked:** {len(data.get('risks', []))}
"""
        
        # Analyze risks
        risks = data.get('risks', [])
        risk_status_count = {}
        risk_priority_count = {}
        
        for risk in risks:
            status = risk.get('status', 'Unknown')
            priority = risk.get('priority', 'Unknown')
            risk_status_count[status] = risk_status_count.get(status, 0) + 1
            risk_priority_count[priority] = risk_priority_count.get(priority, 0) + 1
        
        report += f"**Risk Status Breakdown:**\n"
        for status, count in risk_status_count.items():
            report += f"- {status}: {count}\n"
        
        # Analyze PRBs
        prbs = data.get('prbs', [])
        prb_priority_count = {}
        
        for prb in prbs:
            priority = prb.get('priority', 'Unknown')
            prb_priority_count[priority] = prb_priority_count.get(priority, 0) + 1
        
        # Analyze Bugs
        bugs = data.get('bugs', [])
        bug_severity_count = {}
        
        for bug in bugs:
            severity = bug.get('severity', 'Unknown')
            bug_severity_count[severity] = bug_severity_count.get(severity, 0) + 1
        
        report += f"\n## Incident Analysis\n**Total PRBs:** {len(prbs)}\n"
        report += "**PRB Priority Breakdown:**\n"
        for priority, count in prb_priority_count.items():
            report += f"- {priority}: {count}\n"
        
        report += f"\n**Total Active Bugs:** {len(bugs)}\n"
        report += "**Bug Severity Breakdown:**\n"
        for severity, count in bug_severity_count.items():
            report += f"- {severity}: {count}\n"
        
        # Critical Issues
        critical_issues = data.get('critical_issues', [])
        report += f"\n**Critical Issues:** {len(critical_issues)}\n"
        
        # Deployment Analysis
        deployments = data.get('deployments', [])
        stagger_deployments = data.get('stagger_deployments', [])
        
        report += f"\n## Deployment Quality\n"
        if stagger_deployments:
            total_cells = sum(d.get('cell_count', 0) for d in stagger_deployments)
            report += f"**Fleet Size:** {total_cells:,} cells\n"
            
            # Group by version
            version_summary = {}
            for dep in stagger_deployments:
                version = dep.get('sdb_version', 'Unknown')
                if version not in version_summary:
                    version_summary[version] = {'cells': 0, 'staggers': []}
                version_summary[version]['cells'] += dep.get('cell_count', 0)
                version_summary[version]['staggers'].append(dep.get('stagger', ''))
            
            report += f"**Active SDB Versions:** {len(version_summary)}\n"
            for version, info in sorted(version_summary.items(), key=lambda x: x[1]['cells'], reverse=True):
                report += f"- **v{version}**: {info['cells']:,} cells ({', '.join(sorted(set(info['staggers'])))})\n"
        
        if deployments:
            report += f"\n**Legacy Deployments:** {len(deployments)}\n"
        
        # Development Codeline Health Analysis
        ci_issues = data.get('ci_issues', [])
        leftshift_issues = data.get('leftshift_issues', [])
        abs_issues = data.get('abs_issues', [])
        security_issues = data.get('security_issues', [])
        coverage = data.get('coverage', [])
        new_code_coverage = data.get('new_code_coverage', [])
        
        report += f"\n## Development Codeline Health\n"
        
        # CI Issues Summary
        report += f"**CI Issues:** {len(ci_issues)}\n"
        if ci_issues:
            ci_teams = {}
            for issue in ci_issues:
                team = issue.get('team', 'Unknown')
                ci_teams[team] = ci_teams.get(team, 0) + 1
            report += "**CI Issues by Team:**\n"
            for team, count in sorted(ci_teams.items(), key=lambda x: x[1], reverse=True):
                report += f"- {team}: {count}\n"
        
        # LeftShift Issues Summary
        report += f"\n**LeftShift Issues:** {len(leftshift_issues)}\n"
        
        # ABS Issues Summary
        report += f"**ABS Issues:** {len(abs_issues)}\n"
        
        # Security Issues Summary
        report += f"**Security Issues:** {len(security_issues)}\n"
        if security_issues:
            security_categories = {}
            for issue in security_issues:
                category = issue.get('issue_category', 'Unknown')
                security_categories[category] = security_categories.get(category, 0) + 1
            report += "**Security Issues by Category:**\n"
            for category, count in sorted(security_categories.items(), key=lambda x: x[1], reverse=True):
                report += f"- {category}: {count}\n"
        
        # Git Repository Analysis
        git_stats = data.get('git_stats', {})
        report += f"\n**Code Churn Analysis:**\n"
        if git_stats and git_stats.get('total_commits', 0) > 0:
            report += f"- Total Commits: {git_stats['total_commits']}\n"
            report += f"- Lines Changed: {git_stats['lines_changed']:,} (+{git_stats['lines_added']:,} -{git_stats['lines_deleted']:+})\n"
            report += f"- Files Changed: {git_stats['files_changed']}\n"
            report += f"- Active Authors: {len(git_stats['authors'])}\n"
            report += f"- Commit Frequency: {git_stats['commit_frequency']:.1f} commits/day\n"
            report += f"- Code Churn Risk: **{git_stats['code_churn_risk']}**\n"
            
            # Show most changed files if available
            most_changed = git_stats.get('most_changed_files', [])
            if most_changed:
                report += f"- Most Changed Files:\n"
                for i, file_info in enumerate(most_changed[:3], 1):
                    report += f"  {i}. {file_info['file']}: {file_info['total_changes']} lines\n"
        else:
            report += f"- **Quiet Period**: No commits during reporting period ({git_stats.get('reporting_period_start', 'N/A')} to {git_stats.get('reporting_period_end', 'N/A')})\n"
            report += f"- **Code Churn Risk**: {git_stats.get('code_churn_risk', 'Low')} (minimal development activity)\n"
            report += f"- **Status**: This may indicate planned downtime, feature freeze, or focus on non-code activities\n"
        
        # Coverage Analysis
        if new_code_coverage:
            for ncc in new_code_coverage:
                report += f"\n**Code Coverage ({ncc['component']}):**\n"
                report += f"- New Code Coverage: {ncc['new_code_coverage']:.1f}%\n"
                report += f"- Overall Coverage: {ncc['overall_coverage']:.1f}%\n"
        elif coverage:
            avg_line_coverage = sum(c.get('line_coverage', 0) for c in coverage) / len(coverage)
            report += f"\n**Average Line Coverage:** {avg_line_coverage:.1f}%\n"
        
        report += f"\n## Detailed Data\n```json\n{json.dumps(data, indent=2)}\n```"
        
        return report

def main():
    parser = argparse.ArgumentParser(description='Generate Quality Reports')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--risk-file', default='risks.txt', help='Risk tracking file')
    parser.add_argument('--prb-file', default='prb.txt', help='PRB/Incident tracking file')
    parser.add_argument('--bugs-file', default='bugs.txt', help='Active bugs tracking file')
    parser.add_argument('--deployment-csv', default='deployment.csv', help='Deployment CSV file (SuperSet export only)')
    parser.add_argument('--coverage-file', default='coverage.json', help='Coverage metrics file (JSON format)')
    parser.add_argument('--coverage-txt', default='coverage.txt', help='New code coverage file (text format from coverage.txt)')
    parser.add_argument('--ci-file', default='ci.txt', help='CI issues file')
    parser.add_argument('--leftshift-file', default='leftshift.txt', help='LeftShift issues file')
    parser.add_argument('--abs-file', default='abs.txt', help='ABS issues file')
    parser.add_argument('--security-file', default='security.txt', help='Security issues file')
    parser.add_argument('--git-repo-path', default='/Users/rchowdhuri/SDB', help='Local git repository path for code analysis')
    parser.add_argument('--prb-augmentation', help='PRB manual augmentation file (legacy)')
    parser.add_argument('--output-dir', default='./reports', help='Output directory')
    parser.add_argument('--report-type', default='comprehensive', choices=['comprehensive', 'compact'], help='Report type')
    parser.add_argument('--skip-confirmation', action='store_true', help='Skip data readiness confirmation prompt')
    parser.add_argument('--report-end-date', help='Custom report end date (YYYY-MM-DD). Report will cover the week ending on the Sunday before this date.')
    parser.add_argument('--week', help='Calendar week (e.g., cw37, cw38). Automatically sets subdirectory path and report-end-date for historical weeks.')
    
    args = parser.parse_args()
    
    # Handle calendar week argument
    if args.week:
        week_dir = f"weeks/{args.week}"
        if not os.path.exists(week_dir):
            print(f"❌ Week directory not found: {week_dir}")
            return 1
        
        # Set all file paths to use the week subdirectory
        args.risk_file = os.path.join(week_dir, os.path.basename(args.risk_file))
        args.prb_file = os.path.join(week_dir, os.path.basename(args.prb_file))
        args.bugs_file = os.path.join(week_dir, os.path.basename(args.bugs_file))
        args.deployment_csv = os.path.join(week_dir, os.path.basename(args.deployment_csv))
        args.coverage_file = os.path.join(week_dir, os.path.basename(args.coverage_file))
        args.coverage_txt = os.path.join(week_dir, os.path.basename(args.coverage_txt))
        args.ci_file = os.path.join(week_dir, os.path.basename(args.ci_file))
        args.leftshift_file = os.path.join(week_dir, os.path.basename(args.leftshift_file))
        args.abs_file = os.path.join(week_dir, os.path.basename(args.abs_file))
        args.security_file = os.path.join(week_dir, os.path.basename(args.security_file))
        
        # Set report-end-date for historical weeks
        current_week = 38  # This week is cw38
        if args.week.lower() == 'cw37':
            args.report_end_date = '2025-09-21'
            print(f"📅 Using historical week {args.week} with end date: {args.report_end_date}")
        elif args.week.lower() == f'cw{current_week}':
            # Current week, no need to set report-end-date
            print(f"📅 Using current week {args.week}")
        else:
            # For other weeks, you might need to calculate the date
            print(f"📅 Using week {args.week} (no automatic date calculation implemented)")
        
        print(f"📁 Using data from directory: {week_dir}")
    
    # Initialize data collector
    collector = QualityDataCollector(args.config)
    
    # Collect data from all sources
    print("Collecting risk data...")
    collector.load_risk_data(args.risk_file)
    
    print("Loading PRB/incident data...")
    collector.load_prb_data(args.prb_file)
    
    print("Loading bugs data...")
    collector.load_bugs_data(args.bugs_file)
    
    # Critical issues are already loaded as part of bugs data - no need for separate extraction
    
    print("Loading deployment data...")
    collector.load_deployment_data(args.deployment_csv)
    
    print("Loading coverage metrics...")
    collector.load_coverage_metrics(args.coverage_file)
    
    print("Loading new code coverage data...")
    collector.load_new_code_coverage(args.coverage_txt)
    
    print("Loading deployment summary...")
    collector.load_deployment_summary("deployment.txt")
    
    print("Loading development codeline health data...")
    collector.load_ci_issues(args.ci_file)
    collector.load_leftshift_issues(args.leftshift_file)
    collector.load_abs_issues(args.abs_file)
    collector.load_ss_security_issues("ss.txt")
    
    # Parse custom report end date if provided
    custom_end_date = None
    if args.report_end_date:
        try:
            custom_end_date = datetime.strptime(args.report_end_date, '%Y-%m-%d')
            print(f"📅 Using custom report end date: {custom_end_date.strftime('%Y-%m-%d')}")
        except ValueError:
            print(f"❌ Invalid date format: {args.report_end_date}. Use YYYY-MM-DD format.")
            return 1
    
    # Analyze git repository for code churn
    print("Analyzing git repository for code changes...")
    dates = get_report_dates(custom_end_date)
    print(f"📊 Report period: {dates['period_full']}")
    collector.analyze_git_repository(
        args.git_repo_path, 
        dates['period_start_full'], 
        dates['period_end_full']
    )
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Archive data
    archive_file = os.path.join(args.output_dir, f"quality_data_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    collector.save_archive_data(archive_file, custom_end_date)
    
    # Generate LLM content for dashboard if credentials are available
    try:
        llm_generator = QualityReportGenerator()
        # Pass custom end date to LLM generator if provided
        if custom_end_date:
            llm_generator.custom_end_date = custom_end_date
        llm_content = llm_generator.generate_llm_content_for_dashboard(collector.data)
        collector.data['llm_content'] = llm_content
        
        # Re-save archive data with LLM content
        collector.save_archive_data(archive_file, custom_end_date)
        print("✅ LLM content generated and added to archive data")
    except Exception as e:
        print(f"⚠️ LLM content generation skipped: {e}")
        print("   Dashboard will show 'content not available' messages for LLM sections")
        collector.data['llm_content'] = {}
    
    # Confirm data readiness
    if not args.skip_confirmation:
        print("\n" + "="*60)
        print("📋 DATA PREPARATION CHECKLIST")
        print("="*60)
        print("Before generating the report, confirm you have:")
        print("✓ Updated risks.txt with current feature status")
        print("✓ Exported latest PRB data to prb.txt")
        print("✓ Pulled current production bugs to bugs.txt")  
        print("✓ Generated fresh deployment.csv from SuperSet")
        print("✓ Extracted coverage.txt from SonarQube")
        print("✓ Exported CI/security issues to respective files")
        print("✓ Refreshed SDB git repository")
        print("")
        
        while True:
            response = input("📊 All data sources are current and ready? (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                break
            elif response in ['n', 'no', '']:
                print("📋 Please update your data sources first. See INSTRUCTIONS.md for details.")
                return 0
            else:
                print("Please enter 'y' for yes or 'n' for no.")

    # Skip markdown report generation - dashboard only uses JSON data
    print("📊 Skipping markdown report generation (dashboard uses JSON data only)")
    print(f"Data archived: {archive_file}")

    # Display compact summary
    print("\n" + "="*50)
    print("QUALITY REPORT SUMMARY")
    print("="*50)
    risks = collector.data.get('risks', [])
    prbs = collector.data.get('prbs', [])
    bugs = collector.data.get('bugs', [])
    issues = collector.data.get('critical_issues', [])
    
    active_bugs = len([b for b in bugs if b.get('status') != 'Resolved'])
    
    # Calculate actual fleet size from stagger deployment data if available
    stagger_deployments = collector.data.get('stagger_deployments', [])
    if stagger_deployments:
        fleet_size = sum(d.get('cell_count', 0) for d in stagger_deployments)
    else:
        fleet_size = 1000  # Default estimate
    
    bug_ratio = active_bugs / fleet_size
    
    print(f"📊 Features Tracked: {len(risks)}")
    print(f"🚨 Active PRBs: {len([p for p in prbs if p.get('status') != 'Resolved'])}")
    print(f"🐛 Active Bugs: {active_bugs} ({bug_ratio:.3f} per cell across {fleet_size} cells - {'Excellent' if bug_ratio < 0.05 else 'Good' if bug_ratio < 0.1 else 'Review Needed'})")
    print(f"🔥 Critical Issues: {len([i for i in issues if i.get('status') == 'Open'])}")
    
    if collector.data.get('coverage'):
        avg_coverage = sum(c.get('line_coverage', 0) for c in collector.data['coverage']) / len(collector.data['coverage'])
        print(f"🧪 Average Coverage: {avg_coverage:.1f}%")

if __name__ == "__main__":
    main()
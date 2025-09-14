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

def get_report_dates():
    """Calculate dynamic report dates based on current Monday to Sunday period."""
    today = datetime.now()
    
    # Find current week's Monday (start of this week)
    days_since_monday = today.weekday()  # Monday is 0
    current_monday = today - timedelta(days=days_since_monday)
    
    # Current week's Sunday is 6 days after Monday
    current_sunday = current_monday + timedelta(days=6)
    
    return {
        'report_date': today.strftime('%B %d, %Y'),
        'period_start': current_monday.strftime('%B %d'),
        'period_end': current_sunday.strftime('%B %d, %Y'),
        'period_full': f"{current_monday.strftime('%B %d')}-{current_sunday.strftime('%d, %Y')}",
        'period_start_full': current_monday.strftime('%Y-%m-%d'),
        'period_end_full': current_sunday.strftime('%Y-%m-%d')
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
            'stagger_deployments': [],
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
        """Parse PRB data from Salesforce export format."""
        import re
        prbs = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for PRB number
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
                
                # Search context around this line for details
                for j in range(max(0, i-10), min(len(lines), i+30)):
                    context_line = lines[j].strip()
                    
                    # Extract priority
                    if re.search(r'P[1-4]\(\d+\)', context_line):
                        if 'P1(' in context_line:
                            priority = 'P1-Critical'
                        elif 'P2(' in context_line:
                            priority = 'P2-High'
                        elif 'P3(' in context_line:
                            priority = 'P3-Medium'
                        elif 'P4(' in context_line:
                            priority = 'P4-Low'
                    
                    # Extract team
                    team_patterns = [
                        'CRM Database Sustaining Engineering',
                        'CRM DB Replication and Recovery as a Service',
                        'SDB Performance',
                        'Site Reliability'
                    ]
                    for team_pattern in team_patterns:
                        if team_pattern in context_line:
                            team = team_pattern
                    
                    # Extract status
                    status_patterns = ['Analysis Complete', 'Waiting 3rd Party', 'Open', 'Resolved']
                    for status_pattern in status_patterns:
                        if status_pattern in context_line:
                            status = status_pattern
                    
                    # Extract description/title from retrospective line
                    if 'PRB Retrospective' in context_line and '|' in context_line:
                        parts = context_line.split('|')
                        if len(parts) >= 4:
                            title = parts[3].strip()
                            description = context_line
                    
                    # Extract dates
                    date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', context_line)
                    if date_match:
                        try:
                            date_str = date_match.group()
                            month, day, year = date_str.split('/')
                            created_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                        except:
                            pass
                
                prbs.append(PRBItem(
                    id=prb_id,
                    title=title,
                    priority=priority,
                    status=status,
                    description=description[:300] if description else f"Problem report {prb_id} managed by {team}",
                    created_date=created_date
                ))
            
            i += 1
        
        # Remove duplicates based on ID
        seen_ids = set()
        unique_prbs = []
        for prb in prbs:
            if prb.id not in seen_ids:
                seen_ids.add(prb.id)
                unique_prbs.append(prb)
        
        return unique_prbs
    
    def _parse_text_bugs(self, content: str) -> List[BugItem]:
        """Parse bug data from Salesforce work item export format."""
        import re
        bugs = []
        lines = content.split('\n')
        
        current_work_item = None
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for Work ID pattern
            work_id_match = re.search(r'W-\d{8}', line)
            if work_id_match:
                work_id = work_id_match.group()
                
                # Initialize bug data
                severity = 'Medium'
                status = 'Open'
                component = 'Unknown'
                title = 'Unknown Issue'
                description = ''
                reported_date = datetime.now().strftime('%Y-%m-%d')
                
                # Look for context in surrounding lines
                for j in range(max(0, i-10), min(len(lines), i+15)):
                    context_line = lines[j].strip()
                    
                    # Extract priority/severity
                    if re.search(r'P[1-4]', context_line):
                        if 'P1' in context_line:
                            severity = 'P1-Critical'
                        elif 'P2' in context_line:
                            severity = 'P2-High'
                        elif 'P3' in context_line:
                            severity = 'P3-Medium'
                        elif 'P4' in context_line:
                            severity = 'P4-Low'
                    
                    # Extract team/component
                    if any(team in context_line for team in [
                        'Sayonara TxP', 'SDB Query Proc', 'Sayonara Data Management',
                        'Sayonara Foundation Services', 'SDBStore', 'SDB QP Execution'
                    ]):
                        component = context_line
                    
                    # Extract status
                    if any(stat in context_line for stat in [
                        'New', 'In Progress', 'Triaged', 'Open', 'Resolved', 'Closed'
                    ]):
                        status = context_line
                    
                    # Extract title/subject (usually the line right after Work ID)
                    if j == i + 1 and len(context_line) > 10 and not context_line.startswith('Subtotal'):
                        title = context_line[:100]
                        description = context_line[:200]
                    
                    # Extract date
                    date_match = re.search(r'\d{1,2}/\d{1,2}/\d{4}', context_line)
                    if date_match:
                        try:
                            date_str = date_match.group()
                            # Convert MM/DD/YYYY to YYYY-MM-DD
                            month, day, year = date_str.split('/')
                            reported_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                        except:
                            pass
                
                # Handle EA/PROD error patterns
                if '[EA][PROD]' in title:
                    # Extract the actual error from EA format
                    error_parts = title.split(']')
                    if len(error_parts) > 3:
                        title = error_parts[-1].strip()
                        if not title:
                            title = error_parts[-2].strip() if len(error_parts) > 4 else f"Production Error {work_id}"
                
                bugs.append(BugItem(
                    id=work_id,
                    title=title,
                    severity=severity,
                    status=status,
                    description=description,
                    component=component,
                    reported_date=reported_date
                ))
            
            i += 1
        
        # Remove duplicates and limit results
        seen_ids = set()
        unique_bugs = []
        for bug in bugs[:30]:  # Limit to 30 bugs for performance
            if bug.id not in seen_ids:
                seen_ids.add(bug.id)
                unique_bugs.append(bug)
        
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
            print(f"Warning: Deployment file {csv_file} not found. Creating example.")
            self._create_example_deployment_csv(csv_file)
        
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    deployments.append(DeploymentInfo(
                        version=row.get('version', ''),
                        date=row.get('date', ''),
                        environment=row.get('environment', ''),
                        status=row.get('status', ''),
                        features=row.get('features', '').split(';') if row.get('features') else [],
                        issues=row.get('issues', '').split(';') if row.get('issues') else []
                    ))
        except Exception as e:
            print(f"Error loading deployment data: {e}")
        
        self.data['deployments'] = [vars(dep) for dep in deployments]
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
    
    def save_archive_data(self, archive_file: str):
        """Save all collected data to archive file."""
        os.makedirs(os.path.dirname(archive_file), exist_ok=True)
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
    
    def _build_prompt(self, data: Dict[str, Any], report_type: str) -> str:
        """Build the prompt for LLM report generation."""
        
        # Get dynamic report dates
        dates = get_report_dates()
        
        prompt = f"""Generate a {report_type} quality report based on the following data.

IMPORTANT: Use these specific dates in your report header:
- Report Date: {dates['report_date']}
- Reporting Period: {dates['period_full']}
- Do NOT include "Prepared by: Quality Engineering Team" or similar attribution lines

CRITICAL: Start the report with a "Data Preparation Prerequisites" section that explains how users should populate the required data files before running this report generator.

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
    
    def _generate_template_report(self, data: Dict[str, Any]) -> str:
        """Generate a template report when LLM is not available."""
        
        # Get dynamic report dates
        dates = get_report_dates()
        
        report = f"""# Quality Report - {dates['report_date']}

**Report Date:** {dates['report_date']}  
**Reporting Period:** {dates['period_full']}

**NOTE**: For data preparation instructions, see INSTRUCTIONS.md

---

## Executive Summary
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
    parser.add_argument('--deployment-csv', default='deployments.csv', help='Deployment CSV file (legacy format)')
    parser.add_argument('--stagger-deployment-csv', default='deployment.csv', help='Stagger deployment CSV file')
    parser.add_argument('--coverage-file', default='coverage.json', help='Coverage metrics file (JSON format)')
    parser.add_argument('--coverage-txt', help='New code coverage file (text format from coverage.txt)')
    parser.add_argument('--ci-file', default='ci.txt', help='CI issues file')
    parser.add_argument('--leftshift-file', default='leftshift.txt', help='LeftShift issues file')
    parser.add_argument('--abs-file', default='abs.txt', help='ABS issues file')
    parser.add_argument('--security-file', default='security.txt', help='Security issues file')
    parser.add_argument('--git-repo-path', default='/Users/rchowdhuri/SDB', help='Local git repository path for code analysis')
    parser.add_argument('--prb-augmentation', help='PRB manual augmentation file (legacy)')
    parser.add_argument('--output-dir', default='./reports', help='Output directory')
    parser.add_argument('--report-type', default='comprehensive', choices=['comprehensive', 'compact'], help='Report type')
    
    args = parser.parse_args()
    
    # Initialize data collector
    collector = QualityDataCollector(args.config)
    
    # Collect data from all sources
    print("Collecting risk data...")
    collector.load_risk_data(args.risk_file)
    
    print("Loading PRB/incident data...")
    collector.load_prb_data(args.prb_file)
    
    print("Loading bugs data...")
    collector.load_bugs_data(args.bugs_file)
    
    print("Extracting critical issues...")
    collector.extract_critical_issues("https://gus.lightning.force.com/lightning/r/Report/00OEE0000014M4b2AE/view")
    
    print("Loading deployment data...")
    collector.load_deployment_data(args.deployment_csv)
    
    print("Loading stagger deployment data...")
    collector.load_stagger_deployment_data(args.stagger_deployment_csv)
    
    print("Loading coverage metrics...")
    collector.load_coverage_metrics(args.coverage_file)
    
    if args.coverage_txt:
        print("Loading new code coverage data...")
        collector.load_new_code_coverage(args.coverage_txt)
    
    print("Loading development codeline health data...")
    collector.load_ci_issues(args.ci_file)
    collector.load_leftshift_issues(args.leftshift_file)
    collector.load_abs_issues(args.abs_file)
    collector.load_security_issues(args.security_file)
    
    # Analyze git repository for code churn
    print("Analyzing git repository for code changes...")
    dates = get_report_dates()
    collector.analyze_git_repository(
        args.git_repo_path, 
        dates['period_start_full'], 
        dates['period_end_full']
    )
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Archive data
    archive_file = os.path.join(args.output_dir, f"quality_data_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    collector.save_archive_data(archive_file)
    
    # Generate report
    print("Generating quality report...")
    report_generator = QualityReportGenerator(collector.config.get('llm_api_key', ''))
    try:
        report_content = report_generator.generate_report(collector.data, args.report_type)
    except RuntimeError as e:
        print(f"❌ Report generation failed: {e}")
        print("💡 Ensure your .env file contains valid LLM Gateway credentials")
        print("   Required: LLM_GW_EXPRESS_KEY, OPENAI_USER_ID, SALESFORCE_SESSION_ID")
        return 1
    
    # Save report
    report_file = os.path.join(args.output_dir, f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    with open(report_file, 'w') as f:
        f.write(report_content)
    
    print(f"Quality report generated: {report_file}")
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
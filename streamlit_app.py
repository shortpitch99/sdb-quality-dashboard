#!/usr/bin/env python3
"""
Quality Report Dashboard - Streamlit Web Application
Interactive dashboard for viewing and analyzing quality reports.
"""

import streamlit as st
import os
import json
import pandas as pd
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
    page_title="Quality Reports Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

class QualityReportDashboard:
    """Streamlit dashboard for quality reports."""
    
    def __init__(self):
        self.reports_dir = "./reports"
        self.archive_dir = "./archive"
        
        # Ensure directories exist
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.archive_dir, exist_ok=True)
    
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
    
    def get_archive_data(self, report_date: datetime) -> Optional[Dict[str, Any]]:
        """Get archived data for a specific report date."""
        # Look for archive file matching the report date
        date_str = report_date.strftime('%Y%m%d')
        pattern = os.path.join(self.archive_dir, f"*{date_str}*.json")
        archive_files = glob.glob(pattern)
        
        if archive_files:
            # Get the most recent matching archive
            archive_file = max(archive_files, key=os.path.getmtime)
            try:
                with open(archive_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                st.error(f"Error loading archive data: {e}")
        
        return None
    
    def create_metrics_dashboard(self, data: Dict[str, Any]):
        """Create metrics dashboard from archived data."""
        col1, col2, col3, col4 = st.columns(4)
        
        # Risk metrics
        risks = data.get('risks', [])
        risk_status_count = {}
        for risk in risks:
            status = risk.get('status', 'Unknown')
            risk_status_count[status] = risk_status_count.get(status, 0) + 1
        
        at_risk_count = risk_status_count.get('At Risk', 0)
        col1.metric(
            label="🔴 At Risk Features", 
            value=at_risk_count,
            delta=f"of {len(risks)} total"
        )
        
        # PRB metrics
        prbs = data.get('prbs', [])
        open_prbs = len([p for p in prbs if p.get('status') != 'Resolved'])
        col2.metric(
            label="🚨 Open PRBs", 
            value=open_prbs,
            delta=f"of {len(prbs)} total"
        )
        
        # Critical issues
        critical_issues = data.get('critical_issues', [])
        open_critical = len([i for i in critical_issues if i.get('status') == 'Open'])
        col3.metric(
            label="🔥 Critical Issues", 
            value=open_critical,
            delta=f"of {len(critical_issues)} total"
        )
        
        # Coverage
        coverage = data.get('coverage', [])
        if coverage:
            avg_coverage = sum(c.get('line_coverage', 0) for c in coverage) / len(coverage)
            col4.metric(
                label="🧪 Avg Coverage", 
                value=f"{avg_coverage:.1f}%",
                delta=f"{len(coverage)} components"
            )
    
    def create_risk_chart(self, data: Dict[str, Any]):
        """Create risk status visualization."""
        risks = data.get('risks', [])
        if not risks:
            return
        
        # Count risks by status
        risk_counts = {}
        for risk in risks:
            status = risk.get('status', 'Unknown')
            risk_counts[status] = risk_counts.get(status, 0) + 1
        
        # Create pie chart
        fig = px.pie(
            values=list(risk_counts.values()),
            names=list(risk_counts.keys()),
            title="Risk Distribution by Status",
            color_discrete_map={
                'Green': '#2E8B57',
                'Yellow': '#FFD700', 
                'At Risk': '#DC143C',
                'Unknown': '#708090'
            }
        )
        st.plotly_chart(fig, use_container_width=True)
    
    def create_coverage_chart(self, data: Dict[str, Any]):
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
        
        st.plotly_chart(fig, use_container_width=True)
    
    def create_prb_analysis(self, data: Dict[str, Any]):
        """Create PRB analysis visualization."""
        prbs = data.get('prbs', [])
        if not prbs:
            return
        
        # Count PRBs by priority
        priority_counts = {}
        for prb in prbs:
            priority = prb.get('priority', 'Unknown')
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Create horizontal bar chart
        fig = px.bar(
            x=list(priority_counts.values()),
            y=list(priority_counts.keys()),
            orientation='h',
            title="PRB Distribution by Priority",
            color=list(priority_counts.values()),
            color_continuous_scale='Reds'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
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
                        
                        # Save report
                        report_file = os.path.join(self.reports_dir, f"quality_report_{report_type}_{timestamp}.md")
                        with open(report_file, 'w') as f:
                            f.write(report_content)
                        
                        st.success(f"✅ Report generated successfully!")
                        st.info(f"📄 Report saved: {report_file}")
                        st.info(f"🗃️ Data archived: {archive_file}")
                        
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
    
    # Display galaxy banner - stretches across full width
    if os.path.exists("SDB_galaxy_banner.jpg"):
        st.image("SDB_galaxy_banner.jpg", use_container_width=True)
    elif os.path.exists("assets/SDB_galaxy_banner.jpg"):
        st.image("assets/SDB_galaxy_banner.jpg", use_container_width=True)
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
    reports = dashboard.get_report_files()
    
    # Sidebar for report selection and navigation
    st.sidebar.title("📋 Quality Reports")
    
    if reports:
        # Group reports by type for better organization
        comprehensive_reports = [r for r in reports if r['type'] == 'Comprehensive']
        compact_reports = [r for r in reports if r['type'] == 'Compact']
        
        st.sidebar.markdown("### 📊 Comprehensive Reports")
        selected_report = None
        
        # Use session state to track selected report
        if 'selected_report_path' not in st.session_state:
            # Default to latest comprehensive report
            if comprehensive_reports:
                st.session_state.selected_report_path = comprehensive_reports[0]['path']
            elif compact_reports:
                st.session_state.selected_report_path = compact_reports[0]['path']
            else:
                st.session_state.selected_report_path = None
        
        # Show comprehensive reports first
        for i, report in enumerate(comprehensive_reports[:10]):  # Show latest 10
            is_selected = st.session_state.selected_report_path == report['path']
            if st.sidebar.button(
                f"{'🟢' if is_selected else '📄'} {report['date'].strftime('%m/%d %H:%M')}",
                key=f"comp_{i}",
                help=f"{report['type']} Report",
                type="primary" if is_selected else "secondary"
            ):
                st.session_state.selected_report_path = report['path']
                selected_report = report
        
        st.sidebar.markdown("### 📝 Compact Reports") 
        for i, report in enumerate(compact_reports[:10]):  # Show latest 10
            is_selected = st.session_state.selected_report_path == report['path']
            if st.sidebar.button(
                f"{'🟢' if is_selected else '📄'} {report['date'].strftime('%m/%d %H:%M')}",
                key=f"comp_small_{i}",
                help=f"{report['type']} Report",
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
        if selected_report is None:
            if comprehensive_reports:
                selected_report = comprehensive_reports[0]
                st.session_state.selected_report_path = selected_report['path']
            elif compact_reports:
                selected_report = compact_reports[0]
                st.session_state.selected_report_path = selected_report['path']
    else:
        st.sidebar.warning("No reports found")
        selected_report = None
    
    st.sidebar.markdown("---")
    
    # Sidebar navigation for other functions
    st.sidebar.title("🔍 Actions")
    page = st.sidebar.selectbox(
        "Additional Options:",
        ["📈 Analytics", "🔄 Generate Report"],
        index=0
    )
    
    # Main content area - always show the selected report
    if selected_report:
        # Load and display the selected report
        try:
            # Report header with key info
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.subheader(f"📄 {selected_report['type']} Report")
            with col2:
                st.write(f"**Date:** {selected_report['date'].strftime('%Y-%m-%d %H:%M')}")
            with col3:
                st.write(f"**Type:** {selected_report['type']}")
            
            # Try to load associated archive data for metrics
            archive_data = dashboard.get_archive_data(selected_report['date'])
            
            # Show metrics if archive data is available
            if archive_data:
                st.markdown("### 📊 Key Metrics")
                dashboard.create_metrics_dashboard(archive_data)
                st.markdown("---")
            
            # Load and display the report content
            with open(selected_report['path'], 'r') as f:
                report_content = f.read()
            
            st.markdown("### 📄 Report Content")
            st.markdown(report_content)
            
        except Exception as e:
            st.error(f"Error loading report: {e}")
    
    elif not reports:
        st.warning("📭 No reports found. Generate your first report using the 'Generate Report' option in the sidebar.")
        st.markdown("### 🚀 Get Started")
        st.markdown("""
        1. **Generate a Report**: Use the 'Generate Report' option in the sidebar
        2. **Prepare Your Data**: Ensure you have the necessary input files (risks.txt, deployments.csv, etc.)
        3. **View Results**: Reports will appear in the sidebar once generated
        """)
    
    # Handle other page selections
    if page == "📈 Analytics":
        st.header("📈 Quality Analytics")
        
        reports = dashboard.get_report_files()
        if not reports:
            st.warning("No reports found for analytics.")
            return
        
        # Let user select a report for detailed analytics
        selected_report = st.selectbox(
            "Select report for detailed analytics:",
            options=reports,
            format_func=lambda x: x['display_name']
        )
        
        if selected_report:
            archive_data = dashboard.get_archive_data(selected_report['date'])
            
            if archive_data:
                col1, col2 = st.columns(2)
                
                with col1:
                    dashboard.create_risk_chart(archive_data)
                    dashboard.create_prb_analysis(archive_data)
                
                with col2:
                    dashboard.create_coverage_chart(archive_data)
                
                # Detailed data tables
                st.subheader("📋 Detailed Data")
                
                tab1, tab2, tab3, tab4 = st.tabs(["🔴 Risks", "🚨 PRBs", "🔥 Critical Issues", "🧪 Coverage"])
                
                with tab1:
                    risks = archive_data.get('risks', [])
                    if risks:
                        risk_df = pd.DataFrame(risks)
                        st.dataframe(risk_df, use_container_width=True)
                    else:
                        st.info("No risk data available.")
                
                with tab2:
                    prbs = archive_data.get('prbs', [])
                    if prbs:
                        prb_df = pd.DataFrame(prbs)
                        st.dataframe(prb_df, use_container_width=True)
                    else:
                        st.info("No PRB data available.")
                
                with tab3:
                    critical_issues = archive_data.get('critical_issues', [])
                    if critical_issues:
                        critical_df = pd.DataFrame(critical_issues)
                        st.dataframe(critical_df, use_container_width=True)
                    else:
                        st.info("No critical issues data available.")
                
                with tab4:
                    coverage = archive_data.get('coverage', [])
                    if coverage:
                        coverage_df = pd.DataFrame(coverage)
                        st.dataframe(coverage_df, use_container_width=True)
                    else:
                        st.info("No coverage data available.")
            else:
                st.warning("No archive data found for this report. Analytics not available.")
    
    elif page == "🔄 Generate Report":
        # Clear the main area and show generation interface
        st.markdown("---")
        dashboard.generate_new_report()
    
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

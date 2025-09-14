# Quality Report Generator

A comprehensive Python tool that generates quality reports using LLM analysis of various data sources including risk tracking, PRBs (Problem Reports), critical production issues, deployment information, and code coverage metrics.

## 🌟 Features

- **📊 Interactive Web Dashboard**: Streamlit-based web interface for viewing and analyzing reports
- **🔍 Risk Assessment**: Track features and their status from text files
- **🚨 PRB Analysis**: Extract and analyze Problem Reports from Salesforce (with manual augmentation support)  
- **🔥 Critical Issues Monitoring**: Track critical production issues from Salesforce reports
- **🚀 Deployment Tracking**: Monitor release deployments from CSV data
- **🧪 Coverage Analysis**: Analyze code coverage metrics
- **🤖 LLM-Powered Insights**: Generate intelligent reports using Salesforce LLM Gateway
- **📁 Data Archival**: Save all source data for record keeping
- **📈 Analytics Dashboard**: Interactive charts and visualizations
- **⚡ Flexible Output**: Generate both compact and comprehensive reports

## 🚀 Quick Start

### 1. Run the Interactive Dashboard
```bash
./run_dashboard.sh
```
This will start a web interface at `http://localhost:8501` where you can:
- View all your quality reports
- Generate new reports
- Analyze metrics with interactive charts
- Browse historical data

### 2. Run Demo (Command Line)
```bash
./run_demo.sh
```

### 3. Generate Reports Manually
```bash
source venv/bin/activate
python3 quality_report_generator.py --risk-file risks.txt --deployment-csv deployments.csv
```

## 📱 Web Dashboard Features

### 📋 Report Viewer
- **Browse Reports**: View all generated reports organized by date
- **Quick Metrics**: See key metrics at a glance (at-risk features, open PRBs, coverage)
- **Interactive Content**: Click to view full report content
- **Search & Filter**: Easy navigation through historical reports

### 📈 Analytics
- **Risk Distribution**: Pie chart showing risk status breakdown
- **PRB Analysis**: Priority distribution of problem reports  
- **Coverage Metrics**: Component-wise test coverage visualization
- **Data Tables**: Detailed tabular view of all metrics
- **Historical Trends**: Compare metrics across different reports

### 🔄 Report Generation
- **Web-based Generation**: Create new reports directly from the dashboard
- **File Upload**: Specify custom input files
- **Real-time Progress**: See generation status and results
- **Instant View**: Automatically display newly generated reports

## 🛠️ Setup

### Prerequisites
- Python 3.8+
- Virtual environment support

### Installation
```bash
# Clone or navigate to the project directory
cd /Users/rchowdhuri/QC

# Install and run (automatic setup)
./run_dashboard.sh

# OR manual setup:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuration
1. **Environment Variables**: Copy and edit `.env` file with your credentials:
   ```bash
   cp env.example .env
   # Edit .env with your LLM Gateway and Salesforce credentials
   ```

2. **Input Files**: Prepare your data files or use the provided examples:
   - `risks.txt` - Risk/feature tracking data
   - `deployments.csv` - Release deployment information
   - `coverage.json` - Code coverage metrics

## 📊 Dashboard Screenshots

The web dashboard provides:
- **Multi-tab Interface**: Separate sections for viewing, analytics, and generation
- **Responsive Design**: Works on desktop and mobile devices
- **Real-time Updates**: Automatically refreshes when new reports are generated
- **Export Capabilities**: Download reports and data

## 📁 Project Structure
```
/Users/rchowdhuri/QC/
├── streamlit_app.py              # Web dashboard application
├── quality_report_generator.py   # Main program
├── demo.py                       # Demo script
├── salesforce_integration.py     # Salesforce API integration
├── run_dashboard.sh              # Dashboard launcher
├── run_demo.sh                   # Demo launcher
├── venv/                         # Virtual environment
├── examples/                     # Sample input files
├── reports/                      # Generated reports
├── archive/                      # Data archives
└── .env                         # Your credentials
```

## 🔧 Input File Formats

### Risk Tracking File (risks.txt)
```
# Risk and Feature Tracking

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
```

### Deployment CSV (deployments.csv)
```csv
version,date,environment,status,features,issues
v2.3.1,2024-01-15,production,deployed,auth-improvements;ui-updates,
v2.3.0,2024-01-10,production,deployed,payment-gateway;mobile-fixes,minor-ui-glitch
```

### Coverage Metrics (coverage.json)
```json
[
  {
    "component": "Authentication Module",
    "line_coverage": 85.2,
    "branch_coverage": 78.5, 
    "function_coverage": 92.1,
    "test_count": 156
  }
]
```

### PRB Manual Augmentation (prb_augmentation.json)
```json
{
  "PRB001": "Customer impact confirmed - 500+ users affected",
  "PRB002": "Performance testing scheduled for next sprint"
}
```

## 🌐 Web Dashboard Usage

### Starting the Dashboard
```bash
./run_dashboard.sh
```

### Dashboard Pages

1. **📋 Report Viewer**
   - Lists all available reports chronologically
   - Shows key metrics for quick assessment
   - Click any report to view full content

2. **📈 Analytics**  
   - Interactive charts and visualizations
   - Risk distribution pie chart
   - Coverage metrics by component
   - PRB priority analysis
   - Detailed data tables with filtering

3. **🔄 Generate Report**
   - Web form to create new reports
   - Upload or specify input files
   - Real-time generation progress
   - Immediate viewing of results

### Navigation Tips
- Use the sidebar to switch between pages
- Reports are automatically sorted by date (newest first)
- Metrics dashboard updates based on selected report
- Charts are interactive - hover for details

## 🔌 Salesforce Integration

Currently uses example data for PRBs and Critical Issues. To integrate with actual Salesforce:

1. Obtain Salesforce session ID and instance URL
2. Update the `extract_prb_data()` and `extract_critical_issues()` methods with actual Salesforce API calls
3. The URLs provided in the requirements are:
   - PRBs: https://gus.lightning.force.com/lightning/r/Report/00OEE000001TXjB2AW/view
   - Critical Issues: https://gus.lightning.force.com/lightning/r/Report/00OEE0000014M4b2AE/view

## 📈 Report Structure

Generated reports include:
1. **Executive Summary**: High-level quality status
2. **Risk Assessment**: Risk items analyzed by priority and status  
3. **Incident Analysis**: PRBs and Critical Issues breakdown
4. **Deployment Quality**: Recent deployment analysis
5. **Test Coverage Analysis**: Coverage metrics and recommendations
6. **Recommendations**: Top actionable items
7. **Detailed Data**: Structured view of all metrics (comprehensive reports only)

## 🔄 Automation

### Scheduled Reports
Set up automated report generation:
```bash
# Add to crontab for weekly reports
0 9 * * 1 cd /Users/rchowdhuri/QC && ./run_demo.sh
```

### CI/CD Integration
Include in your deployment pipeline:
```yaml
- name: Generate Quality Report
  run: |
    cd /Users/rchowdhuri/QC
    source venv/bin/activate
    python3 quality_report_generator.py --deployment-csv latest_deployment.csv
```

## 🎯 Customization

### Custom Report Templates
Modify `_build_prompt()` in `quality_report_generator.py` to customize:
- Report sections and focus areas
- Analysis depth and detail level
- Specific metrics and KPIs
- Formatting and presentation style

### Adding Data Sources
Extend the `QualityDataCollector` class to include:
- New data source integrations
- Custom metric calculations  
- Additional report sections
- Enhanced filtering and analysis

### Dashboard Customization
Modify `streamlit_app.py` to add:
- New chart types and visualizations
- Custom filtering and search
- Additional dashboard pages
- Integration with other tools

## 🐛 Troubleshooting

### Common Issues
- **Dashboard won't start**: Check that all dependencies are installed (`pip install -r requirements.txt`)
- **No LLM Gateway access**: Verify `.env` file has correct `LLM_GW_EXPRESS_KEY` and `OPENAI_USER_ID`
- **Missing reports**: Run `./run_demo.sh` to generate example reports
- **Salesforce integration**: Currently uses mock data - implement actual API calls as needed

### Performance Tips
- Archive old reports to keep dashboard responsive
- Use compact report type for faster generation
- Limit chart data points for large datasets

## 🤝 Contributing

This tool is designed for internal quality reporting purposes. To extend functionality:

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality  
4. Submit pull request with detailed description

## 📄 License

Internal tool for quality reporting and analysis.

---

## 🚀 Get Started Now!

1. **Launch Dashboard**: `./run_dashboard.sh`
2. **Browse Reports**: Visit http://localhost:8501
3. **Generate First Report**: Use the "Generate Report" page
4. **Explore Analytics**: Check out the interactive charts and metrics

**Happy Quality Reporting! 📊✨**
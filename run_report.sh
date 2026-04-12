#!/bin/bash

# SDB Quality Report Generator
# This script generates a comprehensive quality report for SDB components
#
# Usage: ./run_report.sh [week] [component] [api?]
# Examples:
#   ./run_report.sh cw40 Engine
#   ./run_report.sh cw40 Store api            # use Salesforce Reports API (no local PRB/bugs/ci/leftshift/security files)
#   ./run_report.sh cw40 SDD --use-salesforce-reports
#
# Components (output folders): Engine, Store, SDD, "Core App Efficiency"
# Dashboard: four tabs — Engine, Store, SDD, Core Optimizer and SFSQL
#
# Git code-churn stats (per component; see quality_report_generator.DEFAULT_GIT_REPO_BY_COMPONENT):
#   Engine → ~/SDB, Store → ~/bookkeeper, SDD → ~/sdd, Core App Efficiency → ~/SDB
#   Override: QC_GIT_REPO_ENGINE, QC_GIT_REPO_STORE, QC_GIT_REPO_SDD, QC_GIT_REPO_CORE or --git-repo-path
#
# DATA SOURCE URLs (Reports API when enabled):
# - PRB Report:      00OEE000001TXjB2AW
# - Fleet Bugs:      00OEE0000014M4b2AE
# - CI Issues:       00OEE000002WjvJ2AS
# - LeftShift:       00OEE000002Wjld2AC
# - ABS Issues (Engine): 00OEE000002bDht2AE
# - ABS Issues (Store):  00OEE0000030o6L2AQ
# - ABS Issues (SDD): 00OEE0000030o7x2AA
# - Security:        00OB0000002qWjvMAE
# - All-time Backlog (Engine): 00OEE000002XRUv2AO
# - All-time Backlog (Store):  00OEE0000030oHd2AI
# - All-time Backlog (SDD): 00OEE0000030oKr2AI
# - PRB Backlog (Engine): 00OEE000002ZnZN2A0
# - PRB Backlog (Store):  00OEE0000030oCn2AI
# - PRB Backlog (SDD): 00OEE0000030oEP2AY
# - SonarQube:     https://sonarqube.sfcq.buildndeliver-s.aws-esvc1-useast2.aws.sfdc.cl/component_measures?id=sayonara.sayonaradb.sdb&metric=uncovered_lines&view=list

# Parse arguments
WEEK="$1"
COMPONENT="$2"
API_FLAG_RAW="$3"

# Enable Reports API if third arg is provided (api/--use-salesforce-reports/true/1) or env USE_SF_REPORTS=1
USE_SF_REPORTS=0
if [ "$API_FLAG_RAW" = "api" ] || [ "$API_FLAG_RAW" = "--use-salesforce-reports" ] || [ "$API_FLAG_RAW" = "true" ] || [ "$API_FLAG_RAW" = "1" ] || [ "$USE_SF_REPORTS" = "1" ]; then
  USE_SF_REPORTS=1
fi

# Check if both parameters are provided
if [ -z "$WEEK" ] || [ -z "$COMPONENT" ]; then
    echo "❌ Error: Both week and component parameters are required"
    echo ""
    echo "Usage: $0 <week> <component>"
    echo ""
    echo "Examples:"
    echo "  $0 cw40 Engine"
    echo "  $0 cw40 Store"
    echo "  $0 cw40 SDD"
    echo "  $0 cw40 \"Core App Efficiency\""
    echo ""
    echo "Available components: Engine, Store, SDD, Core App Efficiency"
    exit 1
fi

echo "🚀 Starting SDB Quality Report Generation..."
echo "📅 Week: $WEEK"
echo "📊 Component: $COMPONENT"
echo "==============================================="
if [ "$USE_SF_REPORTS" = "1" ]; then
  echo "🛰️  Mode: Salesforce Reports API (no local PRB/bugs/CI/leftshift/security files required)"
else
  echo "📄 Mode: Local text files for PRB/bugs/CI/leftshift/security"
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first."
    echo "   Create venv: python3 -m venv venv"
    echo "   Install deps: pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check if all required data files exist
echo "🔍 Checking required data files..."

missing_files=()

# Determine data directory based on week and component parameters
data_dir="weeks/$WEEK/$COMPONENT"
echo "📂 Looking for data files in: $data_dir/"

if [ ! -f "$data_dir/risks.txt" ]; then
    missing_files+=("risks.txt")
fi

# Only require these when NOT using the Reports API
if [ "$USE_SF_REPORTS" != "1" ]; then
  if [ ! -f "$data_dir/prb.txt" ]; then
      missing_files+=("prb.txt")
  fi
  if [ ! -f "$data_dir/bugs.txt" ]; then
      missing_files+=("bugs.txt")
  fi
fi

if [ ! -f "$data_dir/deployment.csv" ]; then
    missing_files+=("deployment.csv")
fi

if [ ! -f "$data_dir/coverage.txt" ]; then
    missing_files+=("coverage.txt")
fi

if [ "$USE_SF_REPORTS" != "1" ]; then
  if [ ! -f "$data_dir/ci.txt" ]; then
      missing_files+=("ci.txt")
  fi
  if [ ! -f "$data_dir/leftshift.txt" ]; then
      missing_files+=("leftshift.txt")
  fi
  if [ ! -f "$data_dir/ss.txt" ]; then
      missing_files+=("ss.txt")
  fi
fi

# Check if git repository exists
if [ ! -d "/Users/rchowdhuri/SDB/.git" ]; then
    missing_files+=("SDB git repository at /Users/rchowdhuri/SDB")
fi

if [ ${#missing_files[@]} -ne 0 ]; then
    echo "❌ Missing required data files in $data_dir/:"
    for file in "${missing_files[@]}"; do
        echo "   - $file"
    done
    echo ""
    if [ "$1" ]; then
        echo "📋 Please ensure all data files are present in the $data_dir/ directory."
        echo "   You can copy files from another week or prepare new data files."
    else
        echo "📋 Please follow the data preparation instructions in the generated report."
    fi
    echo "   Run this script again after preparing all data files."
    exit 1
fi

echo "✅ All data files found!"

# Update git repository
echo "🔄 Updating SDB git repository..."
cd /Users/rchowdhuri/SDB
echo "   - Fetching latest changes..."
git fetch --quiet
echo "   - Updating submodules..."
git submodule update --init --recursive --quiet
echo "   - Rebasing to latest..."
git rebase --quiet
cd - > /dev/null

echo "✅ Git repository updated!"

# Archive previous reports (do not clean - reports are meant to be archived)
echo "📁 Archiving functionality enabled - previous reports preserved"

# Generate the quality report
echo "📊 Generating comprehensive quality report..."

# Generate report with mandatory week and component parameters
echo "📅 Using calendar week: $WEEK"
echo "🔧 Using component: $COMPONENT"
# Git code stats: per-component repo (see DEFAULT_GIT_REPO_BY_COMPONENT in quality_report_generator.py).
# Override all: GEN_CMD+=(--git-repo-path /path/to/repo)
GEN_CMD=(
  python3 quality_report_generator.py
  --week "$WEEK"
  --component "$COMPONENT"
  --report-type comprehensive
  --skip-confirmation
)

if [ "$USE_SF_REPORTS" = "1" ]; then
  GEN_CMD+=(--use-salesforce-reports)
fi

"${GEN_CMD[@]}"
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "✅ Quality report generated successfully!"
    echo "📁 Reports available in: ./reports/$COMPONENT/"
    echo ""
    echo "🌐 To view in dashboard, run: ./run_dashboard.sh"
    echo ""
    
    # Show the latest report file for this component
    latest_report=$(ls -t reports/$COMPONENT/*.json 2>/dev/null | head -1)
    if [ -n "$latest_report" ]; then
        echo "📄 Latest report: $latest_report"
        echo "📏 Report size: $(wc -c < "$latest_report") bytes"
    fi
elif [ $exit_code -eq 1 ] && [ "$USE_SF_REPORTS" = "1" ]; then
    echo ""
    echo "❌ Report generation failed due to Salesforce authentication error!"
    echo "🔐 Your Salesforce session has expired or is invalid."
    echo ""
    echo "📋 To fix this issue:"
    echo "   1. Re-authenticate with Salesforce:"
    echo "      sfdx force:auth:web:login --instance-url https://gus.salesforce.com --alias gus"
    echo "   2. Re-run the report generation command"
    echo ""
    echo "💡 Alternative: Run without --use-salesforce-reports to use local files instead"
    exit 1
else
    echo ""
    echo "❌ Report generation failed!"
    echo "📋 Check the error messages above for details"
    echo "💡 Common issues:"
    echo "   - Missing or invalid .env file with LLM Gateway credentials"
    echo "   - Network connectivity issues"
    echo "   - Invalid data in source files"
    if [ "$USE_SF_REPORTS" = "1" ]; then
        echo "   - Salesforce authentication issues (try re-authenticating)"
    fi
    exit 1
fi

echo "==============================================="
echo "🎉 SDB Quality Report Generation Complete!"

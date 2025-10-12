#!/bin/bash

# SDB Quality Report Generator
# This script generates a comprehensive quality report for SDB components
#
# Usage: ./run_report.sh [week] [component]
# Examples:
#   ./run_report.sh cw40 Engine
#   ./run_report.sh cw40 Store
#   ./run_report.sh cw40 Archival
#
# Components: Engine, Store, Archival, SDD, msSDB, "Core App Efficiency"
#
# DATA SOURCE URLs - ALL CONFIRMED:
# - PRB Report:    https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=report&wave__assetId=00OEE000001TXjB2AW
# - Fleet Bugs:    https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=report&wave__assetId=00OEE0000014M4b2AE
# - CI Issues:     https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=report&wave__assetId=00OEE000002WjvJ2AS
# - LeftShift:     https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=report&wave__assetId=00OEE000002WjvJ2AS
# - ABS Issues:    https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=report&wave__assetId=00OEE000002WjvJ2AS
# - Security:      https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=lightningdashboard&wave__assetId=01ZEE000001BaVp2AK
# - SonarQube:     https://sonarqube.sfcq.buildndeliver-s.aws-esvc1-useast2.aws.sfdc.cl/component_measures?id=sayonara.sayonaradb.sdb&metric=uncovered_lines&view=list

# Parse arguments
WEEK="$1"
COMPONENT="$2"

# Check if both parameters are provided
if [ -z "$WEEK" ] || [ -z "$COMPONENT" ]; then
    echo "❌ Error: Both week and component parameters are required"
    echo ""
    echo "Usage: $0 <week> <component>"
    echo ""
    echo "Examples:"
    echo "  $0 cw40 Engine"
    echo "  $0 cw40 Store"
    echo "  $0 cw40 Archival"
    echo "  $0 cw40 SDD"
    echo "  $0 cw40 msSDB"
    echo "  $0 cw40 \"Core App Efficiency\""
    echo ""
    echo "Available components: Engine, Store, Archival, SDD, msSDB, Core App Efficiency"
    exit 1
fi

echo "🚀 Starting SDB Quality Report Generation..."
echo "📅 Week: $WEEK"
echo "📊 Component: $COMPONENT"
echo "==============================================="

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

if [ ! -f "$data_dir/prb.txt" ]; then
    missing_files+=("prb.txt")
fi

if [ ! -f "$data_dir/bugs.txt" ]; then
    missing_files+=("bugs.txt")
fi

if [ ! -f "$data_dir/deployment.csv" ]; then
    missing_files+=("deployment.csv")
fi

if [ ! -f "$data_dir/coverage.txt" ]; then
    missing_files+=("coverage.txt")
fi

if [ ! -f "$data_dir/ci.txt" ]; then
    missing_files+=("ci.txt")
fi

if [ ! -f "$data_dir/leftshift.txt" ]; then
    missing_files+=("leftshift.txt")
fi

if [ ! -f "$data_dir/ss.txt" ]; then
    missing_files+=("ss.txt")
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
python3 quality_report_generator.py \
  --week "$WEEK" \
  --component "$COMPONENT" \
  --git-repo-path /Users/rchowdhuri/SDB \
  --report-type comprehensive \
  --skip-confirmation

if [ $? -eq 0 ]; then
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
else
    echo ""
    echo "❌ Report generation failed!"
    echo "📋 Check the error messages above for details"
    echo "💡 Common issues:"
    echo "   - Missing or invalid .env file with LLM Gateway credentials"
    echo "   - Network connectivity issues"
    echo "   - Invalid data in source files"
    exit 1
fi

echo "==============================================="
echo "🎉 SDB Quality Report Generation Complete!"

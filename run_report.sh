#!/bin/bash

# SDB Quality Report Generator
# This script generates a comprehensive quality report for the SDB Engine
#
# DATA SOURCE URLs - ALL CONFIRMED:
# - PRB Report:    https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=report&wave__assetId=00OEE000001TXjB2AW
# - Fleet Bugs:    https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=report&wave__assetId=00OEE0000014M4b2AE
# - CI Issues:     https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=report&wave__assetId=00OEE000002WjvJ2AS
# - LeftShift:     https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=report&wave__assetId=00OEE000002WjvJ2AS
# - ABS Issues:    https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=report&wave__assetId=00OEE000002WjvJ2AS
# - Security:      https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=lightningdashboard&wave__assetId=01ZEE000001BaVp2AK
# - SonarQube:     https://sonarqube.sfcq.buildndeliver-s.aws-esvc1-useast2.aws.sfdc.cl/component_measures?id=sayonara.sayonaradb.sdb&metric=uncovered_lines&view=list

echo "🚀 Starting SDB Quality Report Generation..."
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

if [ ! -f "risks.txt" ]; then
    missing_files+=("risks.txt")
fi

if [ ! -f "prb.txt" ]; then
    missing_files+=("prb.txt")
fi

if [ ! -f "bugs.txt" ]; then
    missing_files+=("bugs.txt")
fi

if [ ! -f "deployment.csv" ]; then
    missing_files+=("deployment.csv")
fi

if [ ! -f "coverage.txt" ]; then
    missing_files+=("coverage.txt")
fi

if [ ! -f "ci.txt" ]; then
    missing_files+=("ci.txt")
fi

if [ ! -f "leftshift.txt" ]; then
    missing_files+=("leftshift.txt")
fi

if [ ! -f "security.txt" ]; then
    missing_files+=("security.txt")
fi

# Check if git repository exists
if [ ! -d "/Users/rchowdhuri/SDB/.git" ]; then
    missing_files+=("SDB git repository at /Users/rchowdhuri/SDB")
fi

if [ ${#missing_files[@]} -ne 0 ]; then
    echo "❌ Missing required data files:"
    for file in "${missing_files[@]}"; do
        echo "   - $file"
    done
    echo ""
    echo "📋 Please follow the data preparation instructions in the generated report."
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

# Clean previous reports
echo "🗑️  Cleaning previous reports..."
rm -f reports/*.md reports/*.json

# Generate the quality report
echo "📊 Generating comprehensive quality report..."
python3 quality_report_generator.py \
  --risk-file risks.txt \
  --prb-file prb.txt \
  --bugs-file bugs.txt \
  --deployment-csv deployments.csv \
  --stagger-deployment-csv deployment.csv \
  --coverage-txt coverage.txt \
  --ci-file ci.txt \
  --leftshift-file leftshift.txt \
  --abs-file abs.txt \
  --security-file security.txt \
  --git-repo-path /Users/rchowdhuri/SDB \
  --report-type comprehensive

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Quality report generated successfully!"
    echo "📁 Reports available in: ./reports/"
    echo ""
    echo "🌐 To view in dashboard, run: ./run_dashboard.sh"
    echo ""
    
    # Show the latest report file
    latest_report=$(ls -t reports/*.md 2>/dev/null | head -1)
    if [ -n "$latest_report" ]; then
        echo "📄 Latest report: $latest_report"
        echo "📏 Report size: $(wc -l < "$latest_report") lines"
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

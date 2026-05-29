# Core Optimizer and SFSQL Tab - Configuration Complete ✅

## Status: FULLY CONFIGURED

All Core Optimizer/SFSQL specific GUS reports have been configured! The tab is now ready to use.

---

## ✅ Configured Reports (6 of 7)

### 1. P0/P1 Prod Investigations ✅
- **Report ID**: `00OEE0000038GfN2AU`
- **GUS URL**: https://gus.lightning.force.com/lightning/r/Report/00OEE0000038GfN2AU/view
- **Usage**: Production Metrics - shows as "P0/P1 Prod Investigations" instead of "P0/P1 Prod Bugs"

### 2. CI Issues ✅
- **Report ID**: `00OEE0000038NnJ2AU`
- **GUS URL**: https://gus.lightning.force.com/lightning/r/Report/00OEE0000038NnJ2AU/view
- **Usage**: Development Metrics

### 3. Left Shift Issues ✅
- **Report ID**: `00OEE0000038PHF2A2`
- **GUS URL**: https://gus.lightning.force.com/lightning/r/Report/00OEE0000038PHF2A2/view
- **Usage**: Development Metrics

### 4. Security Issues ✅
- **Report ID**: `00OEE0000038PM52AM`
- **GUS URL**: https://gus.lightning.force.com/lightning/r/Report/00OEE0000038PM52AM/view
- **Usage**: Development Metrics

### 5. All-time Bug Backlog ✅
- **Report ID**: `00OEE0000038PIr2AM`
- **GUS URL**: https://gus.lightning.force.com/lightning/r/Report/00OEE0000038PIr2AM/view
- **Usage**: Development Metrics

### 6. PRB Backlog ✅
- **Report ID**: `00OEE0000038PKT2A2`
- **GUS URL**: https://gus.lightning.force.com/lightning/r/Report/00OEE0000038PKT2A2/view
- **Usage**: Development Metrics

---

## ⚠️ Using Engine Default (1 of 7)

### 7. ABS Bugs ⚠️
- **Report ID**: `00OEE000002bDht2AE` (Engine default)
- **Status**: No Core-specific report available yet
- **Usage**: Development Metrics
- **Note**: Will use Engine report until Core-specific ABS report is created

---

## 📊 Complete Report Mapping

### quality_report_generator.py
```python
_CORE_SF: Dict[str, str] = {
    'bugs': '00OEE0000038GfN2AU',          # P0/P1 Prod Investigations
    'ci': '00OEE0000038NnJ2AU',            # CI Issues
    'leftshift': '00OEE0000038PHF2A2',     # Left Shift Issues
    'abs': '00OEE000002bDht2AE',           # ABS (Engine default)
    'security': '00OEE0000038PM52AM',      # Security Issues
    'alltime_backlog': '00OEE0000038PIr2AM',  # All-time Bug Backlog
    'prb_backlog': '00OEE0000038PKT2A2',   # PRB Backlog
}
```

### streamlit_app.py
All 7 dictionaries updated with 'Core App Efficiency' entries pointing to correct report IDs.

---

## 🚀 How to Generate Reports

### Using Salesforce Reports API (Recommended)

```bash
cd /Users/rchowdhuri/QC

# Generate report for current week
./run_report.sh cw21 "Core App Efficiency" --use-salesforce-reports
```

**Required Files (Minimal):**
```
weeks/cw21/Core App Efficiency/
├── risks.txt                 ← Manual: Feature risk assessment
├── coverage.txt              ← SonarQube data
└── avail.txt                 ← System availability (optional)

weeks/cw21/Shared/
└── deployment.csv            ← SuperSet: Deployment data
```

**Automatically Fetched:**
- ✅ P0/P1 Prod Investigations (`00OEE0000038GfN2AU`)
- ✅ CI Issues (`00OEE0000038NnJ2AU`)
- ✅ Left Shift Issues (`00OEE0000038PHF2A2`)
- ✅ Security Issues (`00OEE0000038PM52AM`)
- ✅ All-time Bug Backlog (`00OEE0000038PIr2AM`)
- ✅ PRB Backlog (`00OEE0000038PKT2A2`)
- ⚠️ ABS Bugs (Engine report: `00OEE000002bDht2AE`)

---

## 📁 Directory Setup

### Quick Setup for CW21:

```bash
cd /Users/rchowdhuri/QC

# Create directories
mkdir -p "weeks/cw21/Core App Efficiency"
mkdir -p "weeks/cw21/Shared"

# Copy and update risk assessment (if exists from previous week)
# cp "weeks/cw20/Core App Efficiency/risks.txt" "weeks/cw21/Core App Efficiency/risks.txt"

# Or create new risks.txt
cat > "weeks/cw21/Core App Efficiency/risks.txt" << 'EOF'
# Risk and Feature Tracking
# Format: Feature, Status, Priority, Description, Updated

Feature: Core Optimizer Performance
Status: Green
Priority: High
Description: Core optimizer running stably in production
Updated: 2026-05-21

Feature: SFSQL Query Engine
Status: Yellow
Priority: Medium
Description: Minor performance issues under heavy load
Updated: 2026-05-21
EOF

# Add system availability (optional)
echo "99.99" > "weeks/cw21/Core App Efficiency/avail.txt"

# TODO: Get coverage.txt from SonarQube
# TODO: Get deployment.csv from SuperSet and save to weeks/cw21/Shared/

# Generate report
./run_report.sh cw21 "Core App Efficiency" --use-salesforce-reports

# View dashboard
./run_dashboard.sh
```

---

## 📊 What You'll See in the Dashboard

### Tab: "⚡ Core Optimizer and SFSQL"

**Production Metrics (Fleet-wide)**
- 🚨 Sev 0/1 PRBs (from Engine)
- 🚀 Prod Deployment (from Engine)
- ⚡ System Availability (from Engine)

**Production Metrics (Core-level)**
- 🚀 Feature Rollout Risk
- 🐛 P0/P1 Prod Investigations ← Custom label!

**Development Metrics**
- 🔧 CI Issues
- 🔒 Security Bugs
- 📊 Left Shift Issues
- 🧪 ABS Bugs (Engine default)
- 📈 Code Coverage
- 💻 Code Changes
- 📋 All-time Bug Backlog
- 🚨 Backlog from PRB

**Detailed Sections**
- 🚨 Problem Reports Analysis
- 🐛 Prod Investigations Analysis (with charts)
- 📊 Code Coverage Analysis
- 🔧 CI Issues Analysis (with team breakdown)
- 🔒 Security Analysis

---

## 🎨 Special Features

### Custom Labeling
The dashboard displays:
- **Core App Efficiency tab**: "P0/P1 Prod Investigations"
- **Other tabs**: "P0/P1 Prod Bugs"

This terminology distinction is automatically handled by the code.

---

## 🔄 Git Repository

**Default Repository**: `/Users/rchowdhuri/SDB`

The report script will:
1. Update the SDB repository
2. Calculate code change metrics for Core Optimizer/SFSQL
3. Track commits and lines changed

**To override**:
```bash
export QC_GIT_REPO_CORE=/path/to/core-repo
```

---

## 📝 Data Sources Reference

### Manual Input Files
1. **risks.txt**: Feature risk assessment (manual entry)
2. **coverage.txt**: From [SonarQube Dashboard](https://sonarqube.sfcq.buildndeliver-s.aws-esvc1-useast2.aws.sfdc.cl)
3. **avail.txt**: System availability percentage (optional)
4. **deployment.csv**: From SuperSet Dashboard (in Shared folder)

### Automated GUS Reports (via API)
1. **P0/P1 Prod Investigations**: `00OEE0000038GfN2AU`
2. **CI Issues**: `00OEE0000038NnJ2AU`
3. **Left Shift Issues**: `00OEE0000038PHF2A2`
4. **Security Issues**: `00OEE0000038PM52AM`
5. **All-time Bug Backlog**: `00OEE0000038PIr2AM`
6. **PRB Backlog**: `00OEE0000038PKT2A2`
7. **ABS Bugs**: `00OEE000002bDht2AE` (Engine default)

---

## ✅ Verification Checklist

Before generating your first report, verify:

- [ ] Directory structure created: `weeks/cw21/Core App Efficiency/`
- [ ] Shared directory exists: `weeks/cw21/Shared/`
- [ ] `risks.txt` created with feature status
- [ ] `coverage.txt` obtained from SonarQube
- [ ] `deployment.csv` obtained from SuperSet
- [ ] (Optional) `avail.txt` created
- [ ] Git repository exists at `/Users/rchowdhuri/SDB`
- [ ] Salesforce API credentials configured (for --use-salesforce-reports)

---

## 🎯 Summary

### Configuration Status: ✅ COMPLETE

**Total Reports**: 7
- **Core-Specific**: 6 reports ✅
- **Engine Default**: 1 report (ABS) ⚠️

**Tab Functionality**: 100% ready
- All links point to correct GUS reports
- Custom labeling implemented
- Report generation fully supported
- Dashboard rendering configured

### Ready to Use!

The Core Optimizer and SFSQL tab is now fully configured and ready to generate reports. Simply prepare your weekly data files and run:

```bash
./run_report.sh cw21 "Core App Efficiency" --use-salesforce-reports
```

---

## 📞 Next Steps

1. **Generate your first report** for CW21
2. **Review the dashboard** to ensure data looks correct
3. **Set up weekly workflow** to regularly update metrics
4. **(Future)** Update ABS report ID when Core-specific report becomes available

---

## 🎉 Completion Date: May 24, 2026

All configuration work for the Core Optimizer and SFSQL tab is complete!

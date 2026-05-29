# Core Optimizer and SFSQL Tab Configuration

## Status: Development Metrics Configuration ✅

The Core Optimizer and SFSQL tab has been configured with initial GUS report IDs. Currently using Development Metrics only.

---

## ✅ Completed Configuration

### 1. P0/P1 Prod Investigations - **CONFIGURED**
- **Report ID**: `00OEE0000038GfN2AU`
- **GUS URL**: https://gus.lightning.force.com/lightning/r/Report/00OEE0000038GfN2AU/view?queryScope=userFolders
- **Status**: ✅ Fully configured and ready to use
- **Label**: Shows as "P0/P1 Prod Investigations" instead of "P0/P1 Prod Bugs" in the dashboard
- **Notes**: Used in Production Metrics section

### 2. CI Issues Report - **CONFIGURED**
- **Report ID**: `00OEE0000038NnJ2AU`
- **GUS URL**: https://gus.lightning.force.com/lightning/r/Report/00OEE0000038NnJ2AU/view?queryScope=userFolders
- **Status**: ✅ Fully configured and ready to use
- **Notes**: Used in Development Metrics section

### Files Updated:
1. **`quality_report_generator.py`**:
   - Added `_CORE_SF` dictionary with Core Optimizer/SFSQL specific report IDs
   - CI report ID set to: `00OEE0000038NnJ2AU`

2. **`streamlit_app.py`**:
   - Added 'Core App Efficiency' to all GUS report ID mappings
   - CI Issues link in dashboard will now point to correct report

---

## 📋 TODO: Additional Report IDs Needed

The following reports are currently using Engine defaults (marked with TODO comments in code). 
Update these when Core Optimizer/SFSQL specific reports are created:

### Development Metrics Reports:

1. **Left Shift Issues**
   - Current: `00OEE000002Wjld2AC` (Engine default)
   - TODO: Create/identify Core Optimizer/SFSQL specific report

3. **ABS Bugs**
   - Current: `00OEE000002bDht2AE` (Engine default)
   - TODO: Create/identify Core Optimizer/SFSQL specific report

4. **Security Issues**
   - Current: `00OB0000002qWjvMAE` (Engine default)
   - TODO: Create/identify Core Optimizer/SFSQL specific report

5. **All-time Bug Backlog**
   - Current: `00OEE000002XRUv2AO` (Engine default)
   - TODO: Create/identify Core Optimizer/SFSQL specific report

6. **PRB Backlog**
   - Current: `00OEE000002ZnZN2A0` (Engine default)
   - TODO: Create/identify Core Optimizer/SFSQL specific report

---

## 🚀 Next Steps to Generate Reports

### Step 1: Prepare Data Files in `/weeks/cwXX/` directory

Create a directory for the target week (e.g., `weeks/cw21/`) with these files:

1. **`risks.txt`** - Feature rollout risks (manual input)
2. **`prb.txt`** - Problem Reports data
3. **`bugs.txt`** - Production bugs data
4. **`deployment.csv`** - Deployment tracking data
5. **`coverage.txt`** - Code coverage metrics
6. **`ci.txt`** - CI issues (will use new report: `00OEE0000038NnJ2AU`)
7. **`leftshift.txt`** - Left shift issues
8. **`abs.txt`** - ABS bugs
9. **`security.txt`** - Security issues
10. **`avail.txt`** - System availability percentage

### Step 2: Run Report Generator

```bash
cd /Users/rchowdhuri/QC

# Generate report for Core App Efficiency component
./run_report.sh cw21 "Core App Efficiency" --use-salesforce-reports

# Or generate for a specific week in weeks/ directory
./run_report.sh cw21 "Core App Efficiency"
```

### Step 3: View Dashboard

```bash
./run_dashboard.sh
```

Then select the week from the sidebar and click on the "⚡ Core Optimizer and SFSQL" tab.

---

## 📂 Report Storage

Generated reports will be stored in:
```
/Users/rchowdhuri/QC/reports/Core App Efficiency/
```

File naming convention:
```
quality_data_archive_YYYYMMDD_HHMMSS.json
```

---

## 🔧 Configuration Files

### quality_report_generator.py
Lines 89-119: Report ID mappings
- `_CORE_SF` dictionary contains Core Optimizer/SFSQL report IDs

### streamlit_app.py
Lines 6981-7028: GUS report URL mappings
- All report ID dictionaries now include 'Core App Efficiency' key

---

## ⚙️ Git Repository Configuration

Core App Efficiency uses the same git repository as Engine:
- **Path**: `/Users/rchowdhuri/SDB`
- **Environment Variable**: `QC_GIT_REPO_CORE`

To override, set in `.env`:
```bash
QC_GIT_REPO_CORE=/path/to/core-optimizer-repo
```

---

## 📊 Development Metrics Displayed

The Core Optimizer/SFSQL tab shows these development metrics:

1. **Production KPI Row** (hybrid view with Engine data)
2. **Development Metrics Dashboard**:
   - P0/P1 Production Bugs
   - CI Issues (✅ configured)
   - Security Bugs
   - Left Shift Issues
   - ABS Bugs
   - All-time Bug Backlog
   - Backlog from PRB
3. **Code Changes** (commits, lines changed)
4. **Feature Rollout Risk**
5. **Weekly Trends**
6. **PRB Analysis**
7. **Bug Analysis with charts**
8. **Code Coverage Analysis**
9. **CI Issues detailed charts**
10. **Security Analysis**

---

## 🎯 Focus: Development Metrics Only

As noted, this tab focuses on **Development Metrics** specifically for Core Optimizer and SFSQL components.

Production metrics (PRBs, deployment data, availability) will continue to be sourced from Engine-level data.

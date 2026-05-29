# Code Coverage Report Configuration

## Core Optimizer/SFSQL Coverage Report

**GUS Report ID**: `00OEE0000038PNh2AM`  
**GUS URL**: https://gus.lightning.force.com/lightning/r/Report/00OEE0000038PNh2AM/view

---

## Current System Behavior

### Coverage Data Source: Manual Text Files

The quality report system currently loads code coverage from **manual text files** (`coverage.txt`), NOT from Salesforce Reports API.

**Expected File**: `weeks/cwXX/Core App Efficiency/coverage.txt`

**Format** (from SonarQube):
```
On new code

Coverage
76.8%

Lines to Cover
23,050

Uncovered Lines
1,884

Line Coverage
91.8%

Conditions to Cover
21,397

Uncovered Conditions
8,424

Condition Coverage
60.6%

Overall

Coverage
68.3%

Lines to Cover
578,072

Uncovered Lines
106,963

Line Coverage
81.5%

Conditions to Cover
508,389

Uncovered Conditions
237,236

Condition Coverage
53.3%
```

---

## How to Use the Coverage Report

### Option 1: Manual Export from GUS Report (Current Workflow)

1. **Open GUS Report**: https://gus.lightning.force.com/lightning/r/Report/00OEE0000038PNh2AM/view
2. **Export/Copy Data**: Use "Export" or "Copy to Clipboard"
3. **Transform to SonarQube Format**: Convert to the text format shown above
4. **Save**: Place in `weeks/cw21/Core App Efficiency/coverage.txt`
5. **Generate Report**: Run `./run_report.sh cw21 "Core App Efficiency" --use-salesforce-reports`

### Option 2: Continue Using SonarQube (Existing Workflow)

If you have SonarQube access for Core Optimizer/SFSQL:

1. **Open SonarQube Dashboard**: https://sonarqube.sfcq.buildndeliver-s.aws-esvc1-useast2.aws.sfdc.cl
2. **Navigate to Core Optimizer/SFSQL Project**
3. **Copy Coverage Metrics**: From "On new code" through "Overall" section
4. **Save**: Place in `weeks/cw21/Core App Efficiency/coverage.txt`
5. **Generate Report**: Run `./run_report.sh cw21 "Core App Efficiency" --use-salesforce-reports`

### Option 3: Skip Coverage (Optional)

Coverage data is **optional**. If not provided:
- Coverage charts will show "No data available"
- Other metrics will still work normally

---

## ⚠️ Important Notes

### 1. No Automatic GUS Coverage Fetching

Unlike other metrics (bugs, CI issues, security, etc.), **coverage is NOT automatically fetched** from GUS via the Salesforce Reports API, even with `--use-salesforce-reports` flag.

**Why?**: The report generator expects a specific SonarQube text format that may not match GUS report output.

### 2. Coverage Report Mapping

The `_CORE_SF` dictionary in `quality_report_generator.py` does NOT include a `'coverage'` key because coverage is loaded from files, not via API.

### 3. Per-Component Coverage Files

Each component needs its own coverage file:
- **Engine**: `weeks/cwXX/Engine/coverage.txt`
- **Store**: `weeks/cwXX/Store/coverage.txt`
- **SDD**: `weeks/cwXX/SDD/coverage.txt`
- **Core App Efficiency**: `weeks/cwXX/Core App Efficiency/coverage.txt`

---

## 📋 Reference: GUS Coverage Report

**Report ID**: `00OEE0000038PNh2AM`

This report is documented here for reference. To use it:
- Export data from GUS
- Convert to SonarQube text format
- Save as `coverage.txt`

**Alternative**: If the GUS report provides the data in a different format (e.g., CSV), the report generator code could be extended to parse it. This would require code changes to `quality_report_generator.py`.

---

## 🔮 Future Enhancement Idea

To automatically fetch coverage from GUS report `00OEE0000038PNh2AM`:

1. **Add to `_CORE_SF` dictionary**:
   ```python
   'coverage': '00OEE0000038PNh2AM',
   ```

2. **Implement GUS coverage parser**:
   - Fetch report data via Salesforce API
   - Parse GUS report format
   - Convert to `NewCodeCoverage` objects
   - Store in `self.data['new_code_coverage']`

3. **Update report generation logic**:
   - Check if `--use-salesforce-reports` is enabled
   - If yes, fetch coverage from GUS instead of file
   - If no, fall back to `coverage.txt` file

**Estimated Effort**: 2-3 hours of development + testing

---

## ✅ Current Status

**Coverage Configuration**: ⚠️ Manual File Required

- GUS Report documented: `00OEE0000038PNh2AM` ✅
- System configured: Expects `coverage.txt` files ⚠️
- Automatic fetching: NOT implemented ❌

**Workaround**: Manually export from GUS report and save as `coverage.txt`

---

## 📝 Quick Reference

### For Core Optimizer/SFSQL Coverage:

**GUS Report**: https://gus.lightning.force.com/lightning/r/Report/00OEE0000038PNh2AM/view  
**File Location**: `weeks/cw21/Core App Efficiency/coverage.txt`  
**Format**: SonarQube text format (see above)  
**Required?**: Optional (charts show "No data" if missing)

### For Engine Coverage:

**SonarQube**: https://sonarqube.sfcq.buildndeliver-s.aws-esvc1-useast2.aws.sfdc.cl/component_measures?id=sayonara.sayonaradb.sdb  
**File Location**: `weeks/cw21/Engine/coverage.txt`  
**Format**: SonarQube text format  
**Required?**: Optional

---

## Summary

The GUS coverage report (`00OEE0000038PNh2AM`) is now **documented** for Core Optimizer/SFSQL, but you'll need to **manually export and format the data** as `coverage.txt` since automatic GUS coverage fetching is not currently implemented.

All other metrics (bugs, CI, security, etc.) are fully automated via Salesforce Reports API. ✅

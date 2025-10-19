# Data Preparation Instructions

**⚠️ IMPORTANT**: The following data files must be prepared before running the quality report generator:

## Required Data Files

### 1. Risk Assessment Data (`risks.txt`)
- **Source**: Manual input based on current feature risk assessment
- **Action**: Populate by hand with known feature risks and their current status

### 2. Problem Reports (`prb.txt`)
- **Source**: [Salesforce PRB Report](https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=report&wave__assetId=00OEE000001TXjB2AW)
- **Action**: Run the report → Use "Copy to clipboard" feature → Create `prb.txt` file

### 3. Production Fleet Bugs (`bugs.txt`)
- **Source**: [Salesforce Fleet Bugs Report](https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=report&wave__assetId=00OEE0000014M4b2AE)
- **Action**: Run the report → Use "Copy to clipboard" feature → Create `bugs.txt` file

### 4. Deployment Data (`deployment.csv`)
- **Source**: SuperSet Dashboard → Save Queries → "SDB Versions - RC"
- **Action**: Copy query → Run SQL → Download as CSV → Save as `deployment.csv`

### 5. Code Coverage Data (`coverage.txt`)
- **Source**: [SonarQube Dashboard](https://sonarqube.sfcq.buildndeliver-s.aws-esvc1-useast2.aws.sfdc.cl/component_measures?id=sayonara.sayonaradb.sdb&metric=uncovered_lines&view=list)
- **Source**: [SonarQube Dashboard for Store](https://sonarqube.sfcq.buildndeliver-s.aws-esvc1-useast2.aws.sfdc.cl/component_measures?id=sfstorage.bookkeeper&metric=line_coverage)
- **Action**: Copy coverage section from "On new code" through end of "Overall" coverage → Create `coverage.txt`

### 6. CI Issues (`ci.txt`)
- **Source**: [Salesforce CI Report](https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=report&wave__assetId=00OEE000002WjvJ2AS)
- **Action**: Run the report → Use "Copy to clipboard" feature → Create `ci.txt` file

### 7. LeftShift Issues (`leftshift.txt`)
- **Source**: [Salesforce LeftShift Report](https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=report&wave__assetId=00OEE000002WjvJ2AS) ✅ **CONFIRMED**
- **Action**: Run the report → Use "Copy to clipboard" feature → Create `leftshift.txt` file

### 8. ABS Issues (`abs.txt`)
- **Source**: [Salesforce ABS Report](https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=report&wave__assetId=00OEE000002WjvJ2AS) ✅ **CONFIRMED**
- **Action**: Run the report → Use "Copy to clipboard" feature → Create `abs.txt` file

### 9. Security Issues (`security.txt`)
- **Source**: [Salesforce Security Dashboard](https://gus.lightning.force.com/lightning/page/analytics?wave__assetType=lightningdashboard&wave__assetId=01ZEE000001BaVp2AK) ✅ **CONFIRMED**
- **Action**: Run the dashboard → Use "Copy to clipboard" feature → Create `security.txt` file

### 10. Git Repository Refresh (`/Users/rchowdhuri/SDB`)
- **Actions Required**:
  ```bash
  cd /Users/rchowdhuri/SDB
  git fetch
  git submodule update --init --recursive
  git rebase
  ```

## Automated Script Usage

Use the provided `run_report.sh` script which automates data validation and git repository updates:

```bash
./run_report.sh
```

The script will:
1. ✅ Validate all required data files exist
2. 🔄 Update the SDB git repository 
3. 📊 Generate comprehensive quality report
4. 🌐 Prepare for dashboard viewing

## Dashboard Viewing

After report generation, view the results in the interactive dashboard:

```bash
./run_dashboard.sh
```

## Notes

- **All URLs Verified**: ✅ All Salesforce report and dashboard URLs confirmed
- **File Formats**: The system auto-detects Salesforce export formats vs structured text
- **Fleet Context**: Reports include 795-cell fleet operational context
- **Git Analysis**: Includes code churn and development velocity metrics
- **Dashboard vs Report**: Security uses Lightning Dashboard format while others use standard reports

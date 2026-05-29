# Changes Summary: Core Optimizer/SFSQL Tab Configuration

## Date: 2026-05-23

---

## ✅ Completed Changes

### 1. Production Metrics - P0/P1 Prod Investigations

**Report Configured:**
- Report ID: `00OEE0000038GfN2AU`
- GUS URL: https://gus.lightning.force.com/lightning/r/Report/00OEE0000038GfN2AU/view?queryScope=userFolders

**Display Updates:**
- Metric card label changed from "🐛 P0/P1 Prod Bugs" to "🐛 P0/P1 Prod Investigations" (only for Core App Efficiency tab)
- Section heading changed from "🐛 Production Bug Analysis" to "🐛 Prod Investigations Analysis"
- Link text changed from "P0/P1 production bugs" to "P0/P1 prod investigations"

**Files Modified:**
- `quality_report_generator.py`: Line 90 - Updated `_CORE_SF['bugs']`
- `streamlit_app.py`: 
  - Line 6984: Updated `P0P1_PROD_BUGS_REPORT_ID_BY_COMPONENT`
  - Line 1110: Made metric label dynamic in `render_production_kpi_row_hybrid()`
  - Line 1462: Made metric label dynamic in `create_two_line_metric_cards()`
  - Lines 7256-7261: Made section heading and link text dynamic in `render_component_development_metrics()`

---

### 2. Development Metrics - CI Issues

**Report Configured:**
- Report ID: `00OEE0000038NnJ2AU`
- GUS URL: https://gus.lightning.force.com/lightning/r/Report/00OEE0000038NnJ2AU/view?queryScope=userFolders

**Display:**
- Label remains "🔧 CI Issues" (consistent with other tabs)
- Links to Core Optimizer/SFSQL specific CI Issues report

**Files Modified:**
- `quality_report_generator.py`: Line 91 - Updated `_CORE_SF['ci']`
- `streamlit_app.py`: Line 6991 - Updated `P0P1_CI_ISSUES_REPORT_ID_BY_COMPONENT`

---

## 📂 New Files Created

1. **`CORE_OPTIMIZER_SFSQL_SETUP.md`**
   - Complete setup documentation
   - Lists all configured and pending reports
   - Includes instructions for generating reports

2. **`CHANGES_SUMMARY.md`** (this file)
   - Summary of all changes made
   - Before/after comparison

---

## 🔄 Configuration Structure

### quality_report_generator.py

Created new `_CORE_SF` dictionary for Core App Efficiency:

```python
_CORE_SF: Dict[str, str] = {
    'bugs': '00OEE0000038GfN2AU',  # P0/P1 Prod Investigations ✅
    'ci': '00OEE0000038NnJ2AU',  # CI Issues ✅
    'leftshift': '00OEE000002Wjld2AC',  # TODO
    'abs': '00OEE000002bDht2AE',  # TODO
    'security': '00OB0000002qWjvMAE',  # TODO
    'alltime_backlog': '00OEE000002XRUv2AO',  # TODO
    'prb_backlog': '00OEE000002ZnZN2A0',  # TODO
}
```

### streamlit_app.py

Added 'Core App Efficiency' entries to all report mapping dictionaries:

1. `P0P1_PROD_BUGS_REPORT_ID_BY_COMPONENT` ✅
2. `P0P1_CI_ISSUES_REPORT_ID_BY_COMPONENT` ✅
3. `P0P1_SECURITY_BUGS_REPORT_ID_BY_COMPONENT` (TODO)
4. `P0P1_LEFT_SHIFT_REPORT_ID_BY_COMPONENT` (TODO)
5. `P0P1_ABS_BUGS_REPORT_ID_BY_COMPONENT` (TODO)
6. `ALL_TIME_BUG_BACKLOG_REPORT_ID_BY_COMPONENT` (TODO)
7. `BACKLOG_FROM_PRB_REPORT_ID_BY_COMPONENT` (TODO)

---

## 🎯 What This Enables

### When viewing the "⚡ Core Optimizer and SFSQL" tab:

**Production Metrics Section:**
- Shows "P0/P1 Prod Investigations" instead of "P0/P1 Prod Bugs"
- Links to: https://gus.lightning.force.com/lightning/r/Report/00OEE0000038GfN2AU/view

**Development Metrics Section:**
- CI Issues section links to: https://gus.lightning.force.com/lightning/r/Report/00OEE0000038NnJ2AU/view
- Section heading: "🐛 Prod Investigations Analysis"

### When generating reports:

```bash
./run_report.sh cw21 "Core App Efficiency" --use-salesforce-reports
```

The report generator will:
- Pull P0/P1 Prod Investigations from report `00OEE0000038GfN2AU`
- Pull CI Issues from report `00OEE0000038NnJ2AU`
- Use Engine defaults for other metrics (until specific reports are configured)

---

## 📝 Before vs After

### Before:
```
Tab 4: "⚡ Core Optimizer and SFSQL"
├── Production Metrics
│   └── 🐛 P0/P1 Prod Bugs → Engine report (00OEE0000030kAn2AI)
└── Development Metrics
    └── 🔧 CI Issues → Engine report (00OEE000002WjvJ2AS)
```

### After:
```
Tab 4: "⚡ Core Optimizer and SFSQL"
├── Production Metrics
│   └── 🐛 P0/P1 Prod Investigations → Core report (00OEE0000038GfN2AU) ✅
└── Development Metrics
    └── 🔧 CI Issues → Core report (00OEE0000038NnJ2AU) ✅
```

---

## 🚀 Next Steps

To fully populate the Core Optimizer/SFSQL tab, you'll need to:

1. **Generate report data** by running:
   ```bash
   ./run_report.sh <week> "Core App Efficiency" --use-salesforce-reports
   ```

2. **Provide the remaining GUS report IDs** for:
   - Left Shift Issues
   - ABS Bugs
   - Security Issues
   - All-time Bug Backlog
   - PRB Backlog

3. **Prepare weekly data files** in `/weeks/cwXX/` directory (see CORE_OPTIMIZER_SFSQL_SETUP.md)

---

## ✨ Key Features

### Dynamic Labeling
The dashboard now intelligently shows different labels based on the selected tab:
- **Core App Efficiency tab**: "P0/P1 Prod Investigations"
- **All other tabs**: "P0/P1 Prod Bugs"

This is implemented via conditional logic in three locations:
1. Production KPI metric card (`render_production_kpi_row_hybrid`)
2. Development metrics card (`create_two_line_metric_cards`)
3. Section heading and link (`render_component_development_metrics`)

### Backward Compatibility
All existing tabs (Engine, Store, SDD) continue to work exactly as before, with no changes to their behavior or displayed labels.

---

## 🔍 Testing Recommendations

1. **Verify tab switching**: Switch between tabs and confirm labels change appropriately
2. **Check GUS links**: Click metric cards and section links to verify correct reports open
3. **Generate test report**: Run report generator with Core App Efficiency component
4. **Validate dashboard rendering**: View generated report in dashboard

---

## 📞 Support

For questions or issues, refer to:
- `CORE_OPTIMIZER_SFSQL_SETUP.md` - Complete setup guide
- `INSTRUCTIONS.md` - Data preparation instructions
- GUS reports - Verify report IDs are accessible

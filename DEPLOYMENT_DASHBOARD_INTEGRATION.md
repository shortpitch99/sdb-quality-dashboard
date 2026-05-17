# Deployment Dashboard Integration

## Overview
Integrated a release plan vs actual dashboard visualization into the main QC dashboard, based on the standalone `release_plan_vs_actual_dashboard.py` code.

## Files Created/Modified

### 1. `/Users/rchowdhuri/QC/release_plan_vs_actual_dashboard.py`
- **Status**: New standalone file created
- **Purpose**: Independent Streamlit app for testing release journey visualizations
- **Key Features**:
  - Upload actuals CSV (deployment-journey.csv format)
  - Paste plan data (SDB Releases Deployment Schedule format)
  - Release journey heatmap by version/stage/week
  - Plan vs actual adherence charts
  - Weekly overview and data tables

### 2. `/Users/rchowdhuri/QC/streamlit_app.py`
- **Status**: Modified (integrated heatmap visualization)
- **Changes**:
  
  a) **Fixed timestamp arithmetic errors** (lines 3434-3435, 3599, 3608):
     - Removed redundant `pd.to_datetime()` calls on already-datetime columns
     - Prevents "Addition/subtraction of integers and integer-arrays with Timestamp" errors
  
  b) **Added new method `create_release_journey_heatmap`** (after line 3079):
     - Creates heatmap showing a selected release's progression through stages over time
     - Uses plotly imshow for heatmap visualization
     - Stages on Y-axis (SB0, SB1, R0, R1, R2a, R2b)
     - Weeks on X-axis
     - Color intensity shows % completion
  
  c) **Integrated heatmap into deployment analysis section** (line ~6154):
     - Added between "Deployment Journey - Cumulative Completion" and "Release Promotion Plan vs Actuals"
     - New heading: "#### Release Journey Heatmap"

## Data Format Requirements

### Actuals Data (deployment-journey.csv)
```csv
current_version,week_start,pct_of_SB0,pct_of_SB1,pct_of_R0,pct_of_R1,pct_of_R2a,pct_of_R2b
260.15,2026-02-23,11.1,2.0,0.0,95.5,83.5,44.8
262.11,2026-02-23,16.7,0.4,0.0,0.0,0.0,0.0
...
```

### Plan Data (SDB Releases Deployment Schedule*.csv)
```csv
,11/24/2025,12/1/2025,12/8/2025,...
Code Freeze,262.1,262.2,262.3,...
Leftshift,260.16,262.1,262.2,...
SB0,260.15,260.16,262.1,...
SB1/SB2.w1,260.14,260.15,260.16,...
R*.w1,260.13,260.14,260.15,...
...
```

## Key Visualizations

### 1. Release Journey Heatmap
- **Purpose**: Show individual release progression through deployment stages
- **Layout**: 
  - Y-axis: Deployment stages (SB0 → SB1 → R0 → R1 → R2a → R2b)
  - X-axis: Week start dates
  - Color: % completion (0-100%, blue gradient)
- **Interaction**: Dropdown selector to choose which release version to visualize

### 2. Timeline Chart (existing, improved)
- **Purpose**: Compare plan vs actual deployment timing
- **Features**:
  - Thin lines with hollow circles = planned deployment
  - Thick lines with solid/hollow circles = actual deployment
  - Solid circle = on-time (within 1 week of plan)
  - Hollow circle = delayed
  - Color-coded by stagger stage

### 3. Cumulative Completion (existing)
- **Purpose**: Multi-line chart showing all releases' cumulative progress
- **Features**: One line per release version showing % complete over 12 weeks

## Testing

### Standalone Dashboard
```bash
cd /Users/rchowdhuri/QC
streamlit run release_plan_vs_actual_dashboard.py
```
Then:
1. Upload `weeks/cw19/Shared/deployment-journey.csv`
2. Copy/paste content from `weeks/cw19/Shared/SDB Releases Deployment Schedule - 262 Visual.csv`

### Integrated Dashboard
```bash
cd /Users/rchowdhuri/QC
streamlit run streamlit_app.py
```
Navigate to: **Deployment Analysis** section

## Bug Fixes Applied

### Issue: Pandas Timestamp Arithmetic Error
**Error Message**: 
```
Addition/subtraction of integers and integer-arrays with Timestamp is no longer supported.
Instead of adding/subtracting n, use n * obj.freq
```

**Root Cause**: 
Calling `pd.to_datetime()` on already-datetime Series/columns, which in newer pandas versions can trigger deprecated integer arithmetic internally.

**Fixes Applied**:
1. Line 3434-3435: Removed `pd.to_datetime()` wrapper around `.min()` calls
2. Line 3599, 3608: Removed `pd.to_datetime()` wrapper in plan week filtering

**Before**:
```python
plan_start = pd.to_datetime(stage_plan["week_start"].min())
actual_start = pd.to_datetime(actual_weeks["week_start"].min())
```

**After**:
```python
plan_start = stage_plan["week_start"].min()
actual_start = actual_weeks["week_start"].min()
```

## Next Steps

1. **Test the integrated heatmap** in the main dashboard
2. **Verify timestamp errors are resolved** by refreshing the dashboard
3. **Optional enhancements**:
   - Add plan vs actual overlay on heatmap
   - Add drill-down from heatmap to detailed stage view
   - Export heatmap data to CSV
   - Add stage duration metrics to heatmap tooltips

## Reference
- PNG file with desired layout: `~/Downloads/ChatGPT Image May 14, 2026, 02_04_26 PM.png`
- Data location: `/Users/rchowdhuri/QC/weeks/cw19/Shared/`

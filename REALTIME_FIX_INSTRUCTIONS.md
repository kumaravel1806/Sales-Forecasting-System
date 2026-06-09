# 🔧 REAL-TIME DASHBOARD FIX - IMPLEMENTATION PLAN

## 🎯 Problem
The real-time dashboard is not loading data properly. It makes multiple separate API calls that fail.

## ✅ Solution
Use the SAME approach as admin_dashboard.html which WORKS:
- Single API endpoint: `/api/analytics/dashboard/realtime`
- One unified data load
- Update all sections from single response

## 📝 Changes Needed

### Replace ALL old loading functions with:

```javascript
// Single unified data load function
async function loadDashboardData() {
  const response = await fetch(API_BASE + '/api/analytics/dashboard/realtime');
  const result = await response.json();
  const { data } = result;
  const { kpi } = data;
  
  // Update all sections
  updateMetrics(kpi);
  updateCharts(data.sales_trend || []);
  updateFeedbackStream(data.recent_activity || []);
  updateTopProducts(data.top_products || []);
  updateStorePerformance(data.store_performance || []);
  updateRecentActivity(data.recent_activity || []);
}

// Individual update functions
function updateMetrics(kpi) { ... }
function updateCharts(salesTrend) { ... }
function updateFeedbackStream(activities) { ... }
function updateTopProducts(products) { ... }
function updateStorePerformance(stores) { ... }
function updateRecentActivity(activities) { ... }
```

### Remove OLD functions:
- loadMetrics()
- loadCharts()
- loadFeedbackStream()
- loadTopProducts()
- loadStorePerformance()
- loadRecentActivity()

These make separate API calls and are causing the issue!

## 🚀 Implementation
Will create new version of realtime_dashboard.html with working data loading logic.

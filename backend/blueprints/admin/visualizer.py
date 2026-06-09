"""
Data Visualizer - Advanced Analytics Module
Handles CSV/Excel uploads, generates charts, and performs historical analysis
"""

import os
import sys
import pandas as pd
import numpy as np
import json
import matplotlib
matplotlib.use('Agg')  # Set non-interactive backend
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from collections import Counter
from pathlib import Path

# Add parent directory to path to import historical_analysis
sys.path.append(str(Path(__file__).parent.parent.parent))
from historical_analysis import HistoricalSalesAnalyzer


def build_time_series(df, start_date=None, end_date=None, time_interval='D'):
    """
    Build a time series with support for date ranges and different time intervals.
    
    Args:
        df: Input DataFrame
        start_date: Start date in 'YYYY-MM-DD' format (optional)
        end_date: End date in 'YYYY-MM-DD' format (optional)
        time_interval: Time interval for aggregation ('D'=daily, 'W'=weekly, 'M'=monthly)
    """
    try:
        if df is None or df.empty:
            return None

        # --- Detect value (numeric) column ---
        value_candidates = [
            'sales', 'sale', 'sales_amount', 'amount', 'total_amount', 'value',
            'revenue', 'qty', 'quantity', 'units', 'price', 'net_amount', 'gross_amount',
            'total', 'sum', 'value', 'price', 'cost', 'revenue'
        ]
        
        value_col = None
        for col in df.columns:
            name = col.lower()
            if name in value_candidates:
                value_col = col
                break
                
        if value_col is None:
            num_cols = df.select_dtypes(include=[np.number]).columns
            if len(num_cols) > 0:
                value_col = num_cols[0]
            else:
                return None

        # --- Detect date column ---
        date_col = None
        date_candidates = [
            'date', 'order_date', 'sale_date', 'timestamp', 'time', 'datetime',
            'created_at', 'updated_at', 'transaction_date', 'purchase_date',
            'order_time', 'sale_time', 'transaction_time'
        ]
        
        # First try exact matches
        for col in df.columns:
            if col.lower() in date_candidates:
                date_col = col
                break
        
        # Then try partial matches
        if date_col is None:
            for col in df.columns:
                if any(term in col.lower() for term in ['date', 'time', 'day', 'created', 'updated']):
                    date_col = col
                    break
        
        # Finally, check datetime dtypes
        if date_col is None:
            for col in df.columns:
                if 'date' in str(df[col].dtype).lower() or 'time' in str(df[col].dtype).lower():
                    date_col = col
                    break
        
        if date_col is None:
            return None

        # Convert to datetime and filter by date range
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col, value_col])
        
        if start_date:
            start_date = pd.to_datetime(start_date)
            df = df[df[date_col] >= start_date]
        if end_date:
            end_date = pd.to_datetime(end_date)
            df = df[df[date_col] <= end_date]

        if df.empty:
            return None

        # Set date as index and sort
        df = df.set_index(date_col).sort_index()
        
        # Resample based on time_interval
        if time_interval == 'W':
            resampled = df[value_col].resample('W-Mon').sum()
            date_format = '%Y-%m-%d'
        elif time_interval == 'M':
            resampled = df[value_col].resample('M').sum()
            date_format = '%Y-%m'
        else:  # Default to daily
            resampled = df[value_col].resample('D').sum()
            date_format = '%Y-%m-%d'

        # Create output
        dates = resampled.index.strftime(date_format).tolist()
        values = resampled.fillna(0).astype(float).tolist()
        
        if not values:
            return None

        # Calculate additional statistics
        max_val = max(values) or 1.0
        min_val = min(values) if values else 0
        avg_val = sum(values) / len(values) if values else 0
        total = sum(values)
        
        # Calculate moving averages (7-day and 30-day)
        moving_avg_7 = resampled.rolling(window=min(7, len(resampled)), min_periods=1).mean().fillna(0).tolist()
        moving_avg_30 = resampled.rolling(window=min(30, len(resampled)), min_periods=1).mean().fillna(0).tolist()

        return {
            'date_column': date_col,
            'value_column': value_col,
            'time_interval': time_interval,
            'dates': dates,
            'values': values,
            'statistics': {
                'min': float(min_val),
                'max': float(max_val),
                'average': float(avg_val),
                'total': float(total),
                'count': len(values)
            },
            'moving_averages': {
                '7_period': moving_avg_7,
                '30_period': moving_avg_30
            },
            'start_date': dates[0] if dates else None,
            'end_date': dates[-1] if dates else None
        }

    except Exception as e:
        print(f"[ERROR] build_time_series: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
        return None


def preprocess_data(df):
    """Preprocess data like WEKA - handle missing values, outliers, normalization"""
    preprocessing_report = {}
    df_clean = df.copy()
    
    # 1. Handle Missing Values
    missing_before = df_clean.isnull().sum().sum()
    
    # For numeric columns: fill with median
    numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if df_clean[col].isnull().any():
            median_val = df_clean[col].median()
            df_clean[col].fillna(median_val, inplace=True)
            preprocessing_report[f'{col}_filled'] = f'Filled {df[col].isnull().sum()} missing values with median: {median_val:.2f}'
    
    # For categorical columns: fill with mode
    categorical_cols = df_clean.select_dtypes(include=['object']).columns
    for col in categorical_cols:
        if df_clean[col].isnull().any():
            mode_val = df_clean[col].mode()[0] if len(df_clean[col].mode()) > 0 else 'Unknown'
            df_clean[col].fillna(mode_val, inplace=True)
            preprocessing_report[f'{col}_filled'] = f'Filled {df[col].isnull().sum()} missing values with mode: {mode_val}'
    
    missing_after = df_clean.isnull().sum().sum()
    preprocessing_report['missing_values_handled'] = f'{missing_before} missing values cleaned → {missing_after} remaining'
    
    # 2. Remove Duplicate Rows
    duplicates_before = df_clean.duplicated().sum()
    if duplicates_before > 0:
        df_clean.drop_duplicates(inplace=True)
        preprocessing_report['duplicates_removed'] = f'{duplicates_before} duplicate rows removed'
    
    # 3. Handle Outliers (cap at 3 std dev)
    outliers_capped = 0
    for col in numeric_cols:
        mean = df_clean[col].mean()
        std = df_clean[col].std()
        lower_bound = mean - 3 * std
        upper_bound = mean + 3 * std
        
        outliers = ((df_clean[col] < lower_bound) | (df_clean[col] > upper_bound)).sum()
        if outliers > 0:
            df_clean[col] = df_clean[col].clip(lower=lower_bound, upper=upper_bound)
            outliers_capped += outliers
            preprocessing_report[f'{col}_outliers'] = f'{outliers} outliers capped to 3σ range'
    
    if outliers_capped > 0:
        preprocessing_report['total_outliers_capped'] = f'{outliers_capped} total outliers capped'
    
    return df_clean, preprocessing_report

def analyze_dataset(df):
    """Perform comprehensive dataset analysis"""
    analysis = {}
    
    # Basic info
    analysis['rows'] = len(df)
    analysis['columns'] = len(df.columns)
    analysis['column_names'] = list(df.columns)
    
    # Identify column types
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    
    analysis['numeric_columns'] = len(numeric_cols)
    analysis['categorical_columns'] = len(categorical_cols)
    analysis['numeric_column_names'] = numeric_cols
    analysis['categorical_column_names'] = categorical_cols
    
    # Missing values
    missing = df.isnull().sum()
    analysis['missing_values'] = {col: int(count) for col, count in missing.items() if count > 0}
    analysis['missing_percentage'] = (df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100
    
    # Duplicate rows
    analysis['duplicate_rows'] = int(df.duplicated().sum())
    
    # Data quality score
    if analysis['missing_percentage'] < 1 and analysis['duplicate_rows'] < 10:
        analysis['quality_score'] = 'Excellent'
    elif analysis['missing_percentage'] < 5 and analysis['duplicate_rows'] < 50:
        analysis['quality_score'] = 'Good'
    elif analysis['missing_percentage'] < 10:
        analysis['quality_score'] = 'Fair'
    else:
        analysis['quality_score'] = 'Poor'
    
    # Numeric statistics with RMSE and outliers
    numeric_stats = {}
    for col in numeric_cols:
        col_data = df[col].dropna()
        if len(col_data) > 0:
            mean_val = float(col_data.mean())
            std_val = float(col_data.std())
            
            # Calculate RMSE (Root Mean Square Error from mean)
            rmse = float(np.sqrt(np.mean((col_data - mean_val) ** 2)))
            
            # Detect outliers using IQR method
            Q1 = col_data.quantile(0.25)
            Q3 = col_data.quantile(0.75)
            IQR = Q3 - Q1
            outliers = ((col_data < (Q1 - 1.5 * IQR)) | (col_data > (Q3 + 1.5 * IQR))).sum()
            
            numeric_stats[col] = {
                'mean': mean_val,
                'median': float(col_data.median()),
                'std': std_val,
                'min': float(col_data.min()),
                'max': float(col_data.max()),
                'rmse': rmse,
                'outliers': int(outliers)
            }
    
    analysis['numeric_stats'] = numeric_stats
    
    # Categorical statistics
    categorical_stats = {}
    for col in categorical_cols[:5]:  # Limit to first 5 categorical columns
        value_counts = df[col].value_counts()
        categorical_stats[col] = {
            'unique_values': int(df[col].nunique()),
            'top_values': {str(k): int(v) for k, v in value_counts.head(10).items()}
        }
    
    analysis['categorical_stats'] = categorical_stats
    
    return analysis

def generate_charts(df, chart_types):
    """Generate chart configurations for Chart.js"""
    charts = []
    
    # Identify column types
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()

    # Try to robustly detect datetime columns (by dtype and by common name patterns)
    datetime_cols = []
    try:
        datetime_cols = df.select_dtypes(include=['datetime64[ns]', 'datetime64[ns, tz]', 'datetime64']).columns.tolist()
    except Exception:
        # Fallback for older pandas versions
        datetime_cols = []

    if not datetime_cols:
        # Heuristic: columns whose names look like dates/times
        candidate_cols = [
            c for c in df.columns
            if any(k in c.lower() for k in ['date', 'time', 'timestamp', 'created', 'updated'])
        ]
        for col in candidate_cols:
            if df[col].dtype == object:
                try:
                    parsed = pd.to_datetime(df[col], errors='coerce')
                    if parsed.notna().sum() > len(df) * 0.5:
                        df[col] = parsed
                        datetime_cols.append(col)
                except Exception:
                    continue
    
    print(f"[CHARTS] Numeric columns: {numeric_cols}")
    print(f"[CHARTS] Categorical columns: {categorical_cols}")
    print(f"[CHARTS] Datetime columns (inferred): {datetime_cols}")
    
    # Generate charts based on available data and requested types
    if 'line' in chart_types and len(numeric_cols) > 0:
        # Prefer history-style charts when a datetime column is available
        time_col = datetime_cols[0] if datetime_cols else None
        for col in numeric_cols[:3]:  # First 3 numeric columns
            series = df[[col]].copy()
            if time_col is not None and time_col in df.columns:
                try:
                    ts_df = df[[time_col, col]].dropna().copy()
                    # Sort by time and keep a reasonable window for display
                    ts_df = ts_df.sort_values(time_col).tail(200)
                    x_series = ts_df[time_col]
                    if hasattr(x_series, 'dt'):
                        labels = x_series.dt.strftime('%Y-%m-%d').astype(str).tolist()
                    else:
                        labels = [str(x) for x in x_series]
                    values = ts_df[col].astype(float).tolist()
                    x_axis_title = str(time_col)
                except Exception:
                    # Fallback to index-based labels if anything goes wrong
                    col_data = df[col].dropna().tolist()
                    labels = [f"Point {i+1}" for i in range(len(col_data))]
                    values = col_data
                    x_axis_title = 'Index'
            else:
                col_data = df[col].dropna().tolist()
                if len(col_data) == 0:
                    continue
                labels = [f"Point {i+1}" for i in range(len(col_data))]
                values = col_data
                x_axis_title = 'Index'

            if len(values) > 0:
                charts.append({
                    'type': 'line',
                    'title': f'{col} - Time Series Trend',
                    'description': f'History of {col} over {x_axis_title}',
                    'data': {
                        'labels': labels[:50],  # Limit to 50 points for display
                        'datasets': [{
                            'label': col,
                            'data': values[:50],
                            'borderColor': 'rgb(59, 130, 246)',
                            'backgroundColor': 'rgba(59, 130, 246, 0.1)',
                            'tension': 0.4,
                            'fill': True
                        }]
                    },
                    'options': {
                        'scales': {
                            'y': {'beginAtZero': False}
                        }
                    }
                })
    
    # 2. BAR CHARTS (Categories)
    if 'bar' in chart_types:
        # If we have categorical columns
        if len(categorical_cols) > 0:
            for cat_col in categorical_cols[:2]:  # First 2 categorical columns
                value_counts = df[cat_col].value_counts().head(10)
                
                charts.append({
                    'type': 'bar',
                    'title': f'{cat_col} - Category Distribution',
                    'description': f'Top categories in {cat_col}',
                    'data': {
                        'labels': [str(x) for x in value_counts.index.tolist()],
                        'datasets': [{
                            'label': 'Count',
                            'data': value_counts.values.tolist(),
                            'backgroundColor': 'rgba(34, 197, 94, 0.8)',
                            'borderColor': 'rgb(34, 197, 94)',
                            'borderWidth': 1
                        }]
                    }
                })
        
        # Numeric columns as bar chart (comparing means/sums)
        if len(numeric_cols) >= 2:
            means = {col: float(df[col].mean()) for col in numeric_cols[:5]}
            
            charts.append({
                'type': 'bar',
                'title': 'Numeric Columns - Mean Comparison',
                'description': 'Average values across numeric columns',
                'data': {
                    'labels': list(means.keys()),
                    'datasets': [{
                        'label': 'Mean Value',
                        'data': list(means.values()),
                        'backgroundColor': [
                            'rgba(255, 99, 132, 0.8)',
                            'rgba(54, 162, 235, 0.8)',
                            'rgba(255, 206, 86, 0.8)',
                            'rgba(75, 192, 192, 0.8)',
                            'rgba(153, 102, 255, 0.8)'
                        ]
                    }]
                }
            })
    
    # 3. PIE CHARTS (Distributions)
    if 'pie' in chart_types and len(categorical_cols) > 0:
        for cat_col in categorical_cols[:2]:  # First 2 categorical columns
            value_counts = df[cat_col].value_counts().head(8)
            
            charts.append({
                'type': 'pie',
                'title': f'{cat_col} - Distribution',
                'description': f'Proportional distribution of {cat_col}',
                'data': {
                    'labels': [str(x) for x in value_counts.index.tolist()],
                    'datasets': [{
                        'data': value_counts.values.tolist(),
                        'backgroundColor': [
                            'rgba(255, 99, 132, 0.8)',
                            'rgba(54, 162, 235, 0.8)',
                            'rgba(255, 206, 86, 0.8)',
                            'rgba(75, 192, 192, 0.8)',
                            'rgba(153, 102, 255, 0.8)',
                            'rgba(255, 159, 64, 0.8)',
                            'rgba(199, 199, 199, 0.8)',
                            'rgba(83, 102, 255, 0.8)'
                        ]
                    }]
                }
            })
    
    # 4. SCATTER PLOTS (Correlations)
    if 'scatter' in chart_types and len(numeric_cols) >= 2:
        # Take first two numeric columns for scatter
        col1, col2 = numeric_cols[0], numeric_cols[1]
        
        # Get paired data
        scatter_data = df[[col1, col2]].dropna()
        if len(scatter_data) > 0:
            charts.append({
                'type': 'scatter',
                'title': f'{col1} vs {col2} - Correlation',
                'description': f'Relationship between {col1} and {col2}',
                'data': {
                    'datasets': [{
                        'label': f'{col1} vs {col2}',
                        'data': [
                            {'x': float(row[col1]), 'y': float(row[col2])}
                            for _, row in scatter_data.head(200).iterrows()
                        ],
                        'backgroundColor': 'rgba(147, 51, 234, 0.6)',
                        'pointRadius': 4
                    }]
                },
                'options': {
                    'scales': {
                        'x': {'title': {'display': True, 'text': col1}},
                        'y': {'title': {'display': True, 'text': col2}}
                    }
                }
            })
    
    return charts

def perform_advanced_analysis(df, analysis_types):
    """Perform advanced analytics including XGBoost forecasting with enhanced features"""
    results = {}
    
    # Ensure we have numeric and date columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    date_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
    
    # If no datetime columns, try to infer from string columns
    if not date_cols:
        for col in df.columns:
            if df[col].dtype == 'object':
                try:
                    df[col] = pd.to_datetime(df[col])
                    date_cols.append(col)
                except:
                    continue
    
    if not date_cols or not numeric_cols:
        return {
            'success': False,
            'error': 'Need at least one datetime and one numeric column for time series analysis.'
        }
    
    # Use the first datetime and numeric column found
    date_col = date_cols[0]
    value_col = numeric_cols[0]
    
    # Sort by date and ensure no duplicates
    df = df.sort_values(by=date_col).drop_duplicates(subset=[date_col])
    
    # Create a complete date range to handle missing dates
    date_range = pd.date_range(start=df[date_col].min(), end=df[date_col].max(), freq='D')
    df = df.set_index(date_col).reindex(date_range).reset_index()
    df = df.rename(columns={'index': date_col})
    
    # Forward fill missing values for the value column
    df[value_col] = df[value_col].fillna(method='ffill')
    
    # Add comprehensive time-based features
    df['day_of_week'] = df[date_col].dt.dayofweek
    df['day_of_month'] = df[date_col].dt.day
    df['month'] = df[date_col].dt.month
    df['quarter'] = df[date_col].dt.quarter
    df['year'] = df[date_col].dt.year
    df['day_of_year'] = df[date_col].dt.dayofyear
    df['week_of_year'] = df[date_col].dt.isocalendar().week
    
    # Add rolling statistics as features
    for window in [7, 14, 30]:  # 1 week, 2 weeks, 1 month
        df[f'rolling_mean_{window}'] = df[value_col].rolling(window=window, min_periods=1).mean()
        df[f'rolling_std_{window}'] = df[value_col].rolling(window=window, min_periods=1).std()
    
    # Add lagged features
    for lag in [1, 7, 14, 30]:  # 1 day, 1 week, 2 weeks, 1 month
        df[f'lag_{lag}'] = df[value_col].shift(lag)
    
    # Drop rows with NaN values that were created by lags
    df = df.dropna()
    
    # Prepare features and target
    feature_cols = [
        'day_of_week', 'day_of_month', 'month', 'quarter', 'year',
        'day_of_year', 'week_of_year',
        'rolling_mean_7', 'rolling_std_7',
        'rolling_mean_14', 'rolling_std_14',
        'rolling_mean_30', 'rolling_std_30',
        'lag_1', 'lag_7', 'lag_14', 'lag_30'
    ]
    
    X = df[feature_cols]
    y = df[value_col]
    
    # Split into train and test sets (80-20 split)
    train_size = int(len(df) * 0.8)
    X_train, X_test = X[:train_size], X[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]
    
    # Initialize results
    results = {
        'success': True,
        'forecasts': {},
        'metrics': {},
        'feature_importance': {}
    }
    
    # XGBoost Forecasting with enhanced features
    if 'xgboost' in analysis_types:
        try:
            import xgboost as xgb
            from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
            
            # Train XGBoost model with hyperparameters
            model = xgb.XGBRegressor(
                objective='reg:squarederror',
                n_estimators=200,
                learning_rate=0.05,
                max_depth=8,
                min_child_weight=1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1
            )
            
            # Fit the model
            model.fit(
                X_train, y_train,
                eval_set=[(X_train, y_train), (X_test, y_test)],
                eval_metric='rmse',
                early_stopping_rounds=20,
                verbose=False
            )
            
            # Make predictions
            y_pred = model.predict(X_test)
            
            # Calculate metrics
            mae = mean_absolute_error(y_test, y_pred)
            mse = mean_squared_error(y_test, y_pred)
            rmse = np.sqrt(mse)
            r2 = r2_score(y_test, y_pred)
            
            # Get feature importance
            importance = model.get_booster().get_score(importance_type='weight')
            importance = {k: float(v) for k, v in sorted(importance.items(), key=lambda x: x[1], reverse=True)}
            
            # Store results
            results['forecasts']['xgboost'] = {
                'dates': df[date_col].iloc[train_size:].astype(str).tolist(),
                'actual': y_test.tolist(),
                'predicted': y_pred.tolist()
            }
            
            results['metrics']['xgboost'] = {
                'mae': float(mae),
                'mse': float(mse),
                'rmse': float(rmse),
                'r2': float(r2)
            }
            
            results['feature_importance'] = importance
            
            # Generate future forecast (next 30 days)
            last_date = df[date_col].max()
            future_dates = [last_date + timedelta(days=i) for i in range(1, 31)]
            
            # Prepare future data with all features
            future_df = pd.DataFrame({
                date_col: future_dates,
                'day_of_week': [d.dayofweek for d in future_dates],
                'day_of_month': [d.day for d in future_dates],
                'month': [d.month for d in future_dates],
                'quarter': [d.quarter for d in future_dates],
                'year': [d.year for d in future_dates],
                'day_of_year': [d.timetuple().tm_yday for d in future_dates],
                'week_of_year': [d.isocalendar()[1] for d in future_dates]
            })
            
            # For the first day, we can use the last known values for rolling features and lags
            # For simplicity, we'll use the last 30 days of actual data to initialize these features
            last_30_days = df[value_col].iloc[-30:].values
            
            # Generate predictions day by day to properly update lags and rolling features
            future_predictions = []
            
            for i in range(len(future_dates)):
                # Prepare features for this day
                day_features = future_df.iloc[i].copy()
                
                # Update rolling features
                if i == 0:
                    # For the first prediction, use the last 30 days of actual data
                    rolling_window = last_30_days
                else:
                    # Update the rolling window with the last prediction
                    rolling_window = np.append(rolling_window[1:], future_predictions[-1])
                
                # Calculate rolling statistics
                for window in [7, 14, 30]:
                    if len(rolling_window) >= window:
                        day_features[f'rolling_mean_{window}'] = np.mean(rolling_window[-window:])
                        day_features[f'rolling_std_{window}'] = np.std(rolling_window[-window:])
                    else:
                        day_features[f'rolling_mean_{window}'] = np.mean(rolling_window)
                        day_features[f'rolling_std_{window}'] = np.std(rolling_window)
                
                # Update lag features
                for lag in [1, 7, 14, 30]:
                    if i >= lag:
                        day_features[f'lag_{lag}'] = future_predictions[-lag]
                    elif len(rolling_window) >= lag - i:
                        day_features[f'lag_{lag}'] = rolling_window[-(lag - i)]
                    else:
                        day_features[f'lag_{lag}'] = rolling_window[0]  # Fallback to first value
                
                # Make prediction for this day
                X_future = day_features[feature_cols].values.reshape(1, -1)
                pred = model.predict(X_future)[0]
                future_predictions.append(pred)
            
            # Store future forecast
            results['forecast_future'] = {
                'dates': [d.strftime('%Y-%m-%d') for d in future_dates],
                'predicted': future_predictions
            }
            
            # Generate feature importance chart data
            results['feature_importance_chart'] = {
                'features': list(importance.keys())[:10],  # Top 10 features
                'importance': list(importance.values())[:10]
            }
            
        except Exception as e:
            import traceback
            error_msg = f'XGBoost forecasting failed: {str(e)}\n{traceback.format_exc()}'
            results['forecasts']['xgboost'] = {'error': error_msg}
    
    return results

def get_time_series_data(df, start_date=None, end_date=None, time_interval='D'):
    """Helper function to get time series data with filters"""
    try:
        time_series = build_time_series(
            df,
            start_date=start_date,
            end_date=end_date,
            time_interval=time_interval
        )
        
        if not time_series:
            return {'success': False, 'error': 'Could not generate time series data'}
            
        return {'success': True, 'data': time_series}
        
    except Exception as e:
        print(f"[ERROR] get_time_series_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

def process_uploaded_file(file, chart_types, analysis_types, time_interval='D'):
    """
    Main processing function for uploaded datasets
    
    Args:
        file: Uploaded file object
        chart_types: List of chart types to generate
        analysis_types: List of analysis types to perform
        time_interval: Time interval for time series ('D'=daily, 'W'=weekly, 'M'=monthly)
    """
    try:
        # Read file (support multiple formats)
        fname = (file.filename or '').lower()
        if fname.endswith(('.csv', '.txt')):
            # Try different encodings if the default fails
            try:
                df = pd.read_csv(file, nrows=10000)  # Limit rows for initial processing
            except UnicodeDecodeError:
                df = pd.read_csv(file, encoding='latin1', nrows=10000)
        elif fname.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file, nrows=10000)
        elif fname.endswith('.json'):
            df = pd.read_json(file)
            if len(df) > 10000:  # Limit rows for large JSON files
                df = df.head(10000)
        elif fname.endswith('.parquet'):
            df = pd.read_parquet(file)
            if len(df) > 10000:  # Limit rows for large parquet files
                df = df.head(10000)
        else:
            return {
                'success': False,
                'error': 'Unsupported file format. Please upload CSV, Excel, JSON, or Parquet.'
            }
        
        print(f"[VISUALIZER] Loaded dataset: {len(df)} rows, {len(df.columns)} columns")
        print(f"[VISUALIZER] Columns: {list(df.columns)}")
        
        # Store original stats
        original_missing = df.isnull().sum().sum()
        original_rows = len(df)
        
        # Preprocess data
        df_clean = preprocess_data(df)
        print("[VISUALIZER] Preprocessing complete")
        
        # Perform basic analysis
        summary = analyze_dataset(df_clean)
        print(f"[VISUALIZER] Analysis complete: {summary.get('quality_score', 'N/A')} quality")
        
        # Generate time series data
        time_series = get_time_series_data(df_clean, time_interval=time_interval)
        if not time_series['success']:
            print(f"[WARNING] Could not generate time series: {time_series.get('error')}")
        
        # Generate charts
        charts = generate_charts(df_clean, chart_types)
        print(f"[VISUALIZER] Generated {len(charts)} charts")
        
        # Perform advanced analysis if requested
        advanced_analysis = {}
        if analysis_types:
            advanced_analysis = perform_advanced_analysis(df_clean, analysis_types)
            print("[VISUALIZER] Advanced analysis complete")
        
        # Prepare the result
        result = {
            'summary': {
                **summary,
                'original_rows': original_rows,
                'cleaned_rows': len(df_clean),
                'original_missing_values': int(original_missing),
                'columns': list(df_clean.columns),
                'column_types': {col: str(dtype) for col, dtype in df_clean.dtypes.items()}
            },
            'time_series': time_series.get('data') if time_series['success'] else None,
            'charts': charts,
            'analysis': advanced_analysis,
            'preview': df_clean.head(10).to_dict('records')
        }
        
        return {
            'success': True,
            'data': result,
            'meta': {
                'message': 'Dataset processed successfully',
                'rows_processed': len(df_clean),
                'columns_processed': len(df_clean.columns)
            }
        }
        
    except Exception as e:
        error_msg = f"Error processing file: {str(e)}"
        print(f"[ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': error_msg}

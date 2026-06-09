import pandas as pd
import numpy as np
from typing import Dict, Any, List


def clean_dataframe(df: pd.DataFrame, rules: Dict[str, Any]) -> pd.DataFrame:
    df = df.copy()

    # Basic options
    if rules.get("lowercase_columns"):
        df.columns = [str(c).strip().lower() for c in df.columns]

    if rules.get("trim_whitespace"):
        for c in df.select_dtypes(include=["object"]).columns:
            df[c] = df[c].astype(str).str.strip()

    # Date parsing
    date_cols: List[str] = rules.get("date_parse", []) or []
    for c in date_cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")

    # Missing handling
    drop_threshold = float(rules.get("drop_threshold", 1.1))  # >1 means disabled by default
    if 0 <= drop_threshold <= 1:
        miss_ratio = df.isna().mean()
        drop_cols = miss_ratio[miss_ratio > drop_threshold].index.tolist()
        if drop_cols:
            df = df.drop(columns=drop_cols)

    if rules.get("drop_duplicates", True):
        df = df.drop_duplicates()

    # Fill strategy
    default_strategy = (rules.get("fill_missing") or {}).get("default", "none")
    default_value = (rules.get("fill_missing") or {}).get("value")
    per_col = (rules.get("fill_missing") or {}).get("per_column", {})

    def apply_fill(col: str, series: pd.Series) -> pd.Series:
        strat = per_col.get(col, default_strategy)
        if strat == "none":
            return series
        if strat == "constant":
            return series.fillna(per_col.get(f"{col}__value", default_value))
        if strat == "mean" and series.dtype.kind in "biuf":
            return series.fillna(series.mean())
        if strat == "median" and series.dtype.kind in "biuf":
            return series.fillna(series.median())
        if strat == "mode":
            try:
                return series.fillna(series.mode().iloc[0])
            except Exception:
                return series
        return series

    for c in df.columns:
        df[c] = apply_fill(c, df[c])

    return df


def summarize_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    summary = {
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
        "columns": [
            {
                "name": str(c),
                "dtype": str(df[c].dtype),
                "missing": int(df[c].isna().sum()),
                "missing_ratio": float(df[c].isna().mean()),
            }
            for c in df.columns
        ],
    }
    try:
        preview = df.head(20).to_dict(orient="records")
    except Exception:
        preview = []
    summary["preview"] = preview
    return summary

def analyze_data_quality(df):
    """Analyze data quality and provide metrics like RMSE, MSE, and quality assessment"""
    try:
        analysis = {
            "total_rows": int(len(df)),
            "total_columns": int(len(df.columns)),
            "missing_values": int(df.isnull().sum().sum()),
            "missing_percentage": float((df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100) if len(df) > 0 and len(df.columns) > 0 else 0.0,
            "duplicate_rows": int(df.duplicated().sum()),
            "data_types": {str(k): str(v) for k, v in df.dtypes.to_dict().items()},
            "quality_score": "Good"
        }
        
        # Calculate quality score
        missing_pct = analysis["missing_percentage"]
        duplicate_pct = (analysis["duplicate_rows"] / len(df)) * 100 if len(df) > 0 else 0
        
        if missing_pct > 30 or duplicate_pct > 20:
            analysis["quality_score"] = "Poor"
        elif missing_pct > 15 or duplicate_pct > 10:
            analysis["quality_score"] = "Fair"
        elif missing_pct > 5 or duplicate_pct > 5:
            analysis["quality_score"] = "Good"
        else:
            analysis["quality_score"] = "Excellent"
        
        # Numeric column analysis
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            analysis["numeric_stats"] = {}
            for col in numeric_cols:
                col_data = df[col].dropna()
                if len(col_data) > 1:
                    mean_val = col_data.mean()
                    std_val = col_data.std()
                    # Simple MSE calculation (variance)
                    mse = std_val ** 2 if not pd.isna(std_val) else 0
                    rmse = std_val if not pd.isna(std_val) else 0
                    
                    analysis["numeric_stats"][col] = {
                        "mean": float(mean_val) if not pd.isna(mean_val) else 0.0,
                        "std": float(std_val) if not pd.isna(std_val) else 0.0,
                        "mse": float(mse),
                        "rmse": float(rmse),
                        "min": float(col_data.min()) if not pd.isna(col_data.min()) else 0.0,
                        "max": float(col_data.max()) if not pd.isna(col_data.max()) else 0.0,
                        "outliers": int(len(col_data[(col_data < (mean_val - 2*std_val)) | (col_data > (mean_val + 2*std_val))]))
                    }
        
        # Date column analysis
        date_cols = []
        for col in df.columns:
            if df[col].dtype == 'object':
                try:
                    pd.to_datetime(df[col].dropna().head(10))
                    date_cols.append(col)
                except:
                    pass
        
        if date_cols:
            analysis["date_columns"] = date_cols
            analysis["date_range"] = {}
            for col in date_cols:
                try:
                    dates = pd.to_datetime(df[col].dropna())
                    if len(dates) > 0:
                        analysis["date_range"][col] = {
                            "start": dates.min().isoformat(),
                            "end": dates.max().isoformat(),
                            "span_days": (dates.max() - dates.min()).days
                        }
                except:
                    pass
        
        return analysis
        
    except Exception as e:
        return {"error": str(e), "quality_score": "Unknown"}

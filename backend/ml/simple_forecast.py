from __future__ import annotations
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from typing import Dict, Any, List


def _prep_timeseries(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Standardize columns
    cols = {c.lower(): c for c in df.columns}
    rename_map = {}
    for expected in ["date", "ds", "timestamp"]:
        if expected in cols:
            rename_map[cols[expected]] = "date"
            break
    for expected in ["qty", "quantity", "y", "sales"]:
        if expected in cols:
            rename_map[cols[expected]] = "qty"
            break
    for expected in ["sku", "product_id", "item"]:
        if expected in cols:
            rename_map[cols[expected]] = "sku"
            break
    if rename_map:
        df = df.rename(columns=rename_map)

    if "date" not in df.columns or "qty" not in df.columns:
        raise ValueError("Input must contain date and qty columns (or equivalents)")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])  # drop unparseable
    df = df.sort_values("date")
    if "sku" not in df.columns:
        df["sku"] = "ALL"

    # coerce qty numeric
    df["qty"] = pd.to_numeric(df["qty"], errors="coerce")
    df = df.dropna(subset=["qty"])  # drop missing qty
    return df


essential_meta = {
    "model": "LinearRegression(time_index)",
    "version": "0.1-local",
    "hints": "Lightweight baseline for CPU; not seasonality-aware",
}


def _forecast_single(series: pd.DataFrame, horizon: int) -> Dict[str, Any]:
    # map dates to integer time index starting at 0
    s = series.sort_values("date").reset_index(drop=True)
    if s.shape[0] < 2:
        # fallback: naive last value
        last = float(s["qty"].iloc[-1]) if s.shape[0] else 0.0
        preds = [last for _ in range(horizon)]
        return {"history": s.to_dict("records"), "forecast": preds}

    X = np.arange(len(s)).reshape(-1, 1)
    y = s["qty"].astype(float).values
    model = LinearRegression()
    model.fit(X, y)

    X_future = np.arange(len(s), len(s) + horizon).reshape(-1, 1)
    yhat = model.predict(X_future)
    yhat = [float(max(0.0, v)) for v in yhat]  # clamp negatives

    return {
        "history": s.tail(5).to_dict("records"),
        "forecast": yhat,
        "coef": float(model.coef_[0]),
        "intercept": float(model.intercept_),
        "r2": float(model.score(X, y)),
    }


def forecast_sales(df: pd.DataFrame, horizon: int = 7) -> Dict[str, Any]:
    df = _prep_timeseries(df)
    out: Dict[str, Any] = {"meta": {**essential_meta, "horizon": int(horizon)}, "results": []}

    for sku, g in df.groupby("sku"):
        res = _forecast_single(g[["date", "qty"]], horizon)
        out["results"].append({"sku": str(sku), **res})

    return out

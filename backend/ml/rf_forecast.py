from __future__ import annotations
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from typing import Dict, Any

from .simple_forecast import _prep_timeseries


def forecast_sales_random_forest(df: pd.DataFrame, horizon: int = 7) -> Dict[str, Any]:
    """
    Forecast sales using Random Forest Regressor.
    """
    df = _prep_timeseries(df)
    out: Dict[str, Any] = {"meta": {"model": "RandomForestRegressor(time_index)", "version": "0.1-local", "horizon": int(horizon)}, "results": []}

    for sku, g in df.groupby("sku"):
        s = g.sort_values("date").reset_index(drop=True)
        if s.shape[0] < 2:
            continue

        X = np.arange(len(s)).reshape(-1, 1)
        y = s["qty"].astype(float).values
        model = RandomForestRegressor(n_estimators=50, max_depth=3, random_state=42, n_jobs=1)
        model.fit(X, y)
        X_future = np.arange(len(s), len(s) + horizon).reshape(-1, 1)
        yhat = model.predict(X_future)
        yhat = np.maximum(yhat, 0)  # ensure non-negative

        # Build result structure
        start_date = pd.to_datetime(s["date"].iloc[-1])
        result = {
            "sku": sku,
            "history": [{"date": row["date"], "qty": float(row["qty"])} for _, row in s.iterrows()],
            "forecast": [
                {
                    "date": (start_date + pd.Timedelta(days=i + 1)).isoformat(),
                    "qty": float(val),
                }
                for i, val in enumerate(yhat)
            ],
        }
        out["results"].append(result)

    return out

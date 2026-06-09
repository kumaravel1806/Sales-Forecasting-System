from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, Any

try:
    from xgboost import XGBRegressor
except Exception as e:  # pragma: no cover
    XGBRegressor = None  # allow import even if not installed

from .simple_forecast import _prep_timeseries


def forecast_sales_xgb(df: pd.DataFrame, horizon: int = 7) -> Dict[str, Any]:
    if XGBRegressor is None:
        raise RuntimeError("xgboost not installed")

    df = _prep_timeseries(df)
    out: Dict[str, Any] = {"meta": {"model": "XGBRegressor(time_index)", "version": "0.1-local", "horizon": int(horizon)}, "results": []}

    for sku, g in df.groupby("sku"):
        s = g.sort_values("date").reset_index(drop=True)
        if s.shape[0] < 2:
            last = float(s["qty"].iloc[-1]) if s.shape[0] else 0.0
            preds = [last for _ in range(horizon)]
            out["results"].append({"sku": str(sku), "history": s.tail(5).to_dict("records"), "forecast": preds})
            continue

        X = np.arange(len(s)).reshape(-1, 1)
        y = s["qty"].astype(float).values
        model = XGBRegressor(n_estimators=50, max_depth=3, learning_rate=0.1, subsample=0.9, colsample_bytree=1.0, objective='reg:squarederror', n_jobs=1, tree_method='hist')
        model.fit(X, y)
        X_future = np.arange(len(s), len(s) + horizon).reshape(-1, 1)
        yhat = model.predict(X_future)
        yhat = [float(max(0.0, v)) for v in yhat]
        out["results"].append({"sku": str(sku), "history": s.tail(5).to_dict("records"), "forecast": yhat})

    return out

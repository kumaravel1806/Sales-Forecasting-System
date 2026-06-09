import argparse
import os
import pandas as pd
import joblib
from datetime import datetime

from .simple_forecast import _prep_timeseries

try:
    from xgboost import XGBRegressor
except Exception:
    XGBRegressor = None

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
import numpy as np


def train_lr(df: pd.DataFrame):
    s = df.sort_values('date').reset_index(drop=True)
    X = np.arange(len(s)).reshape(-1, 1)
    y = s['qty'].astype(float).values
    m = LinearRegression()
    m.fit(X, y)
    return m


def train_xgb(df: pd.DataFrame, local: bool = True):
    if XGBRegressor is None:
        return None
    s = df.sort_values('date').reset_index(drop=True)
    X = np.arange(len(s)).reshape(-1, 1)
    y = s['qty'].astype(float).values
    n_estimators = 30 if local else 200
    m = XGBRegressor(n_estimators=n_estimators, max_depth=3, learning_rate=0.1, subsample=0.9, colsample_bytree=1.0, objective='reg:squarederror', n_jobs=1, tree_method='hist')
    m.fit(X, y)
    return m


def train_random_forest(df: pd.DataFrame, local: bool = True):
    s = df.sort_values('date').reset_index(drop=True)
    X = np.arange(len(s)).reshape(-1, 1)
    y = s['qty'].astype(float).values
    n_estimators = 30 if local else 200
    m = RandomForestRegressor(n_estimators=n_estimators, max_depth=3, random_state=42, n_jobs=1)
    m.fit(X, y)
    return m


def main():
    ap = argparse.ArgumentParser(description='Train simple models per SKU')
    ap.add_argument('--input', required=True, help='Path to CSV/Excel with columns date, qty, sku(optional)')
    ap.add_argument('--local', action='store_true', help='Lightweight settings for CPU')
    ap.add_argument('--outdir', default=os.path.join(os.path.dirname(__file__), '..', 'data', 'models'))
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # Load input
    if args.input.lower().endswith('.csv'):
        df = pd.read_csv(args.input)
    else:
        df = pd.read_excel(args.input)
    df = _prep_timeseries(df)

    stamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')

    for sku, g in df.groupby('sku'):
        if g.shape[0] < 2:
            continue
        lr = train_lr(g)
        joblib.dump(lr, os.path.join(args.outdir, f'{stamp}_lr_{sku}.joblib'))
        xgb = train_xgb(g, local=args.local)
        if xgb is not None:
            joblib.dump(xgb, os.path.join(args.outdir, f'{stamp}_xgb_{sku}.joblib'))
        rf = train_random_forest(g, local=args.local)
        joblib.dump(rf, os.path.join(args.outdir, f'{stamp}_rf_{sku}.joblib'))

    print('Done. Models saved to', args.outdir)


if __name__ == '__main__':
    main()

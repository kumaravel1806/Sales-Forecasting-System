import argparse
import os
import sys
from datetime import datetime
import numpy as np
import pandas as pd

try:
    import tensorflow as tf
    from tensorflow.keras import Sequential
    from tensorflow.keras.layers import LSTM, Dense
    TF_AVAILABLE = True
except Exception:
    TF_AVAILABLE = False

from .simple_forecast import _prep_timeseries


def build_dataset(values: np.ndarray, lookback: int = 14):
    X, y = [], []
    for i in range(len(values) - lookback):
        X.append(values[i:i+lookback])
        y.append(values[i+lookback])
    if not X:
        return np.empty((0, lookback, 1)), np.empty((0,))
    X = np.array(X).reshape(-1, lookback, 1)
    y = np.array(y).astype(float)
    return X, y


def build_model(lookback: int = 14):
    m = Sequential([
        LSTM(16, input_shape=(lookback, 1)),
        Dense(1)
    ])
    m.compile(optimizer='adam', loss='mse')
    return m


def train_per_sku(df: pd.DataFrame, outdir: str, local: bool = True, lookback: int = 14, epochs: int = None, batch: int = None):
    if not TF_AVAILABLE:
        print('TensorFlow not available. Install it or run on cloud. Skipping LSTM training.', file=sys.stderr)
        return 1

    os.makedirs(outdir, exist_ok=True)
    stamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')

    # Defaults tuned for CPU-local
    epochs = epochs if epochs is not None else (3 if local else 20)
    batch = batch if batch is not None else (8 if local else 32)

    for sku, g in df.groupby('sku'):
        s = g.sort_values('date').reset_index(drop=True)
        vals = s['qty'].astype(float).values
        X, y = build_dataset(vals, lookback=lookback)
        if X.shape[0] < 5:
            print(f'SKU {sku}: not enough data for LSTM (samples={X.shape[0]}). Skipping.')
            continue
        model = build_model(lookback=lookback)
        model.fit(X, y, epochs=epochs, batch_size=batch, verbose=0)

        # Save model
        target = os.path.join(outdir, f'{stamp}_lstm_{sku}')
        try:
            model.save(target)
            print('Saved', target)
        except Exception as e:
            # Fallback to H5
            model.save(target + '.h5')
            print('Saved', target + '.h5')

    print('Done.')
    return 0


def main():
    ap = argparse.ArgumentParser(description='Train LSTM models per SKU')
    ap.add_argument('--input', required=True, help='Path to CSV/Excel with columns date, qty, sku(optional)')
    ap.add_argument('--local', action='store_true', help='Use tiny CPU-friendly settings')
    ap.add_argument('--lookback', type=int, default=14)
    ap.add_argument('--epochs', type=int)
    ap.add_argument('--batch', type=int)
    ap.add_argument('--config', help='Optional YAML config file (lookback, epochs, batch, mode: local/cloud)')
    ap.add_argument('--outdir', default=os.path.join(os.path.dirname(__file__), '..', 'data', 'models'))
    args = ap.parse_args()

    # Optional config
    if args.config and os.path.isfile(args.config):
        try:
            import yaml  # type: ignore
            with open(args.config, 'r', encoding='utf-8') as fh:
                cfg = yaml.safe_load(fh) or {}
            if isinstance(cfg, dict):
                if cfg.get('mode') == 'cloud':
                    args.local = False
                if 'lookback' in cfg and args.lookback == 14:
                    args.lookback = int(cfg['lookback'])
                if 'epochs' in cfg and args.epochs is None:
                    args.epochs = int(cfg['epochs'])
                if 'batch' in cfg and args.batch is None:
                    args.batch = int(cfg['batch'])
        except Exception as e:
            print('Warning: failed to read config:', e, file=sys.stderr)

    # Load
    if args.input.lower().endswith('.csv'):
        raw = pd.read_csv(args.input)
    else:
        raw = pd.read_excel(args.input)
    df = _prep_timeseries(raw)

    code = train_per_sku(df, outdir=args.outdir, local=args.local, lookback=args.lookback, epochs=args.epochs, batch=args.batch)
    raise SystemExit(code)


if __name__ == '__main__':
    main()

from flask import Blueprint, jsonify, request
from datetime import datetime
import json
import pandas as pd
from typing import Any, Dict
try:
    from ml.simple_forecast import forecast_sales as lr_forecast  # when running from backend/ directly
except Exception:  # pragma: no cover
    from backend.ml.simple_forecast import forecast_sales as lr_forecast  # when running from repo root / docker
try:
    from ml.xgb_forecast import forecast_sales_xgb  # when running from backend/
except Exception:  # pragma: no cover
    from backend.ml.xgb_forecast import forecast_sales_xgb  # when running from repo root / docker
try:
    from ml.rf_forecast import forecast_sales_random_forest  # when running from backend/
except Exception:  # pragma: no cover
    from backend.ml.rf_forecast import forecast_sales_random_forest  # when running from repo root / docker
try:
    from ml.simple_forecast import _prep_timeseries  # for splitting
except Exception:  # pragma: no cover
    from backend.ml.simple_forecast import _prep_timeseries
try:
    from ml.metrics import summarize as summarize_metrics
except Exception:  # pragma: no cover
    from backend.ml.metrics import summarize as summarize_metrics
try:
    from db import get_conn
except Exception:  # pragma: no cover
    from backend.db import get_conn

bp = Blueprint("ml", __name__)


@bp.post("/predict/sales")
def predict_sales():
    horizon = int(request.args.get("horizon", request.form.get("horizon", 7)))
    df = None
    # CSV/Excel upload
    if "file" in request.files:
        f = request.files["file"]
        name = (f.filename or "").lower()
        try:
            if name.endswith(".csv"):
                df = pd.read_csv(f)
            elif name.endswith(".xlsx") or name.endswith(".xls"):
                df = pd.read_excel(f)
            else:
                return jsonify({"success": False, "data": None, "meta": {"error": "unsupported_extension"}}), 400
        except Exception as e:
            return jsonify({"success": False, "data": None, "meta": {"error": "parse_failed", "detail": str(e)}}), 400
    else:
        # JSON body: { data: [ {date, qty, sku?}, ...], horizon? }
        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        if "horizon" in payload:
            try:
                horizon = int(payload["horizon"])  # override
            except Exception:
                pass
        rows = payload.get("data") or []
        try:
            df = pd.DataFrame(rows)
        except Exception:
            df = None
    if df is None or df.empty:
        return jsonify({"success": False, "data": None, "meta": {"error": "empty_input"}}), 400

    try:
        result = lr_forecast(df, horizon=horizon)
    except Exception as e:
        return jsonify({"success": False, "data": None, "meta": {"error": "forecast_failed", "detail": str(e)}}), 400

    return jsonify({"success": True, "data": result, "meta": {"horizon": horizon}})


@bp.post("/predict/recommend")
def recommend():
    return jsonify({"success": True, "data": {"recommendations": []}, "meta": {"model": "stub"}})


@bp.post("/predict/sentiment")
def sentiment():
    try:
        try:
            from ml.sentiment import train_and_predict  # when running from backend/
        except Exception:  # pragma: no cover
            from backend.ml.sentiment import train_and_predict

        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        texts = payload.get("texts") or []
        train_samples = payload.get("train_samples")  # optional
        if not isinstance(texts, list) or not texts:
            return jsonify({"success": False, "data": None, "meta": {"error": "texts_required"}}), 400
        out = train_and_predict(train_samples, texts)
        return jsonify({"success": True, "data": out, "meta": {}})
    except Exception as e:
        return jsonify({"success": False, "data": None, "meta": {"error": "sentiment_failed", "detail": str(e)}}), 400


@bp.post("/compare")
def compare_models():
    """
    Simple holdout evaluation: last `horizon` points are test, the rest are train.
    Runs LinearRegression baseline and XGBoost (if available) and reports MAE/RMSE/MAPE per SKU and overall average.
    Accepts JSON { data: [...], horizon? } or multipart file upload (CSV/Excel) with optional horizon.
    """
    horizon = int(request.args.get("horizon", request.form.get("horizon", 7)))

    df = None
    if "file" in request.files:
        f = request.files["file"]
        name = (f.filename or "").lower()
        try:
            if name.endswith(".csv"):
                df = pd.read_csv(f)
            elif name.endswith(".xlsx") or name.endswith(".xls"):
                df = pd.read_excel(f)
            else:
                return jsonify({"success": False, "data": None, "meta": {"error": "unsupported_extension"}}), 400
        except Exception as e:
            return jsonify({"success": False, "data": None, "meta": {"error": "parse_failed", "detail": str(e)}}), 400
    else:
        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        if "horizon" in payload:
            try:
                horizon = int(payload["horizon"])  # override
            except Exception:
                pass
        rows = payload.get("data") or []
        try:
            df = pd.DataFrame(rows)
        except Exception:
            df = None

    if df is None or df.empty:
        return jsonify({"success": False, "data": None, "meta": {"error": "empty_input"}}), 400

    try:
        ts = _prep_timeseries(df)
    except Exception as e:
        return jsonify({"success": False, "data": None, "meta": {"error": "prep_failed", "detail": str(e)}}), 400

    results = []
    agg = {"lr": {"mae": [], "rmse": [], "mape": [], "r2": []}, "xgb": {"mae": [], "rmse": [], "mape": [], "r2": []}, "rf": {"mae": [], "rmse": [], "mape": [], "r2": []}}

    for sku, g in ts.groupby("sku"):
        g = g.sort_values("date").reset_index(drop=True)
        if g.shape[0] <= horizon:
            # skip too short series
            continue
        train = g.iloc[:-horizon]
        test = g.iloc[-horizon:]

        # Build inputs
        train_df = train[["date", "qty", "sku"]].copy()
        test_df = g[["date", "qty", "sku"]].copy()  # full for consistent interface

        # LR
        lr_out = lr_forecast(train_df, horizon=horizon)
        lr_pred = lr_out["results"][0]["forecast"] if lr_out["results"] else [0.0] * horizon
        lr_metrics = summarize_metrics(test["qty"].values, lr_pred)

        # XGB (may fail if not installed)
        try:
            xgb_out = forecast_sales_xgb(train_df, horizon=horizon)
            xgb_pred = xgb_out["results"][0]["forecast"] if xgb_out["results"] else [0.0] * horizon
            xgb_metrics = summarize_metrics(test["qty"].values, xgb_pred)
        except Exception as e:
            xgb_out = {"meta": {"error": str(e)}}
            xgb_pred = None
            xgb_metrics = None

        # Random Forest
        try:
            rf_out = forecast_sales_random_forest(train_df, horizon=horizon)
            rf_pred = rf_out["results"][0]["forecast"] if rf_out["results"] else [0.0] * horizon
            rf_metrics = summarize_metrics(test["qty"].values, rf_pred)
        except Exception as e:
            rf_out = {"meta": {"error": str(e)}}
            rf_pred = None
            rf_metrics = None

        results.append({
            "sku": str(sku),
            "horizon": horizon,
            "metrics": {
                "lr": lr_metrics,
                "xgb": xgb_metrics,
                "rf": rf_metrics,
            },
        })

        agg["lr"]["mae"].append(lr_metrics["mae"]) ; agg["lr"]["rmse"].append(lr_metrics["rmse"]) ; agg["lr"]["mape"].append(lr_metrics["mape"]) ; agg["lr"]["r2"].append(lr_metrics.get("r2"))  # noqa: E702
        if xgb_metrics:
            agg["xgb"]["mae"].append(xgb_metrics["mae"]) ; agg["xgb"]["rmse"].append(xgb_metrics["rmse"]) ; agg["xgb"]["mape"].append(xgb_metrics["mape"]) ; agg["xgb"]["r2"].append(xgb_metrics.get("r2"))  # noqa: E702
        if rf_metrics:
            agg["rf"]["mae"].append(rf_metrics["mae"]) ; agg["rf"]["rmse"].append(rf_metrics["rmse"]) ; agg["rf"]["mape"].append(rf_metrics["mape"]) ; agg["rf"]["r2"].append(rf_metrics.get("r2"))  # noqa: E702

    def avg(d):
        import numpy as np
        return {k: float(np.mean(v)) if v else None for k, v in d.items()}

    overall = {"lr": avg(agg["lr"]), "xgb": avg(agg["xgb"]), "rf": avg(agg["rf"]) }

    return jsonify({"success": True, "data": {"per_sku": results, "overall": overall}, "meta": {"horizon": horizon}})


@bp.post("/scenario/last_n")
def scenario_last_n():
    """
    Evaluate multiple last-N-day windows in one request.
    Body JSON: { data: [...], windows?: [7,10,15,30], model?: 'lr'|'xgb'|'both' }
    For each window n: train on all but last n rows per SKU, test on last n, compute metrics.
    Returns per-window aggregated metrics and the best window per metric.
    """
    df = None
    windows = None
    model_sel = None

    # Prefer multipart file upload
    if "file" in request.files:
        f = request.files["file"]
        name = (f.filename or "").lower()
        try:
            if name.endswith(".csv"):
                df = pd.read_csv(f)
            elif name.endswith(".xlsx") or name.endswith(".xls"):
                df = pd.read_excel(f)
            else:
                return jsonify({"success": False, "data": None, "meta": {"error": "unsupported_extension"}}), 400
        except Exception as e:
            return jsonify({"success": False, "data": None, "meta": {"error": "parse_failed", "detail": str(e)}}), 400
        # windows may be comma-separated in form field
        w_str = request.form.get("windows") or "7,10,15,30"
        try:
            windows = [int(x.strip()) for x in w_str.split(",") if x.strip()]
        except Exception:
            windows = [7, 10, 15, 30]
        model_sel = (request.form.get("model") or "both").lower()
    else:
        # Backward compatible JSON body
        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        rows = payload.get("data") or []
        windows = payload.get("windows") or [7, 10, 15, 30]
        model_sel = (payload.get("model") or "both").lower()
        try:
            df = pd.DataFrame(rows)
        except Exception as e:
            return jsonify({"success": False, "data": None, "meta": {"error": "prep_failed", "detail": str(e)}}), 400

    # Prepare time series
    try:
        ts = _prep_timeseries(df)
    except Exception as e:
        return jsonify({"success": False, "data": None, "meta": {"error": "prep_failed", "detail": str(e)}}), 400

    # Normalize windows
    windows = [int(w) for w in windows if int(w) > 0]
    if not windows:
        return jsonify({"success": False, "data": None, "meta": {"error": "no_windows"}}), 400

    out: Dict[str, Any] = {"windows": {}, "best": {}}

    for n in windows:
        agg = {"lr": {"mae": [], "rmse": [], "mape": []}, "xgb": {"mae": [], "rmse": [], "mape": []}}
        for sku, g in ts.groupby("sku"):
            g = g.sort_values("date").reset_index(drop=True)
            if g.shape[0] <= n:
                continue
            train = g.iloc[:-n]
            test = g.iloc[-n:]

            # LR
            if model_sel in ("lr", "both"):
                lr_out = lr_forecast(train[["date", "qty", "sku"]], horizon=n)
                lr_pred = lr_out["results"][0]["forecast"] if lr_out["results"] else [0.0] * n
                m = summarize_metrics(test["qty"].values, lr_pred)
                for k in m:
                    agg["lr"][k].append(m[k])

            # XGB
            if model_sel in ("xgb", "both"):
                try:
                    xgb_out = forecast_sales_xgb(train[["date", "qty", "sku"]], horizon=n)
                    xgb_pred = xgb_out["results"][0]["forecast"] if xgb_out["results"] else [0.0] * n
                    m = summarize_metrics(test["qty"].values, xgb_pred)
                    for k in m:
                        agg["xgb"][k].append(m[k])
                except Exception:
                    pass

        def avg(d):
            import numpy as np
            return {k: float(np.mean(v)) if v else None for k, v in d.items()}

        out["windows"][str(n)] = {"lr": avg(agg["lr"]), "xgb": avg(agg["xgb"]) }

    # Pick best window per metric for selected model(s) using lowest value criterion
    def pick_best(model_key: str):
        best = {"mae": None, "rmse": None, "mape": None}
        for metric in ["mae", "rmse", "mape"]:
            best_win = None
            best_val = None
            for w_str, vals in out["windows"].items():
                v = (vals.get(model_key) or {}).get(metric)
                if v is None:
                    continue
                if best_val is None or v < best_val:
                    best_val = v
                    best_win = int(w_str)
            best[metric] = {"window": best_win, "value": best_val}
        return best

    if model_sel in ("lr", "both"):
        out["best"]["lr"] = pick_best("lr")
    if model_sel in ("xgb", "both"):
        out["best"]["xgb"] = pick_best("xgb")

    return jsonify({"success": True, "data": out, "meta": {"windows": windows, "model": model_sel}})


@bp.post("/pipeline/run")
def pipeline_run():
    """
    Lightweight automated pipeline for sales forecasting evaluation.
    Input (JSON or multipart with file):
      - data: array of rows with date, qty, optional sku
      - horizon (int, optional): validation window (default 14)
      - model: 'lr'|'xgb'|'both' (default 'both')
      - rules (optional): cleaning rules for clean_dataframe
    Output: per_sku metrics for LR/XGB, best per SKU, and overall summary.
    """
    model_sel = (request.values.get("model") or request.json.get("model") if request.is_json else None) or "both"
    try:
        horizon = int((request.values.get("horizon") or (request.json.get("horizon") if request.is_json else 14)) or 14)
    except Exception:
        horizon = 14

    rules = {}
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        rules = payload.get("rules") or {}
        rows = payload.get("data") or []
        df = pd.DataFrame(rows)
    elif "file" in request.files:
        # Minimal parser for CSV/Excel
        f = request.files["file"]
        name = f.filename.lower()
        import os, tempfile
        fd, path = tempfile.mkstemp(suffix=os.path.splitext(name)[1])
        os.close(fd)
        f.save(path)
        try:
            if name.endswith(".csv"):
                df = pd.read_csv(path)
            elif name.endswith(".xlsx") or name.endswith(".xls"):
                df = pd.read_excel(path)
            else:
                return jsonify({"success": False, "data": None, "meta": {"error": "unsupported_file"}}), 400
        finally:
            try:
                os.remove(path)
            except Exception:
                pass
    else:
        return jsonify({"success": False, "data": None, "meta": {"error": "no_input"}}), 400

    try:
        df = clean_dataframe(df, rules)
        ts = _prep_timeseries(df)
    except Exception as e:
        return jsonify({"success": False, "data": None, "meta": {"error": "prep_failed", "detail": str(e)}}), 400

    results: List[Dict[str, Any]] = []
    agg = {"lr": {"mae": [], "rmse": [], "mape": []}, "xgb": {"mae": [], "rmse": [], "mape": []}}

    for sku, g in ts.groupby("sku"):
        g = g.sort_values("date").reset_index(drop=True)
        if g.shape[0] <= horizon:
            continue
        train = g.iloc[:-horizon]
        test = g.iloc[-horizon:]

        sku_res: Dict[str, Any] = {"sku": sku, "horizon": horizon}

        # LR
        lr_metrics = None
        if model_sel in ("lr", "both"):
            lr_out = lr_forecast(train[["date", "qty", "sku"]], horizon=horizon)
            lr_pred = lr_out["results"][0]["forecast"] if lr_out["results"] else [0.0] * horizon
            lr_metrics = summarize_metrics(test["qty"].values, lr_pred)
            sku_res["lr"] = {"metrics": lr_metrics}
            for k in lr_metrics:
                if k in agg["lr"]:
                    agg["lr"][k].append(lr_metrics[k])

        # XGB
        xgb_metrics = None
        if model_sel in ("xgb", "both"):
            try:
                xgb_out = forecast_sales_xgb(train[["date", "qty", "sku"]], horizon=horizon)
                xgb_pred = xgb_out["results"][0]["forecast"] if xgb_out["results"] else [0.0] * horizon
                xgb_metrics = summarize_metrics(test["qty"].values, xgb_pred)
                sku_res["xgb"] = {"metrics": xgb_metrics}
                for k in xgb_metrics:
                    if k in agg["xgb"]:
                        agg["xgb"][k].append(xgb_metrics[k])
            except Exception:
                pass

        # pick best by MAE with tie-breaker RMSE
        def better(a, b):
            if a is None:
                return False
            if b is None:
                return True
            if a["mae"] != b["mae"]:
                return a["mae"] < b["mae"]
            return a["rmse"] < b["rmse"]

        best_model = None
        best_metrics = None
        if lr_metrics and (model_sel in ("lr", "both")):
            best_model, best_metrics = "lr", lr_metrics
        if xgb_metrics and (model_sel in ("xgb", "both")) and better(xgb_metrics, best_metrics):
            best_model, best_metrics = "xgb", xgb_metrics
        sku_res["best"] = {"model": best_model, "metrics": best_metrics}
        results.append(sku_res)

    def avg(d):
        import numpy as np
        return {k: float(np.mean(v)) if v else None for k, v in d.items()}

    overall = {"lr": avg(agg["lr"]), "xgb": avg(agg["xgb"]) }

    return jsonify({"success": True, "data": {"per_sku": results, "overall": overall}, "meta": {"horizon": horizon, "model": model_sel}})


@bp.post("/runs/save")
def save_run():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip() or None
    notes = (payload.get("notes") or "").strip() or None
    horizon = int(payload.get("horizon") or 0)
    model = (payload.get("model") or "both").strip()
    result = payload.get("result")
    if not isinstance(result, dict):
        return jsonify({"success": False, "data": None, "meta": {"error": "result_required"}}), 400
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO model_runs(name, notes, horizon, model, result_json, created_at) VALUES(?,?,?,?,?,?)',
            (name, notes, horizon, model, json.dumps(result), datetime.utcnow().isoformat())
        )
        rid = cur.lastrowid
        conn.commit()
    return jsonify({"success": True, "data": {"run_id": rid}, "meta": {}})

@bp.route("/scenario/enhanced", methods=["POST"])
def enhanced_scenario():
    """Enhanced scenario analysis with product selection and seasonal adjustments"""
    try:
        # Handle file upload
        if 'file' not in request.files:
            return jsonify({"success": False, "meta": {"error": "No file uploaded"}})
        
        file = request.files['file']
        if not file.filename:
            return jsonify({"success": False, "meta": {"error": "No file selected"}})
        
        # Get parameters
        windows_str = request.form.get('windows', '7,14,30,60')
        model = request.form.get('model', 'both')
        product_filter = request.form.get('product_filter', '')
        scenario_type = request.form.get('scenario_type', 'normal')
        
        # Parse windows
        try:
            windows = [int(w.strip()) for w in windows_str.split(',') if w.strip()]
        except ValueError:
            return jsonify({"success": False, "meta": {"error": "Invalid windows format"}})
        
        # Read and process file
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file)
        else:
            return jsonify({"success": False, "meta": {"error": "Unsupported file format"}})
        
        # Validate columns
        required_cols = ['date', 'qty']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return jsonify({"success": False, "meta": {"error": f"Missing columns: {missing_cols}"}})
        
        # Filter by product if specified
        if product_filter and 'sku' in df.columns:
            df = df[df['sku'] == product_filter]
            if df.empty:
                return jsonify({"success": False, "meta": {"error": f"No data found for product: {product_filter}"}})
        
        # Apply scenario adjustments
        scenario_multipliers = {
            'normal': 1.0,
            'discount_10': 1.15,
            'discount_20': 1.35,
            'discount_30': 1.60,
            'summer': 1.25,
            'winter': 0.85,
            'holiday': 1.80,
            'back_to_school': 1.40
        }
        
        multiplier = scenario_multipliers.get(scenario_type, 1.0)
        df['qty'] = df['qty'] * multiplier
        
        # Convert to the format expected by existing scenario analysis
        data_rows = df[['date', 'qty']].to_dict('records')
        
        # Run analysis for each window
        results = {}
        best_models = {}
        
        for window in windows:
            window_results = {}
            
            if model in ['lr', 'both']:
                try:
                    lr_result = simple_forecast(data_rows, window)
                    if lr_result.get('success'):
                        lr_metrics = lr_result.get('metrics', {})
                        window_results['lr'] = lr_metrics
                except Exception:
                    pass
            
            if model in ['xgb', 'both']:
                try:
                    xgb_result = xgb_forecast(data_rows, window)
                    if xgb_result.get('success'):
                        xgb_metrics = xgb_result.get('metrics', {})
                        window_results['xgb'] = xgb_metrics
                except Exception:
                    pass
            
            results[str(window)] = window_results
            
            # Determine best model for this window
            if 'lr' in window_results and 'xgb' in window_results:
                lr_mae = window_results['lr'].get('mae', float('inf'))
                xgb_mae = window_results['xgb'].get('mae', float('inf'))
                best_models[str(window)] = 'lr' if lr_mae <= xgb_mae else 'xgb'
            elif 'lr' in window_results:
                best_models[str(window)] = 'lr'
            elif 'xgb' in window_results:
                best_models[str(window)] = 'xgb'
        
        # Calculate overall best
        overall_best = {}
        if model in ['lr', 'both']:
            lr_maes = [results[str(w)].get('lr', {}).get('mae') for w in windows if results[str(w)].get('lr')]
            if lr_maes:
                best_lr_mae = min(mae for mae in lr_maes if mae is not None)
                best_lr_window = next(str(w) for w in windows if results[str(w)].get('lr', {}).get('mae') == best_lr_mae)
                overall_best['lr'] = {'mae': {'value': best_lr_mae, 'window': best_lr_window}}
        
        if model in ['xgb', 'both']:
            xgb_maes = [results[str(w)].get('xgb', {}).get('mae') for w in windows if results[str(w)].get('xgb')]
            if xgb_maes:
                best_xgb_mae = min(mae for mae in xgb_maes if mae is not None)
                best_xgb_window = next(str(w) for w in windows if results[str(w)].get('xgb', {}).get('mae') == best_xgb_mae)
                overall_best['xgb'] = {'mae': {'value': best_xgb_mae, 'window': best_xgb_window}}
        
        return jsonify({
            "success": True,
            "data": {
                "windows": results,
                "best": overall_best,
                "scenario_info": {
                    "type": scenario_type,
                    "multiplier": multiplier,
                    "product": product_filter or "All Products",
                    "data_points": len(df)
                }
            },
            "meta": {
                "windows": windows,
                "model": model,
                "scenario_type": scenario_type,
                "product_filter": product_filter
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "meta": {"error": str(e)}})

@bp.get("/runs")
def list_runs():
    with get_conn() as conn:
        cur = conn.cursor()
        rows = cur.execute('SELECT id, name, notes, horizon, model, result_json, created_at FROM model_runs ORDER BY id DESC').fetchall()
    data = []
    for r in rows:
        try:
            res = json.loads(r[5])
        except Exception:
            res = None
        data.append({
            "id": r[0],
            "name": r[1],
            "notes": r[2],
            "horizon": r[3],
            "model": r[4],
            "result": res,
            "created_at": r[6],
        })
    return jsonify({"success": True, "data": data, "meta": {}})


@bp.get("/runs/<int:run_id>")
def get_run(run_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        row = cur.execute('SELECT id, name, notes, horizon, model, result_json, created_at FROM model_runs WHERE id=?', (run_id,)).fetchone()
    if not row:
        return jsonify({"success": False, "data": None, "meta": {"error": "not_found"}}), 404
    try:
        res = json.loads(row[5])
    except Exception:
        res = None
    data = {"id": row[0], "name": row[1], "notes": row[2], "horizon": row[3], "model": row[4], "result": res, "created_at": row[6]}
    return jsonify({"success": True, "data": data, "meta": {}})


@bp.get("/runs/<int:run_id>/report")
def run_report(run_id: int):
    # Simple pass-through JSON report for now
    with get_conn() as conn:
        cur = conn.cursor()
        row = cur.execute('SELECT result_json FROM model_runs WHERE id=?', (run_id,)).fetchone()
    if not row:
        return jsonify({"success": False, "data": None, "meta": {"error": "not_found"}}), 404
    try:
        res = json.loads(row[0])
    except Exception:
        res = None
    return jsonify({"success": True, "data": res, "meta": {"run_id": run_id}})

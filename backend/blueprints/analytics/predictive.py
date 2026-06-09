import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from db import get_conn
import json

class SalesPredictor:
    def __init__(self):
        self.model_type = "linear_trend"
    
    def get_historical_sales_data(self, days=90):
        """Get historical sales data for prediction"""
        with get_conn() as conn:
            cur = conn.cursor()
            
            # Get sales data from orders table
            query = '''
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as orders,
                    COALESCE(SUM(total), 0) as revenue,
                    COALESCE(SUM(total), 0) / COUNT(*) as avg_order_value
                FROM orders 
                WHERE created_at >= date('now', '-{} days')
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            '''.format(days)
            
            data = cur.execute(query).fetchall()
            
            if not data:
                return self._generate_mock_data(days)
            
            df = pd.DataFrame(data, columns=['date', 'orders', 'revenue', 'avg_order_value'])
            df['date'] = pd.to_datetime(df['date'])
            
            return df
    
    def _generate_mock_data(self, days):
        """Generate mock historical data for demonstration"""
        dates = pd.date_range(end=datetime.now().date(), periods=days, freq='D')
        np.random.seed(42)
        
        # Simulate seasonal and trend patterns
        trend = np.linspace(100, 200, days)
        seasonal = 50 * np.sin(np.linspace(0, 4*np.pi, days))
        noise = np.random.normal(0, 20, days)
        
        orders = np.maximum(10, trend + seasonal + noise)
        revenue = orders * np.random.uniform(150, 500, days)
        avg_order_value = revenue / orders
        
        return pd.DataFrame({
            'date': dates,
            'orders': orders.astype(int),
            'revenue': revenue,
            'avg_order_value': avg_order_value
        })
    
    def predict_future_sales(self, forecast_days=30):
        """Predict future sales using linear trend and seasonality"""
        try:
            df = self.get_historical_sales_data(90)
            
            if len(df) < 7:
                return self._generate_simple_forecast(forecast_days)
            
            # Prepare features
            df['day_of_week'] = df['date'].dt.dayofweek
            df['day_of_month'] = df['date'].dt.day
            df['month'] = df['date'].dt.month
            df['days_since_start'] = (df['date'] - df['date'].min()).dt.days
            
            # Simple linear regression for trend
            X = df[['days_since_start', 'day_of_week', 'day_of_month']].values
            y_orders = df['orders'].values
            y_revenue = df['revenue'].values
            
            # Calculate coefficients manually (simple linear regression)
            X_with_intercept = np.column_stack([np.ones(len(X)), X])
            
            # Orders prediction
            coef_orders = np.linalg.lstsq(X_with_intercept, y_orders, rcond=None)[0]
            
            # Revenue prediction
            coef_revenue = np.linalg.lstsq(X_with_intercept, y_revenue, rcond=None)[0]
            
            # Generate future dates
            last_date = df['date'].max()
            future_dates = pd.date_range(start=last_date + timedelta(days=1), periods=forecast_days, freq='D')
            
            predictions = []
            for i, date in enumerate(future_dates):
                future_X = np.array([
                    1,  # intercept
                    df['days_since_start'].max() + i + 1,  # days since start
                    date.dayofweek,  # day of week
                    date.day  # day of month
                ])
                
                pred_orders = max(1, np.dot(future_X, coef_orders))
                pred_revenue = max(0, np.dot(future_X, coef_revenue))
                pred_avg_order = pred_revenue / pred_orders if pred_orders > 0 else 0
                
                predictions.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'predicted_orders': int(round(pred_orders)),
                    'predicted_revenue': round(pred_revenue, 2),
                    'predicted_avg_order': round(pred_avg_order, 2),
                    'confidence': self._calculate_confidence(i, forecast_days)
                })
            
            return predictions
            
        except Exception as e:
            print(f"Prediction error: {e}")
            return self._generate_simple_forecast(forecast_days)
    
    def _calculate_confidence(self, days_out, total_days):
        """Calculate confidence score that decreases with time"""
        return max(0.3, 1.0 - (days_out / total_days) * 0.5)
    
    def _generate_simple_forecast(self, days):
        """Generate simple forecast based on recent averages"""
        predictions = []
        base_date = datetime.now().date()
        
        # Get recent average
        with get_conn() as conn:
            cur = conn.cursor()
            recent_data = cur.execute('''
                SELECT 
                    COUNT(*) as orders,
                    COALESCE(SUM(total), 0) as revenue
                FROM orders 
                WHERE created_at >= date('now', '-7 days')
            ''').fetchone()
            
            if recent_data and recent_data[0] > 0:
                avg_orders = recent_data[0] / 7
                avg_revenue = recent_data[1] / 7
            else:
                avg_orders = 15
                avg_revenue = 5000
        
        for i in range(days):
            date = base_date + timedelta(days=i+1)
            # Add some variation
            variation = 1 + np.random.normal(0, 0.1)
            pred_orders = int(round(avg_orders * variation))
            pred_revenue = round(avg_revenue * variation, 2)
            
            predictions.append({
                'date': date.strftime('%Y-%m-%d'),
                'predicted_orders': pred_orders,
                'predicted_revenue': pred_revenue,
                'predicted_avg_order': round(pred_revenue / pred_orders, 2) if pred_orders > 0 else 0,
                'confidence': 0.7
            })
        
        return predictions
    
    def get_inventory_health_metrics(self):
        """Get real-time inventory health analytics"""
        with get_conn() as conn:
            cur = conn.cursor()
            
            # Total inventory value
            total_value = cur.execute('''
                SELECT COALESCE(SUM(p.price * COALESCE(p.stock_quantity, 0)), 0)
                FROM products p
            ''').fetchone()[0]
            
            # Stock distribution
            stock_status = cur.execute('''
                SELECT 
                    CASE 
                        WHEN p.stock_quantity = 0 THEN 'out_of_stock'
                        WHEN p.stock_quantity < p.min_stock_level THEN 'low_stock'
                        ELSE 'in_stock'
                    END as status,
                    COUNT(*) as count,
                    COALESCE(SUM(p.price * p.stock_quantity), 0) as value
                FROM products p
                GROUP BY status
            ''').fetchall()
            
            # Expiry analytics
            expiry_data = cur.execute('''
                SELECT 
                    CASE 
                        WHEN date(expiry_date) < date('now') THEN 'expired'
                        WHEN date(expiry_date) <= date('now', '+7 days') THEN 'expiring_soon'
                        WHEN date(expiry_date) <= date('now', '+30 days') THEN 'expiring_this_month'
                        ELSE 'good'
                    END as expiry_status,
                    COUNT(*) as batch_count,
                    COALESCE(SUM(qty), 0) as total_quantity,
                    COALESCE(SUM(qty * p.price), 0) as value_at_risk
                FROM inventory_batches ib
                JOIN products p ON ib.product_id = p.id
                WHERE ib.qty > 0
                GROUP BY expiry_status
            ''').fetchall()
            
            # Category performance
            category_performance = cur.execute('''
                SELECT 
                    p.category,
                    COUNT(*) as product_count,
                    COALESCE(SUM(p.stock_quantity), 0) as total_stock,
                    COALESCE(SUM(p.price * p.stock_quantity), 0) as category_value
                FROM products p
                GROUP BY p.category
                ORDER BY category_value DESC
            ''').fetchall()
            
            return {
                'total_inventory_value': total_value,
                'stock_distribution': dict([(row[0], {'count': row[1], 'value': row[2]}) for row in stock_status]),
                'expiry_analytics': dict([(row[0], {'batches': row[1], 'quantity': row[2], 'value': row[3]}) for row in expiry_data]),
                'category_performance': [(row[0], row[1], row[2], row[3]) for row in category_performance]
            }
    
    def get_real_time_alerts(self):
        """Get real-time alerts for critical inventory issues"""
        with get_conn() as conn:
            cur = conn.cursor()
            
            alerts = []
            
            # Critical stock alerts
            critical_stock = cur.execute('''
                SELECT p.name, p.category, p.stock_quantity, p.min_stock_level
                FROM products p
                WHERE p.stock_quantity = 0 OR p.stock_quantity < p.min_stock_level * 0.5
                ORDER BY p.stock_quantity ASC
                LIMIT 10
            ''').fetchall()
            
            for product in critical_stock:
                alerts.append({
                    'type': 'critical_stock',
                    'severity': 'high' if product[2] == 0 else 'medium',
                    'message': f"{product[0]} ({product[1]}) has only {product[2]} units (min: {product[3]})",
                    'timestamp': datetime.now().isoformat(),
                    'product_id': product[0]
                })
            
            # Expiry alerts
            expiring_soon = cur.execute('''
                SELECT p.name, ib.batch_no, ib.expiry_date, ib.qty, p.category
                FROM inventory_batches ib
                JOIN products p ON ib.product_id = p.id
                WHERE date(ib.expiry_date) BETWEEN date('now') AND date('now', '+7 days')
                AND ib.qty > 0
                ORDER BY ib.expiry_date ASC
                LIMIT 10
            ''').fetchall()
            
            for batch in expiring_soon:
                days_left = (datetime.strptime(batch[2], '%Y-%m-%d').date() - datetime.now().date()).days
                alerts.append({
                    'type': 'expiry_alert',
                    'severity': 'high' if days_left <= 3 else 'medium',
                    'message': f"{batch[0]} ({batch[4]}) batch {batch[1]} expires in {days_left} days ({batch[3]} units)",
                    'timestamp': datetime.now().isoformat(),
                    'batch_no': batch[1]
                })
            
            # High value items at risk
            high_value_risk = cur.execute('''
                SELECT p.name, p.price * ib.qty as value, ib.expiry_date
                FROM inventory_batches ib
                JOIN products p ON ib.product_id = p.id
                WHERE date(ib.expiry_date) <= date('now', '+30 days')
                AND ib.qty > 0
                AND p.price * ib.qty > 10000
                ORDER BY value DESC
                LIMIT 5
            ''').fetchall()
            
            for item in high_value_risk:
                alerts.append({
                    'type': 'high_value_risk',
                    'severity': 'medium',
                    'message': f"High-value item {item[0]} (₹{item[1]:,.0f}) at risk of expiry",
                    'timestamp': datetime.now().isoformat(),
                    'value': item[1]
                })
            
            return sorted(alerts, key=lambda x: (x['severity'] == 'high', x['timestamp']), reverse=True)

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import threading
import time
import random
import json
from datetime import datetime, timedelta
from db import get_conn
import numpy as np

app = Flask(__name__)
app.config['SECRET_KEY'] = 'realtime_dashboard_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

class RealTimeDataGenerator:
    def __init__(self):
        self.running = False
        self.connected_clients = 0
        
    def get_real_time_metrics(self):
        """Get real-time metrics from database"""
        try:
            with get_conn() as conn:
                cur = conn.cursor()
                
                # Get current product count
                total_products = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
                
                # Get inventory status
                inventory_status = cur.execute('''
                    SELECT 
                        COUNT(*) FILTER (WHERE stock_quantity = 0) as out_of_stock,
                        COUNT(*) FILTER (WHERE stock_quantity > 0 AND stock_quantity < min_stock_level) as low_stock,
                        COUNT(*) FILTER (WHERE stock_quantity >= min_stock_level) as in_stock,
                        COALESCE(SUM(price * stock_quantity), 0) as total_value
                    FROM products
                ''').fetchone()
                
                # Get expiry data
                today = datetime.now().date()
                expiry_data = cur.execute('''
                    SELECT 
                        COUNT(*) FILTER (WHERE date(expiry_date) < date(?)) as expired,
                        COUNT(*) FILTER (WHERE date(expiry_date) BETWEEN date(?) AND date(?, '+7 days')) as near_expiry,
                        COUNT(*) FILTER (WHERE date(expiry_date) BETWEEN date(?, '+8 days') AND date(?, '+30 days')) as expiring_soon
                    FROM products 
                    WHERE expiry_date IS NOT NULL
                ''', (today, today, today, today, today)).fetchone()
                
                # Get today's orders
                today_orders = cur.execute('''
                    SELECT COUNT(*) as orders, COALESCE(SUM(total), 0) as revenue
                    FROM orders 
                    WHERE DATE(created_at) = ?
                ''', (today,)).fetchone()
                
                # Get category breakdown
                categories = cur.execute('''
                    SELECT category, COUNT(*) as count, COALESCE(SUM(stock_quantity), 0) as stock
                    FROM products
                    GROUP BY category
                    ORDER BY count DESC
                ''').fetchall()
                
                return {
                    'timestamp': datetime.now().isoformat(),
                    'total_products': total_products,
                    'inventory': {
                        'out_of_stock': inventory_status[0] or 0,
                        'low_stock': inventory_status[1] or 0,
                        'in_stock': inventory_status[2] or 0,
                        'total_value': inventory_status[3] or 0
                    },
                    'expiry': {
                        'expired': expiry_data[0] or 0,
                        'near_expiry': expiry_data[1] or 0,
                        'expiring_soon': expiry_data[2] or 0
                    },
                    'orders': {
                        'today_orders': today_orders[0] or 0,
                        'today_revenue': today_orders[1] or 0
                    },
                    'categories': [{'name': cat[0], 'count': cat[1], 'stock': cat[2]} for cat in categories],
                    'system_status': {
                        'server_status': 'online',
                        'database_status': 'connected',
                        'active_sessions': self.connected_clients,
                        'data_freshness': 'real-time'
                    }
                }
        except Exception as e:
            print(f"Error getting real-time metrics: {e}")
            return self.get_fallback_data()
    
    def get_fallback_data(self):
        """Fallback data when database is not available"""
        return {
            'timestamp': datetime.now().isoformat(),
            'total_products': random.randint(8, 12),
            'inventory': {
                'out_of_stock': random.randint(0, 2),
                'low_stock': random.randint(1, 4),
                'in_stock': random.randint(5, 8),
                'total_value': random.randint(100000, 500000)
            },
            'expiry': {
                'expired': random.randint(0, 2),
                'near_expiry': random.randint(1, 3),
                'expiring_soon': random.randint(2, 5)
            },
            'orders': {
                'today_orders': random.randint(10, 50),
                'today_revenue': random.randint(5000, 25000)
            },
            'categories': [
                {'name': 'Electronics', 'count': random.randint(3, 6), 'stock': random.randint(50, 200)},
                {'name': 'Food', 'count': random.randint(4, 8), 'stock': random.randint(100, 500)},
                {'name': 'Sports', 'count': random.randint(2, 4), 'stock': random.randint(30, 100)},
                {'name': 'General', 'count': random.randint(2, 5), 'stock': random.randint(40, 150)}
            ],
            'system_status': {
                'server_status': 'online',
                'database_status': 'simulated',
                'active_sessions': self.connected_clients,
                'data_freshness': 'simulated'
            }
        }
    
    def simulate_real_time_updates(self):
        """Simulate real-time data changes"""
        while self.running:
            try:
                # Get current metrics
                metrics = self.get_real_time_metrics()
                
                # Add some realistic variations
                if metrics['system_status']['database_status'] == 'simulated':
                    # Simulate order changes
                    metrics['orders']['today_orders'] += random.randint(-2, 5)
                    metrics['orders']['today_revenue'] += random.randint(-500, 2000)
                    
                    # Simulate stock changes
                    for category in metrics['categories']:
                        category['stock'] += random.randint(-10, 20)
                    
                    # Simulate value changes
                    metrics['inventory']['total_value'] += random.randint(-5000, 10000)
                
                # Broadcast to all connected clients
                socketio.emit('real_time_update', metrics)
                
                # Also emit specific sales update for data visualizer
                if metrics['system_status']['database_status'] == 'connected':
                    socketio.emit('sales_update', {
                        'type': 'sales_update',
                        'timestamp': metrics['timestamp'],
                        'today_orders': metrics['orders']['today_orders'],
                        'today_revenue': metrics['orders']['today_revenue']
                    })
                
                # Update every 2 seconds for truly real-time feel
                time.sleep(2)
                
            except Exception as e:
                print(f"Error in real-time updates: {e}")
                time.sleep(5)

# Initialize data generator
data_generator = RealTimeDataGenerator()

@app.route('/')
def index():
    return render_template('realtime_government_dashboard.html')

@app.route('/api/realtime/metrics')
def get_metrics():
    """API endpoint for current metrics"""
    return jsonify(data_generator.get_real_time_metrics())

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    global connected_clients
    data_generator.connected_clients += 1
    print(f'Client connected. Total clients: {data_generator.connected_clients}')
    
    # Send current data immediately
    emit('initial_data', data_generator.get_real_time_metrics())
    
    # Start data generator if not running
    if not data_generator.running:
        data_generator.running = True
        thread = threading.Thread(target=data_generator.simulate_real_time_updates)
        thread.daemon = True
        thread.start()

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    data_generator.connected_clients -= 1
    print(f'Client disconnected. Total clients: {data_generator.connected_clients}')

@socketio.on('request_refresh')
def handle_refresh():
    """Handle manual refresh request"""
    emit('real_time_update', data_generator.get_real_time_metrics())

if __name__ == '__main__':
    print("Starting Real-Time Government Dashboard Server...")
    print("Open: http://localhost:8001")
    socketio.run(app, host='0.0.0.0', port=8001, debug=False)

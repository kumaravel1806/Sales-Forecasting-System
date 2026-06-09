import sqlite3

conn = sqlite3.connect('data/app.db')
cur = conn.cursor()

# Check today's total revenue
today_revenue = cur.execute('SELECT COALESCE(SUM(total), 0) FROM orders WHERE DATE(created_at) = DATE("now")').fetchone()[0]
print('Today revenue: {:.2f}'.format(today_revenue))

# Check order statuses
cur.execute('SELECT status, COUNT(*) FROM orders GROUP BY status')
statuses = cur.fetchall()
print('Order statuses:')
for status, count in statuses:
    print(f'  {status}: {count}')

conn.close()

import requests

BASE = "http://localhost:8000"

login = requests.post(f"{BASE}/api/auth/login", json={"email": "admin@example.com", "password": "password"})
print("login", login.status_code, login.text)

data = login.json()
access = data["data"]["access_token"]
headers = {
    "Authorization": f"Bearer {access}",
    "Content-Type": "application/json"
}

payload = {
    "name": "Test Milk",
    "price": 199.0,
    "category": "Food",
    "sku": "FOOD-DAIRY-006",
    "description": "nice",
    "expiry_date": "2025-11-15",
    "stock_quantity": 10,
    "min_stock_level": 5
}

resp = requests.post(f"{BASE}/api/products/", json=payload, headers=headers)
print("create", resp.status_code, resp.text)

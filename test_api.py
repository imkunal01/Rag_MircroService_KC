"""
test_api.py — Phase 1 smoke tests for the Products API.

Covers:
  1. GET  /api/products           → full list
  2. GET  /api/products?category= → category filter
  3. GET  /api/products/{id}      → single product
  4. GET  /api/products/INVALID   → 404
  5. POST /api/products           → create product (auto-id)
  6. POST /api/products           → duplicate id → 409
"""

import json
import urllib.error
import urllib.request

BASE = "http://localhost:8000/api"


def get(path: str) -> tuple[int, dict]:
    try:
        r = urllib.request.urlopen(f"{BASE}{path}")
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def post(path: str, body: dict) -> tuple[int, dict]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        r = urllib.request.urlopen(req)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def check(label: str, condition: bool, extra: str = ""):
    icon = "✅" if condition else "❌"
    print(f"  {icon}  {label}" + (f"  →  {extra}" if extra else ""))


print("\n" + "=" * 60)
print("  Phase 1 — Products API smoke tests")
print("=" * 60)

# ── 1. GET /products (full list) ─────────────────────────────────
print("\n[1] GET /api/products")
status, data = get("/products")
check("HTTP 200", status == 200, f"got {status}")
check("total == 15", data.get("total") == 15, str(data.get("total")))
check("count == 15", data.get("count") == 15, str(data.get("count")))
check("products is list", isinstance(data.get("products"), list))
check("first item has 'id'", "id" in data["products"][0])

# ── 2. GET /products?category=Electronics ────────────────────────
print("\n[2] GET /api/products?category=Electronics")
status, data = get("/products?category=Electronics")
check("HTTP 200", status == 200, f"got {status}")
check("all items are Electronics",
      all(p["category"] == "Electronics" for p in data["products"]),
      str(data.get("total")))

# ── 3. GET /products?tag=ergonomic ───────────────────────────────
print("\n[3] GET /api/products?tag=ergonomic")
status, data = get("/products?tag=ergonomic")
check("HTTP 200", status == 200)
check("count >= 1", data.get("count", 0) >= 1, str(data.get("count")))

# ── 4. GET /products?min_price=100&max_price=200 ─────────────────
print("\n[4] GET /api/products?min_price=100&max_price=200")
status, data = get("/products?min_price=100&max_price=200")
check("HTTP 200", status == 200)
check("all prices in [100, 200]",
      all(100 <= p["price"] <= 200 for p in data["products"]),
      f'{data.get("count")} items')

# ── 5. GET /products/{id} ────────────────────────────────────────
print("\n[5] GET /api/products/P001")
status, data = get("/products/P001")
check("HTTP 200", status == 200, f"got {status}")
check("id == P001", data.get("id") == "P001", data.get("id"))
check("has name/price/tags",
      all(k in data for k in ("name", "price", "tags")))

# ── 6. GET /products/INVALID → 404 ───────────────────────────────
print("\n[6] GET /api/products/INVALID")
status, data = get("/products/INVALID")
check("HTTP 404", status == 404, f"got {status}")

# ── 7. POST /products (auto-id) ───────────────────────────────────
print("\n[7] POST /api/products  (auto-id)")
status, data = post("/products", {
    "name": "Smart LED Bulb",
    "category": "Home & Office",
    "price": 24.99,
    "stock": 300,
    "rating": 4.1,
    "description": "Wi-Fi enabled colour-changing bulb, 16M colours, works with Alexa and Google Home.",
    "tags": ["smart-home", "lighting", "wifi"]
})
check("HTTP 201", status == 201, f"got {status}")
check("auto-generated id starts with P", data.get("id", "").startswith("P"), data.get("id"))
print(f"     New product id → {data.get('id')}")

# ── 8. POST /products with explicit id ───────────────────────────
print("\n[8] POST /api/products  (explicit id=P099)")
status, data = post("/products", {
    "id": "P099",
    "name": "Test Product",
    "category": "Test",
    "price": 9.99,
    "stock": 1,
    "rating": 3.0,
    "description": "Throwaway test product.",
    "tags": ["test"]
})
check("HTTP 201", status == 201, f"got {status}")
check("id == P099", data.get("id") == "P099", data.get("id"))

# ── 9. POST duplicate → 409 ───────────────────────────────────────
print("\n[9] POST /api/products  (duplicate P099 → 409)")
status, data = post("/products", {
    "id": "P099",
    "name": "Duplicate",
    "category": "Test",
    "price": 1.00,
    "stock": 0,
    "rating": 0.0,
    "description": "Should fail.",
    "tags": []
})
check("HTTP 409 conflict", status == 409, f"got {status}")

# ── 10. Verify total grew ─────────────────────────────────────────
print("\n[10] GET /api/products  (total should be 17 after 2 inserts)")
status, data = get("/products")
check("HTTP 200", status == 200)
check("total == 17", data.get("total") == 17, str(data.get("total")))

# ── 11. POST /recommend (semantic search foundation) ─────────────
print("\n[11] POST /api/recommend  (query='good camera phone')")
status, data = post("/recommend", {
    "query": "good camera phone",
    "limit": 5
})
check("HTTP 200", status == 200, f"got {status}")
check("has parsed_filters", "parsed_filters" in data)
check("count >= 1", data.get("count", 0) >= 1, str(data.get("count")))
check("products is list", isinstance(data.get("products"), list))

# ── 12. POST /recommend hybrid query (filter + semantic) ─────────
print("\n[12] POST /api/recommend  (query='gaming phone under 20k')")
status, data = post("/recommend", {
    "query": "gaming phone under 20k",
    "limit": 5
})
check("HTTP 200", status == 200, f"got {status}")
parsed_filters = data.get("parsed_filters", {})
check("category parsed as Electronics", parsed_filters.get("category") == "Electronics", str(parsed_filters))
check("max_price parsed as 20000", parsed_filters.get("max_price") == 20000.0, str(parsed_filters))
check("count >= 1", data.get("count", 0) >= 1, str(data.get("count")))

print("\n" + "=" * 60 + "\n")

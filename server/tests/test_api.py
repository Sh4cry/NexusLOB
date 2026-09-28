import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "engine_backend" in data

def test_place_and_cancel_order():
    # Place Limit Buy Order
    order_payload = {
        "side": "BUY",
        "order_type": "LIMIT",
        "price": 95.50,
        "quantity": 25
    }
    res = client.post("/api/v1/orders", json=order_payload)
    assert res.status_code == 200
    data = res.json()
    order_id = data["id"]
    assert order_id > 0
    assert data["status"] in ["PLACED", "FILLED"]

    # Cancel order
    cancel_res = client.delete(f"/api/v1/orders/{order_id}")
    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()
    assert cancel_data["status"] == "CANCELLED"

def test_get_l2_depth():
    res = client.get("/api/v1/book/depth?depth=10")
    assert res.status_code == 200
    data = res.json()
    assert "bids" in data
    assert "asks" in data
    assert data["symbol"] == "APEX/USD"

def test_stress_test_endpoint():
    res = client.post("/api/v1/stress-test", json={"order_count": 1000})
    assert res.status_code == 200
    data = res.json()
    assert data["total_orders"] == 1000
    assert data["throughput_ops_sec"] > 0
    assert data["p50_us"] >= 0

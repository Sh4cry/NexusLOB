import unittest
import sys
import os

# Add server directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

class TestGateway(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        res = self.client.get("/api/v1/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("engine_backend", data)
        print("\n[TEST] Health check endpoint: PASSED")

    def test_place_and_cancel_order(self):
        order_payload = {
            "side": "BUY",
            "order_type": "LIMIT",
            "price": 95.50,
            "quantity": 25
        }
        res = self.client.post("/api/v1/orders", json=order_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        order_id = data["id"]
        self.assertGreater(order_id, 0)
        self.assertIn(data["status"], ["PLACED", "FILLED"])

        cancel_res = self.client.delete(f"/api/v1/orders/{order_id}")
        self.assertEqual(cancel_res.status_code, 200)
        self.assertEqual(cancel_res.json()["status"], "CANCELLED")
        print("[TEST] Place & cancel order: PASSED")

    def test_get_l2_depth(self):
        res = self.client.get("/api/v1/book/depth?depth=10")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("bids", data)
        self.assertIn("asks", data)
        self.assertEqual(data["symbol"], "APEX/USD")
        print("[TEST] L2 depth query: PASSED")

    def test_stress_test_endpoint(self):
        res = self.client.post("/api/v1/stress-test", json={"order_count": 1000})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_orders"], 1000)
        self.assertGreater(data["throughput_ops_sec"], 0)
        print(f"[TEST] Stress test API (1,000 orders): PASSED -> {data['throughput_ops_sec']:.0f} ops/sec, p50={data['p50_us']}µs")

if __name__ == "__main__":
    unittest.main()

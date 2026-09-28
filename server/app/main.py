import asyncio
import time
import json
from typing import Set, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.engine_bridge import EngineBridge
from app.market_maker import MarkovMarketMaker
from app.schemas import (
    OrderRequest,
    OrderResponse,
    L2SnapshotModel,
    StressTestRequest,
    StressTestResult,
)

# Global Engine & Market Maker instances
engine = EngineBridge()
market_maker = MarkovMarketMaker(engine, base_price=100.0, tick_size=0.05)

# Recent trade buffer (last 50 trades)
recent_trades: List[Dict[str, Any]] = []

def handle_trade(trade: Dict[str, Any]):
    recent_trades.insert(0, trade)
    if len(recent_trades) > 100:
        recent_trades.pop()

market_maker.register_trade_callback(handle_trade)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast_json(self, data: dict):
        if not self.active_connections:
            return
        dead_connections = set()
        for conn in self.active_connections:
            try:
                await conn.send_json(data)
            except Exception:
                dead_connections.add(conn)
        for dead in dead_connections:
            self.active_connections.discard(dead)

manager = ConnectionManager()

# Background broadcast loop (20-30 updates/sec)
async def market_data_broadcaster():
    while True:
        try:
            if manager.active_connections:
                l2 = engine.get_l2_depth(depth=15)
                payload = {
                    "type": "SNAPSHOT",
                    "data": l2,
                    "recent_trades": recent_trades[:25],
                    "order_count": engine.order_count(),
                    "sim_state": {
                        "running": market_maker.is_running,
                        "markov_state": market_maker.current_state,
                        "state_name": ["Low Depth", "Medium Depth", "High Depth"][market_maker.current_state]
                    },
                    "backend": "C++20 (Low-Latency)" if engine.is_cpp_backend else "Python",
                }
                await manager.broadcast_json(payload)
        except Exception as e:
            print(f"[Broadcaster Error] {e}")
        await asyncio.sleep(0.05) # 50ms = 20 Hz update rate

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Seed initial order book and start simulator
    await market_maker.initialize_book()
    market_maker.start(interval_ms=60)
    broadcaster_task = asyncio.create_task(market_data_broadcaster())
    yield
    # Shutdown
    market_maker.stop()
    broadcaster_task.cancel()

app = FastAPI(
    title="NexusLOB Real-Time Matching Engine Gateway",
    description="Ultra-low latency institutional limit order book matching engine & market data gateway",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/health")
def get_health():
    return {
        "status": "healthy",
        "engine_backend": "C++20 Native" if engine.is_cpp_backend else "Python Fallback",
        "orders_in_book": engine.order_count(),
        "timestamp_ns": time.time_ns(),
    }

@app.get("/api/v1/book/depth", response_model=L2SnapshotModel)
def get_depth(depth: int = Query(15, ge=1, le=50)):
    return engine.get_l2_depth(depth=depth)

@app.post("/api/v1/orders", response_model=OrderResponse)
def place_order(order: OrderRequest):
    start_ns = time.time_ns()
    order_id, trades = engine.add_order(
        order_id=order.id,
        side=order.side.value,
        order_type=order.order_type.value,
        price_dollars=order.price,
        quantity=order.quantity,
    )
    for tr in trades:
        handle_trade(tr)

    return OrderResponse(
        id=order_id,
        status="FILLED" if trades else "PLACED",
        trades_count=len(trades),
        trades=trades,
    )

@app.delete("/api/v1/orders/{order_id}")
def cancel_order(order_id: int):
    success = engine.cancel_order(order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found or already filled/cancelled")
    return {"order_id": order_id, "status": "CANCELLED"}

@app.post("/api/v1/simulation/start")
def start_simulation(speed_ms: int = 60):
    market_maker.start(interval_ms=speed_ms)
    return {"status": "started", "speed_ms": speed_ms}

@app.post("/api/v1/simulation/stop")
def stop_simulation():
    market_maker.stop()
    return {"status": "stopped"}

@app.post("/api/v1/stress-test", response_model=StressTestResult)
def run_stress_test(req: StressTestRequest):
    count = req.order_count
    import numpy as np

    latencies_us = []
    total_trades = 0
    start_time = time.perf_counter()

    for i in range(1, count + 1):
        side = "BUY" if (i % 2 == 0) else "SELL"
        # 70% Limit, 30% Crossing
        price = 100.0 + (i % 20) * 0.05
        t0 = time.perf_counter_ns()
        _, trades = engine.add_order(
            order_id=10000000 + i,
            side=side,
            order_type="LIMIT",
            price_dollars=price,
            quantity=10,
        )
        t1 = time.perf_counter_ns()
        latencies_us.append((t1 - t0) / 1000.0)
        total_trades += len(trades)

    elapsed = time.perf_counter() - start_time
    latencies_us.sort()

    return StressTestResult(
        total_orders=count,
        total_trades=total_trades,
        elapsed_seconds=round(elapsed, 4),
        throughput_ops_sec=round(count / elapsed, 1),
        p50_us=round(float(np.percentile(latencies_us, 50)), 2),
        p95_us=round(float(np.percentile(latencies_us, 95)), 2),
        p99_us=round(float(np.percentile(latencies_us, 99)), 2),
    )

@app.websocket("/ws/market-data")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Client can send control messages or keepalive pings
            text = await websocket.receive_text()
            data = json.loads(text)
            if data.get("action") == "PING":
                await websocket.send_json({"type": "PONG"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

# Serve web build if dist exists
dist_dir = os.path.join(os.path.dirname(__file__), "..", "..", "web", "dist")
if os.path.exists(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")

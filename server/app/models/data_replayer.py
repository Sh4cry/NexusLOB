import os
import csv
import time
import asyncio
from typing import List, Dict, Any, Optional, Callable
from app.engine_bridge import EngineBridge

class HistoricalDataReplayer:
    """
    Replays historical market tick data (CSV format) directly through
    the NexusLOB matching engine.
    Supports any dataset with columns: [timestamp, side, price, quantity, order_type]
    """

    def __init__(self, engine: EngineBridge):
        self.engine = engine
        self.is_running: bool = False
        self.current_index: int = 0
        self.ticks: List[Dict[str, Any]] = []
        self.on_trade_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.file_path: Optional[str] = None

    def register_trade_callback(self, cb: Callable[[Dict[str, Any]], None]):
        self.on_trade_callbacks.append(cb)

    def load_csv(self, file_path: str) -> int:
        """Load tick data from any CSV file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dataset not found: {file_path}")

        self.file_path = file_path
        self.ticks.clear()
        self.current_index = 0

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Support multiple header variations
                side = row.get("side", row.get("Side", "BUY")).upper()
                price = float(row.get("price", row.get("Price", 100.0)))
                qty = int(float(row.get("quantity", row.get("qty", row.get("Size", 10)))))
                order_type = row.get("order_type", row.get("type", "LIMIT")).upper()
                ts = int(float(row.get("timestamp", row.get("time", time.time_ns()))))

                self.ticks.append({
                    "side": side,
                    "price": price,
                    "quantity": qty,
                    "order_type": order_type,
                    "timestamp": ts,
                })

        print(f"[DataReplayer] Loaded {len(self.ticks)} ticks from {file_path}")
        return len(self.ticks)

    async def step(self):
        """Execute one historical tick against the matching engine."""
        if not self.ticks:
            return

        tick = self.ticks[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.ticks)

        order_id, trades = self.engine.add_order(
            order_id=None,
            side=tick["side"],
            order_type=tick["order_type"],
            price_dollars=tick["price"],
            quantity=tick["quantity"],
        )

        for tr in trades:
            for cb in self.on_trade_callbacks:
                cb(tr)

    def get_progress(self) -> Dict[str, Any]:
        return {
            "model_name": "Historical Tick Replayer",
            "file": os.path.basename(self.file_path) if self.file_path else "None",
            "current_index": self.current_index,
            "total_ticks": len(self.ticks),
            "progress_pct": round((self.current_index / max(len(self.ticks), 1)) * 100, 1),
        }

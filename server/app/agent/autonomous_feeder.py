import asyncio
import time
from typing import Dict, Any, Optional
from app.engine_bridge import EngineBridge
from app.agent.screen_reader import ScreenReaderAgent
from app.agent.web_streamer import WebStreamerAgent

class AutonomousFeederAgent:
    """
    Background Autonomous Agent.
    Continuously monitors the screen (via Windows UI Automation) or a live webpage feed
    without taking screenshots, and automatically feeds the extracted market data into
    the NexusLOB matching engine in real time.
    """

    def __init__(self, engine: EngineBridge):
        self.engine = engine
        self.screen_reader = ScreenReaderAgent()
        self.web_streamer = WebStreamerAgent()

        self.is_running: bool = False
        self.mode: str = "WEB_FEED" # "SCREEN_UIA" or "WEB_FEED"
        self.web_symbol: str = "BTCUSDT"
        self.interval_sec: float = 1.0
        self._task: Optional[asyncio.Task] = None

        self.last_extraction: Dict[str, Any] = {
            "status": "idle",
            "source": "None",
            "symbol": "None",
            "mid_price": 0.0,
            "timestamp": 0
        }

    async def poll_once(self) -> Dict[str, Any]:
        """Reads data from the selected source and feeds it directly into the C++ matching engine."""
        data = None
        if self.mode == "SCREEN_UIA":
            data = self.screen_reader.scan_screen_now()
        else:
            try:
                data = await self.web_streamer.fetch_binance_depth(self.web_symbol, limit=10)
            except Exception:
                try:
                    data = await self.web_streamer.fetch_yahoo_quote("AAPL")
                except Exception as e:
                    data = {"error": str(e), "source": "Failed", "mid_price": 100.0, "symbol": "ERROR"}

        if not data or "error" in data:
            return self.last_extraction

        mid_price = data.get("mid_price", 100.0)
        symbol = data.get("symbol", "LIVE")

        # Inject into C++ Matching Engine
        self.engine.clear()

        # Seed extracted bids
        for b in data.get("bids", [])[:8]:
            p = b["price"]
            q = max(5, b["quantity"])
            self.engine.add_order(None, "BUY", "LIMIT", p, q)

        # Seed extracted asks
        for a in data.get("asks", [])[:8]:
            p = a["price"]
            q = max(5, a["quantity"])
            self.engine.add_order(None, "SELL", "LIMIT", p, q)

        self.last_extraction = {
            "status": "active",
            "source": data.get("source", self.mode),
            "symbol": symbol,
            "mid_price": mid_price,
            "bids_count": len(data.get("bids", [])),
            "asks_count": len(data.get("asks", [])),
            "timestamp": time.time_ns(),
        }

        return self.last_extraction

    async def _loop(self):
        self.is_running = True
        while self.is_running:
            try:
                await self.poll_once()
            except Exception as e:
                print(f"[AutonomousFeeder] Error in loop: {e}")
            await asyncio.sleep(self.interval_sec)

    def start(self, mode: str = "WEB_FEED", symbol: str = "BTCUSDT", interval_sec: float = 1.0):
        if not self.is_running:
            self.mode = mode
            self.web_symbol = symbol
            self.interval_sec = interval_sec
            self.is_running = True
            self._task = asyncio.create_task(self._loop())
            print(f"[AutonomousFeeder] Started background agent in {mode} mode ({symbol})")

    def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            self._task = None
        print("[AutonomousFeeder] Stopped background agent")

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "mode": self.mode,
            "symbol": self.web_symbol,
            "interval_sec": self.interval_sec,
            "last_extraction": self.last_extraction,
        }

import asyncio
import random
import time
from typing import List, Optional, Callable, Dict, Any
from app.engine_bridge import EngineBridge

class MarkovMarketMaker:
    """
    Quantitative High-Frequency Market Maker Bot.
    Uses a 3-State Discrete-Time Markov Chain to model queue depth microstructures:
      - State 0: Low Depth / High Volatility (Wide spreads, thin liquidity)
      - State 1: Medium Depth / Normal Flow (Balanced spreads, standard liquidity)
      - State 2: High Depth / Mean-Reverting (Tight spreads, deep liquidity walls)
    """

    TRANSITION_MATRIX = [
        # From Low: [To Low, To Med, To High]
        [0.65, 0.30, 0.05],
        # From Med: [To Low, To Med, To High]
        [0.20, 0.60, 0.20],
        # From High: [To Low, To Med, To High]
        [0.05, 0.35, 0.60],
    ]

    STATE_PARAMS = {
        0: {"depth_levels": 5, "min_qty": 5, "max_qty": 20, "spread_ticks": 4, "cancel_prob": 0.45},
        1: {"depth_levels": 10, "min_qty": 15, "max_qty": 50, "spread_ticks": 2, "cancel_prob": 0.25},
        2: {"depth_levels": 15, "min_qty": 30, "max_qty": 100, "spread_ticks": 1, "cancel_prob": 0.10},
    }

    def __init__(
        self,
        engine: EngineBridge,
        symbol: str = "APEX/USD",
        base_price: float = 100.0,
        tick_size: float = 0.05,
    ):
        self.engine = engine
        self.symbol = symbol
        self.base_price = base_price
        self.tick_size = tick_size

        self.current_state = 1 # Start at Medium Depth
        self.mid_price = base_price
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.active_order_ids: List[int] = []

        # Trade callbacks (e.g. for WebSocket broadcasts)
        self.on_trade_callbacks: List[Callable[[Dict[str, Any]], None]] = []

    def register_trade_callback(self, cb: Callable[[Dict[str, Any]], None]):
        self.on_trade_callbacks.append(cb)

    def _transition_state(self):
        probs = self.TRANSITION_MATRIX[self.current_state]
        r = random.random()
        cumulative = 0.0
        for next_st, p in enumerate(probs):
            cumulative += p
            if r <= cumulative:
                self.current_state = next_st
                break

    async def initialize_book(self):
        """Seed initial liquidity around mid-price."""
        self.engine.clear()
        self.active_order_ids.clear()

        # Seed 10 bid levels and 10 ask levels
        for level in range(1, 12):
            bid_p = round(self.mid_price - (level * self.tick_size), 2)
            ask_p = round(self.mid_price + (level * self.tick_size), 2)
            qty = random.randint(20, 80)

            bid_id, _ = self.engine.add_order(None, "BUY", "LIMIT", bid_p, qty)
            ask_id, _ = self.engine.add_order(None, "SELL", "LIMIT", ask_p, qty)
            self.active_order_ids.extend([bid_id, ask_id])

    async def step(self):
        """Execute one simulation cycle."""
        # 1. Update Markov state
        if random.random() < 0.20:
            self._transition_state()

        params = self.STATE_PARAMS[self.current_state]

        # 2. Potential cancellation of stale orders
        if self.active_order_ids and random.random() < params["cancel_prob"]:
            cancel_idx = random.randint(0, len(self.active_order_ids) - 1)
            cancel_id = self.active_order_ids.pop(cancel_idx)
            self.engine.cancel_order(cancel_id)

        # 3. New passive quote arrival
        spread_half = (params["spread_ticks"] * self.tick_size) / 2.0
        side = "BUY" if random.random() < 0.5 else "SELL"
        offset_levels = random.randint(0, params["depth_levels"])
        qty = random.randint(params["min_qty"], params["max_qty"])

        if side == "BUY":
            price = round(self.mid_price - spread_half - (offset_levels * self.tick_size), 2)
        else:
            price = round(self.mid_price + spread_half + (offset_levels * self.tick_size), 2)

        order_id, trades = self.engine.add_order(None, side, "LIMIT", price, qty)
        self.active_order_ids.append(order_id)

        # Notify any trades
        for tr in trades:
            for cb in self.on_trade_callbacks:
                cb(tr)

        # 4. Occasional aggressive market taker flow (15% chance)
        if random.random() < 0.15:
            taker_side = "BUY" if random.random() < 0.5 else "SELL"
            taker_qty = random.randint(5, 30)
            best_bid, best_ask = self.engine.get_bbo()
            exec_price = (best_ask if taker_side == "BUY" else best_bid) or self.mid_price

            _, taker_trades = self.engine.add_order(None, taker_side, "MARKET", exec_price, taker_qty)
            for tr in taker_trades:
                for cb in self.on_trade_callbacks:
                    cb(tr)

        # 5. Drift mid-price based on order book BBO
        best_bid, best_ask = self.engine.get_bbo()
        if best_bid and best_ask:
            self.mid_price = round((best_bid + best_ask) / 2.0, 2)
        else:
            # Re-seed if book emptied out
            await self.initialize_book()

    async def run_loop(self, interval_ms: int = 50):
        self.is_running = True
        await self.initialize_book()
        try:
            while self.is_running:
                await self.step()
                await asyncio.sleep(interval_ms / 1000.0)
        except asyncio.CancelledError:
            self.is_running = False

    def start(self, interval_ms: int = 50):
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.create_task(self.run_loop(interval_ms))

    def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            self._task = None

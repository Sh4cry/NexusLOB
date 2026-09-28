import math
import time
import random
from collections import deque
from typing import List, Dict, Any, Optional, Callable
from app.engine_bridge import EngineBridge

class AvellanedaStoikovModel:
    """
    Avellaneda-Stoikov (2008) Optimal Market Making Model.
    Dynamically adapts quotes to:
      1. Asset Volatility (sigma) - dynamically computed from rolling price history.
      2. Market Maker Inventory (q) - skews reservation price to mean-revert inventory.
      3. Order Arrival Intensity (kappa) - adapts half-spread to fill probability.
    """

    def __init__(
        self,
        engine: EngineBridge,
        gamma: float = 0.1,       # Risk aversion parameter
        kappa: float = 1.5,       # Order arrival liquidity intensity
        tick_size: float = 0.05,
        max_inventory: int = 150, # Inventory constraint
        rolling_window: int = 30  # Window for rolling volatility
    ):
        self.engine = engine
        self.gamma = gamma
        self.kappa = kappa
        self.tick_size = tick_size
        self.max_inventory = max_inventory
        self.rolling_window = rolling_window

        # State tracking
        self.inventory: int = 0
        self.cash: float = 0.0
        self.realized_pnl: float = 0.0
        self.mid_price: float = 100.0
        self.volatility: float = 0.02 # Initial volatility estimate

        self.price_history = deque(maxlen=rolling_window)
        self.active_quote_ids: List[int] = []
        self.on_trade_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.is_running: bool = False

    def register_trade_callback(self, cb: Callable[[Dict[str, Any]], None]):
        self.on_trade_callbacks.append(cb)

    def update_volatility(self, new_mid: float):
        """Calculates rolling standard deviation of percentage returns to adapt to any market regime."""
        self.price_history.append(new_mid)
        if len(self.price_history) >= 5:
            returns = [
                (self.price_history[i] - self.price_history[i - 1]) / self.price_history[i - 1]
                for i in range(1, len(self.price_history))
            ]
            mean_ret = sum(returns) / len(returns)
            variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
            # Annualized/scaled volatility floor
            self.volatility = max(0.005, math.sqrt(variance) * 10.0)

    def calculate_reservation_price(self) -> float:
        """
        r(s, q) = s - q * gamma * sigma^2
        When inventory q > 0 (long), reservation price drops below mid to encourage sales.
        When inventory q < 0 (short), reservation price rises above mid to encourage buys.
        """
        return self.mid_price - (self.inventory * self.gamma * (self.volatility ** 2))

    def calculate_optimal_spread(self) -> float:
        """
        Optimal half-spread delta:
        delta = (gamma * sigma^2) + (2 / gamma) * ln(1 + gamma / kappa)
        """
        reg_term = (2.0 / self.gamma) * math.log(1.0 + (self.gamma / self.kappa))
        vol_term = self.gamma * (self.volatility ** 2)
        spread = vol_term + (reg_term * 0.02) # Scaled to dollar tick space
        return max(self.tick_size * 2, spread)

    async def initialize_book(self):
        """Seed initial two-sided depth."""
        self.engine.clear()
        self.active_quote_ids.clear()
        self.price_history.clear()

        # Seed passive background liquidity
        for i in range(1, 10):
            p_bid = round(self.mid_price - (i * self.tick_size), 2)
            p_ask = round(self.mid_price + (i * self.tick_size), 2)
            b_id, _ = self.engine.add_order(None, "BUY", "LIMIT", p_bid, 25)
            a_id, _ = self.engine.add_order(None, "SELL", "LIMIT", p_ask, 25)
            self.active_quote_ids.extend([b_id, a_id])

    async def step(self):
        """Execute one Avellaneda-Stoikov quoting cycle."""
        # 1. Update mid-price from book
        bbo_bid, bbo_ask = self.engine.get_bbo()
        if bbo_bid and bbo_ask:
            self.mid_price = round((bbo_bid + bbo_ask) / 2.0, 2)
        self.update_volatility(self.mid_price)

        # 2. Cancel previous active quotes
        for q_id in self.active_quote_ids:
            self.engine.cancel_order(q_id)
        self.active_quote_ids.clear()

        # 3. Compute Avellaneda-Stoikov reservation price & optimal spread
        r_price = self.calculate_reservation_price()
        half_spread = self.calculate_optimal_spread() / 2.0

        target_bid = round(r_price - half_spread, 2)
        target_ask = round(r_price + half_spread, 2)

        # Ensure quotes don't cross and align with tick size
        if target_ask <= target_bid:
            target_ask = round(target_bid + self.tick_size, 2)

        # 4. Quoting size dynamic with inventory limits
        bid_qty = max(5, int(30 * (1 - self.inventory / self.max_inventory))) if self.inventory < self.max_inventory else 0
        ask_qty = max(5, int(30 * (1 + self.inventory / self.max_inventory))) if self.inventory > -self.max_inventory else 0

        # Post AS optimal quotes
        if bid_qty > 0:
            bid_id, trades = self.engine.add_order(None, "BUY", "LIMIT", target_bid, bid_qty)
            self.active_quote_ids.append(bid_id)
            self._process_trades(trades, is_buy=True)

        if ask_qty > 0:
            ask_id, trades = self.engine.add_order(None, "SELL", "LIMIT", target_ask, ask_qty)
            self.active_quote_ids.append(ask_id)
            self._process_trades(trades, is_buy=False)

        # 5. Simulate stochastic external market order arrivals
        if random.random() < 0.35:
            taker_side = "BUY" if random.random() < 0.5 else "SELL"
            taker_qty = random.randint(10, 40)
            best_bid, best_ask = self.engine.get_bbo()
            exec_price = (best_ask if taker_side == "BUY" else best_bid) or self.mid_price

            _, ext_trades = self.engine.add_order(None, taker_side, "MARKET", exec_price, taker_qty)
            for tr in ext_trades:
                for cb in self.on_trade_callbacks:
                    cb(tr)

    def _process_trades(self, trades: List[Dict[str, Any]], is_buy: bool):
        for tr in trades:
            qty = tr["quantity"]
            price = tr["price"]
            if is_buy:
                self.inventory += qty
                self.cash -= qty * price
            else:
                self.inventory -= qty
                self.cash += qty * price

            for cb in self.on_trade_callbacks:
                cb(tr)

    def get_metrics(self) -> Dict[str, Any]:
        """Return current quantitative performance & inventory metrics."""
        unrealized = self.inventory * self.mid_price
        total_pnl = self.cash + unrealized
        return {
            "model_name": "Avellaneda-Stoikov (Adaptive)",
            "inventory": self.inventory,
            "mid_price": self.mid_price,
            "reservation_price": round(self.calculate_reservation_price(), 2),
            "volatility": round(self.volatility, 4),
            "optimal_spread": round(self.calculate_optimal_spread(), 2),
            "cash": round(self.cash, 2),
            "total_pnl": round(total_pnl, 2),
        }

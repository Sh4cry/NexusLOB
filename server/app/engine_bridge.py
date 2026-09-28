import os
import sys
import ctypes
from typing import List, Tuple, Optional, Dict, Any
import time

class CTrade(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("makerOrderId", ctypes.c_uint64),
        ("takerOrderId", ctypes.c_uint64),
        ("takerSide", ctypes.c_uint8),
        ("price", ctypes.c_uint32),
        ("quantity", ctypes.c_uint32),
        ("timestamp", ctypes.c_uint64),
    ]

class CLevel(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("price", ctypes.c_uint32),
        ("quantity", ctypes.c_uint32),
        ("orderCount", ctypes.c_uint32),
    ]

class EngineBridge:
    def __init__(self, dll_path: Optional[str] = None):
        self.is_cpp_backend = False
        self._handle = None
        self._next_order_id = 1000

        # Try to locate the compiled C++ DLL
        search_paths = [
            dll_path,
            os.path.join(os.path.dirname(__file__), "..", "..", "engine", "nexus_engine.dll"),
            os.path.join(os.path.dirname(__file__), "..", "..", "engine", "build", "nexus_engine.dll"),
            os.path.join(os.path.dirname(__file__), "..", "..", "engine", "libnexus_engine.so"),
            os.path.join(os.path.dirname(__file__), "..", "..", "engine", "libnexus_engine.dylib"),
        ]

        lib_file = None
        for p in search_paths:
            if p and os.path.exists(p):
                lib_file = os.path.abspath(p)
                break

        if lib_file:
            try:
                self.lib = ctypes.CDLL(lib_file)
                self._setup_ffi()
                self._handle = self.lib.nexus_create_book(200000)
                self.is_cpp_backend = True
                print(f"[EngineBridge] Successfully loaded C++ Low-Latency Engine: {lib_file}")
            except Exception as e:
                print(f"[EngineBridge] Failed to load DLL ({e}), using Python fallback.")
                self._init_python_fallback()
        else:
            print("[EngineBridge] C++ binary not found, using Python fallback.")
            self._init_python_fallback()

    def _setup_ffi(self):
        self.lib.nexus_create_book.argtypes = [ctypes.c_uint32]
        self.lib.nexus_create_book.restype = ctypes.c_void_p

        self.lib.nexus_destroy_book.argtypes = [ctypes.c_void_p]
        self.lib.nexus_destroy_book.restype = None

        self.lib.nexus_clear_book.argtypes = [ctypes.c_void_p]
        self.lib.nexus_clear_book.restype = None

        self.lib.nexus_add_order.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint64,
            ctypes.c_uint8,
            ctypes.c_uint8,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint64,
            ctypes.POINTER(CTrade),
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
        ]
        self.lib.nexus_add_order.restype = ctypes.c_int

        self.lib.nexus_cancel_order.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
        self.lib.nexus_cancel_order.restype = ctypes.c_bool

        self.lib.nexus_modify_order.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint32]
        self.lib.nexus_modify_order.restype = ctypes.c_bool

        self.lib.nexus_has_order.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
        self.lib.nexus_has_order.restype = ctypes.c_bool

        self.lib.nexus_order_count.argtypes = [ctypes.c_void_p]
        self.lib.nexus_order_count.restype = ctypes.c_uint32

        self.lib.nexus_get_bbo.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
        ]
        self.lib.nexus_get_bbo.restype = ctypes.c_bool

        self.lib.nexus_get_l2_depth.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(CLevel),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(CLevel),
            ctypes.POINTER(ctypes.c_uint32),
        ]
        self.lib.nexus_get_l2_depth.restype = None

    def __del__(self):
        if self.is_cpp_backend and self._handle and hasattr(self, 'lib'):
            self.lib.nexus_destroy_book(self._handle)
            self._handle = None

    def get_next_order_id(self) -> int:
        self._next_order_id += 1
        return self._next_order_id

    def add_order(
        self,
        order_id: Optional[int],
        side: str,
        order_type: str,
        price_dollars: float,
        quantity: int,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        if order_id is None or order_id <= 0:
            order_id = self.get_next_order_id()

        # Fixed point price in cents (e.g. $100.50 -> 10050)
        price_cents = int(round(price_dollars * 100))
        side_code = 0 if side.upper() == "BUY" else 1

        type_map = {"LIMIT": 0, "MARKET": 1, "IOC": 2, "FOK": 3}
        type_code = type_map.get(order_type.upper(), 0)

        if self.is_cpp_backend:
            max_trades = 64
            trades_arr = (CTrade * max_trades)()
            num_trades = ctypes.c_uint32(0)
            ts = time.time_ns()

            res = self.lib.nexus_add_order(
                self._handle,
                ctypes.c_uint64(order_id),
                ctypes.c_uint8(side_code),
                ctypes.c_uint8(type_code),
                ctypes.c_uint32(price_cents),
                ctypes.c_uint32(quantity),
                ctypes.c_uint64(ts),
                trades_arr,
                ctypes.c_uint32(max_trades),
                ctypes.byref(num_trades),
            )

            trades_list = []
            for i in range(num_trades.value):
                tr = trades_arr[i]
                trades_list.append({
                    "maker_order_id": tr.makerOrderId,
                    "taker_order_id": tr.takerOrderId,
                    "taker_side": "BUY" if tr.takerSide == 0 else "SELL",
                    "price": round(tr.price / 100.0, 2),
                    "quantity": tr.quantity,
                    "timestamp_ns": tr.timestamp,
                })
            return order_id, trades_list

        else:
            return self._py_add_order(order_id, side_code, type_code, price_cents, quantity)

    def cancel_order(self, order_id: int) -> bool:
        if self.is_cpp_backend:
            return bool(self.lib.nexus_cancel_order(self._handle, ctypes.c_uint64(order_id)))
        return self._py_cancel_order(order_id)

    def get_bbo(self) -> Tuple[Optional[float], Optional[float]]:
        if self.is_cpp_backend:
            bid_c = ctypes.c_uint32(0)
            ask_c = ctypes.c_uint32(0)
            has_bbo = self.lib.nexus_get_bbo(self._handle, ctypes.byref(bid_c), ctypes.byref(ask_c))
            best_bid = round(bid_c.value / 100.0, 2) if bid_c.value > 0 else None
            best_ask = round(ask_c.value / 100.0, 2) if ask_c.value > 0 else None
            return best_bid, best_ask
        return self._py_get_bbo()

    def get_l2_depth(self, depth: int = 15) -> Dict[str, Any]:
        if self.is_cpp_backend:
            bids_arr = (CLevel * depth)()
            asks_arr = (CLevel * depth)()
            num_bids = ctypes.c_uint32(0)
            num_asks = ctypes.c_uint32(0)

            self.lib.nexus_get_l2_depth(
                self._handle,
                ctypes.c_uint32(depth),
                bids_arr,
                ctypes.byref(num_bids),
                asks_arr,
                ctypes.byref(num_asks),
            )

            bids = [
                {
                    "price": round(bids_arr[i].price / 100.0, 2),
                    "quantity": bids_arr[i].quantity,
                    "order_count": bids_arr[i].orderCount,
                }
                for i in range(num_bids.value)
            ]
            asks = [
                {
                    "price": round(asks_arr[i].price / 100.0, 2),
                    "quantity": asks_arr[i].quantity,
                    "order_count": asks_arr[i].orderCount,
                }
                for i in range(num_asks.value)
            ]

            best_bid = bids[0]["price"] if bids else None
            best_ask = asks[0]["price"] if asks else None
            spread = round(best_ask - best_bid, 2) if (best_bid and best_ask) else None
            mid = round((best_bid + best_ask) / 2.0, 2) if (best_bid and best_ask) else None

            return {
                "timestamp_ns": time.time_ns(),
                "symbol": "APEX/USD",
                "bids": bids,
                "asks": asks,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread": spread,
                "mid_price": mid,
            }
        return self._py_get_l2_depth(depth)

    def order_count(self) -> int:
        if self.is_cpp_backend:
            return int(self.lib.nexus_order_count(self._handle))
        return len(self._py_orders)

    def clear(self):
        if self.is_cpp_backend:
            self.lib.nexus_clear_book(self._handle)
        else:
            self._py_orders.clear()
            self._py_bids.clear()
            self._py_asks.clear()

    # --- Python Fallback Implementation ---
    def _init_python_fallback(self):
        self._py_orders = {}
        self._py_bids = {} # price -> [orders]
        self._py_asks = {} # price -> [orders]

    def _py_add_order(self, order_id, side_code, type_code, price_cents, quantity):
        trades = []
        now_ns = time.time_ns()
        rem_qty = quantity

        if side_code == 0: # BUY
            sorted_ask_prices = sorted(self._py_asks.keys())
            for ask_p in sorted_ask_prices:
                if type_code != 1 and ask_p > price_cents:
                    break
                queue = self._py_asks[ask_p]
                new_queue = []
                for maker in queue:
                    if rem_qty <= 0:
                        new_queue.append(maker)
                        continue
                    fill_qty = min(rem_qty, maker["qty"])
                    trades.append({
                        "maker_order_id": maker["id"],
                        "taker_order_id": order_id,
                        "taker_side": "BUY",
                        "price": round(ask_p / 100.0, 2),
                        "quantity": fill_qty,
                        "timestamp_ns": now_ns,
                    })
                    rem_qty -= fill_qty
                    maker["qty"] -= fill_qty
                    if maker["qty"] > 0:
                        new_queue.append(maker)
                    else:
                        self._py_orders.pop(maker["id"], None)
                if new_queue:
                    self._py_asks[ask_p] = new_queue
                else:
                    del self._py_asks[ask_p]
                if rem_qty <= 0:
                    break

            if rem_qty > 0 and type_code == 0: # LIMIT
                ord_info = {"id": order_id, "side": 0, "price": price_cents, "qty": rem_qty}
                self._py_orders[order_id] = ord_info
                self._py_bids.setdefault(price_cents, []).append(ord_info)

        else: # SELL
            sorted_bid_prices = sorted(self._py_bids.keys(), reverse=True)
            for bid_p in sorted_bid_prices:
                if type_code != 1 and bid_p < price_cents:
                    break
                queue = self._py_bids[bid_p]
                new_queue = []
                for maker in queue:
                    if rem_qty <= 0:
                        new_queue.append(maker)
                        continue
                    fill_qty = min(rem_qty, maker["qty"])
                    trades.append({
                        "maker_order_id": maker["id"],
                        "taker_order_id": order_id,
                        "taker_side": "SELL",
                        "price": round(bid_p / 100.0, 2),
                        "quantity": fill_qty,
                        "timestamp_ns": now_ns,
                    })
                    rem_qty -= fill_qty
                    maker["qty"] -= fill_qty
                    if maker["qty"] > 0:
                        new_queue.append(maker)
                    else:
                        self._py_orders.pop(maker["id"], None)
                if new_queue:
                    self._py_bids[bid_p] = new_queue
                else:
                    del self._py_bids[bid_p]
                if rem_qty <= 0:
                    break

            if rem_qty > 0 and type_code == 0: # LIMIT
                ord_info = {"id": order_id, "side": 1, "price": price_cents, "qty": rem_qty}
                self._py_orders[order_id] = ord_info
                self._py_asks.setdefault(price_cents, []).append(ord_info)

        return order_id, trades

    def _py_cancel_order(self, order_id):
        if order_id not in self._py_orders:
            return False
        ord_info = self._py_orders.pop(order_id)
        book = self._py_bids if ord_info["side"] == 0 else self._py_asks
        p = ord_info["price"]
        if p in book:
            book[p] = [o for o in book[p] if o["id"] != order_id]
            if not book[p]:
                del book[p]
        return True

    def _py_get_bbo(self):
        best_bid = max(self._py_bids.keys()) / 100.0 if self._py_bids else None
        best_ask = min(self._py_asks.keys()) / 100.0 if self._py_asks else None
        return best_bid, best_ask

    def _py_get_l2_depth(self, depth):
        bids = []
        for p in sorted(self._py_bids.keys(), reverse=True)[:depth]:
            bids.append({
                "price": round(p / 100.0, 2),
                "quantity": sum(o["qty"] for o in self._py_bids[p]),
                "order_count": len(self._py_bids[p]),
            })
        asks = []
        for p in sorted(self._py_asks.keys())[:depth]:
            asks.append({
                "price": round(p / 100.0, 2),
                "quantity": sum(o["qty"] for o in self._py_asks[p]),
                "order_count": len(self._py_asks[p]),
            })
        best_bid = bids[0]["price"] if bids else None
        best_ask = asks[0]["price"] if asks else None
        spread = round(best_ask - best_bid, 2) if (best_bid and best_ask) else None
        mid = round((best_bid + best_ask) / 2.0, 2) if (best_bid and best_ask) else None
        return {
            "timestamp_ns": time.time_ns(),
            "symbol": "APEX/USD",
            "bids": bids,
            "asks": asks,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": spread,
            "mid_price": mid,
        }

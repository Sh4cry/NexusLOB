import re
import time
from typing import Dict, Any, List, Optional
import win32gui
import win32process

try:
    import uiautomation as auto
    UIA_AVAILABLE = True
except ImportError:
    UIA_AVAILABLE = False

class ScreenReaderAgent:
    """
    Direct Windows Screen Reader Agent.
    Inspects active application windows (Chrome, Edge, TradingView, etc.)
    directly via the Windows UI Automation (UIA) accessibility tree.
    Reads digital text, labels, and table cells from the screen WITHOUT screenshots.
    """

    PRICE_REGEX = re.compile(r'[$€£]?\s*([0-9]{1,6}(?:,[0-9]{3})*(?:\.[0-9]{1,4})?)')
    TICKER_REGEX = re.compile(r'\b([A-Z]{2,6}(?:/[A-Z]{2,6}|USDT|USD)?)\b')

    def __init__(self, target_window_keywords: Optional[List[str]] = None):
        self.keywords = target_window_keywords or [
            "tradingview", "binance", "coinbase", "robinhood", "yahoo finance",
            "chrome", "edge", "firefox", "bloomberg"
        ]

    def find_target_windows(self) -> List[Dict[str, Any]]:
        """Finds running browser or financial windows on the screen."""
        found_windows = []

        def enum_cb(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    title_lower = title.lower()
                    if any(k in title_lower for k in self.keywords):
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        found_windows.append({"hwnd": hwnd, "title": title, "pid": pid})

        win32gui.EnumWindows(enum_cb, None)
        return found_windows

    def extract_text_from_window(self, hwnd: int, max_elements: int = 150) -> List[str]:
        """Reads UI Automation element tree from the target window without taking a screenshot."""
        if not UIA_AVAILABLE:
            return []

        text_nodes = []
        try:
            control = auto.ControlFromHandle(hwnd)
            if not control:
                return []

            # Traverse child controls (Text, Edit, DataItem, Header, Title)
            def walker(elem, depth=0):
                if depth > 6 or len(text_nodes) >= max_elements:
                    return

                name = elem.Name
                if name and len(name.strip()) > 0:
                    text_nodes.append(name.strip())

                # Check Value pattern if available
                val_pattern = elem.GetPattern(auto.PatternId.ValuePattern)
                if val_pattern:
                    val = val_pattern.Value
                    if val and len(val.strip()) > 0 and val.strip() != name:
                        text_nodes.append(val.strip())

                for child in elem.GetChildren():
                    walker(child, depth + 1)

            walker(control)
        except Exception as e:
            print(f"[ScreenReader] Error walking UIA tree: {e}")

        return text_nodes

    def parse_market_data(self, texts: List[str]) -> Dict[str, Any]:
        """Parses extracted digital screen text into structured financial market parameters."""
        detected_prices: List[float] = []
        detected_tickers: List[str] = []

        for txt in texts:
            # Check for ticker symbols
            tickers = self.TICKER_REGEX.findall(txt)
            for t in tickers:
                if t not in ["USD", "EUR", "GBP", "BUY", "SELL", "NEW", "ALL", "TOP", "DAY", "VOL"]:
                    detected_tickers.append(t)

            # Check for price patterns
            matches = self.PRICE_REGEX.findall(txt)
            for m in matches:
                clean_num = m.replace(",", "")
                try:
                    val = float(clean_num)
                    # Filter out integers that look like years or small quantities
                    if 0.01 <= val <= 250000.0 and val not in [2024.0, 2025.0, 2026.0]:
                        detected_prices.append(val)
                except ValueError:
                    continue

        symbol = detected_tickers[0] if detected_tickers else "DETECTED/USD"
        median_price = detected_prices[len(detected_prices) // 2] if detected_prices else 100.0

        # Construct synthetic bid/ask ladder around the detected screen price
        spread_ticks = 0.05
        bids = [
            {"price": round(median_price - (i * spread_ticks), 2), "quantity": 10 * i}
            for i in range(1, 6)
        ]
        asks = [
            {"price": round(median_price + (i * spread_ticks), 2), "quantity": 10 * i}
            for i in range(1, 6)
        ]

        return {
            "source": "Windows UI Automation (Direct Screen Tree)",
            "symbol": symbol,
            "mid_price": median_price,
            "detected_prices_count": len(detected_prices),
            "bids": bids,
            "asks": asks,
            "timestamp_ns": time.time_ns(),
        }

    def scan_screen_now(self) -> Dict[str, Any]:
        """Performs a live scan of the active screen window."""
        windows = self.find_target_windows()
        if not windows:
            # Fallback to foreground window
            fg_hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(fg_hwnd) if fg_hwnd else "Unknown"
            windows = [{"hwnd": fg_hwnd, "title": title, "pid": 0}]

        target = windows[0]
        texts = self.extract_text_from_window(target["hwnd"])
        parsed = self.parse_market_data(texts)
        parsed["window_title"] = target["title"]
        return parsed

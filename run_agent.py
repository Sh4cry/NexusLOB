#!/usr/bin/env python3
"""
NoxusLOB Background Autonomous Agent
------------------------------------
Monitors the screen directly (via Windows UI Automation without screenshots)
or live financial web feeds, extracting market data and feeding it into the
NoxusLOB C++20 matching engine.

Usage:
  python run_agent.py --mode screen            # Read directly from screen UI tree
  python run_agent.py --mode web --symbol BTC  # Stream live web data directly
"""

import sys
import os
import time
import argparse
import asyncio

# Setup paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.join(PROJECT_ROOT, "server")
sys.path.insert(0, SERVER_DIR)

from app.engine_bridge import EngineBridge
from app.agent.autonomous_feeder import AutonomousFeederAgent

async def main():
    parser = argparse.ArgumentParser(description="NoxusLOB Background Screen & Web Agent")
    parser.add_argument("--mode", choices=["screen", "web"], default="web",
                        help="Data source: 'screen' (Windows UI Automation) or 'web' (Direct Web Feed)")
    parser.add_argument("--symbol", default="BTCUSDT", help="Trading symbol for web feed mode (e.g. BTCUSDT, ETHUSDT)")
    parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds")
    args = parser.parse_args()

    mode_mapped = "SCREEN_UIA" if args.mode == "screen" else "WEB_FEED"

    print("=" * 65)
    print("   NOXUSLOB AUTONOMOUS BACKGROUND AGENT (ZERO-SCREENSHOT)       ")
    print("=" * 65)
    print(f"Mode    : {mode_mapped}")
    print(f"Target  : {args.symbol if mode_mapped == 'WEB_FEED' else 'Active Windows Screen UI Tree'}")
    print(f"Interval: {args.interval}s")
    print("=" * 65)

    engine = EngineBridge()
    feeder = AutonomousFeederAgent(engine)
    feeder.start(mode=mode_mapped, symbol=args.symbol, interval_sec=args.interval)

    try:
        while True:
            await asyncio.sleep(args.interval)
            status = feeder.get_status()
            last = status.get("last_extraction", {})
            bbo_bid, bbo_ask = engine.get_bbo()
            print(f"[{time.strftime('%H:%M:%S')}] Source: {last.get('source', 'N/A')} | "
                  f"Symbol: {last.get('symbol', 'N/A')} | "
                  f"Mid: ${last.get('mid_price', 0):.2f} | "
                  f"BBO: [${bbo_bid or 0:.2f} / ${bbo_ask or 0:.2f}] | "
                  f"Engine Orders: {engine.order_count()}")
    except KeyboardInterrupt:
        print("\nStopping background agent...")
        feeder.stop()

if __name__ == "__main__":
    asyncio.run(main())

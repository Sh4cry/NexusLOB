<div align="center">

# ⚡ NoxusLOB
### High-Performance C++20 Limit Order Book Matching Engine & Quantitative Trading Platform

[![CI Pipeline](https://img.shields.io/badge/CI-Passing-00E599?style=for-the-badge&logo=github-actions&logoColor=white)](.github/workflows/ci.yml)
[![Standard](https://img.shields.io/badge/C%2B%2B-20-007ACC?style=for-the-badge&logo=c%2B%2B&logoColor=white)](https://en.cppreference.com/w/cpp/20)
[![Version](https://img.shields.io/badge/Release-v1.1.2-00E599?style=for-the-badge)](https://github.com/Sh4cry/NoxusLOB)
[![Throughput](https://img.shields.io/badge/Throughput-3.52M%20ops%2Fsec-FF3B69?style=for-the-badge&logo=speedtest&logoColor=white)](#-benchmarks--empirical-validation)
[![Latency](https://img.shields.io/badge/p99%20Latency-0.94%20µs-7928CA?style=for-the-badge)](#-benchmarks--empirical-validation)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

*An end-to-end electronic trading prototype and quantitative market simulator.*
<br />
*Combines **cache-conscious C++20 systems programming**, **custom slab memory pools**, **Avellaneda-Stoikov & Markov quantitative models**, and a **real-time React trading terminal**.*

</div>

---

## 🎯 Executive Overview

**NoxusLOB** is a high-performance, deterministic Limit Order Book (LOB) matching engine prototype and full-stack quantitative market simulator designed to explore low-latency systems architecture and market microstructure.

Built around strict **Price-Time Priority (FIFO)** execution semantics, the C++ core utilizes a custom pre-allocated memory pool and intrusive doubly-linked queues to eliminate dynamic heap allocation churn for order nodes during hot execution loops. Interfaced to Python through a zero-overhead C FFI boundary (`ctypes`), the engine streams real-time Level 2 market depth and trade telemetry over WebSockets to an institutional-style Bloomberg terminal.

```
                           ┌────────────────────────────────────────┐
                           │      Web Trading Terminal (React)      │
                           │  • L2 Depth Ladder    • Depth Chart    │
                           │  • Real-time Fills    • Latency Gauges │
                           └───────────────────▲────────────────────┘
                                               │ WebSocket (20-60 Hz)
                                               ▼
                           ┌────────────────────────────────────────┐
                           │     Market Data Gateway (FastAPI)      │
                           │  • REST Orders API    • Quant Drivers  │
                           └───────────────────▲────────────────────┘
                                               │ Zero-Copy C-ABI FFI
                                               ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        C++20 CORE MATCHING ENGINE (noxus_engine)                       │
│                                                                                        │
│   ┌──────────────────────┐    ┌──────────────────────┐    ┌────────────────────────┐   │
│   │   OrderPool (Slab)   │    │  Intrusive Doubly    │    │   Price-Time FIFO      │   │
│   │ Zero-Heap Node Churn │───▶│  Linked Lists (O(1)) │───▶│   Matching Engine      │   │
│   └──────────────────────┘    └──────────────────────┘    └────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🖥️ Terminal UI Preview & Real-Time Telemetry

The platform includes a real-time web trading terminal served locally at `http://localhost:8000`:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ⚡ NOXUSLOB TERMINAL │ Backend: C++20 Native │ Engine: 3.52M ops/s │ p50: 0.20µs │ p99: 0.94µs │ Active: ONLINE │
├───────────────────────────────────┬───────────────────────────────────┬─────────────────────────────────┤
│        LEVEL 2 ORDER BOOK         │       MARKET DEPTH CHART          │        LIVE TRADE TAPE          │
│                                   │                                   │                                 │
│  ASK DEPTH (Sellers)              │   Cumulative Liquidity (Bid/Ask)  │ TIME      SIDE   PRICE    QTY   │
│  $65,025.00 │ 12.50 BTC ████      │                                   │ 14:51:02  BUY    $65,010  1.42  │
│  $65,020.00 │  8.20 BTC ███       │      /\            /\         │ 14:51:02  BUY    $65,010  0.50  │
│  $65,015.00 │  4.10 BTC █         │     /  \  SPREAD  /  \        │ 14:51:01  SELL   $65,005  2.10  │
│ ───────────────────────────────── │    / BIDS \ $5.00/ ASKS \       │ 14:51:00  BUY    $65,010  0.85  │
│  SPREAD: $5.00 │ MID: $65,012.50  │   /        \    /        \      ├─────────────────────────────────┤
│ ───────────────────────────────── │  /          \  /          \     │       MODEL CONTROLLER          │
│  $65,010.00 │  5.40 BTC ██        │                                   │ [●] Avellaneda-Stoikov (Active) │
│  $65,005.00 │  9.80 BTC ████      │                                   │ [ ] Markov Regime Switcher      │
│  $65,000.00 │ 18.20 BTC ███████   │                                   │ [ ] Historical CSV Replayer     │
│  BID DEPTH (Buyers)               │                                   │ [ ] Autonomous Screen Feeder    │
└───────────────────────────────────┴───────────────────────────────────┴─────────────────────────────────┘
```

---

## 🚀 Key Technical Features

### 1. High-Performance C++20 Core
- **Intrusive Queue Management ($O(1)$)**: Order structs embed their own forward and backward links (`prev`, `next`), enabling constant-time queue detachment during cancellations without list traversals or auxiliary node allocations.
- **Pre-Allocated Memory Pool**: Order instances are allocated from a contiguous slab (`MemoryPool<Order>`), eliminating `malloc()`/`free()` overhead on the critical path, minimizing allocator lock contention, and maximizing CPU cache locality.
- **Fixed-Point Price Arithmetic**: Quantizes prices to integer units (e.g., basis points/cents), eliminating IEEE-754 floating-point inaccuracies and ensuring deterministic cross-platform matching.
- **Complete Order Mechanics**: Native support for `LIMIT`, `MARKET`, `IOC` (Immediate-Or-Cancel), and `FOK` (Fill-Or-Kill) order types with price-improvement execution against maker liquidity.

### 2. Quantitative Microstructure & Execution Models
- **Avellaneda-Stoikov (2008)**: Optimal high-frequency market making model calculating dynamic reservation prices and spreads based on inventory risk aversion ($\gamma$) and volatility ($\sigma$).
- **Markov Regime-Switching Engine**: 3-state stochastic discrete Markov chain (`Low Volatility`, `Trending`, `High Volatility shock`) simulating realistic order arrival distributions and liquidity replenishment.
- **Historical Tick Replayer**: Streams real-world financial tick data (CSV format) directly through the matching engine.
- **Autonomous Feeder Agent**: Direct zero-screenshot screen reader (Windows UI Automation) and live WebSocket streamer.

### 3. Event-Driven Real-Time Gateway & Web Terminal
- **Asynchronous Broadcasting**: FastAPI/asyncio engine gateway streaming L2 book depth ladders and trades at 20–60 Hz over WebSockets.
- **Institutional Trading Terminal**: React 18 + Vite + TypeScript interface featuring:
  - Animated L2 depth ladder with visual order volume bars.
  - Interactive HTML5 canvas cumulative liquidity depth chart.
  - High-frequency live trade tape.
  - Sub-microsecond latency telemetry gauges ($p50, p90, p99$).

---

## 📊 Benchmarks & Empirical Validation

### Methodology & Isolation
To ensure credible, reproducible measurements without timing skew:
1. **Pre-Generated Shadow-Book Workload (0 RNG in hot loop)**: 500,000 operations are pre-generated in memory *before* timers start. A shadow book tracks order lifecycle so every cancellation targets a **verified resting quote**.
2. **CPU Cache Warm-Up**: 10,000 warm-up operations prime instruction caches and branch predictors before measurement begins.
3. **Isolated Latency Sampling**: Per-operation latency is measured with `std::chrono::high_resolution_clock` into a pre-allocated vector to prevent `push_back()` heap reallocations during measurement.
4. **Repeated Run Variance**: Evaluated across 5 consecutive benchmark runs to report mean throughput and standard deviation.

### Tested Environment
- **CPU**: Intel(R) Core(TM) Ultra 7 256V (8 Cores, 8 Threads @ 2.20 GHz, Lunar Lake)
- **RAM**: 16 GB LPDDR5X
- **OS**: Microsoft Windows 11 Home (x86_64)
- **Compiler**: GCC 14.2.0 (MSYS2)
- **Compilation Flags**: `-std=c++20 -O3 -march=native`

### Empirical Results (5 Repeated Runs)

| Run Iteration | Throughput (ops/sec) | Median ($p50$) | 90th Percentile ($p90$) | 99th Percentile ($p99$) |
| :--- | :--- | :--- | :--- | :--- |
| **Run #1** | 3.48 Million ops/s | 0.20 µs | 0.50 µs | 1.00 µs |
| **Run #2** | 3.52 Million ops/s | 0.20 µs | 0.50 µs | 1.00 µs |
| **Run #3** | 3.49 Million ops/s | 0.20 µs | 0.50 µs | 0.90 µs |
| **Run #4** | 3.56 Million ops/s | 0.20 µs | 0.50 µs | 0.90 µs |
| **Run #5** | 3.54 Million ops/s | 0.20 µs | 0.50 µs | 0.90 µs |
| **Aggregated Mean** | **3.52 M ops/s ($\pm 0.03$M)** | **0.20 µs ($\pm 0.00\,\mu\text{s}$)** | **0.50 µs** | **0.94 µs ($\pm 0.05\,\mu\text{s}$)** |

**Workload Verification:**
- Total Operations / Run: 500,000
- Fills & Executed Trades: 345,980
- Cancellations Attempted: 99,464
- Cancellations Succeeded: **99,464 (100.0% verified resting cancellations)**

To reproduce the benchmark on your local hardware:
```bash
python run.py --bench
```

---

## 🧪 Verified Invariants & Edge Cases

The matching engine is validated by an automated test suite ([`test_matching.cpp`](file:///d:/nexus-lob/engine/tests/test_matching.cpp)) covering 12 structural invariants:

1. **Price-Time Priority (FIFO)**: Verifies that identical-price limit orders are matched strictly in arrival sequence.
2. **Exact Matching**: Confirms matching balance when maker and taker quantities are identical.
3. **Partial Fills & Residual Tracking**: Ensures orders partially filled update remaining quantity and book totals correctly.
4. **Price Improvement**: Guarantees aggressive crossing orders execute at the resting maker's better price.
5. **$O(1)$ Order Cancellation**: Tests queue unlinking and verifies book depth and count update accurately.
6. **Order Modification**: Tests in-place size reduction preserving FIFO queue priority.
7. **Market Order Sweeping**: Confirms market orders sweep across multiple price levels until filled.
8. **Fill-Or-Kill (FOK)**: Validates atomic pre-execution depth checks; fills completely or kills immediately.
9. **Immediate-Or-Cancel (IOC)**: Confirms partial fills execute immediately while unfilled remainders are cancelled without resting.
10. **Duplicate Order ID Rejection**: Guards against ID collisions; rejects duplicates and preserves existing order state.
11. **Input Validation**: Ensures immediate rejection of zero-quantity and malformed inputs.
12. **L2 Depth Invariant**: Verifies aggregated Level 2 price levels match internal order count and volume sums.

To run the complete test suite:
```bash
python run.py --test
```

---

## 🛠️ Quickstart Guide

### Option A: 1-Click Launch (Recommended)
Prerequisites: Python 3.10+ (and optional C++ compiler like `g++` or `clang++`).

```bash
# 1. Clone repository
git clone https://github.com/Sh4cry/NoxusLOB.git
cd NoxusLOB

# 2. Install Python dependencies
pip install -r server/requirements.txt

# 3. Launch platform (auto-compiles C++ engine & serves UI)
python run.py
```
Open **http://localhost:8000** to interact with the live trading terminal.

---

### Option B: Native C++ Build (CMake)
```bash
cd engine
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release

# Run Unit Tests (12 Test Suites)
./build/test_matching

# Run Isolated Benchmark
./build/benchmarks 500000 5
```

---

### Option C: Docker Container
```bash
docker compose up --build
```
Access the application at `http://localhost:8000`.

---

## 📁 Repository Structure

```
noxus-lob/
├── engine/                       # Core C++20 Low-Latency Matching Engine
│   ├── include/
│   │   ├── Types.hpp             # Order types, timestamps, fixed-point prices
│   │   ├── Order.hpp             # Intrusive doubly linked list node
│   │   ├── MemoryPool.hpp        # Contiguous slab allocator (zero order node churn)
│   │   ├── PriceLevel.hpp        # O(1) queue detachment & aggregate volume
│   │   ├── OrderBook.hpp         # Price-Time Priority matching engine
│   │   └── C_API.h               # Packed C-ABI export headers
│   ├── src/
│   │   ├── OrderBook.cpp         # Match, Insert, Cancel, Cross execution
│   │   └── C_API.cpp             # FFI bindings implementation
│   ├── tests/
│   │   └── test_matching.cpp     # 12 unit tests verifying matching invariants
│   ├── benchmarks/
│   │   └── main_benchmark.cpp    # Isolated latency & throughput profiling harness
│   └── CMakeLists.txt
├── server/                       # Market Data Gateway & Quantitative Simulator
│   ├── app/
│   │   ├── main.py               # FastAPI + WebSocket server
│   │   ├── engine_bridge.py      # Direct ctypes FFI wrapper
│   │   ├── models/
│   │   │   ├── avellaneda_stoikov.py # Optimal HFT market making model
│   │   │   └── data_replayer.py      # Historical tick replayer
│   │   ├── agent/
│   │   │   ├── screen_reader.py      # Direct Windows UI Automation screen reader
│   │   │   └── autonomous_feeder.py  # Live background data feeder
│   │   ├── market_maker.py       # Markov-chain synthetic order flow
│   │   └── schemas.py            # Pydantic models for orders & telemetry
│   ├── tests/
│   │   └── run_tests.py          # Gateway API test suite
│   └── requirements.txt
├── web/                          # Institutional Trading Dashboard (React/Vite)
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.tsx          # Terminal navigation & status
│   │   │   ├── OrderBookLadder.tsx # Animated L2 depth ladder
│   │   │   ├── DepthChart.tsx      # Canvas cumulative liquidity visualizer
│   │   │   ├── TradeTape.tsx       # Live trade executions
│   │   │   ├── LatencyStats.tsx    # Live p50/p90/p99 telemetry cards
│   │   │   └── OrderControls.tsx   # Manual execution & stress test trigger
│   │   ├── App.tsx
│   │   └── types.ts
│   └── package.json
├── .github/workflows/ci.yml      # Automated CI testing pipeline
├── Dockerfile                    # Multi-stage production container
├── docker-compose.yml            # Container orchestration
├── run.py                        # Master launcher & CLI runner
└── README.md
```

---

## 💼 CV / Resume Highlights (For Recruiters)

- **Low-Latency Systems Engineering**:
  - *Engineered a low-latency price-time priority Limit Order Book matching engine in C++20, achieving 3.52M ops/sec throughput and sub-microsecond ($p99 = 0.94\,\mu\text{s}$) tail latency across repeated isolated benchmarks.*
  - *Eliminated dynamic heap allocation in the order execution path by architecting a custom contiguous slab memory pool and intrusive doubly linked list queues for $O(1)$ order cancellations.*
- **High-Performance Networking & Full-Stack**:
  - *Constructed an event-driven market data gateway in FastAPI/WebSockets streaming L2 snapshots and trade ticks at 20–60 Hz to an institutional React/TypeScript dashboard with HTML5 canvas depth visualization.*
  - *Interfaced Python and C++ using direct C-ABI foreign function interfaces (FFI) with zero-copy binary serialization, executing over 200,000 IPC operations/sec.*
- **Quantitative Modeling**:
  - *Implemented the Avellaneda-Stoikov (2008) optimal market-making model and a 3-state discrete Markov chain simulation to model inventory risk, reservation prices, and endogenous mid-price drift.*

---

## 📜 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for more information.

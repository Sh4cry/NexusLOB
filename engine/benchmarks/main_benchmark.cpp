#include "OrderBook.hpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <random>
#include <algorithm>
#include <numeric>
#include <iomanip>

using namespace noxus;

enum class BenchmarkOpType : uint8_t {
    ADD_LIMIT = 0,
    CANCEL = 1,
    CROSSING_LIMIT = 2,
    MARKET_SWEEP = 3
};

struct PreGeneratedOp {
    BenchmarkOpType opType{BenchmarkOpType::ADD_LIMIT};
    OrderId id{0};
    Side side{Side::BUY};
    OrderType orderType{OrderType::LIMIT};
    Price price{0};
    Quantity qty{0};
    OrderId cancelId{0};
};

struct BenchmarkResult {
    size_t totalOperations{0};
    size_t totalTrades{0};
    double throughputDurationSec{0.0};
    double throughputOpsPerSec{0.0};
    double p50Us{0.0};
    double p90Us{0.0};
    double p99Us{0.0};
    double p999Us{0.0};
    double maxUs{0.0};
    double minUs{0.0};
    double meanUs{0.0};
};

// Phase 1: Pre-generate entire workload in memory (untimed)
// Isolates matching engine execution from RNG calls and auxiliary allocations.
std::vector<PreGeneratedOp> generateWorkload(size_t orderCount) {
    std::vector<PreGeneratedOp> ops;
    ops.reserve(orderCount);

    std::mt19937_64 rng(1337); // Fixed seed for deterministic reproducibility
    std::uniform_int_distribution<uint32_t> sideDist(0, 1);
    std::uniform_int_distribution<uint32_t> opDist(0, 9); // 0-5: Limit, 6-7: Cancel, 8: Cross, 9: Market
    std::uniform_int_distribution<uint32_t> priceOffsetDist(1, 15);
    std::uniform_int_distribution<uint32_t> qtyDist(1, 50);

    Price currentMid = 10000; // $100.00 base
    std::vector<OrderId> activeOrderIds;
    activeOrderIds.reserve(orderCount);

    for (OrderId id = 1; id <= orderCount; ++id) {
        uint32_t op = opDist(rng);
        Side side = sideDist(rng) == 0 ? Side::BUY : Side::SELL;
        Quantity qty = qtyDist(rng);

        PreGeneratedOp item;
        item.id = id;
        item.side = side;
        item.qty = qty;

        if (op < 6 || activeOrderIds.empty()) {
            // Passive Limit Quote (Liquidity Maker)
            item.opType = BenchmarkOpType::ADD_LIMIT;
            item.orderType = OrderType::LIMIT;
            item.price = (side == Side::BUY) ? (currentMid - priceOffsetDist(rng))
                                             : (currentMid + priceOffsetDist(rng));
            activeOrderIds.push_back(id);
        } else if (op < 8) {
            // Cancellation of random resting order
            item.opType = BenchmarkOpType::CANCEL;
            size_t idx = rng() % activeOrderIds.size();
            item.cancelId = activeOrderIds[idx];
            activeOrderIds[idx] = activeOrderIds.back();
            activeOrderIds.pop_back();
        } else if (op == 8) {
            // Aggressive Crossing Limit Order (Liquidity Taker)
            item.opType = BenchmarkOpType::CROSSING_LIMIT;
            item.orderType = OrderType::LIMIT;
            item.price = (side == Side::BUY) ? (currentMid + priceOffsetDist(rng))
                                             : (currentMid - priceOffsetDist(rng));
            activeOrderIds.push_back(id);
        } else {
            // Immediate Market Sweep
            item.opType = BenchmarkOpType::MARKET_SWEEP;
            item.orderType = OrderType::MARKET;
            item.price = 0;
        }

        // Random walk mid-price drift
        if (id % 10 == 0) {
            int drift = static_cast<int>(rng() % 5) - 2;
            if (static_cast<int>(currentMid) + drift > 1000) {
                currentMid += drift;
            }
        }

        ops.push_back(item);
    }

    return ops;
}

// Phase 2: Warm up CPU cache & branch predictors
void warmupEngine(const std::vector<PreGeneratedOp>& ops, size_t warmupCount) {
    OrderBook warmupBook(warmupCount);
    for (size_t i = 0; i < warmupCount && i < ops.size(); ++i) {
        const auto& op = ops[i];
        if (op.opType == BenchmarkOpType::CANCEL) {
            warmupBook.cancelOrder(op.cancelId);
        } else {
            warmupBook.addOrder(op.id, op.side, op.orderType, op.price, op.qty);
        }
    }
}

// Phase 3 & 4: Execute Isolated Throughput & Latency Benchmarks
BenchmarkResult runRigorousBenchmark(size_t orderCount) {
    // 1. Pre-generate workload (untimed)
    auto workload = generateWorkload(orderCount);

    // 2. Warm up CPU cache (untimed)
    warmupEngine(workload, std::min<size_t>(10000, orderCount / 10));

    // 3. Isolated Throughput Run (no clock queries or allocations inside loop)
    OrderBook throughputBook(orderCount);
    size_t totalTrades = 0;

    auto tStart = std::chrono::high_resolution_clock::now();
    for (const auto& op : workload) {
        if (op.opType == BenchmarkOpType::CANCEL) {
            throughputBook.cancelOrder(op.cancelId);
        } else {
            auto trades = throughputBook.addOrder(op.id, op.side, op.orderType, op.price, op.qty);
            totalTrades += trades.size();
        }
    }
    auto tEnd = std::chrono::high_resolution_clock::now();
    double totalSec = std::chrono::duration<double>(tEnd - tStart).count();

    // 4. Isolated Per-Operation Latency Run (pre-allocated measurement vector)
    OrderBook latencyBook(orderCount);
    size_t latencySamples = std::min<size_t>(orderCount, 250000);
    std::vector<double> latenciesUs(latencySamples, 0.0);

    for (size_t i = 0; i < latencySamples; ++i) {
        const auto& op = workload[i];
        auto op0 = std::chrono::high_resolution_clock::now();
        if (op.opType == BenchmarkOpType::CANCEL) {
            latencyBook.cancelOrder(op.cancelId);
        } else {
            latencyBook.addOrder(op.id, op.side, op.orderType, op.price, op.qty);
        }
        auto op1 = std::chrono::high_resolution_clock::now();
        latenciesUs[i] = std::chrono::duration<double, std::micro>(op1 - op0).count();
    }

    // 5. Compute Percentiles
    std::sort(latenciesUs.begin(), latenciesUs.end());
    double sum = std::accumulate(latenciesUs.begin(), latenciesUs.end(), 0.0);

    BenchmarkResult res;
    res.totalOperations = orderCount;
    res.totalTrades = totalTrades;
    res.throughputDurationSec = totalSec;
    res.throughputOpsPerSec = orderCount / totalSec;
    res.minUs = latenciesUs.front();
    res.maxUs = latenciesUs.back();
    res.meanUs = sum / latencySamples;
    res.p50Us = latenciesUs[latencySamples * 50 / 100];
    res.p90Us = latenciesUs[latencySamples * 90 / 100];
    res.p99Us = latenciesUs[latencySamples * 99 / 100];
    res.p999Us = latenciesUs[latencySamples * 999 / 1000];

    return res;
}

int main(int argc, char* argv[]) {
    size_t orderCount = 500000;
    if (argc > 1) {
        orderCount = std::stoull(argv[1]);
    }

    std::cout << "===========================================================\n";
    std::cout << "       NoxusLOB Isolated C++20 Benchmark Suite            \n";
    std::cout << "===========================================================\n";
    std::cout << "[*] Workload Size  : " << orderCount << " operations\n";
    std::cout << "[*] Methodology    : Pre-generated memory workload (0 RNG in hot path)\n";
    std::cout << "[*] Warm-up Phase  : 10,000 operations cache prime\n";
#if defined(__clang__)
    std::cout << "[*] Compiler       : Clang " << __clang_version__ << "\n";
#elif defined(__GNUC__)
    std::cout << "[*] Compiler       : GCC " << __VERSION__ << "\n";
#elif defined(_MSC_VER)
    std::cout << "[*] Compiler       : MSVC " << _MSC_VER << "\n";
#endif
    std::cout << "[*] C++ Standard   : C++" << (__cplusplus / 100 % 100) << "\n";
    std::cout << "===========================================================\n";
    std::cout << "Running benchmark...\n";

    auto res = runRigorousBenchmark(orderCount);

    std::cout << std::fixed << std::setprecision(2);
    std::cout << "\n--- THROUGHPUT (Pure Engine Matching, 0 RNG) ---\n";
    std::cout << "Total Operations : " << res.totalOperations << "\n";
    std::cout << "Total Trades     : " << res.totalTrades << "\n";
    std::cout << "Elapsed Time     : " << res.throughputDurationSec << " s\n";
    std::cout << "Throughput       : " << (res.throughputOpsPerSec / 1e6) << " Million Ops/sec ("
              << static_cast<uint64_t>(res.throughputOpsPerSec) << " ops/s)\n";

    std::cout << "\n--- ISOLATED LATENCY PERCENTILES ---\n";
    std::cout << "Min Latency      : " << res.minUs << " µs\n";
    std::cout << "Median (p50)     : " << res.p50Us << " µs\n";
    std::cout << "90th Percentile  : " << res.p90Us << " µs\n";
    std::cout << "99th Percentile  : " << res.p99Us << " µs\n";
    std::cout << "99.9th Percentile: " << res.p999Us << " µs\n";
    std::cout << "Max Latency      : " << res.maxUs << " µs\n";
    std::cout << "Mean Latency     : " << res.meanUs << " µs\n";
    std::cout << "===========================================================\n";

    return 0;
}

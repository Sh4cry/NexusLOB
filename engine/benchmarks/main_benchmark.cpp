#include "OrderBook.hpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <random>
#include <algorithm>
#include <numeric>
#include <iomanip>

using namespace noxus;

struct BenchmarkResult {
    size_t totalOrders{0};
    size_t totalTrades{0};
    double durationSec{0.0};
    double throughputOpsPerSec{0.0};
    double p50Us{0.0};
    double p90Us{0.0};
    double p99Us{0.0};
    double p999Us{0.0};
    double maxUs{0.0};
    double minUs{0.0};
    double meanUs{0.0};
};

BenchmarkResult runThroughputBenchmark(size_t orderCount = 1000000) {
    OrderBook book(orderCount);
    std::vector<double> latenciesUs;
    latenciesUs.reserve(orderCount);

    std::mt19937_64 rng(1337); // Fixed seed for reproducibility
    std::uniform_int_distribution<uint32_t> sideDist(0, 1);
    std::uniform_int_distribution<uint32_t> opDist(0, 9); // 0-5: Limit, 6-7: Cancel, 8-9: Cross
    std::uniform_int_distribution<uint32_t> priceOffsetDist(1, 20);
    std::uniform_int_distribution<uint32_t> qtyDist(1, 50);

    Price currentMid = 10000; // $100.00
    std::vector<OrderId> activeOrderIds;
    activeOrderIds.reserve(orderCount);

    size_t totalTrades = 0;

    auto wallClockStart = std::chrono::high_resolution_clock::now();

    for (OrderId id = 1; id <= orderCount; ++id) {
        uint32_t op = opDist(rng);
        Side side = sideDist(rng) == 0 ? Side::BUY : Side::SELL;
        Quantity qty = qtyDist(rng);

        auto opStart = std::chrono::high_resolution_clock::now();

        if (op < 6 || activeOrderIds.empty()) {
            // Passive Limit order near mid
            Price price;
            if (side == Side::BUY) {
                price = currentMid - priceOffsetDist(rng);
            } else {
                price = currentMid + priceOffsetDist(rng);
            }
            auto trades = book.addOrder(id, side, OrderType::LIMIT, price, qty);
            totalTrades += trades.size();
            activeOrderIds.push_back(id);
        } else if (op < 8) {
            // Cancel random active order
            size_t idx = rng() % activeOrderIds.size();
            OrderId cancelId = activeOrderIds[idx];
            activeOrderIds[idx] = activeOrderIds.back();
            activeOrderIds.pop_back();

            book.cancelOrder(cancelId);
        } else {
            // Aggressive Crossing order (Market liquidity taker)
            Price price;
            if (side == Side::BUY) {
                price = currentMid + priceOffsetDist(rng);
            } else {
                price = currentMid - priceOffsetDist(rng);
            }
            auto trades = book.addOrder(id, side, OrderType::LIMIT, price, qty);
            totalTrades += trades.size();
            if (book.hasOrder(id)) {
                activeOrderIds.push_back(id);
            }
        }

        auto opEnd = std::chrono::high_resolution_clock::now();
        double elapsedUs = std::chrono::duration<double, std::micro>(opEnd - opStart).count();
        latenciesUs.push_back(elapsedUs);

        // Update mid-price drift
        auto bestBid = book.getBestBid();
        auto bestAsk = book.getBestAsk();
        if (bestBid && bestAsk) {
            currentMid = (*bestBid + *bestAsk) / 2;
        }
    }

    auto wallClockEnd = std::chrono::high_resolution_clock::now();
    double totalDuration = std::chrono::duration<double>(wallClockEnd - wallClockStart).count();

    // Compute percentiles
    std::sort(latenciesUs.begin(), latenciesUs.end());
    double sum = std::accumulate(latenciesUs.begin(), latenciesUs.end(), 0.0);

    BenchmarkResult res;
    res.totalOrders = orderCount;
    res.totalTrades = totalTrades;
    res.durationSec = totalDuration;
    res.throughputOpsPerSec = orderCount / totalDuration;
    res.minUs = latenciesUs.front();
    res.maxUs = latenciesUs.back();
    res.meanUs = sum / orderCount;
    res.p50Us = latenciesUs[orderCount * 50 / 100];
    res.p90Us = latenciesUs[orderCount * 90 / 100];
    res.p99Us = latenciesUs[orderCount * 99 / 100];
    res.p999Us = latenciesUs[orderCount * 999 / 1000];

    return res;
}

int main(int argc, char* argv[]) {
    size_t orderCount = 500000; // 500k default for quick CLI, or 1M
    if (argc > 1) {
        orderCount = std::stoull(argv[1]);
    }

    std::cout << "===========================================================\n";
    std::cout << "     NoxusLOB Low-Latency Benchmark Suite                 \n";
    std::cout << "===========================================================\n";
    std::cout << "Running workload of " << orderCount << " mixed operations...\n";

    auto res = runThroughputBenchmark(orderCount);

    std::cout << std::fixed << std::setprecision(2);
    std::cout << "\n--- THROUGHPUT SUMMARY ---\n";
    std::cout << "Total Operations : " << res.totalOrders << "\n";
    std::cout << "Total Fills/Trades: " << res.totalTrades << "\n";
    std::cout << "Elapsed Time     : " << res.durationSec << " s\n";
    std::cout << "Throughput       : " << (res.throughputOpsPerSec / 1e6) << " Million Ops/sec (" 
              << static_cast<uint64_t>(res.throughputOpsPerSec) << " ops/s)\n";

    std::cout << "\n--- LATENCY PERCENTILES (Microseconds) ---\n";
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

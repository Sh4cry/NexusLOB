#pragma once

#include <cstdint>
#include <string>
#include <vector>
#include <chrono>

namespace nexus {

using OrderId = uint64_t;
using Price = uint32_t;       // Stored in basis points or cents (e.g. $100.50 -> 10050)
using Quantity = uint32_t;
using Timestamp = uint64_t;   // Nanoseconds since epoch

enum class Side : uint8_t {
    BUY = 0,
    SELL = 1
};

enum class OrderType : uint8_t {
    LIMIT = 0,
    MARKET = 1,
    IOC = 2,    // Immediate-Or-Cancel
    FOK = 3     // Fill-Or-Kill
};

inline const char* sideToString(Side side) {
    return side == Side::BUY ? "BUY" : "SELL";
}

inline const char* orderTypeToString(OrderType type) {
    switch (type) {
        case OrderType::LIMIT: return "LIMIT";
        case OrderType::MARKET: return "MARKET";
        case OrderType::IOC: return "IOC";
        case OrderType::FOK: return "FOK";
        default: return "UNKNOWN";
    }
}

inline Timestamp currentTimestampNs() {
    return static_cast<Timestamp>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::high_resolution_clock::now().time_since_epoch()
        ).count()
    );
}

struct Trade {
    OrderId makerOrderId{0};
    OrderId takerOrderId{0};
    Side takerSide{Side::BUY};
    Price price{0};
    Quantity quantity{0};
    Timestamp timestamp{0};
};

struct LevelSummary {
    Price price{0};
    Quantity quantity{0};
    uint32_t orderCount{0};
};

struct L2Snapshot {
    Timestamp timestamp{0};
    std::vector<LevelSummary> bids;
    std::vector<LevelSummary> asks;
};

} // namespace nexus

namespace noxus = nexus;

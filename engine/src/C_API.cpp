#include "C_API.h"
#include "OrderBook.hpp"
#include <cstring>

using namespace noxus;

extern "C" {

// Primary Noxus C API Implementation
void* noxus_create_book(uint32_t capacity) {
    return new OrderBook(capacity > 0 ? capacity : 100000);
}

void noxus_destroy_book(void* bookPtr) {
    if (bookPtr) {
        delete static_cast<OrderBook*>(bookPtr);
    }
}

void noxus_clear_book(void* bookPtr) {
    if (bookPtr) {
        static_cast<OrderBook*>(bookPtr)->clear();
    }
}

int noxus_add_order(
    void* bookPtr,
    uint64_t id,
    uint8_t side,
    uint8_t type,
    uint32_t price,
    uint32_t qty,
    uint64_t ts,
    CTrade* outTrades,
    uint32_t maxTrades,
    uint32_t* outTradeCount
) {
    if (!bookPtr) return -1;
    auto* book = static_cast<OrderBook*>(bookPtr);

    Side s = (side == 0) ? Side::BUY : Side::SELL;
    OrderType t = static_cast<OrderType>(type);

    auto trades = book->addOrder(id, s, t, price, qty, ts);

    uint32_t count = static_cast<uint32_t>(trades.size());
    if (outTradeCount) {
        *outTradeCount = std::min(count, maxTrades);
    }

    if (outTrades && maxTrades > 0) {
        uint32_t toCopy = std::min(count, maxTrades);
        for (uint32_t i = 0; i < toCopy; ++i) {
            outTrades[i].makerOrderId = trades[i].makerOrderId;
            outTrades[i].takerOrderId = trades[i].takerOrderId;
            outTrades[i].takerSide = static_cast<uint8_t>(trades[i].takerSide);
            outTrades[i].price = trades[i].price;
            outTrades[i].quantity = trades[i].quantity;
            outTrades[i].timestamp = trades[i].timestamp;
        }
    }

    return static_cast<int>(trades.size());
}

bool noxus_cancel_order(void* bookPtr, uint64_t id) {
    if (!bookPtr) return false;
    return static_cast<OrderBook*>(bookPtr)->cancelOrder(id);
}

bool noxus_modify_order(void* bookPtr, uint64_t id, uint32_t newQty) {
    if (!bookPtr) return false;
    return static_cast<OrderBook*>(bookPtr)->modifyOrder(id, newQty);
}

bool noxus_has_order(void* bookPtr, uint64_t id) {
    if (!bookPtr) return false;
    return static_cast<OrderBook*>(bookPtr)->hasOrder(id);
}

uint32_t noxus_order_count(void* bookPtr) {
    if (!bookPtr) return 0;
    return static_cast<uint32_t>(static_cast<OrderBook*>(bookPtr)->orderCount());
}

bool noxus_get_bbo(void* bookPtr, uint32_t* outBid, uint32_t* outAsk) {
    if (!bookPtr) return false;
    auto* book = static_cast<OrderBook*>(bookPtr);
    auto bid = book->getBestBid();
    auto ask = book->getBestAsk();

    bool hasBbo = false;
    if (outBid) {
        *outBid = bid.value_or(0);
        if (bid.has_value()) hasBbo = true;
    }
    if (outAsk) {
        *outAsk = ask.value_or(0);
        if (ask.has_value()) hasBbo = true;
    }
    return hasBbo;
}

void noxus_get_l2_depth(
    void* bookPtr,
    uint32_t maxLevels,
    CLevel* outBids,
    uint32_t* outBidCount,
    CLevel* outAsks,
    uint32_t* outAskCount
) {
    if (!bookPtr) return;
    auto* book = static_cast<OrderBook*>(bookPtr);
    auto snap = book->getL2Snapshot(maxLevels);

    if (outBids && outBidCount) {
        uint32_t nBids = std::min(maxLevels, static_cast<uint32_t>(snap.bids.size()));
        *outBidCount = nBids;
        for (uint32_t i = 0; i < nBids; ++i) {
            outBids[i].price = snap.bids[i].price;
            outBids[i].quantity = snap.bids[i].quantity;
            outBids[i].orderCount = snap.bids[i].orderCount;
        }
    }

    if (outAsks && outAskCount) {
        uint32_t nAsks = std::min(maxLevels, static_cast<uint32_t>(snap.asks.size()));
        *outAskCount = nAsks;
        for (uint32_t i = 0; i < nAsks; ++i) {
            outAsks[i].price = snap.asks[i].price;
            outAsks[i].quantity = snap.asks[i].quantity;
            outAsks[i].orderCount = snap.asks[i].orderCount;
        }
    }
}

// Backward Compatibility Aliases
void* nexus_create_book(uint32_t capacity) { return noxus_create_book(capacity); }
void nexus_destroy_book(void* bookPtr) { noxus_destroy_book(bookPtr); }
void nexus_clear_book(void* bookPtr) { noxus_clear_book(bookPtr); }
int nexus_add_order(void* bookPtr, uint64_t id, uint8_t side, uint8_t type, uint32_t price, uint32_t qty, uint64_t ts, CTrade* outTrades, uint32_t maxTrades, uint32_t* outTradeCount) {
    return noxus_add_order(bookPtr, id, side, type, price, qty, ts, outTrades, maxTrades, outTradeCount);
}
bool nexus_cancel_order(void* bookPtr, uint64_t id) { return noxus_cancel_order(bookPtr, id); }
bool nexus_modify_order(void* bookPtr, uint64_t id, uint32_t newQty) { return noxus_modify_order(bookPtr, id, newQty); }
bool nexus_has_order(void* bookPtr, uint64_t id) { return noxus_has_order(bookPtr, id); }
uint32_t nexus_order_count(void* bookPtr) { return noxus_order_count(bookPtr); }
bool nexus_get_bbo(void* bookPtr, uint32_t* outBid, uint32_t* outAsk) { return noxus_get_bbo(bookPtr, outBid, outAsk); }
void nexus_get_l2_depth(void* bookPtr, uint32_t maxLevels, CLevel* outBids, uint32_t* outBidCount, CLevel* outAsks, uint32_t* outAskCount) {
    noxus_get_l2_depth(bookPtr, maxLevels, outBids, outBidCount, outAsks, outAskCount);
}

} // extern "C"

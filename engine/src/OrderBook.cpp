#include "OrderBook.hpp"
#include <algorithm>

namespace nexus {

OrderBook::OrderBook(size_t initialPoolCapacity)
    : m_pool(initialPoolCapacity) {
    m_orderIndex.reserve(initialPoolCapacity);
}

OrderBook::~OrderBook() {
    clear();
}

void OrderBook::clear() {
    for (auto& [id, order] : m_orderIndex) {
        m_pool.deallocate(order);
    }
    m_orderIndex.clear();
    m_bids.clear();
    m_asks.clear();
}

bool OrderBook::hasOrder(OrderId id) const noexcept {
    return m_orderIndex.find(id) != m_orderIndex.end();
}

const Order* OrderBook::getOrder(OrderId id) const noexcept {
    auto it = m_orderIndex.find(id);
    return (it != m_orderIndex.end()) ? it->second : nullptr;
}

std::optional<Price> OrderBook::getBestBid() const noexcept {
    if (m_bids.empty()) return std::nullopt;
    return m_bids.begin()->first;
}

std::optional<Price> OrderBook::getBestAsk() const noexcept {
    if (m_asks.empty()) return std::nullopt;
    return m_asks.begin()->first;
}

std::optional<Price> OrderBook::getSpread() const noexcept {
    if (m_bids.empty() || m_asks.empty()) return std::nullopt;
    Price bestBid = m_bids.begin()->first;
    Price bestAsk = m_asks.begin()->first;
    if (bestAsk >= bestBid) {
        return bestAsk - bestBid;
    }
    return 0; // Cross book edge-case
}

std::optional<double> OrderBook::getMidPrice() const noexcept {
    if (m_bids.empty() || m_asks.empty()) return std::nullopt;
    return (static_cast<double>(m_bids.begin()->first) + static_cast<double>(m_asks.begin()->first)) / 2.0;
}

Quantity OrderBook::getBidVolume() const noexcept {
    Quantity total = 0;
    for (const auto& [price, level] : m_bids) {
        total += level.totalQuantity();
    }
    return total;
}

Quantity OrderBook::getAskVolume() const noexcept {
    Quantity total = 0;
    for (const auto& [price, level] : m_asks) {
        total += level.totalQuantity();
    }
    return total;
}

std::vector<Trade> OrderBook::addOrder(OrderId id, Side side, OrderType type, Price price, Quantity qty, Timestamp ts) {
    if (qty == 0 || hasOrder(id)) {
        return {}; // Invalid quantity or duplicate order id
    }

    if (ts == 0) {
        ts = currentTimestampNs();
    }

    // Allocate order from object pool
    Order* order = m_pool.allocate();
    order->id = id;
    order->price = price;
    order->initialQty = qty;
    order->remainingQty = qty;
    order->side = side;
    order->type = type;
    order->timestamp = ts;

    // Handle FOK (Fill-Or-Kill) pre-check
    if (type == OrderType::FOK) {
        Quantity availableVolume = 0;
        if (side == Side::BUY) {
            for (const auto& [askPrice, level] : m_asks) {
                if (price > 0 && askPrice > price) break;
                availableVolume += level.totalQuantity();
                if (availableVolume >= qty) break;
            }
        } else {
            for (const auto& [bidPrice, level] : m_bids) {
                if (price > 0 && bidPrice < price) break;
                availableVolume += level.totalQuantity();
                if (availableVolume >= qty) break;
            }
        }

        if (availableVolume < qty) {
            m_pool.deallocate(order);
            return {}; // Cannot fully fill, kill order immediately
        }
    }

    // Match order
    std::vector<Trade> trades;
    if (side == Side::BUY) {
        trades = matchBuyOrder(order);
    } else {
        trades = matchSellOrder(order);
    }

    return trades;
}

std::vector<Trade> OrderBook::matchBuyOrder(Order* order) {
    std::vector<Trade> trades;

    while (!m_asks.empty() && order->remainingQty > 0) {
        auto askIt = m_asks.begin();
        Price bestAsk = askIt->first;

        // If LIMIT order and bestAsk exceeds limit price, stop matching
        if (order->type != OrderType::MARKET && bestAsk > order->price) {
            break;
        }

        PriceLevel& level = askIt->second;
        while (!level.isEmpty() && order->remainingQty > 0) {
            Order* maker = level.head();
            Quantity fillQty = std::min(order->remainingQty, maker->remainingQty);

            Trade trade{
                .makerOrderId = maker->id,
                .takerOrderId = order->id,
                .takerSide = Side::BUY,
                .price = bestAsk,
                .quantity = fillQty,
                .timestamp = order->timestamp
            };
            trades.push_back(trade);

            order->remainingQty -= fillQty;
            maker->remainingQty -= fillQty;
            level.decreaseQuantity(fillQty);

            if (maker->isFilled()) {
                m_orderIndex.erase(maker->id);
                level.remove(maker);
                m_pool.deallocate(maker);
            }
        }

        if (level.isEmpty()) {
            m_asks.erase(askIt);
        }
    }

    if (order->remainingQty > 0) {
        if (order->type == OrderType::LIMIT) {
            // Resting limit order added to book
            addOrderToBook(order);
        } else {
            // MARKET or IOC remainder is cancelled
            m_pool.deallocate(order);
        }
    } else {
        // Taker fully filled
        m_pool.deallocate(order);
    }

    return trades;
}

std::vector<Trade> OrderBook::matchSellOrder(Order* order) {
    std::vector<Trade> trades;

    while (!m_bids.empty() && order->remainingQty > 0) {
        auto bidIt = m_bids.begin();
        Price bestBid = bidIt->first;

        // If LIMIT order and bestBid is below limit price, stop matching
        if (order->type != OrderType::MARKET && bestBid < order->price) {
            break;
        }

        PriceLevel& level = bidIt->second;
        while (!level.isEmpty() && order->remainingQty > 0) {
            Order* maker = level.head();
            Quantity fillQty = std::min(order->remainingQty, maker->remainingQty);

            Trade trade{
                .makerOrderId = maker->id,
                .takerOrderId = order->id,
                .takerSide = Side::SELL,
                .price = bestBid,
                .quantity = fillQty,
                .timestamp = order->timestamp
            };
            trades.push_back(trade);

            order->remainingQty -= fillQty;
            maker->remainingQty -= fillQty;
            level.decreaseQuantity(fillQty);

            if (maker->isFilled()) {
                m_orderIndex.erase(maker->id);
                level.remove(maker);
                m_pool.deallocate(maker);
            }
        }

        if (level.isEmpty()) {
            m_bids.erase(bidIt);
        }
    }

    if (order->remainingQty > 0) {
        if (order->type == OrderType::LIMIT) {
            // Resting limit order added to book
            addOrderToBook(order);
        } else {
            // MARKET or IOC remainder is cancelled
            m_pool.deallocate(order);
        }
    } else {
        // Taker fully filled
        m_pool.deallocate(order);
    }

    return trades;
}

void OrderBook::addOrderToBook(Order* order) {
    m_orderIndex[order->id] = order;
    if (order->side == Side::BUY) {
        auto it = m_bids.find(order->price);
        if (it == m_bids.end()) {
            auto [insertedIt, success] = m_bids.emplace(order->price, PriceLevel(order->price));
            insertedIt->second.append(order);
        } else {
            it->second.append(order);
        }
    } else {
        auto it = m_asks.find(order->price);
        if (it == m_asks.end()) {
            auto [insertedIt, success] = m_asks.emplace(order->price, PriceLevel(order->price));
            insertedIt->second.append(order);
        } else {
            it->second.append(order);
        }
    }
}

void OrderBook::removeOrderFromBook(Order* order) {
    if (order->side == Side::BUY) {
        auto it = m_bids.find(order->price);
        if (it != m_bids.end()) {
            it->second.remove(order);
            if (it->second.isEmpty()) {
                m_bids.erase(it);
            }
        }
    } else {
        auto it = m_asks.find(order->price);
        if (it != m_asks.end()) {
            it->second.remove(order);
            if (it->second.isEmpty()) {
                m_asks.erase(it);
            }
        }
    }
}

bool OrderBook::cancelOrder(OrderId id) {
    auto it = m_orderIndex.find(id);
    if (it == m_orderIndex.end()) {
        return false;
    }

    Order* order = it->second;
    removeOrderFromBook(order);
    m_orderIndex.erase(it);
    m_pool.deallocate(order);
    return true;
}

bool OrderBook::modifyOrder(OrderId id, Quantity newQty) {
    auto it = m_orderIndex.find(id);
    if (it == m_orderIndex.end() || newQty == 0) {
        return false;
    }

    Order* order = it->second;
    if (newQty < order->remainingQty) {
        // Reducing quantity retains queue priority!
        Quantity diff = order->remainingQty - newQty;
        order->remainingQty = newQty;
        if (order->side == Side::BUY) {
            m_bids[order->price].decreaseQuantity(diff);
        } else {
            m_asks[order->price].decreaseQuantity(diff);
        }
        return true;
    } else if (newQty > order->remainingQty) {
        // Increasing quantity loses queue priority (must re-queue)
        Side side = order->side;
        Price price = order->price;
        cancelOrder(id);
        addOrder(id, side, OrderType::LIMIT, price, newQty, currentTimestampNs());
        return true;
    }

    return true; // No change
}

L2Snapshot OrderBook::getL2Snapshot(size_t depth) const {
    L2Snapshot snapshot;
    snapshot.timestamp = currentTimestampNs();
    snapshot.bids.reserve(depth);
    snapshot.asks.reserve(depth);

    size_t count = 0;
    for (const auto& [price, level] : m_bids) {
        if (count++ >= depth) break;
        snapshot.bids.push_back(LevelSummary{
            .price = price,
            .quantity = level.totalQuantity(),
            .orderCount = level.orderCount()
        });
    }

    count = 0;
    for (const auto& [price, level] : m_asks) {
        if (count++ >= depth) break;
        snapshot.asks.push_back(LevelSummary{
            .price = price,
            .quantity = level.totalQuantity(),
            .orderCount = level.orderCount()
        });
    }

    return snapshot;
}

} // namespace nexus

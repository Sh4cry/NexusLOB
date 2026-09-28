#pragma once

#include "Order.hpp"
#include <cstdint>

namespace nexus {

class PriceLevel {
public:
    explicit PriceLevel(Price p = 0) : m_price(p) {}

    Price price() const noexcept { return m_price; }
    Quantity totalQuantity() const noexcept { return m_totalQty; }
    uint32_t orderCount() const noexcept { return m_orderCount; }
    bool isEmpty() const noexcept { return m_head == nullptr; }
    Order* head() noexcept { return m_head; }
    const Order* head() const noexcept { return m_head; }

    // O(1) append to the end of the queue (FIFO Price-Time Priority)
    void append(Order* order) noexcept {
        if (!order) return;
        order->prev = m_tail;
        order->next = nullptr;
        if (m_tail) {
            m_tail->next = order;
        } else {
            m_head = order;
        }
        m_tail = order;
        m_totalQty += order->remainingQty;
        ++m_orderCount;
    }

    // O(1) unlinking of an order from anywhere in the queue
    void remove(Order* order) noexcept {
        if (!order) return;

        if (order->prev) {
            order->prev->next = order->next;
        } else {
            m_head = order->next;
        }

        if (order->next) {
            order->next->prev = order->prev;
        } else {
            m_tail = order->prev;
        }

        m_totalQty -= order->remainingQty;
        if (m_orderCount > 0) {
            --m_orderCount;
        }

        order->prev = nullptr;
        order->next = nullptr;
    }

    void decreaseQuantity(Quantity qty) noexcept {
        if (qty > m_totalQty) {
            m_totalQty = 0;
        } else {
            m_totalQty -= qty;
        }
    }

private:
    Price m_price{0};
    Quantity m_totalQty{0};
    uint32_t m_orderCount{0};
    Order* m_head{nullptr};
    Order* m_tail{nullptr};
};

} // namespace nexus

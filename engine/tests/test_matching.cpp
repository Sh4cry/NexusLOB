#include "OrderBook.hpp"
#include <iostream>
#include <cassert>

using namespace nexus;

void testBasicInsertion() {
    std::cout << "[TEST] Running testBasicInsertion... ";
    OrderBook book;
    auto trades = book.addOrder(1, Side::BUY, OrderType::LIMIT, 10000, 50);
    assert(trades.empty());
    assert(book.orderCount() == 1);
    assert(book.hasOrder(1));
    assert(book.getBestBid().value() == 10000);
    assert(!book.getBestAsk().has_value());
    assert(book.getBidVolume() == 50);
    std::cout << "PASSED\n";
}

void testExactMatch() {
    std::cout << "[TEST] Running testExactMatch... ";
    OrderBook book;
    // Maker Sell: 100 units at $100.00 (10000)
    book.addOrder(1, Side::SELL, OrderType::LIMIT, 10000, 100);
    assert(book.getBestAsk().value() == 10000);

    // Taker Buy: 100 units at $100.00
    auto trades = book.addOrder(2, Side::BUY, OrderType::LIMIT, 10000, 100);
    assert(trades.size() == 1);
    assert(trades[0].makerOrderId == 1);
    assert(trades[0].takerOrderId == 2);
    assert(trades[0].price == 10000);
    assert(trades[0].quantity == 100);
    assert(book.orderCount() == 0);
    assert(!book.getBestBid().has_value());
    assert(!book.getBestAsk().has_value());
    std::cout << "PASSED\n";
}

void testPriceTimePriorityFIFO() {
    std::cout << "[TEST] Running testPriceTimePriorityFIFO... ";
    OrderBook book;
    // Two makers at same price: $50.00
    book.addOrder(101, Side::SELL, OrderType::LIMIT, 5000, 40); // First
    book.addOrder(102, Side::SELL, OrderType::LIMIT, 5000, 60); // Second

    // Taker buys 50: Should fully fill 101 (40) and partially fill 102 (10)
    auto trades = book.addOrder(201, Side::BUY, OrderType::LIMIT, 5000, 50);
    assert(trades.size() == 2);
    assert(trades[0].makerOrderId == 101);
    assert(trades[0].quantity == 40);
    assert(trades[1].makerOrderId == 102);
    assert(trades[1].quantity == 10);

    // Remaining in book should be 102 with 50 units
    assert(book.orderCount() == 1);
    assert(book.hasOrder(102));
    assert(book.getOrder(102)->remainingQty == 50);
    std::cout << "PASSED\n";
}

void testPriceImprovement() {
    std::cout << "[TEST] Running testPriceImprovement... ";
    OrderBook book;
    // Maker Sell at $100.00
    book.addOrder(1, Side::SELL, OrderType::LIMIT, 10000, 10);
    // Taker aggressively bids $105.00 -> should execute at maker's price ($100.00)
    auto trades = book.addOrder(2, Side::BUY, OrderType::LIMIT, 10500, 10);
    assert(trades.size() == 1);
    assert(trades[0].price == 10000);
    assert(book.orderCount() == 0);
    std::cout << "PASSED\n";
}

void testOrderCancellation() {
    std::cout << "[TEST] Running testOrderCancellation... ";
    OrderBook book;
    book.addOrder(1, Side::BUY, OrderType::LIMIT, 20000, 30);
    book.addOrder(2, Side::BUY, OrderType::LIMIT, 19900, 50);
    assert(book.orderCount() == 2);
    assert(book.getBestBid().value() == 20000);

    bool cancelled = book.cancelOrder(1);
    assert(cancelled);
    assert(book.orderCount() == 1);
    assert(!book.hasOrder(1));
    assert(book.getBestBid().value() == 19900);

    bool cancelNonExistent = book.cancelOrder(999);
    assert(!cancelNonExistent);
    std::cout << "PASSED\n";
}

void testOrderModification() {
    std::cout << "[TEST] Running testOrderModification... ";
    OrderBook book;
    book.addOrder(1, Side::BUY, OrderType::LIMIT, 30000, 100);
    
    // Reduce size: keeps priority, reduces book volume
    bool modSuccess = book.modifyOrder(1, 60);
    assert(modSuccess);
    assert(book.getOrder(1)->remainingQty == 60);
    assert(book.getBidVolume() == 60);
    std::cout << "PASSED\n";
}

void testMarketOrder() {
    std::cout << "[TEST] Running testMarketOrder... ";
    OrderBook book;
    book.addOrder(1, Side::SELL, OrderType::LIMIT, 1000, 20);
    book.addOrder(2, Side::SELL, OrderType::LIMIT, 1010, 30);

    // Market Buy for 40 units: sweeps level 1000 (20) and level 1010 (20)
    auto trades = book.addOrder(3, Side::BUY, OrderType::MARKET, 0, 40);
    assert(trades.size() == 2);
    assert(trades[0].price == 1000 && trades[0].quantity == 20);
    assert(trades[1].price == 1010 && trades[1].quantity == 20);
    assert(book.orderCount() == 1);
    assert(book.getOrder(2)->remainingQty == 10);
    std::cout << "PASSED\n";
}

void testFillOrKill() {
    std::cout << "[TEST] Running testFillOrKill... ";
    OrderBook book;
    book.addOrder(1, Side::SELL, OrderType::LIMIT, 5000, 30);

    // FOK for 50 units (insufficient liquidity) -> killed immediately
    auto trades1 = book.addOrder(2, Side::BUY, OrderType::FOK, 5000, 50);
    assert(trades1.empty());
    assert(book.orderCount() == 1); // Order 1 unaffected

    // FOK for 30 units (exact match available) -> fills
    auto trades2 = book.addOrder(3, Side::BUY, OrderType::FOK, 5000, 30);
    assert(trades2.size() == 1);
    assert(book.orderCount() == 0);
    std::cout << "PASSED\n";
}

int main() {
    std::cout << "==========================================\n";
    std::cout << "   NexusLOB Matching Engine Unit Tests    \n";
    std::cout << "==========================================\n";

    testBasicInsertion();
    testExactMatch();
    testPriceTimePriorityFIFO();
    testPriceImprovement();
    testOrderCancellation();
    testOrderModification();
    testMarketOrder();
    testFillOrKill();

    std::cout << "==========================================\n";
    std::cout << "   ALL 8 TEST SUITES PASSED CLEANLY!      \n";
    std::cout << "==========================================\n";
    return 0;
}

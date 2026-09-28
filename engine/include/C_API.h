#pragma once

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#ifdef _WIN32
#define NEXUS_EXPORT __declspec(dllexport)
#else
#define NEXUS_EXPORT __attribute__((visibility("default")))
#endif

#pragma pack(push, 1)
typedef struct {
    uint64_t makerOrderId;
    uint64_t takerOrderId;
    uint8_t takerSide;
    uint32_t price;
    uint32_t quantity;
    uint64_t timestamp;
} CTrade;

typedef struct {
    uint32_t price;
    uint32_t quantity;
    uint32_t orderCount;
} CLevel;
#pragma pack(pop)

NEXUS_EXPORT void* nexus_create_book(uint32_t capacity);
NEXUS_EXPORT void nexus_destroy_book(void* bookPtr);
NEXUS_EXPORT void nexus_clear_book(void* bookPtr);

NEXUS_EXPORT int nexus_add_order(
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
);

NEXUS_EXPORT bool nexus_cancel_order(void* bookPtr, uint64_t id);
NEXUS_EXPORT bool nexus_modify_order(void* bookPtr, uint64_t id, uint32_t newQty);
NEXUS_EXPORT bool nexus_has_order(void* bookPtr, uint64_t id);

NEXUS_EXPORT uint32_t nexus_order_count(void* bookPtr);
NEXUS_EXPORT bool nexus_get_bbo(void* bookPtr, uint32_t* outBid, uint32_t* outAsk);

NEXUS_EXPORT void nexus_get_l2_depth(
    void* bookPtr,
    uint32_t maxLevels,
    CLevel* outBids,
    uint32_t* outBidCount,
    CLevel* outAsks,
    uint32_t* outAskCount
);

#ifdef __cplusplus
}
#endif

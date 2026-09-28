#pragma once

#include "Order.hpp"
#include <vector>
#include <memory>
#include <stdexcept>
#include <cassert>

namespace nexus {

template <typename T, size_t BlockSize = 100000>
class MemoryPool {
public:
    explicit MemoryPool(size_t initialCapacity = BlockSize) {
        allocateBlock(initialCapacity);
    }

    ~MemoryPool() = default;

    // Non-copyable
    MemoryPool(const MemoryPool&) = delete;
    MemoryPool& operator=(const MemoryPool&) = delete;

    // O(1) allocation from free list
    T* allocate() {
        if (m_freeList.empty()) {
            allocateBlock(BlockSize);
        }
        T* ptr = m_freeList.back();
        m_freeList.pop_back();
        ptr->reset();
        ++m_activeAllocations;
        return ptr;
    }

    // O(1) return to free list
    void deallocate(T* ptr) {
        if (ptr == nullptr) return;
        ptr->reset();
        m_freeList.push_back(ptr);
        --m_activeAllocations;
    }

    size_t activeCount() const noexcept {
        return m_activeAllocations;
    }

    size_t totalCapacity() const noexcept {
        return m_totalCapacity;
    }

private:
    void allocateBlock(size_t size) {
        auto block = std::make_unique<T[]>(size);
        m_freeList.reserve(m_freeList.size() + size);
        for (size_t i = 0; i < size; ++i) {
            m_freeList.push_back(&block[i]);
        }
        m_blocks.push_back(std::move(block));
        m_totalCapacity += size;
    }

    std::vector<std::unique_ptr<T[]>> m_blocks;
    std::vector<T*> m_freeList;
    size_t m_activeAllocations{0};
    size_t m_totalCapacity{0};
};

using OrderPool = MemoryPool<Order>;

} // namespace nexus

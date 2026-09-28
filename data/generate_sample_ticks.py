import csv
import random
import time

def generate_sample_ticks(filename="d:/nexus-lob/data/sample_btc_ticks.csv", num_ticks=2000):
    mid = 65000.0
    now = time.time_ns()

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "side", "price", "quantity", "order_type"])

        for i in range(num_ticks):
            # Random walk with momentum
            drift = random.choice([-5.0, -2.5, 0.0, 2.5, 5.0])
            mid += drift
            side = random.choice(["BUY", "SELL"])
            offset = random.randint(1, 10) * 0.5
            price = round(mid - offset if side == "BUY" else mid + offset, 2)
            qty = random.randint(1, 15)
            # 85% limit quotes, 15% market sweeps
            order_type = "MARKET" if random.random() < 0.15 else "LIMIT"
            ts = now + (i * 50_000_000) # 50ms intervals

            writer.writerow([ts, side, price, qty, order_type])

    print(f"Generated {num_ticks} sample ticks at {filename}")

if __name__ == "__main__":
    generate_sample_ticks()

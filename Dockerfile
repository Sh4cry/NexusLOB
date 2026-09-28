# Stage 1: Build C++ Matching Engine
FROM gcc:13-bookworm AS engine-builder
WORKDIR /app/engine
COPY engine/ .
RUN g++ -std=c++20 -O3 -shared -fPIC -I include src/OrderBook.cpp src/C_API.cpp -o libnexus_engine.so
RUN g++ -std=c++20 -O3 -I include src/OrderBook.cpp tests/test_matching.cpp -o test_matching && ./test_matching

# Stage 2: Build Frontend
FROM node:20-bookworm-slim AS web-builder
WORKDIR /app/web
COPY web/package.json ./
RUN npm install
COPY web/ .
RUN npm run build

# Stage 3: Runtime
FROM python:3.11-slim-bookworm AS runtime
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

COPY server/requirements.txt server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

COPY server/ server/
COPY --from=engine-builder /app/engine/libnexus_engine.so engine/libnexus_engine.so
COPY --from=web-builder /app/web/dist web/dist

EXPOSE 8000
ENV PYTHONPATH=/app/server

CMD ["uvicorn", "server.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

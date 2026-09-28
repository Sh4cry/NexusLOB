export interface LevelSummary {
  price: number;
  quantity: number;
  order_count: number;
}

export interface L2Snapshot {
  timestamp_ns: number;
  symbol: string;
  bids: LevelSummary[];
  asks: LevelSummary[];
  best_bid: number | null;
  best_ask: number | null;
  spread: number | null;
  mid_price: number | null;
}

export interface Trade {
  maker_order_id: number;
  taker_order_id: number;
  taker_side: 'BUY' | 'SELL';
  price: number;
  quantity: number;
  timestamp_ns: number;
}

export interface ModelMetadata {
  model_name?: string;
  inventory?: number;
  mid_price?: number;
  reservation_price?: number;
  volatility?: number;
  optimal_spread?: number;
  cash?: number;
  total_pnl?: number;
  markov_state?: number;
  state_name?: string;
  file?: string;
  progress_pct?: number;
}

export interface SimState {
  running: boolean;
  active_mode: 'AVELLANEDA_STOIKOV' | 'MARKOV' | 'DATA_REPLAY';
  metadata: ModelMetadata;
}

export interface MarketDataMessage {
  type: string;
  data: L2Snapshot;
  recent_trades: Trade[];
  order_count: number;
  sim_state: SimState;
  backend: string;
}

export interface StressTestMetrics {
  total_orders: number;
  total_trades: number;
  elapsed_seconds: number;
  throughput_ops_sec: number;
  p50_us: number;
  p95_us: number;
  p99_us: number;
}

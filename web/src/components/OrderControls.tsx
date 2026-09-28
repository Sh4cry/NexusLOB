import React, { useState } from 'react';
import { Play, Pause, Zap, Send, Loader2, CheckCircle2 } from 'lucide-react';
import { StressTestMetrics } from '../types';

interface OrderControlsProps {
  selectedPrice: number | null;
  simRunning: boolean;
  onToggleSim: (running: boolean) => void;
  onUpdateMetrics: (metrics: StressTestMetrics) => void;
}

export const OrderControls: React.FC<OrderControlsProps> = ({
  selectedPrice,
  simRunning,
  onToggleSim,
  onUpdateMetrics,
}) => {
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [orderType, setOrderType] = useState<'LIMIT' | 'MARKET'>('LIMIT');
  const [price, setPrice] = useState<string>('100.00');
  const [quantity, setQuantity] = useState<string>('50');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isStressTesting, setIsStressTesting] = useState<boolean>(false);
  const [lastOrderMsg, setLastOrderMsg] = useState<string | null>(null);

  // Sync selected price from ladder click
  React.useEffect(() => {
    if (selectedPrice !== null) {
      setPrice(selectedPrice.toFixed(2));
    }
  }, [selectedPrice]);

  const handlePlaceOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    const numPrice = parseFloat(price);
    const numQty = parseInt(quantity, 10);
    if (isNaN(numPrice) || isNaN(numQty) || numQty <= 0) return;

    setIsSubmitting(true);
    setLastOrderMsg(null);
    try {
      const res = await fetch('/api/v1/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          side,
          order_type: orderType,
          price: numPrice,
          quantity: numQty,
        }),
      });
      const data = await res.json();
      setLastOrderMsg(`Order #${data.id} ${data.status} (${data.trades_count} fills)`);
      setTimeout(() => setLastOrderMsg(null), 4000);
    } catch (err) {
      console.error(err);
      setLastOrderMsg('Failed to place order');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRunStressTest = async () => {
    setIsStressTesting(true);
    try {
      const res = await fetch('/api/v1/stress-test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_count: 10000 }),
      });
      const data = await res.json();
      onUpdateMetrics(data);
    } catch (err) {
      console.error('Stress test failed', err);
    } finally {
      setIsStressTesting(false);
    }
  };

  return (
    <div className="bg-surface rounded-xl border border-surfaceBorder p-4 flex flex-col gap-4 shadow-lg">
      <div className="flex items-center justify-between border-b border-surfaceBorder/60 pb-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
          Order Execution & Controls
        </h2>
        
        {/* Market Maker Simulation Toggle */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => onToggleSim(!simRunning)}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all ${
              simRunning
                ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30 hover:bg-amber-500/20'
                : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20'
            }`}
          >
            {simRunning ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            <span>{simRunning ? 'Pause Market Maker' : 'Resume Flow'}</span>
          </button>
        </div>
      </div>

      {/* Manual Order Placement Form */}
      <form onSubmit={handlePlaceOrder} className="flex flex-col gap-3">
        {/* Side Tabs */}
        <div className="grid grid-cols-2 gap-2 bg-background p-1 rounded-lg border border-surfaceBorder">
          <button
            type="button"
            onClick={() => setSide('BUY')}
            className={`py-1.5 text-xs font-bold rounded-md transition-all ${
              side === 'BUY'
                ? 'bg-bidGreen text-black shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            BUY (BID)
          </button>
          <button
            type="button"
            onClick={() => setSide('SELL')}
            className={`py-1.5 text-xs font-bold rounded-md transition-all ${
              side === 'SELL'
                ? 'bg-askRed text-white shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            SELL (ASK)
          </button>
        </div>

        {/* Order Type Tabs */}
        <div className="flex items-center gap-2 text-xs">
          <button
            type="button"
            onClick={() => setOrderType('LIMIT')}
            className={`flex-1 py-1 rounded border text-[11px] font-mono font-medium transition-colors ${
              orderType === 'LIMIT'
                ? 'bg-brandCyan/10 border-brandCyan/40 text-brandCyan'
                : 'border-surfaceBorder text-slate-400 hover:border-slate-600'
            }`}
          >
            LIMIT
          </button>
          <button
            type="button"
            onClick={() => setOrderType('MARKET')}
            className={`flex-1 py-1 rounded border text-[11px] font-mono font-medium transition-colors ${
              orderType === 'MARKET'
                ? 'bg-brandCyan/10 border-brandCyan/40 text-brandCyan'
                : 'border-surfaceBorder text-slate-400 hover:border-slate-600'
            }`}
          >
            MARKET
          </button>
        </div>

        {/* Price & Quantity Inputs */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-[10px] text-slate-400 font-mono block mb-1">
              PRICE ($) {orderType === 'MARKET' && '(BEST EXEC)'}
            </label>
            <input
              type="number"
              step="0.01"
              disabled={orderType === 'MARKET'}
              value={orderType === 'MARKET' ? '' : price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="100.00"
              className="w-full bg-background border border-surfaceBorder rounded-md px-3 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-brandCyan disabled:opacity-50"
            />
          </div>

          <div>
            <label className="text-[10px] text-slate-400 font-mono block mb-1">QUANTITY</label>
            <input
              type="number"
              min="1"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder="50"
              className="w-full bg-background border border-surfaceBorder rounded-md px-3 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-brandCyan"
            />
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isSubmitting}
          className={`w-full py-2 rounded-lg font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all ${
            side === 'BUY'
              ? 'bg-bidGreen hover:bg-bidGreen/90 text-black shadow-lg shadow-bidGreen/20'
              : 'bg-askRed hover:bg-askRed/90 text-white shadow-lg shadow-askRed/20'
          }`}
        >
          {isSubmitting ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Send className="w-3.5 h-3.5" />
          )}
          <span>{side === 'BUY' ? 'Submit Buy Order' : 'Submit Sell Order'}</span>
        </button>

        {lastOrderMsg && (
          <div className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded border border-emerald-500/20 animate-fade-in">
            <CheckCircle2 className="w-3 h-3" />
            <span>{lastOrderMsg}</span>
          </div>
        )}
      </form>

      {/* Autonomous Background Screen & Web Agent Panel */}
      <div className="border-t border-surfaceBorder/60 pt-3 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
            <span className="w-2 h-2 rounded-full bg-brandCyan animate-pulse inline-block" />
            <span>Autonomous Screen & Web Agent</span>
          </div>
          <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
            Zero-Screenshot
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2 mt-1">
          <button
            type="button"
            onClick={async () => {
              try {
                const res = await fetch('/api/v1/agent/scan-screen', { method: 'POST' });
                const d = await res.json();
                setLastOrderMsg(`Screen Scan: ${d.symbol} @ $${d.mid_price}`);
                setTimeout(() => setLastOrderMsg(null), 4000);
              } catch (e) {
                console.error(e);
              }
            }}
            className="py-1.5 px-2 bg-surfaceBorder/50 hover:bg-surfaceBorder text-slate-200 rounded text-[11px] font-mono transition-colors text-center border border-surfaceBorder"
          >
            🔍 Scan Screen Now
          </button>

          <button
            type="button"
            onClick={async () => {
              try {
                const res = await fetch('/api/v1/agent/start?mode=WEB_FEED&symbol=BTCUSDT', { method: 'POST' });
                const d = await res.json();
                setLastOrderMsg(`Live Agent Started (BTCUSDT)`);
                setTimeout(() => setLastOrderMsg(null), 4000);
              } catch (e) {
                console.error(e);
              }
            }}
            className="py-1.5 px-2 bg-brandCyan/10 hover:bg-brandCyan/20 text-brandCyan rounded text-[11px] font-mono transition-colors text-center border border-brandCyan/30"
          >
            ⚡ Stream Live Web
          </button>
        </div>
        <p className="text-[10px] text-slate-500">
          Directly reads UI element trees & web feeds into the C++ engine without pixel capture
        </p>
      </div>

      {/* Stress Benchmark Button */}
      <div className="border-t border-surfaceBorder/60 pt-3">
        <button
          onClick={handleRunStressTest}
          disabled={isStressTesting}
          className="w-full bg-gradient-to-r from-indigo-600 to-brandCyan hover:from-indigo-500 hover:to-cyan-400 text-white py-2 px-3 rounded-lg font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/20 transition-all disabled:opacity-50"
        >
          {isStressTesting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Zap className="w-4 h-4 text-amber-300" />
          )}
          <span>{isStressTesting ? 'Executing 10,000 Orders...' : '⚡ Run 10,000 Order Stress Test'}</span>
        </button>
        <p className="text-[10px] text-slate-500 text-center mt-1.5">
          Benchmarks real-time matching throughput and p99 tail latency live in C++20
        </p>
      </div>
    </div>
  );
};

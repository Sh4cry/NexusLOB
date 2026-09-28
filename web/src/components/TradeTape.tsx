import React from 'react';
import { Trade } from '../types';

interface TradeTapeProps {
  trades: Trade[];
}

export const TradeTape: React.FC<TradeTapeProps> = ({ trades }) => {
  return (
    <div className="bg-surface rounded-xl border border-surfaceBorder overflow-hidden flex flex-col h-full shadow-lg">
      <div className="px-4 py-2.5 border-b border-surfaceBorder flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
          Trade Tape <span className="text-slate-500 font-mono">(Executions)</span>
        </h2>
        <span className="text-[11px] text-slate-500 font-mono">Real-time</span>
      </div>

      <div className="grid grid-cols-4 px-3 py-1.5 text-[11px] font-mono text-slate-500 border-b border-surfaceBorder/60 bg-background/40">
        <div>TIME</div>
        <div className="text-right">PRICE ($)</div>
        <div className="text-right">SIZE</div>
        <div className="text-right">SIDE</div>
      </div>

      <div className="flex-1 overflow-y-auto font-mono text-xs divide-y divide-surfaceBorder/20">
        {trades.length === 0 ? (
          <div className="p-6 text-center text-slate-500 text-xs font-sans">
            No executions yet. Awaiting trades...
          </div>
        ) : (
          trades.map((tr, idx) => {
            const date = new Date(tr.timestamp_ns / 1_000_000);
            const timeStr = date.toTimeString().split(' ')[0] + '.' + String(date.getMilliseconds()).padStart(3, '0');
            const isBuy = tr.taker_side === 'BUY';

            return (
              <div
                key={`trade-${tr.taker_order_id}-${tr.timestamp_ns}-${idx}`}
                className={`grid grid-cols-4 px-3 py-1 items-center hover:bg-white/5 transition-colors ${
                  idx === 0 ? (isBuy ? 'flash-buy' : 'flash-sell') : ''
                }`}
              >
                <div className="text-slate-400 text-[11px]">{timeStr}</div>
                <div className={`text-right font-semibold ${isBuy ? 'text-bidGreen' : 'text-askRed'}`}>
                  {tr.price.toFixed(2)}
                </div>
                <div className="text-right text-slate-200">
                  {tr.quantity.toLocaleString()}
                </div>
                <div className="text-right">
                  <span className={`inline-block px-1.5 py-0.2 rounded text-[10px] font-bold ${
                    isBuy ? 'bg-bidGreen/10 text-bidGreen border border-bidGreen/20' : 'bg-askRed/10 text-askRed border border-askRed/20'
                  }`}>
                    {tr.taker_side}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

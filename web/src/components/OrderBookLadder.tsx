import React, { useMemo } from 'react';
import { L2Snapshot } from '../types';

interface OrderBookLadderProps {
  snapshot: L2Snapshot | null;
  onSelectPrice: (price: number) => void;
}

export const OrderBookLadder: React.FC<OrderBookLadderProps> = ({ snapshot, onSelectPrice }) => {
  const bids = snapshot?.bids ?? [];
  const asks = snapshot?.asks ?? [];

  // Calculate cumulative volumes
  const { asksWithCumulative, maxAskCum } = useMemo(() => {
    let cum = 0;
    // Asks are displayed with highest ask at top down to lowest ask near spread
    const reversed = [...asks].slice(0, 10).reverse();
    const withCum = reversed.map((item) => {
      cum += item.quantity;
      return { ...item, cumulative: cum };
    });
    return { asksWithCumulative: withCum, maxAskCum: cum || 1 };
  }, [asks]);

  const { bidsWithCumulative, maxBidCum } = useMemo(() => {
    let cum = 0;
    const sliced = bids.slice(0, 10);
    const withCum = sliced.map((item) => {
      cum += item.quantity;
      return { ...item, cumulative: cum };
    });
    return { bidsWithCumulative: withCum, maxBidCum: cum || 1 };
  }, [bids]);

  const maxTotalVolume = Math.max(maxAskCum, maxBidCum, 1);

  return (
    <div className="bg-surface rounded-xl border border-surfaceBorder overflow-hidden flex flex-col h-full shadow-lg">
      <div className="px-4 py-2.5 border-b border-surfaceBorder flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
          Order Book <span className="text-slate-500 font-mono">(L2 Depth)</span>
        </h2>
        <span className="text-[11px] text-slate-500 font-mono">10 Levels</span>
      </div>

      {/* Column Headers */}
      <div className="grid grid-cols-4 px-3 py-1.5 text-[11px] font-mono text-slate-500 border-b border-surfaceBorder/60 bg-background/40">
        <div>PRICE ($)</div>
        <div className="text-right">SIZE</div>
        <div className="text-right">TOTAL</div>
        <div className="text-right">ORDERS</div>
      </div>

      {/* Ladder Content */}
      <div className="flex-1 overflow-y-auto font-mono text-xs flex flex-col justify-between py-1">
        {/* Asks (Sells) */}
        <div className="flex flex-col gap-[1px]">
          {asksWithCumulative.map((ask) => {
            const depthPercent = Math.min(100, Math.round((ask.cumulative / maxTotalVolume) * 100));
            return (
              <div
                key={`ask-${ask.price}`}
                onClick={() => onSelectPrice(ask.price)}
                className="grid grid-cols-4 px-3 py-0.5 hover:bg-white/5 cursor-pointer relative items-center transition-colors group"
              >
                {/* Visual Depth Bar */}
                <div
                  className="absolute right-0 top-0 bottom-0 bg-askRed/15 transition-all duration-150 pointer-events-none"
                  style={{ width: `${depthPercent}%` }}
                />
                <div className="text-askRed font-semibold relative z-10">
                  {ask.price.toFixed(2)}
                </div>
                <div className="text-right text-slate-300 relative z-10">
                  {ask.quantity.toLocaleString()}
                </div>
                <div className="text-right text-slate-400 relative z-10 text-[11px]">
                  {ask.cumulative.toLocaleString()}
                </div>
                <div className="text-right text-slate-500 relative z-10 text-[10px]">
                  {ask.order_count}
                </div>
              </div>
            );
          })}
        </div>

        {/* Spread / Mid-Price Bar */}
        <div className="my-1.5 mx-2 py-1 px-3 rounded bg-background border border-surfaceBorder flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-2">
            <span className="text-slate-500 uppercase text-[10px] font-sans font-semibold">Spread</span>
            <span className="font-bold text-slate-200">
              ${snapshot?.spread ? snapshot.spread.toFixed(2) : '0.00'}
            </span>
          </div>
          <div className="text-brandCyan font-bold">
            ${snapshot?.mid_price ? snapshot.mid_price.toFixed(2) : '---.--'}
          </div>
        </div>

        {/* Bids (Buys) */}
        <div className="flex flex-col gap-[1px]">
          {bidsWithCumulative.map((bid) => {
            const depthPercent = Math.min(100, Math.round((bid.cumulative / maxTotalVolume) * 100));
            return (
              <div
                key={`bid-${bid.price}`}
                onClick={() => onSelectPrice(bid.price)}
                className="grid grid-cols-4 px-3 py-0.5 hover:bg-white/5 cursor-pointer relative items-center transition-colors group"
              >
                {/* Visual Depth Bar */}
                <div
                  className="absolute right-0 top-0 bottom-0 bg-bidGreen/15 transition-all duration-150 pointer-events-none"
                  style={{ width: `${depthPercent}%` }}
                />
                <div className="text-bidGreen font-semibold relative z-10">
                  {bid.price.toFixed(2)}
                </div>
                <div className="text-right text-slate-300 relative z-10">
                  {bid.quantity.toLocaleString()}
                </div>
                <div className="text-right text-slate-400 relative z-10 text-[11px]">
                  {bid.cumulative.toLocaleString()}
                </div>
                <div className="text-right text-slate-500 relative z-10 text-[10px]">
                  {bid.order_count}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

import React, { useRef, useEffect } from 'react';
import { L2Snapshot } from '../types';

interface DepthChartProps {
  snapshot: L2Snapshot | null;
}

export const DepthChart: React.FC<DepthChartProps> = ({ snapshot }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Handle HiDPI displays
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;

    ctx.clearRect(0, 0, width, height);

    if (!snapshot || !snapshot.bids.length || !snapshot.asks.length) {
      ctx.fillStyle = '#64748B';
      ctx.font = '12px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText('Awaiting order book liquidity...', width / 2, height / 2);
      return;
    }

    // Cumulative bid volume
    let bidCum = 0;
    const bidPoints = snapshot.bids.map((b) => {
      bidCum += b.quantity;
      return { price: b.price, cum: bidCum };
    });

    // Cumulative ask volume
    let askCum = 0;
    const askPoints = snapshot.asks.map((a) => {
      askCum += a.quantity;
      return { price: a.price, cum: askCum };
    });

    const maxVolume = Math.max(bidCum, askCum, 1) * 1.1;
    const minPrice = bidPoints[bidPoints.length - 1].price;
    const maxPrice = askPoints[askPoints.length - 1].price;
    const priceRange = Math.max(maxPrice - minPrice, 0.01);

    const midX = width / 2;
    const bottomY = height - 20;

    // Helper to map price to X coordinate
    const getX = (price: number) => {
      return ((price - minPrice) / priceRange) * width;
    };

    // Helper to map volume to Y coordinate
    const getY = (volume: number) => {
      return bottomY - (volume / maxVolume) * (bottomY - 20);
    };

    // --- Draw Bids (Green Mountain) ---
    ctx.beginPath();
    ctx.moveTo(getX(bidPoints[bidPoints.length - 1].price), bottomY);

    for (let i = bidPoints.length - 1; i >= 0; i--) {
      const pt = bidPoints[i];
      const px = getX(pt.price);
      const py = getY(pt.cum);
      ctx.lineTo(px, py);
    }

    // Drop to bottom at mid
    ctx.lineTo(midX, bottomY);
    ctx.closePath();

    const bidGrad = ctx.createLinearGradient(0, 0, 0, bottomY);
    bidGrad.addColorStop(0, 'rgba(0, 242, 157, 0.4)');
    bidGrad.addColorStop(1, 'rgba(0, 242, 157, 0.02)');
    ctx.fillStyle = bidGrad;
    ctx.fill();

    ctx.strokeStyle = '#00F29D';
    ctx.lineWidth = 2;
    ctx.stroke();

    // --- Draw Asks (Red Mountain) ---
    ctx.beginPath();
    ctx.moveTo(midX, bottomY);

    for (let i = 0; i < askPoints.length; i++) {
      const pt = askPoints[i];
      const px = getX(pt.price);
      const py = getY(pt.cum);
      ctx.lineTo(px, py);
    }

    ctx.lineTo(getX(askPoints[askPoints.length - 1].price), bottomY);
    ctx.closePath();

    const askGrad = ctx.createLinearGradient(0, 0, 0, bottomY);
    askGrad.addColorStop(0, 'rgba(255, 59, 105, 0.4)');
    askGrad.addColorStop(1, 'rgba(255, 59, 105, 0.02)');
    ctx.fillStyle = askGrad;
    ctx.fill();

    ctx.strokeStyle = '#FF3B69';
    ctx.lineWidth = 2;
    ctx.stroke();

    // --- Mid-Price Dotted Center Line ---
    ctx.strokeStyle = '#38BDF8';
    ctx.setLineDash([4, 4]);
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(midX, 10);
    ctx.lineTo(midX, bottomY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Price Labels
    ctx.fillStyle = '#94A3B8';
    ctx.font = '10px "JetBrains Mono", monospace';
    ctx.textAlign = 'left';
    ctx.fillText(`$${minPrice.toFixed(2)}`, 10, height - 6);

    ctx.textAlign = 'center';
    ctx.fillStyle = '#38BDF8';
    ctx.fillText(`MID $${(snapshot.mid_price ?? 0).toFixed(2)}`, midX, height - 6);

    ctx.textAlign = 'right';
    ctx.fillStyle = '#94A3B8';
    ctx.fillText(`$${maxPrice.toFixed(2)}`, width - 10, height - 6);

  }, [snapshot]);

  return (
    <div className="bg-surface rounded-xl border border-surfaceBorder p-4 flex flex-col h-full shadow-lg">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
          Market Depth Chart <span className="text-slate-500 font-mono">(Liquidity Walls)</span>
        </h2>
        <div className="flex items-center gap-4 text-[11px] font-mono">
          <div className="flex items-center gap-1.5 text-bidGreen">
            <span className="w-2.5 h-2.5 rounded-sm bg-bidGreen/40 border border-bidGreen inline-block" />
            <span>Bids (Cumulative)</span>
          </div>
          <div className="flex items-center gap-1.5 text-askRed">
            <span className="w-2.5 h-2.5 rounded-sm bg-askRed/40 border border-askRed inline-block" />
            <span>Asks (Cumulative)</span>
          </div>
        </div>
      </div>

      <div className="flex-1 w-full min-h-[220px] relative">
        <canvas ref={canvasRef} className="w-full h-full block" />
      </div>
    </div>
  );
};

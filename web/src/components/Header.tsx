import React from 'react';
import { Activity, Cpu, Zap, Wifi, WifiOff, TrendingUp, Layers, Database } from 'lucide-react';
import { L2Snapshot, SimState } from '../types';

interface HeaderProps {
  snapshot: L2Snapshot | null;
  simState: SimState | null;
  backend: string;
  orderCount: number;
  isConnected: boolean;
  onSelectModel: (mode: 'AVELLANEDA_STOIKOV' | 'MARKOV' | 'DATA_REPLAY') => void;
}

export const Header: React.FC<HeaderProps> = ({
  snapshot,
  simState,
  backend,
  orderCount,
  isConnected,
  onSelectModel,
}) => {
  const midPrice = snapshot?.mid_price ?? 0;
  const spread = snapshot?.spread ?? 0;
  const spreadBps = midPrice > 0 ? ((spread / midPrice) * 10000).toFixed(1) : '0.0';

  const meta = simState?.metadata || {};
  const activeMode = simState?.active_mode || 'AVELLANEDA_STOIKOV';

  return (
    <header className="border-b border-surfaceBorder bg-surface/95 backdrop-blur px-6 py-3 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-50">
      {/* Brand & Market */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-brandCyan to-emerald-400 flex items-center justify-center font-black text-black text-base shadow-lg shadow-brandCyan/20">
            NL
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-base tracking-wide text-white">NOXUS<span className="text-brandCyan">LOB</span></h1>
              <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-brandCyan/10 text-brandCyan border border-brandCyan/20">
                v1.1
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Low-Latency C++20 Matching Engine</p>
          </div>
        </div>

        <div className="h-6 w-px bg-surfaceBorder hidden sm:block" />

        {/* Symbol & Mid Price */}
        <div className="flex items-center gap-4">
          <div>
            <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Symbol</div>
            <div className="text-sm font-bold font-mono text-slate-100 flex items-center gap-1.5">
              APEX/USD
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping inline-block" />
            </div>
          </div>

          <div>
            <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Mid Price</div>
            <div className="text-sm font-bold font-mono text-brandCyan">
              ${midPrice > 0 ? midPrice.toFixed(2) : '---.--'}
            </div>
          </div>

          <div>
            <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Spread</div>
            <div className="text-sm font-mono text-slate-200">
              ${spread.toFixed(2)} <span className="text-xs text-slate-400">({spreadBps} bps)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Model Selector & Quantitative Badges */}
      <div className="flex items-center gap-3 text-xs flex-wrap">
        {/* Model Switcher Dropdown */}
        <div className="flex items-center gap-1.5 bg-background border border-surfaceBorder rounded-lg px-2 py-1">
          <Layers className="w-3.5 h-3.5 text-brandCyan" />
          <span className="text-[11px] text-slate-400 font-mono hidden md:inline">Model:</span>
          <select
            value={activeMode}
            onChange={(e) => onSelectModel(e.target.value as any)}
            className="bg-transparent text-slate-200 text-xs font-semibold focus:outline-none cursor-pointer"
          >
            <option value="AVELLANEDA_STOIKOV" className="bg-surface text-slate-200">
              Avellaneda-Stoikov (Adaptive)
            </option>
            <option value="MARKOV" className="bg-surface text-slate-200">
              Markov Chain (Microstructure)
            </option>
            <option value="DATA_REPLAY" className="bg-surface text-slate-200">
              Historical Tick Replayer (CSV)
            </option>
          </select>
        </div>

        {/* Model-specific Telemetry Badge */}
        {activeMode === 'AVELLANEDA_STOIKOV' && (
          <div className="hidden lg:flex items-center gap-3 bg-background/80 px-3 py-1.5 rounded-md border border-surfaceBorder font-mono text-[11px]">
            <div>
              <span className="text-slate-400">Inventory (q): </span>
              <span className={`font-bold ${meta.inventory && meta.inventory > 0 ? 'text-emerald-400' : meta.inventory && meta.inventory < 0 ? 'text-askRed' : 'text-slate-200'}`}>
                {meta.inventory ?? 0}
              </span>
            </div>
            <span>•</span>
            <div>
              <span className="text-slate-400">Vol (σ): </span>
              <span className="text-brandCyan font-bold">{meta.volatility ? (meta.volatility * 100).toFixed(1) + '%' : '2.0%'}</span>
            </div>
            <span>•</span>
            <div>
              <span className="text-slate-400">PnL: </span>
              <span className={`font-bold ${meta.total_pnl && meta.total_pnl >= 0 ? 'text-emerald-400' : 'text-askRed'}`}>
                ${meta.total_pnl ? meta.total_pnl.toFixed(2) : '0.00'}
              </span>
            </div>
          </div>
        )}

        {activeMode === 'MARKOV' && meta.state_name && (
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-md border text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
            <Zap className="w-3.5 h-3.5" />
            <span>State: {meta.state_name}</span>
          </div>
        )}

        {activeMode === 'DATA_REPLAY' && (
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-md border text-[11px] font-semibold bg-indigo-500/10 text-indigo-400 border-indigo-500/20 font-mono">
            <Database className="w-3.5 h-3.5" />
            <span>Replay: {meta.file} ({meta.progress_pct}%)</span>
          </div>
        )}

        {/* Backend Indicator */}
        <div className="flex items-center gap-1.5 bg-background/80 px-3 py-1.5 rounded-md border border-surfaceBorder font-mono text-slate-300">
          <Cpu className="w-3.5 h-3.5 text-brandCyan" />
          <span>{backend}</span>
        </div>

        {/* Connection Indicator */}
        <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border ${
          isConnected 
            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
            : 'bg-red-500/10 text-red-400 border-red-500/20'
        }`}>
          {isConnected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
          <span className="font-medium text-[11px]">{isConnected ? 'LIVE WS' : 'DISCONNECTED'}</span>
        </div>
      </div>
    </header>
  );
};

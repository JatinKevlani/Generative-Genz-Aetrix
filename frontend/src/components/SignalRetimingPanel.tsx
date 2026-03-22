'use client';

import { SignalRetiming } from '@/types';
import { Timer, ArrowUp, ArrowDown, Minus, Loader2 } from 'lucide-react';

interface SignalRetimingPanelProps {
  signalRetiming: SignalRetiming[];
  loading: boolean;
}

export default function SignalRetimingPanel({
  signalRetiming,
  loading,
}: SignalRetimingPanelProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
          <Timer size={14} className="text-red-400" />
          Signal Re-Timing
        </h3>
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="p-3 bg-slate-800/50 border border-slate-700/50 rounded-lg animate-pulse"
          >
            <div className="h-4 bg-slate-700 rounded w-3/4 mb-2" />
            <div className="flex gap-3">
              <div className="h-10 bg-slate-700 rounded flex-1" />
              <div className="h-10 bg-slate-700 rounded flex-1" />
              <div className="h-10 bg-slate-700 rounded w-16" />
            </div>
            <div className="h-3 bg-slate-700 rounded w-full mt-2" />
          </div>
        ))}
        <p className="text-xs text-slate-500 text-center animate-pulse">
          Analyzing intersections…
        </p>
      </div>
    );
  }

  if (signalRetiming.length === 0) {
    return (
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
          <Timer size={14} className="text-red-400" />
          Signal Re-Timing
        </h3>
        <div className="p-4 bg-slate-800/30 border border-slate-700/30 rounded-lg text-center">
          <p className="text-xs text-slate-500">
            Declare an incident to generate signal re-timing recommendations.
          </p>
        </div>
      </div>
    );
  }

  // Sort by magnitude of change (largest first)
  const sorted = [...signalRetiming].sort(
    (a, b) =>
      Math.abs(b.recommended_green_seconds - b.current_green_seconds) -
      Math.abs(a.recommended_green_seconds - a.current_green_seconds)
  );

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
        <Timer size={14} className="text-red-400" />
        Signal Re-Timing
        <span className="ml-auto text-[10px] font-normal text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full">
          {sorted.length} intersections
        </span>
      </h3>

      {sorted.map((item, index) => {
        const delta =
          item.recommended_green_seconds - item.current_green_seconds;
        const isIncrease = delta > 0;
        const isDecrease = delta < 0;
        const absDelta = Math.abs(delta);

        // Severity-based color
        let deltaColor = 'text-slate-400';
        let deltaBg = 'bg-slate-700/50';
        let borderColor = 'border-slate-700/50';

        if (absDelta >= 20) {
          deltaColor = isIncrease ? 'text-red-400' : 'text-blue-400';
          deltaBg = isIncrease ? 'bg-red-500/10' : 'bg-blue-500/10';
          borderColor = isIncrease
            ? 'border-red-500/20'
            : 'border-blue-500/20';
        } else if (absDelta >= 10) {
          deltaColor = isIncrease ? 'text-orange-400' : 'text-cyan-400';
          deltaBg = isIncrease ? 'bg-orange-500/10' : 'bg-cyan-500/10';
          borderColor = isIncrease
            ? 'border-orange-500/20'
            : 'border-cyan-500/20';
        } else {
          deltaColor = isIncrease ? 'text-yellow-400' : 'text-emerald-400';
          deltaBg = isIncrease ? 'bg-yellow-500/10' : 'bg-emerald-500/10';
          borderColor = isIncrease
            ? 'border-yellow-500/20'
            : 'border-emerald-500/20';
        }

        const DeltaIcon = isIncrease
          ? ArrowUp
          : isDecrease
            ? ArrowDown
            : Minus;

        return (
          <div
            key={index}
            className={`p-3 rounded-lg border ${borderColor} ${deltaBg} transition-all duration-200 hover:scale-[1.01]`}
          >
            {/* Intersection name */}
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold text-slate-100">
                {item.intersection}
              </span>
              <span
                className={`flex items-center gap-1 text-xs font-bold ${deltaColor} ${deltaBg} px-2 py-0.5 rounded-full border ${borderColor}`}
              >
                <DeltaIcon size={10} />
                {isIncrease ? '+' : ''}
                {delta}s
              </span>
            </div>

            {/* Phase duration comparison */}
            <div className="flex items-center gap-2 mb-2">
              <div className="flex-1 text-center">
                <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-0.5">
                  Current
                </div>
                <div className="text-lg font-mono font-bold text-slate-400">
                  {item.current_green_seconds}
                  <span className="text-xs font-normal text-slate-600">s</span>
                </div>
              </div>

              <div className="text-slate-600 text-lg">→</div>

              <div className="flex-1 text-center">
                <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-0.5">
                  Recommended
                </div>
                <div className={`text-lg font-mono font-bold ${deltaColor}`}>
                  {item.recommended_green_seconds}
                  <span className="text-xs font-normal opacity-60">s</span>
                </div>
              </div>
            </div>

            {/* Rationale */}
            <p className="text-[11px] text-slate-400 leading-relaxed">
              {item.rationale}
            </p>
          </div>
        );
      })}
    </div>
  );
}

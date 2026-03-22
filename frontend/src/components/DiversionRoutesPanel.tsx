'use client';

import type { DiversionRouteItem } from '@/types';
import { Navigation, Clock, Loader2 } from 'lucide-react';

interface DiversionRoutesPanelProps {
  routes: DiversionRouteItem[];
  loading: boolean;
}

export default function DiversionRoutesPanel({
  routes,
  loading,
}: DiversionRoutesPanelProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
          <Navigation size={14} className="text-blue-400" />
          Diversion Routes
        </h3>
        {[1, 2].map((i) => (
          <div
            key={i}
            className="p-3 bg-slate-800/50 border border-slate-700/50 rounded-lg animate-pulse"
          >
            <div className="h-4 bg-slate-700 rounded w-2/3 mb-2" />
            <div className="h-3 bg-slate-700 rounded w-full mb-1" />
            <div className="h-3 bg-slate-700 rounded w-1/2" />
          </div>
        ))}
        <p className="text-xs text-slate-500 text-center animate-pulse">
          Computing diversion routes…
        </p>
      </div>
    );
  }

  if (routes.length === 0) {
    return (
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
          <Navigation size={14} className="text-blue-400" />
          Diversion Routes
        </h3>
        <div className="p-4 bg-slate-800/30 border border-slate-700/30 rounded-lg text-center">
          <p className="text-xs text-slate-500">
            Declare an incident to generate diversion route recommendations.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
        <Navigation size={14} className="text-blue-400" />
        Diversion Routes
        <span className="ml-auto text-[10px] font-normal text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full">
          {routes.length} routes
        </span>
      </h3>

      {routes.map((route, index) => (
        <div
          key={index}
          className="p-3 rounded-lg border border-blue-500/20 bg-blue-500/5 transition-all duration-200 hover:scale-[1.01]"
        >
          {/* Route header */}
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-slate-100">
              {route.name}
            </span>
            <span className="text-[10px] font-bold text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full border border-blue-500/20">
              Step {route.activate_step}
            </span>
          </div>

          {/* From → To */}
          <div className="flex items-center gap-2 mb-2 text-xs text-slate-400">
            <span className="font-medium text-emerald-400">{route.from_local}</span>
            <span className="text-slate-600">→</span>
            <span className="font-medium text-red-400">{route.to_local}</span>
          </div>

          {/* Via streets */}
          <div className="flex flex-wrap gap-1 mb-2">
            {route.via_streets.map((street, i) => (
              <span
                key={i}
                className="text-[10px] px-2 py-0.5 bg-slate-700/50 border border-slate-600/30 rounded-full text-slate-300"
              >
                {street}
              </span>
            ))}
          </div>

          {/* Extra time */}
          <div className="flex items-center gap-1.5 text-xs text-orange-400">
            <Clock size={10} />
            +{route.extra_travel_minutes} min additional travel time
          </div>
        </div>
      ))}
    </div>
  );
}

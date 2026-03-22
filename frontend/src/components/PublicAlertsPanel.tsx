'use client';

import { useState } from 'react';
import type { PublicAlerts } from '@/types';
import { Megaphone, Monitor, Radio, MessageCircle, Copy, Check, Download, Loader2 } from 'lucide-react';

interface PublicAlertsPanelProps {
  alerts: PublicAlerts | null;
  loading: boolean;
  incidentNarrative: string;
}

type Channel = 'vms' | 'radio' | 'social';

export default function PublicAlertsPanel({
  alerts,
  loading,
  incidentNarrative,
}: PublicAlertsPanelProps) {
  const [copied, setCopied] = useState<Channel | 'narrative' | null>(null);

  const handleCopy = async (text: string, channel: Channel | 'narrative') => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(channel);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      // Fallback: no clipboard API available
    }
  };

  const handleExport = () => {
    if (!alerts) return;
    const content = [
      '=== INCIDENT PUBLIC ALERTS ===',
      `Generated: ${new Date().toISOString()}`,
      '',
      '--- VMS (Variable Message Sign) ---',
      alerts.vms,
      '',
      '--- RADIO BROADCAST ---',
      alerts.radio,
      '',
      '--- SOCIAL MEDIA ---',
      alerts.social,
      '',
      '--- INCIDENT NARRATIVE ---',
      incidentNarrative,
    ].join('\n');

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `incident_alerts_${new Date().toISOString().replace(/[:.]/g, '-')}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
          <Megaphone size={14} className="text-amber-400" />
          Public Alerts
        </h3>
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="p-3 bg-slate-800/50 border border-slate-700/50 rounded-lg animate-pulse"
          >
            <div className="h-3 bg-slate-700 rounded w-1/3 mb-2" />
            <div className="h-4 bg-slate-700 rounded w-full mb-1" />
            <div className="h-4 bg-slate-700 rounded w-3/4" />
          </div>
        ))}
        <p className="text-xs text-slate-500 text-center animate-pulse">
          Generating alert drafts…
        </p>
      </div>
    );
  }

  if (!alerts) {
    return (
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
          <Megaphone size={14} className="text-amber-400" />
          Public Alerts
        </h3>
        <div className="p-4 bg-slate-800/30 border border-slate-700/30 rounded-lg text-center">
          <p className="text-xs text-slate-500">
            Declare an incident to generate public alert drafts.
          </p>
        </div>
      </div>
    );
  }

  const channels: { key: Channel; label: string; icon: typeof Monitor; color: string; borderColor: string; bgColor: string; constraint: string }[] = [
    {
      key: 'vms',
      label: 'Variable Message Sign',
      icon: Monitor,
      color: 'text-green-400',
      borderColor: 'border-green-500/20',
      bgColor: 'bg-green-500/5',
      constraint: '≤3 lines, ≤60 chars/line',
    },
    {
      key: 'radio',
      label: 'Radio Broadcast',
      icon: Radio,
      color: 'text-purple-400',
      borderColor: 'border-purple-500/20',
      bgColor: 'bg-purple-500/5',
      constraint: '~100 words',
    },
    {
      key: 'social',
      label: 'Social Media',
      icon: MessageCircle,
      color: 'text-sky-400',
      borderColor: 'border-sky-500/20',
      bgColor: 'bg-sky-500/5',
      constraint: `${alerts.social.length}/280 chars`,
    },
  ];

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
        <Megaphone size={14} className="text-amber-400" />
        Public Alerts
        <span className="ml-auto text-[10px] font-normal text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full">
          3 channels
        </span>
      </h3>

      {channels.map(({ key, label, icon: Icon, color, borderColor, bgColor, constraint }) => (
        <div
          key={key}
          className={`p-3 rounded-lg border ${borderColor} ${bgColor} transition-all duration-200`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className={`text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5 ${color}`}>
              <Icon size={12} />
              {label}
            </span>
            <div className="flex items-center gap-1">
              <span className="text-[9px] text-slate-500">{constraint}</span>
              <button
                onClick={() => handleCopy(alerts[key], key)}
                className="p-1 rounded hover:bg-slate-700/50 transition-colors"
                title="Copy to clipboard"
              >
                {copied === key ? (
                  <Check size={12} className="text-green-400" />
                ) : (
                  <Copy size={12} className="text-slate-400" />
                )}
              </button>
            </div>
          </div>
          <p className={`text-xs text-slate-300 leading-relaxed ${key === 'vms' ? 'font-mono whitespace-pre-line' : ''}`}>
            {alerts[key]}
          </p>
        </div>
      ))}

      {/* Incident Narrative */}
      {incidentNarrative && (
        <div className="p-3 rounded-lg border border-amber-500/20 bg-amber-500/5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-400">
              📋 Incident Narrative
            </span>
            <button
              onClick={() => handleCopy(incidentNarrative, 'narrative')}
              className="p-1 rounded hover:bg-slate-700/50 transition-colors"
              title="Copy to clipboard"
            >
              {copied === 'narrative' ? (
                <Check size={12} className="text-green-400" />
              ) : (
                <Copy size={12} className="text-slate-400" />
              )}
            </button>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            {incidentNarrative}
          </p>
        </div>
      )}

      {/* Export button */}
      <button
        onClick={handleExport}
        className="w-full py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs text-slate-300 font-medium flex items-center justify-center gap-2 transition-colors"
      >
        <Download size={12} />
        Export All Alerts (.txt)
      </button>
    </div>
  );
}

'use client';
import dynamic from 'next/dynamic';
import ChatComponent from '@/components/ChatComponent';
import SignalRetimingPanel from '@/components/SignalRetimingPanel';
import DiversionRoutesPanel from '@/components/DiversionRoutesPanel';
import PublicAlertsPanel from '@/components/PublicAlertsPanel';
import { useEffect, useState, useCallback } from 'react';
import { AlertTriangle, MapPin, Send, ChevronDown } from 'lucide-react';
import type { SignalRetiming, DiversionRouteItem, PublicAlerts, Incident, IncidentAnalysisResponse } from '@/types';

const MapComponent = dynamic(() => import('@/components/MapComponent'), {
  ssr: false,
  loading: () => <div className="w-full h-full bg-slate-900 animate-pulse rounded-xl" />,
});


const INCIDENT_TYPES = [
  'Major Accident',
  'Vehicle Fire',
  'Road Collapse',
  'Flooding',
  'Hazardous Spill',
  'Stalled Vehicle',
];

export default function Dashboard() {
  const [trafficData, setTrafficData] = useState<any>(null);
  const [incidentActive, setIncidentActive] = useState(false);
  const [diversionRoute, setDiversionRoute] = useState<[number, number][]>([]);
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [signalRetiming, setSignalRetiming] = useState<SignalRetiming[]>([]);
  const [diversionRoutesData, setDiversionRoutesData] = useState<DiversionRouteItem[]>([]);
  const [publicAlerts, setPublicAlerts] = useState<PublicAlerts | null>(null);
  const [incidentNarrative, setIncidentNarrative] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [activeIntelTab, setActiveIntelTab] = useState<'signals' | 'diversions' | 'alerts'>('signals');

  // Incident form state
  const [formType, setFormType] = useState(INCIDENT_TYPES[0]);
  const [formSeverity, setFormSeverity] = useState(3);
  const [formNotes, setFormNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Request live location on mount
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setUserLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          });
        },
        () => {
          // Default to NYC if denied
          setUserLocation({ lat: 23.0225, lng: 72.5714 });
        },
        { enableHighAccuracy: true, timeout: 10000 }
      );
    } else {
      setUserLocation({ lat: 23.0225, lng: 72.5714 });
    }
  }, []);

  // Fetch live data from backend
  useEffect(() => {
    const fetchLive = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/live');
        const data = await res.json();
        setTrafficData(data.traffic);
        setIncidentActive(data.incident_active || incidents.length > 0);
        setDiversionRoute(data.diversion_route || []);
      } catch (err) {
        console.error('Failed to fetch live data', err);
      }
    };
    fetchLive();
    const interval = setInterval(fetchLive, 5000);
    return () => clearInterval(interval);
  }, [incidents.length]);

  // Submit incident report and analyze for signal re-timing
  const handleReportIncident = useCallback(async () => {
    if (!userLocation) return;
    setSubmitting(true);
    setAnalyzing(true);

    const newIncident: Incident = {
      lat: userLocation.lat,
      lng: userLocation.lng,
      incident_type: formType,
      severity: formSeverity,
      notes: formNotes,
      timestamp: new Date().toISOString(),
    };

    // Report the incident
    try {
      await fetch('http://localhost:8000/api/report-incident', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newIncident),
      });
    } catch (err) {
      console.error('Backend unavailable, saving locally', err);
    }

    setIncidents((prev) => [...prev, newIncident]);
    setIncidentActive(true);
    setFormNotes('');
    setFormSeverity(3);
    setSubmitting(false);

    // Analyze incident for signal re-timing
    try {
      const analysisRes = await fetch('http://localhost:8000/api/analyze-incident', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat: userLocation.lat,
          lng: userLocation.lng,
          incident_type: formType,
          severity: formSeverity,
          lanes_blocked: 1,
          notes: formNotes,
        }),
      });
      const analysisData: IncidentAnalysisResponse = await analysisRes.json();
      setSignalRetiming(analysisData.signal_retiming || []);
      setDiversionRoutesData(analysisData.diversion_routes || []);
      setPublicAlerts(analysisData.public_alerts || null);
      setIncidentNarrative(analysisData.incident_narrative || '');
      // Set computed route coordinates for the map polyline
      if (analysisData.route_coordinates && analysisData.route_coordinates.length > 0) {
        setDiversionRoute(analysisData.route_coordinates);
      }
    } catch (err) {
      console.error('Incident analysis failed', err);
    } finally {
      setAnalyzing(false);
    }
  }, [userLocation, formType, formSeverity, formNotes]);

  const severityColor = (s: number) => {
    if (s >= 4) return 'text-red-500 bg-red-500/10 border-red-500/20';
    if (s >= 3) return 'text-orange-400 bg-orange-400/10 border-orange-400/20';
    return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20';
  };

  const severityLabel = (s: number) => {
    const labels: Record<number, string> = { 1: 'Minor', 2: 'Low', 3: 'Moderate', 4: 'High', 5: 'Critical' };
    return labels[s] || 'Unknown';
  };

  return (
    <div className="h-screen w-full bg-slate-950 flex flex-col p-4 gap-4">
      {/* Header */}
      <header className="flex justify-between items-center py-2 px-4 bg-slate-900 border border-slate-800 rounded-xl shadow-sm">
        <h1 className="text-2xl font-bold tracking-tight text-slate-50">
          Traffic Incident Command
        </h1>
        <div className="flex gap-4">
          {incidentActive || incidents.length > 0 ? (
            <div className="px-3 py-1 rounded-full bg-red-500/10 text-red-500 text-sm font-medium animate-pulse">
              Active Incident: {incidents.length > 0 ? severityLabel(incidents[incidents.length - 1].severity).toUpperCase() : 'CRITICAL'}
            </div>
          ) : (
            <div className="px-3 py-1 rounded-full bg-green-500/10 text-green-500 text-sm font-medium">
              Status: Normal
            </div>
          )}
        </div>
      </header>

      <div className="flex-1 flex gap-4 min-h-0">
        {/* Left pane: Incident Report Form + Intelligence */}
        <div className="w-1/4 min-w-[300px] flex flex-col gap-4">

          {/* Incident Report Form */}
          <div className="bg-slate-900 p-4 rounded-xl shadow-lg border border-slate-800">
            <h2 className="text-lg font-semibold mb-3 text-slate-50 flex items-center gap-2">
              <AlertTriangle size={18} className="text-orange-400" />
              Report Incident
            </h2>
            <div className="space-y-3">
              {/* Type dropdown */}
              <div>
                <label className="text-xs text-slate-400 mb-1 block">Incident Type</label>
                <div className="relative">
                  <select
                    value={formType}
                    onChange={(e) => setFormType(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-50 appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {INCIDENT_TYPES.map((type) => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>
                  <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                </div>
              </div>

              {/* Severity slider */}
              <div>
                <label className="text-xs text-slate-400 mb-1 block">
                  Severity: <span className={`font-medium ${formSeverity >= 4 ? 'text-red-400' : formSeverity >= 3 ? 'text-orange-400' : 'text-yellow-400'}`}>
                    {formSeverity}/5 — {severityLabel(formSeverity)}
                  </span>
                </label>
                <input
                  type="range"
                  min={1}
                  max={5}
                  value={formSeverity}
                  onChange={(e) => setFormSeverity(Number(e.target.value))}
                  className="w-full accent-blue-500"
                />
              </div>

              {/* Notes */}
              <div>
                <label className="text-xs text-slate-400 mb-1 block">Notes</label>
                <textarea
                  value={formNotes}
                  onChange={(e) => setFormNotes(e.target.value)}
                  placeholder="Describe the incident..."
                  rows={2}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-50 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                />
              </div>

              {/* Location display */}
              <div className="p-2 bg-slate-800 rounded-lg flex items-center gap-2 text-xs text-slate-400">
                <MapPin size={12} className="text-blue-400" />
                {userLocation
                  ? `Live: ${userLocation.lat.toFixed(4)}, ${userLocation.lng.toFixed(4)}`
                  : 'Fetching location…'}
              </div>

              {/* Declare + Clear buttons */}
              <div className="flex gap-2">
                <button
                  onClick={handleReportIncident}
                  disabled={submitting || !userLocation}
                  className="flex-[2] py-2.5 bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg flex items-center justify-center gap-2 transition-colors"
                >
                  <AlertTriangle size={14} />
                  {submitting ? 'Declaring…' : '🚨 Declare Incident'}
                </button>
                <button
                  onClick={() => {
                    setIncidents([]);
                    setIncidentActive(false);
                    setSignalRetiming([]);
                    setDiversionRoutesData([]);
                    setPublicAlerts(null);
                    setIncidentNarrative('');
                    setAnalyzing(false);
                    setFormNotes('');
                    setFormSeverity(3);
                    setFormType(INCIDENT_TYPES[0]);
                    setActiveIntelTab('signals');
                  }}
                  disabled={incidents.length === 0}
                  className="flex-1 py-2.5 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
                >
                  ✕ Clear
                </button>
              </div>
            </div>
          </div>

          {/* Intel Stream with Tabs */}
          <div className="flex-1 bg-slate-900 p-4 rounded-xl shadow-lg border border-slate-800 overflow-y-auto">
            <h2 className="text-lg font-semibold mb-2 text-slate-50">Intelligence Stream</h2>

            {/* Reported incidents list */}
            <div className="text-sm space-y-3 mb-3">
              {incidents.map((inc, i) => (
                <div
                  key={i}
                  className={`p-3 border rounded-lg ${severityColor(inc.severity)}`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-xs uppercase">{inc.incident_type}</span>
                    <span className="text-[10px] opacity-70">
                      {new Date(inc.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="text-xs opacity-80">
                    Severity {inc.severity}/5 — {severityLabel(inc.severity)}
                    {' • '}
                    {inc.lat.toFixed(4)}, {inc.lng.toFixed(4)}
                  </div>
                  {inc.notes && (
                    <div className="text-xs mt-1 opacity-70 italic">{inc.notes}</div>
                  )}
                </div>
              ))}
            </div>

            {/* Tab navigation */}
            <div className="flex gap-1 mb-3 bg-slate-800/50 p-1 rounded-lg">
              {[
                { id: 'signals' as const, label: '🔴 Signals', count: signalRetiming.length },
                { id: 'diversions' as const, label: '🔵 Diversions', count: diversionRoutesData.length },
                { id: 'alerts' as const, label: '📢 Alerts', count: publicAlerts ? 3 : 0 },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveIntelTab(tab.id)}
                  className={`flex-1 px-2 py-1.5 rounded-md text-xs font-medium transition-all duration-150 ${
                    activeIntelTab === tab.id
                      ? 'bg-slate-700 text-slate-100 shadow-sm'
                      : 'text-slate-400 hover:text-slate-300 hover:bg-slate-700/50'
                  }`}
                >
                  {tab.label}
                  {tab.count > 0 && (
                    <span className="ml-1 text-[9px] bg-slate-600 px-1.5 py-0.5 rounded-full">
                      {tab.count}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div className="text-sm space-y-3">
              {activeIntelTab === 'signals' && (
                <SignalRetimingPanel
                  signalRetiming={signalRetiming}
                  loading={analyzing}
                />
              )}
              {activeIntelTab === 'diversions' && (
                <DiversionRoutesPanel
                  routes={diversionRoutesData}
                  loading={analyzing}
                />
              )}
              {activeIntelTab === 'alerts' && (
                <PublicAlertsPanel
                  alerts={publicAlerts}
                  loading={analyzing}
                  incidentNarrative={incidentNarrative}
                />
              )}
            </div>

            {/* Backend-detected incidents */}
            {incidentActive && incidents.length === 0 && (
              <div className="mt-3 space-y-2">
                <div className="p-2 bg-red-500/10 border border-red-500/20 rounded text-red-500 text-sm">
                  CRITICAL ACCIDENT detected at {trafficData?.location}. Speeds dropped to 0 mph.
                </div>
                <div className="p-2 bg-yellow-500/10 border border-yellow-500/20 rounded text-yellow-600 dark:text-yellow-400 text-sm">
                  A* Routing Algorithm identified diversion route. Processing LLM recommendations.
                </div>
              </div>
            )}

            {!incidentActive && incidents.length === 0 && (
              <div className="text-sm text-slate-400">Monitoring traffic patterns...</div>
            )}
          </div>
        </div>

        {/* Center pane: Map */}
        <div className="flex-1 relative">
          <MapComponent
            userLocation={userLocation}
            incidents={incidents}
            diversionRoute={diversionRoute}
          />
        </div>

        {/* Right pane: Chat */}
        <div className="w-[350px]">
          <ChatComponent />
        </div>
      </div>
    </div>
  );
}

'use client';

import { useEffect, useState } from 'react';
import { MapPin, Loader2 } from 'lucide-react';

interface Incident {
  lat: number;
  lng: number;
  incident_type: string;
  severity: number;
  notes: string;
  timestamp: string;
}

interface MapComponentProps {
  userLocation?: { lat: number; lng: number } | null;
  incidents?: Incident[];
}

export default function MapComponent({ userLocation, incidents = [] }: MapComponentProps) {
  const [location, setLocation] = useState<{ lat: number; lng: number }>({ lat: 40.7128, lng: -74.006 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (userLocation) {
      setLocation(userLocation);
      setLoading(false);
      return;
    }

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          });
          setLoading(false);
        },
        () => {
          // Permission denied or error — use default NYC
          setLoading(false);
        },
        { enableHighAccuracy: true, timeout: 10000 }
      );
    } else {
      setLoading(false);
    }
  }, [userLocation]);

  // Center on latest incident if one exists
  const activeIncident = incidents.length > 0 ? incidents[incidents.length - 1] : null;
  const mapCenter = activeIncident
    ? { lat: activeIncident.lat, lng: activeIncident.lng }
    : location;

  const getMapUrl = () => {
    if (mapCenter.lat && mapCenter.lng) {
      return `https://www.openstreetmap.org/export/embed.html?bbox=${mapCenter.lng - 0.005},${mapCenter.lat - 0.003},${mapCenter.lng + 0.005},${mapCenter.lat + 0.003}&layer=mapnik&marker=${mapCenter.lat},${mapCenter.lng}`;
    }
    return null;
  };

  const mapUrl = getMapUrl();

  if (loading) {
    return (
      <div className="h-full w-full rounded-xl overflow-hidden shadow-lg border border-slate-800 bg-slate-900 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin" />
          <span className="text-sm">Requesting live location…</span>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full rounded-xl overflow-hidden shadow-lg border border-slate-800 relative">
      {mapUrl ? (
        <iframe
          src={mapUrl}
          style={{
            width: '100%',
            height: '100%',
            border: 'none',
            borderRadius: '0.75rem',
            position: 'absolute',
            top: 0,
            left: 0,
          }}
          title="Location map"
          loading="lazy"
        />
      ) : (
        <div className="h-full w-full bg-slate-900 flex items-center justify-center text-slate-400">
          Unable to load map
        </div>
      )}

      {/* Incident count overlay */}
      {incidents.length > 0 && (
        <div className="absolute top-3 left-3 z-[1000] bg-red-600/90 backdrop-blur-sm text-white px-3 py-1.5 rounded-lg text-sm font-medium flex items-center gap-2 shadow-lg">
          <MapPin size={14} />
          {incidents.length} Active Incident{incidents.length > 1 ? 's' : ''}
        </div>
      )}

      {/* Location info overlay */}
      <div className="absolute bottom-3 left-3 z-[1000] bg-slate-900/80 backdrop-blur-sm text-slate-300 px-3 py-1.5 rounded-lg text-xs font-mono">
        {mapCenter.lat.toFixed(4)}, {mapCenter.lng.toFixed(4)}
      </div>
    </div>
  );
}

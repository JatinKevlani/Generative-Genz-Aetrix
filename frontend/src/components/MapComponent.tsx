'use client';

import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';

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
  diversionRoute?: [number, number][];
}

// Custom red icon for incidents
const incidentIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

// Blue icon for user location
const userIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

// Component to recenter map when incidents are declared
function RecenterMap({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo(center, 15, { duration: 1.2 });
  }, [center, map]);
  return null;
}

export default function MapComponent({
  userLocation,
  incidents = [],
  diversionRoute = [],
}: MapComponentProps) {
  const [ready, setReady] = useState(false);
  const defaultCenter: [number, number] = [23.0225, 72.5714]; // Ahmedabad

  useEffect(() => {
    setReady(true);
  }, []);

  const activeIncident = incidents.length > 0 ? incidents[incidents.length - 1] : null;
  const mapCenter: [number, number] = activeIncident
    ? [activeIncident.lat, activeIncident.lng]
    : userLocation
      ? [userLocation.lat, userLocation.lng]
      : defaultCenter;

  if (!ready) {
    return (
      <div className="h-full w-full rounded-xl overflow-hidden shadow-lg border border-slate-800 bg-slate-900 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-slate-400">
          <div className="w-8 h-8 border-2 border-slate-600 border-t-blue-400 rounded-full animate-spin" />
          <span className="text-sm">Loading map…</span>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full rounded-xl overflow-hidden shadow-lg border border-slate-800 relative">
      <MapContainer
        center={mapCenter}
        zoom={14}
        scrollWheelZoom={true}
        style={{ width: '100%', height: '100%', borderRadius: '0.75rem' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <RecenterMap center={mapCenter} />

        {/* User location marker */}
        {userLocation && (
          <Marker position={[userLocation.lat, userLocation.lng]} icon={userIcon}>
            <Popup>
              <strong>📍 Your Location</strong>
              <br />
              {userLocation.lat.toFixed(4)}, {userLocation.lng.toFixed(4)}
            </Popup>
          </Marker>
        )}

        {/* Incident markers */}
        {incidents.map((inc, i) => (
          <Marker key={i} position={[inc.lat, inc.lng]} icon={incidentIcon}>
            <Popup>
              <strong>🚨 {inc.incident_type}</strong>
              <br />
              Severity: {inc.severity}/5
              <br />
              {inc.notes && <em>{inc.notes}</em>}
              <br />
              <small>{new Date(inc.timestamp).toLocaleTimeString()}</small>
            </Popup>
          </Marker>
        ))}

        {/* Diversion route polyline */}
        {diversionRoute.length > 1 && (
          <Polyline
            positions={diversionRoute}
            pathOptions={{
              color: '#3498DB',
              weight: 5,
              opacity: 0.85,
              dashArray: '10 6',
            }}
          />
        )}
      </MapContainer>

      {/* Incident count overlay */}
      {incidents.length > 0 && (
        <div className="absolute top-3 left-3 z-[1000] bg-red-600/90 backdrop-blur-sm text-white px-3 py-1.5 rounded-lg text-sm font-medium flex items-center gap-2 shadow-lg">
          🚨 {incidents.length} Active Incident{incidents.length > 1 ? 's' : ''}
        </div>
      )}

      {/* Diversion route legend */}
      {diversionRoute.length > 1 && (
        <div className="absolute bottom-3 right-3 z-[1000] bg-slate-900/80 backdrop-blur-sm text-sky-300 px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-2 shadow-lg">
          <span className="w-4 h-0.5 bg-blue-400 inline-block" style={{ borderTop: '2px dashed #3498DB' }} />
          Diversion Route
        </div>
      )}
    </div>
  );
}

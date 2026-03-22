export interface SignalRetiming {
  intersection: string;
  current_green_seconds: number;
  recommended_green_seconds: number;
  rationale: string;
}

export interface DiversionRouteItem {
  name: string;
  from_local: string;
  to_local: string;
  via_streets: string[];
  extra_travel_minutes: number;
  activate_step: number;
}

export interface PublicAlerts {
  vms: string;
  radio: string;
  social: string;
}

export interface IncidentAnalysisResponse {
  signal_retiming: SignalRetiming[];
  diversion_routes: DiversionRouteItem[];
  public_alerts: PublicAlerts;
  incident_narrative: string;
  route_coordinates: [number, number][];
}

export interface Incident {
  lat: number;
  lng: number;
  incident_type: string;
  severity: number;
  notes: string;
  timestamp: string;
}

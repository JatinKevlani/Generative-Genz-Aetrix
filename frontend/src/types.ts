export interface SignalRetiming {
  intersection: string;
  current_green_seconds: number;
  recommended_green_seconds: number;
  rationale: string;
}

export interface IncidentAnalysisResponse {
  signal_retiming: SignalRetiming[];
}

export interface Incident {
  lat: number;
  lng: number;
  incident_type: string;
  severity: number;
  notes: string;
  timestamp: string;
}

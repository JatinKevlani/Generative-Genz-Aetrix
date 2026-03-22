# modules/state.py
from typing import TypedDict, Optional


class IncidentState(TypedDict):
    declared: bool
    lat: Optional[float]
    lng: Optional[float]
    incident_type: str
    severity: int
    lanes_blocked: int
    notes: str
    declared_at: Optional[str]


class SpeedRecord(TypedDict):
    speed: float
    name: str
    lat_lngs: list


class FeedState(TypedDict):
    current_speeds: dict
    current_timestamp: str
    tick_count: int
    is_running: bool
    replay_multiplier: float


class SignalRetiming(TypedDict):
    intersection: str
    current_green_seconds: int
    recommended_green_seconds: int
    rationale: str


class DiversionRoute(TypedDict):
    name: str
    from_location: str
    to_location: str
    via_streets: list[str]
    extra_travel_minutes: int
    activate_step: int


class PublicAlerts(TypedDict):
    vms: str
    radio: str
    social: str


class LLMOutputState(TypedDict):
    signal_retiming: list[SignalRetiming]
    diversion_routes: list[DiversionRoute]
    public_alerts: PublicAlerts
    incident_narrative: str
    last_updated: Optional[str]
    parse_error: bool


class ChatMessage(TypedDict):
    role: str
    content: str
    timestamp: str


class ChatState(TypedDict):
    messages: list[ChatMessage]


class AppState(TypedDict):
    incident: IncidentState
    feed: FeedState
    llm_output: LLMOutputState
    chat: ChatState
    active_diversion_index: int
    diversion_path: Optional[list]
    map_needs_refresh: bool


def get_default_state() -> AppState:
    """Return the clean initial state for a new session."""
    return {
        "incident": {
            "declared": False, "lat": None, "lng": None,
            "incident_type": "Major Accident", "severity": 3,
            "lanes_blocked": 1, "notes": "", "declared_at": None
        },
        "feed": {
            "current_speeds": {}, "current_timestamp": "—",
            "tick_count": 0, "is_running": False, "replay_multiplier": 1.0
        },
        "llm_output": {
            "signal_retiming": [], "diversion_routes": [],
            "public_alerts": {"vms": "", "radio": "", "social": ""},
            "incident_narrative": "", "last_updated": None, "parse_error": False
        },
        "chat": {"messages": []},
        "active_diversion_index": 0,
        "diversion_path": None,
        "map_needs_refresh": False
    }

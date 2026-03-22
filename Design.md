# Technical Design Document
# LLM Co-Pilot for Traffic Incident Command
 
**Version:** 1.0  
**Status:** Ready for Implementation  
**Author:** AI Systems Architecture  
**Companion Document:** PRD.md v1.0
 
---
 
## Table of Contents
 
1. [Architecture Decisions](#1-architecture-decisions)
2. [Module Specifications](#2-module-specifications)
3. [Data Flow Diagrams](#3-data-flow-diagrams)
4. [Prompt Engineering Design](#4-prompt-engineering-design)
5. [State Management Design](#5-state-management-design)
6. [Threading & Concurrency Design](#6-threading--concurrency-design)
7. [Map Rendering Pipeline](#7-map-rendering-pipeline)
8. [Error Handling Strategy](#8-error-handling-strategy)
9. [Configuration Reference](#9-configuration-reference)
10. [Full Code Skeletons](#10-full-code-skeletons)
11. [Dependency Installation](#11-dependency-installation)
 
---
 
## 1. Architecture Decisions
 
### ADR-01: Streamlit as the UI Framework
 
**Decision:** Use Streamlit over Flask+React or Dash.  
**Rationale:** This is a demo-grade prototype. Streamlit eliminates frontend/backend split, provides native session state, and allows a single Python developer to own the full stack. The trade-off (limited real-time push, full-page re-renders) is acceptable for 5-second feed ticks.  
**Consequence:** Map updates require a `st.rerun()` call from the feed thread's callback, which triggers a full UI re-render. This is managed by a `map_needs_refresh` flag in session state to avoid redundant renders.
 
### ADR-02: Folium + streamlit-folium over Pydeck or Plotly Maps
 
**Decision:** Use Folium for map rendering.  
**Rationale:** Folium provides direct Leaflet.js access with fine-grained polyline control. It supports the exact rendering required: colour-coded road segments from encoded polylines, clickable map events, and overlaid route paths. Pydeck's layer model is heavier and less suited to dynamic re-colouring per tick. Plotly maps require Mapbox API tokens.  
**Consequence:** `streamlit-folium` re-renders the entire map HTML on each tick. For the bounding box size chosen (~200 segments), this is within the 2-second target. Larger cities would require tile-based optimisation.
 
### ADR-03: Python Threading over asyncio
 
**Decision:** Use `threading.Thread` for feed simulation, not `asyncio`.  
**Rationale:** Streamlit's execution model is synchronous and not natively compatible with `asyncio` event loops. `threading` integrates cleanly with Streamlit's session state via locks. The feed thread has minimal CPU work (CSV row lookup + dict update), making GIL contention negligible.  
**Consequence:** All shared state access must be locked. See §6 for the full threading design.
 
### ADR-04: Single Structured LLM Call for Initial Analysis
 
**Decision:** All four output types (signal re-timing, diversion, alerts, narrative) are requested in one API call using a JSON schema prompt.  
**Rationale:** Multiple sequential calls would multiply latency (4× API round trips). One structured call with a JSON schema ensures atomic delivery of all intel within the 10-second target. The Anthropic API is reliable for JSON-mode responses when the schema is explicit and small.  
**Consequence:** Prompt is larger (~1,500 tokens), but the response is predictably parseable. Fallback handling covers cases where the model deviates from the schema.
 
### ADR-05: OSMnx Graph Cached as GraphML
 
**Decision:** Cache the OSM road network as `.graphml` rather than re-downloading each session.  
**Rationale:** OSMnx downloads can take 30–120 seconds depending on network and area size. This would make every cold start painful for demo purposes. GraphML is OSMnx's native format and round-trips losslessly.  
**Consequence:** Cache must be invalidated manually if the bounding box changes in `config.py`. A `FORCE_RELOAD` flag in config bypasses the cache for development.
 
---
 
## 2. Module Specifications
 
### 2.1 `config.py`
 
All constants centralised here. No other module defines configuration values.
 
```python
# config.py
 
# ── Geographic ────────────────────────────────────────────────────────────────
# Bounding box: (south, west, north, east) — Lower/Mid Manhattan
OSM_BBOX = (40.700, -74.020, 40.780, -73.930)
OSM_CACHE_PATH = "data/osm_cache/nyc_graph.graphml"
FORCE_GRAPH_RELOAD = False  # Set True to re-download OSM
 
# ── Data ──────────────────────────────────────────────────────────────────────
NYC_SPEED_CSV = "data/nyc_traffic_speed.csv"
 
# ── Feed Simulation ───────────────────────────────────────────────────────────
FEED_INTERVAL_SECONDS = 5.0   # Seconds between feed ticks
FEED_REPLAY_SPEEDS = {        # Multiplier options for sidebar slider
    "1×": 1.0,
    "2×": 0.5,
    "5×": 0.2
}
 
# ── Speed Thresholds (mph) ────────────────────────────────────────────────────
SPEED_FREE_FLOW = 40          # ≥ green
SPEED_SLOW = 20               # ≥ amber, < green threshold
# < SPEED_SLOW = red
 
# ── Map ───────────────────────────────────────────────────────────────────────
MAP_TILE_PROVIDER = "CartoDB positron"  # Clean basemap, no clutter
MAP_DEFAULT_ZOOM = 13
COLOUR_FREE_FLOW = "#2ECC71"
COLOUR_SLOW = "#F39C12"
COLOUR_CONGESTED = "#E74C3C"
COLOUR_DIVERSION = "#3498DB"
SEGMENT_WEIGHT = 3            # Polyline pixel width for speed segments
DIVERSION_WEIGHT = 5          # Polyline pixel width for diversion overlay
 
# ── LLM ──────────────────────────────────────────────────────────────────────
ANTHROPIC_MODEL = "claude-sonnet-4-6"
LLM_MAX_TOKENS = 2048
LLM_TEMPERATURE = 0.2         # Low temperature for precise, deterministic recommendations
LLM_TIMEOUT_SECONDS = 30
LLM_MAX_RETRIES = 3
LLM_RETRY_BASE_DELAY = 1.0    # Exponential backoff: 1s, 2s, 4s
 
# Chat context window management
CHAT_MAX_HISTORY_TURNS = 10   # Rolling window of turns to include
SPEED_SNAPSHOT_TOP_N = 10     # Number of slowest segments to include in prompt
 
# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE = "logs/app.log"
LOG_LEVEL = "INFO"
 
# ── Export ────────────────────────────────────────────────────────────────────
ALERT_EXPORT_DIR = "exports/"  # Not used in v1; export is in-memory download
```
 
---
 
### 2.2 `modules/state.py`
 
TypedDicts for all session state keys. Import these in every module that reads/writes session state to ensure type consistency.
 
```python
# modules/state.py
from typing import TypedDict, Optional
 
class IncidentState(TypedDict):
    declared: bool
    lat: Optional[float]
    lng: Optional[float]
    incident_type: str          # e.g., "Major Accident"
    severity: int               # 1–5
    lanes_blocked: int
    notes: str
    declared_at: Optional[str]  # ISO 8601
 
class SpeedRecord(TypedDict):
    speed: float                # mph
    name: str                   # Human-readable segment name
    lat_lngs: list              # [[lat, lng], ...] decoded polyline
 
class FeedState(TypedDict):
    current_speeds: dict        # {linkId: SpeedRecord}
    current_timestamp: str
    tick_count: int
    is_running: bool
    replay_multiplier: float    # 1.0, 0.5, 0.2
 
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
    parse_error: bool           # True if JSON parse failed; raw text in narrative
 
class ChatMessage(TypedDict):
    role: str                   # "user" | "assistant"
    content: str
    timestamp: str
 
class ChatState(TypedDict):
    messages: list[ChatMessage]
 
class AppState(TypedDict):
    incident: IncidentState
    feed: FeedState
    llm_output: LLMOutputState
    chat: ChatState
    active_diversion_index: int     # 0-indexed, which route to show on map
    diversion_path: Optional[list]  # [(lat, lng), ...] from routing
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
```
 
---
 
### 2.3 `modules/feed_manager.py`
 
Responsibilities: CSV loading, polyline decoding, background feed thread.
 
```python
# modules/feed_manager.py
"""
Feed Manager
============
Loads the NYC traffic speed CSV and replays it in a background thread,
updating shared speed state at each tick.
 
Public API:
    load_and_prepare_csv(path) -> pd.DataFrame
    start_feed(df, lock, get_state, set_state, interval) -> threading.Thread
    stop_feed(thread, stop_event) -> None
    get_speed_snapshot(lock, state) -> list[dict]
"""
import threading
import time
import logging
from datetime import datetime
import pandas as pd
import polyline  # pip install polyline — Google encoded polyline decoder
 
logger = logging.getLogger(__name__)
 
 
class FeedError(Exception):
    pass
 
 
REQUIRED_COLUMNS = {
    "Id", "Speed", "TravelTime", "Status", "DataAsOf",
    "linkId", "linkName", "EncodedPolyLine", "Borough"
}
 
 
def load_and_prepare_csv(path: str) -> pd.DataFrame:
    """
    Load the NYC speed CSV, validate columns, decode polylines,
    and sort by timestamp for replay ordering.
 
    Raises FeedError if required columns are missing.
    Returns a prepared DataFrame with a decoded 'lat_lngs' column.
    """
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise FeedError(f"CSV missing required columns: {missing}")
 
    df["DataAsOf"] = pd.to_datetime(df["DataAsOf"], errors="coerce")
    df = df.dropna(subset=["DataAsOf", "Speed", "linkId"])
    df = df.sort_values("DataAsOf").reset_index(drop=True)
 
    # Decode Google encoded polyline to list of [lat, lng] pairs
    def safe_decode(encoded: str) -> list:
        try:
            return [[lat, lng] for lat, lng in polyline.decode(encoded)]
        except Exception:
            return []
 
    df["lat_lngs"] = df["EncodedPolyLine"].apply(safe_decode)
    df = df[df["lat_lngs"].map(len) > 0]  # Drop segments with no geometry
 
    logger.info(f"Feed loaded: {len(df)} records, "
                f"{df['DataAsOf'].min()} → {df['DataAsOf'].max()}")
    return df
 
 
def _feed_loop(
    df: pd.DataFrame,
    lock: threading.Lock,
    speed_state: dict,          # Mutable dict shared with main thread
    stop_event: threading.Event,
    interval: float
) -> None:
    """
    Internal thread target. Iterates through DataFrame rows, updating
    speed_state under lock at each interval.
    """
    total = len(df)
    tick = 0
 
    while not stop_event.is_set():
        idx = tick % total
        row = df.iloc[idx]
 
        link_id = int(row["linkId"])
        record = {
            "speed": float(row["Speed"]),
            "name": str(row["linkName"]),
            "lat_lngs": row["lat_lngs"]
        }
        timestamp = row["DataAsOf"].isoformat()
 
        with lock:
            speed_state["current_speeds"][link_id] = record
            speed_state["current_timestamp"] = timestamp
            speed_state["tick_count"] = tick
            speed_state["is_running"] = True
 
        if tick % 10 == 0:
            logger.info(f"Feed tick {tick}: linkId={link_id}, "
                        f"speed={record['speed']} mph, ts={timestamp}")
 
        tick += 1
        stop_event.wait(interval)
 
    with lock:
        speed_state["is_running"] = False
    logger.info("Feed thread stopped cleanly.")
 
 
def start_feed(
    df: pd.DataFrame,
    lock: threading.Lock,
    speed_state: dict,
    interval: float = 5.0
) -> tuple[threading.Thread, threading.Event]:
    """
    Start the feed replay thread.
 
    Returns:
        (thread, stop_event) — call stop_event.set() to stop the thread.
    """
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_feed_loop,
        args=(df, lock, speed_state, stop_event, interval),
        daemon=True,
        name="FeedSimulator"
    )
    thread.start()
    logger.info(f"Feed thread started. Interval: {interval}s")
    return thread, stop_event
 
 
def stop_feed(thread: threading.Thread, stop_event: threading.Event) -> None:
    """Signal the feed thread to stop and wait for it to finish."""
    stop_event.set()
    thread.join(timeout=10)
 
 
def get_speed_snapshot(lock: threading.Lock, speed_state: dict, top_n: int = 10) -> list[dict]:
    """
    Return the top_n slowest segments from current speed state.
    Thread-safe read.
 
    Returns list of dicts: [{name, speed_mph, lat_lngs}]
    """
    with lock:
        speeds = dict(speed_state.get("current_speeds", {}))
 
    sorted_segments = sorted(speeds.values(), key=lambda x: x["speed"])
    return [
        {"name": seg["name"], "speed_mph": seg["speed"], "lat_lngs": seg["lat_lngs"]}
        for seg in sorted_segments[:top_n]
    ]
```
 
---
 
### 2.4 `modules/routing.py`
 
Responsibilities: OSMnx graph load/cache, nearest-node lookup, A* routing.
 
```python
# modules/routing.py
"""
Routing Module
==============
Handles OSM road network loading and A* diversion path computation.
 
Public API:
    load_graph(bbox, cache_path, force_reload) -> nx.MultiDiGraph
    find_nearest_node(graph, lat, lng) -> int
    compute_diversion(graph, origin_node, dest_node) -> list[tuple[float, float]]
    get_nearby_intersections(graph, lat, lng, radius_m) -> list[dict]
"""
import os
import logging
import networkx as nx
import osmnx as ox
 
logger = logging.getLogger(__name__)
 
 
class RoutingError(Exception):
    pass
 
 
def load_graph(
    bbox: tuple[float, float, float, float],
    cache_path: str,
    force_reload: bool = False
) -> nx.MultiDiGraph:
    """
    Load the OSM drive network for the given bounding box.
    Uses disk cache if available and force_reload is False.
 
    Args:
        bbox: (south, west, north, east) in decimal degrees
        cache_path: Path to .graphml cache file
        force_reload: If True, ignore cache and re-download
 
    Returns:
        NetworkX MultiDiGraph with speed and travel_time edge attributes
    """
    if not force_reload and os.path.exists(cache_path):
        logger.info(f"Loading OSM graph from cache: {cache_path}")
        G = ox.load_graphml(cache_path)
        logger.info(f"Graph loaded: {len(G.nodes)} nodes, {len(G.edges)} edges")
        return G
 
    logger.info(f"Downloading OSM graph for bbox: {bbox}")
    south, west, north, east = bbox
    G = ox.graph_from_bbox(
        north=north, south=south, east=east, west=west,
        network_type="drive",
        simplify=True
    )
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)
 
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    ox.save_graphml(G, cache_path)
    logger.info(f"Graph saved to cache: {cache_path}")
    return G
 
 
def find_nearest_node(graph: nx.MultiDiGraph, lat: float, lng: float) -> int:
    """
    Find the OSM node ID nearest to the given coordinates.
 
    Returns:
        OSM node ID (int)
    """
    node_id = ox.nearest_nodes(graph, X=lng, Y=lat)
    return int(node_id)
 
 
def compute_diversion(
    graph: nx.MultiDiGraph,
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float
) -> list[tuple[float, float]]:
    """
    Compute the A* shortest path between two coordinates using travel_time weight.
 
    Returns:
        Ordered list of (lat, lng) tuples forming the path.
 
    Raises:
        RoutingError if no path exists between the nodes.
    """
    try:
        origin_node = find_nearest_node(graph, origin_lat, origin_lng)
        dest_node = find_nearest_node(graph, dest_lat, dest_lng)
 
        path_nodes = nx.astar_path(
            graph, origin_node, dest_node, weight="travel_time"
        )
 
        path_coords = [
            (graph.nodes[node]["y"], graph.nodes[node]["x"])
            for node in path_nodes
        ]
        logger.info(f"Diversion computed: {len(path_nodes)} nodes, "
                    f"{origin_node} → {dest_node}")
        return path_coords
 
    except nx.NetworkXNoPath as e:
        raise RoutingError(f"No path between nodes: {e}") from e
    except Exception as e:
        raise RoutingError(f"Routing failed: {e}") from e
 
 
def get_nearby_intersections(
    graph: nx.MultiDiGraph,
    lat: float,
    lng: float,
    radius_m: float = 500.0
) -> list[dict]:
    """
    Return intersections (degree > 2 nodes) within radius_m metres of (lat, lng).
 
    Returns:
        List of dicts: [{name, distance_m, node_id}]
    """
    import math
 
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
 
    nearby = []
    for node_id, data in graph.nodes(data=True):
        if graph.degree(node_id) < 3:
            continue  # Not a meaningful intersection
        dist = haversine(lat, lng, data["y"], data["x"])
        if dist <= radius_m:
            # Get street names from adjacent edges
            edges = list(graph.edges(node_id, data=True))
            street_names = list({e[2].get("name", "") for e in edges if e[2].get("name")})
            name = " & ".join(street_names[:2]) if street_names else f"Node {node_id}"
            nearby.append({
                "name": name,
                "distance_m": round(dist),
                "node_id": node_id
            })
 
    nearby.sort(key=lambda x: x["distance_m"])
    return nearby[:8]  # Return closest 8 intersections
```
 
---
 
### 2.5 `modules/prompt_builder.py`
 
Responsibilities: Assembling structured prompts for incident analysis and chat queries.
 
```python
# modules/prompt_builder.py
"""
Prompt Builder
==============
Constructs structured prompts for the Anthropic API.
All prompt logic lives here. No prompt strings in other modules.
 
Public API:
    build_incident_prompt(incident, speed_snapshot, nearby_intersections) -> str
    build_chat_messages(incident, llm_output, chat_history, query) -> list[dict]
    SYSTEM_PROMPT -> str
"""
import json
from modules.state import IncidentState, LLMOutputState, ChatMessage
 
SYSTEM_PROMPT = """You are a Traffic Incident Command AI Co-Pilot embedded in a city Traffic Management Centre.
 
Your role is to assist traffic control officers during live incidents by providing:
- Specific, actionable signal re-timing recommendations (exact intersections, exact seconds)
- Diversion routes with activation sequences and real street names  
- Channel-ready public alert copy (VMS, radio, social media)
- Clear incident narratives for officer situational awareness
 
Rules you must always follow:
1. Be specific. Name intersections, streets, and exact durations. Never say "nearby intersections" — name them.
2. Be decisive. Use command language. "Extend green phase to 90 seconds." Not "you might consider extending."
3. Never recommend actions outside your data. If you cannot identify a specific intersection, say so.
4. Calibrate tone to urgency. Severity 5 = urgent, terse. Severity 1 = measured, thorough.
5. When answering chat queries, lead with a one-sentence decision, then supporting detail.
"""
 
OUTPUT_SCHEMA = {
    "signal_retiming": [
        {
            "intersection": "Exact intersection name (e.g., '3rd Ave & E 34th St')",
            "current_green_seconds": "integer — estimated current phase",
            "recommended_green_seconds": "integer — your recommendation",
            "rationale": "One sentence. Why this change. What traffic it addresses."
        }
    ],
    "diversion_routes": [
        {
            "name": "Short route label (e.g., 'Route Alpha — Via 9th Ave')",
            "from": "Origin street/area",
            "to": "Destination street/area",
            "via_streets": ["Street 1", "Street 2", "Street 3"],
            "extra_travel_minutes": "integer",
            "activate_step": "integer — 1 = first to activate, 2 = second, etc."
        }
    ],
    "public_alerts": {
        "vms": "Line 1 (max 60 chars)\nLine 2 (max 60 chars)\nLine 3 (max 60 chars)",
        "radio": "Broadcast-ready text, approximately 100 words, spoken at 130 wpm (~45 seconds).",
        "social": "Twitter/X post, max 280 characters. Include relevant hashtags."
    },
    "incident_narrative": "100-150 word plain-English situational summary. Describe what happened, current road impact, actions underway, and what the officer should monitor next."
}
 
 
def build_incident_prompt(
    incident: IncidentState,
    speed_snapshot: list[dict],
    nearby_intersections: list[dict]
) -> str:
    """
    Build the structured user message for initial incident analysis.
 
    The prompt is a JSON object the model is asked to respond to
    with a JSON object matching OUTPUT_SCHEMA.
    """
    payload = {
        "task": "incident_analysis",
        "incident": {
            "type": incident["incident_type"],
            "severity": f"{incident['severity']}/5",
            "severity_label": _severity_label(incident["severity"]),
            "location": {
                "lat": incident["lat"],
                "lng": incident["lng"]
            },
            "lanes_blocked": incident["lanes_blocked"],
            "notes": incident["notes"] or "None provided",
            "declared_at": incident["declared_at"]
        },
        "current_traffic_conditions": {
            "top_congested_segments": [
                {
                    "name": seg["name"],
                    "current_speed_mph": seg["speed_mph"],
                    "congestion_level": _congestion_label(seg["speed_mph"])
                }
                for seg in speed_snapshot
            ],
            "data_timestamp": speed_snapshot[0].get("timestamp", "unknown") if speed_snapshot else "unknown"
        },
        "nearby_intersections": [
            {
                "name": inter["name"],
                "distance_from_incident_m": inter["distance_m"]
            }
            for inter in nearby_intersections
        ],
        "instructions": (
            "Respond ONLY with a valid JSON object matching the output_schema below. "
            "No preamble, no explanation outside the JSON. "
            "All street names must be real names from the road network data provided."
        ),
        "output_schema": OUTPUT_SCHEMA
    }
 
    return json.dumps(payload, indent=2)
 
 
def build_chat_messages(
    incident: IncidentState,
    llm_output: LLMOutputState,
    chat_history: list[ChatMessage],
    query: str
) -> list[dict]:
    """
    Build the messages array for a multi-turn chat query.
 
    Structure:
        [system context turn, prior AI analysis, ...rolling chat history..., current query]
 
    Rolling window: last CHAT_MAX_HISTORY_TURNS turns from chat_history.
    """
    from config import CHAT_MAX_HISTORY_TURNS
 
    # Build the incident context as the first user message
    context_message = {
        "role": "user",
        "content": json.dumps({
            "context": "live_incident",
            "incident": {
                "type": incident["incident_type"],
                "severity": incident["severity"],
                "location": {"lat": incident["lat"], "lng": incident["lng"]},
                "lanes_blocked": incident["lanes_blocked"],
                "notes": incident["notes"],
                "declared_at": incident["declared_at"]
            },
            "current_analysis": {
                "signal_retiming": llm_output["signal_retiming"],
                "diversion_routes": llm_output["diversion_routes"],
                "public_alerts": llm_output["public_alerts"],
                "narrative": llm_output["incident_narrative"]
            }
        }, indent=2)
    }
 
    # Simulate prior assistant acknowledgement to anchor the conversation
    anchor_response = {
        "role": "assistant",
        "content": (
            f"Incident acknowledged. {llm_output['incident_narrative'][:200]}... "
            "I have generated signal re-timing, diversion, and alert recommendations. "
            "Ask me anything about current conditions."
        )
    }
 
    # Rolling chat history (exclude current query)
    history_window = chat_history[-CHAT_MAX_HISTORY_TURNS * 2:]  # *2 for user+assistant pairs
    history_messages = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history_window
    ]
 
    # Current officer query
    current_query = {"role": "user", "content": query}
 
    return [context_message, anchor_response] + history_messages + [current_query]
 
 
def _severity_label(severity: int) -> str:
    labels = {1: "Minor", 2: "Low", 3: "Moderate", 4: "High", 5: "Critical"}
    return labels.get(severity, "Unknown")
 
 
def _congestion_label(speed_mph: float) -> str:
    if speed_mph >= 40:
        return "free_flow"
    elif speed_mph >= 20:
        return "slow"
    else:
        return "severe_congestion"
```
 
---
 
### 2.6 `modules/llm_client.py`
 
Responsibilities: Anthropic API calls, JSON parsing, retry logic, logging.
 
```python
# modules/llm_client.py
"""
LLM Client
==========
Wraps the Anthropic Python SDK for incident analysis and chat queries.
Handles retry logic, JSON parsing, fallback, and token logging.
 
Public API:
    analyze_incident(incident, speed_snapshot, nearby_intersections) -> LLMOutputState
    query_incident(query, incident, llm_output, chat_history) -> str
"""
import json
import time
import logging
import os
from datetime import datetime, timezone
 
import anthropic
 
from config import (
    ANTHROPIC_MODEL, LLM_MAX_TOKENS, LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS, LLM_MAX_RETRIES, LLM_RETRY_BASE_DELAY
)
from modules.state import IncidentState, LLMOutputState, ChatMessage
from modules.prompt_builder import (
    build_incident_prompt, build_chat_messages, SYSTEM_PROMPT
)
 
logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
 
 
class LLMError(Exception):
    pass
 
 
def _call_with_retry(messages: list[dict]) -> anthropic.types.Message:
    """
    Call the Anthropic API with exponential backoff retry.
    Raises LLMError after max retries.
    """
    last_error = None
    for attempt in range(LLM_MAX_RETRIES):
        try:
            start = time.monotonic()
            response = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=LLM_MAX_TOKENS,
                temperature=LLM_TEMPERATURE,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)
 
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            logger.info(
                f"LLM call OK | attempt={attempt+1} | "
                f"in={input_tokens} out={output_tokens} tokens | {elapsed_ms}ms"
            )
            return response
 
        except anthropic.RateLimitError as e:
            last_error = e
            delay = LLM_RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(f"Rate limit hit (attempt {attempt+1}). Retrying in {delay}s.")
            time.sleep(delay)
 
        except anthropic.APIStatusError as e:
            last_error = e
            delay = LLM_RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(f"API error {e.status_code} (attempt {attempt+1}). Retrying in {delay}s.")
            time.sleep(delay)
 
    raise LLMError(f"LLM call failed after {LLM_MAX_RETRIES} attempts: {last_error}")
 
 
def _parse_incident_response(raw_text: str) -> LLMOutputState:
    """
    Parse the LLM's JSON response into LLMOutputState.
    Falls back to raw narrative on parse failure.
    """
    try:
        # Strip markdown code fences if model wraps response
        clean = raw_text.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
 
        data = json.loads(clean)
        return {
            "signal_retiming": data.get("signal_retiming", []),
            "diversion_routes": data.get("diversion_routes", []),
            "public_alerts": data.get("public_alerts", {"vms": "", "radio": "", "social": ""}),
            "incident_narrative": data.get("incident_narrative", ""),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "parse_error": False
        }
 
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"LLM response JSON parse failed: {e}\nRaw: {raw_text[:500]}")
        return {
            "signal_retiming": [],
            "diversion_routes": [],
            "public_alerts": {"vms": "", "radio": "", "social": ""},
            "incident_narrative": raw_text,   # Surface raw text as narrative
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "parse_error": True
        }
 
 
def analyze_incident(
    incident: IncidentState,
    speed_snapshot: list[dict],
    nearby_intersections: list[dict]
) -> LLMOutputState:
    """
    Run a full structured incident analysis.
 
    Returns LLMOutputState with all four output types populated.
    Raises LLMError if API calls fail after retries.
    """
    prompt = build_incident_prompt(incident, speed_snapshot, nearby_intersections)
    messages = [{"role": "user", "content": prompt}]
 
    response = _call_with_retry(messages)
    raw_text = response.content[0].text
    return _parse_incident_response(raw_text)
 
 
def query_incident(
    query: str,
    incident: IncidentState,
    llm_output: LLMOutputState,
    chat_history: list[ChatMessage]
) -> str:
    """
    Answer a natural language query from the officer in the context of the live incident.
 
    Returns the AI response as a plain text string.
    Raises LLMError if API calls fail after retries.
    """
    messages = build_chat_messages(incident, llm_output, chat_history, query)
    response = _call_with_retry(messages)
    return response.content[0].text
```
 
---
 
### 2.7 `modules/map_builder.py`
 
Responsibilities: Build the Folium map with all overlays.
 
```python
# modules/map_builder.py
"""
Map Builder
===========
Constructs the Folium map for each render tick.
Called on every feed update and any incident state change.
 
Public API:
    build_map(speed_state, incident, diversion_path) -> folium.Map
"""
import folium
import logging
from modules.state import IncidentState, FeedState
from config import (
    OSM_BBOX, MAP_TILE_PROVIDER, MAP_DEFAULT_ZOOM,
    COLOUR_FREE_FLOW, COLOUR_SLOW, COLOUR_CONGESTED, COLOUR_DIVERSION,
    SEGMENT_WEIGHT, DIVERSION_WEIGHT, SPEED_FREE_FLOW, SPEED_SLOW
)
 
logger = logging.getLogger(__name__)
 
 
def _speed_to_colour(speed_mph: float) -> str:
    """Map speed to colour string for road segments."""
    if speed_mph >= SPEED_FREE_FLOW:
        return COLOUR_FREE_FLOW
    elif speed_mph >= SPEED_SLOW:
        return COLOUR_SLOW
    return COLOUR_CONGESTED
 
 
def build_map(
    feed_state: FeedState,
    incident: IncidentState,
    diversion_path: list[tuple[float, float]] | None = None
) -> folium.Map:
    """
    Build the complete Folium map for the current application state.
 
    Args:
        feed_state: Current speed data for all road segments
        incident: Current incident state (may be undeclared)
        diversion_path: Optional list of (lat, lng) tuples for diversion overlay
 
    Returns:
        Configured folium.Map instance ready for streamlit_folium render
    """
    south, west, north, east = OSM_BBOX
    center_lat = (south + north) / 2
    center_lng = (west + east) / 2
 
    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=MAP_DEFAULT_ZOOM,
        tiles=MAP_TILE_PROVIDER,
        control_scale=True
    )
 
    # ── Speed Segments ────────────────────────────────────────────────────────
    speeds = feed_state.get("current_speeds", {})
    segment_count = 0
 
    for link_id, record in speeds.items():
        lat_lngs = record.get("lat_lngs", [])
        if len(lat_lngs) < 2:
            continue
 
        colour = _speed_to_colour(record["speed"])
        tooltip_text = (
            f"<b>{record['name']}</b><br>"
            f"Speed: {record['speed']:.1f} mph<br>"
            f"Status: {'Free flow' if colour == COLOUR_FREE_FLOW else 'Slow' if colour == COLOUR_SLOW else 'Congested'}"
        )
 
        folium.PolyLine(
            locations=lat_lngs,
            color=colour,
            weight=SEGMENT_WEIGHT,
            opacity=0.8,
            tooltip=folium.Tooltip(tooltip_text, sticky=False)
        ).add_to(m)
        segment_count += 1
 
    logger.debug(f"Map: rendered {segment_count} speed segments")
 
    # ── Diversion Overlay ─────────────────────────────────────────────────────
    if diversion_path and len(diversion_path) >= 2:
        folium.PolyLine(
            locations=diversion_path,
            color=COLOUR_DIVERSION,
            weight=DIVERSION_WEIGHT,
            opacity=0.9,
            dash_array="10 5",
            tooltip=folium.Tooltip("Recommended Diversion Route", sticky=False)
        ).add_to(m)
 
        # Start/end markers for diversion
        folium.CircleMarker(
            location=diversion_path[0],
            radius=8,
            color=COLOUR_DIVERSION,
            fill=True,
            tooltip="Diversion Start"
        ).add_to(m)
        folium.CircleMarker(
            location=diversion_path[-1],
            radius=8,
            color=COLOUR_DIVERSION,
            fill=True,
            tooltip="Diversion End"
        ).add_to(m)
 
    # ── Incident Pin ──────────────────────────────────────────────────────────
    if incident["declared"] and incident["lat"] and incident["lng"]:
        icon = folium.Icon(color="red", icon="exclamation-sign", prefix="glyphicon")
        popup_text = (
            f"<b>🚨 {incident['incident_type']}</b><br>"
            f"Severity: {incident['severity']}/5<br>"
            f"Lanes blocked: {incident['lanes_blocked']}<br>"
            f"<i>{incident['notes']}</i>"
        )
        folium.Marker(
            location=[incident["lat"], incident["lng"]],
            icon=icon,
            popup=folium.Popup(popup_text, max_width=250),
            tooltip="Active Incident"
        ).add_to(m)
 
    return m
```
 
---
 
### 2.8 `app.py` — Entry Point
 
The Streamlit entry point. Handles only layout, event wiring, and state initialisation. All logic is delegated to modules.
 
```python
# app.py
"""
Traffic Incident Co-Pilot — Streamlit Entry Point
==================================================
Layout only. All logic delegated to modules/.
Run with: streamlit run app.py
"""
import os
import threading
import logging
from datetime import datetime, timezone
 
import streamlit as st
from streamlit_folium import st_folium
from dotenv import load_dotenv
 
load_dotenv()
 
from config import (
    NYC_SPEED_CSV, OSM_BBOX, OSM_CACHE_PATH, FORCE_GRAPH_RELOAD,
    FEED_INTERVAL_SECONDS, SPEED_SNAPSHOT_TOP_N, ANTHROPIC_MODEL
)
from modules.state import get_default_state
from modules.feed_manager import load_and_prepare_csv, start_feed, get_speed_snapshot
from modules.routing import load_graph, compute_diversion, get_nearby_intersections
from modules.map_builder import build_map
from modules.llm_client import analyze_incident, query_incident, LLMError
 
# ── Logging Setup ─────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ],
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)
 
# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Traffic Incident Co-Pilot",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)
 
# ── Session State Init ────────────────────────────────────────────────────────
if "app" not in st.session_state:
    st.session_state.app = get_default_state()
if "feed_lock" not in st.session_state:
    st.session_state.feed_lock = threading.Lock()
if "feed_speed_state" not in st.session_state:
    st.session_state.feed_speed_state = {
        "current_speeds": {}, "current_timestamp": "—",
        "tick_count": 0, "is_running": False
    }
 
# ── One-time Resource Loading (@cache_resource persists across reruns) ────────
@st.cache_resource
def load_resources():
    df = load_and_prepare_csv(NYC_SPEED_CSV)
    graph = load_graph(OSM_BBOX, OSM_CACHE_PATH, FORCE_GRAPH_RELOAD)
    return df, graph
 
with st.spinner("Loading road network and traffic data…"):
    speed_df, osm_graph = load_resources()
 
# ── Start Feed Thread (once per session) ─────────────────────────────────────
if "feed_thread" not in st.session_state or not st.session_state.feed_thread.is_alive():
    thread, stop_event = start_feed(
        df=speed_df,
        lock=st.session_state.feed_lock,
        speed_state=st.session_state.feed_speed_state,
        interval=FEED_INTERVAL_SECONDS
    )
    st.session_state.feed_thread = thread
    st.session_state.feed_stop_event = stop_event
 
# ── Convenience Aliases ───────────────────────────────────────────────────────
app = st.session_state.app
incident = app["incident"]
feed_state = st.session_state.feed_speed_state
llm_output = app["llm_output"]
chat = app["chat"]
 
# ── Header ────────────────────────────────────────────────────────────────────
col_title, col_status = st.columns([4, 1])
with col_title:
    st.title("🚦 Traffic Incident Co-Pilot")
with col_status:
    status_colour = "🟢" if feed_state["is_running"] else "🔴"
    st.metric("Feed", f"{status_colour} {'LIVE' if feed_state['is_running'] else 'STOPPED'}",
              f"Tick {feed_state['tick_count']}")
 
# ── Active Incident Banner ────────────────────────────────────────────────────
if incident["declared"]:
    elapsed = ""
    if incident["declared_at"]:
        delta = datetime.now(timezone.utc) - datetime.fromisoformat(incident["declared_at"])
        minutes, seconds = divmod(int(delta.total_seconds()), 60)
        hours, minutes = divmod(minutes, 60)
        elapsed = f"{hours:02d}:{minutes:02d}:{seconds:02d} elapsed"
    st.error(
        f"🚨 ACTIVE INCIDENT — {incident['incident_type']} | "
        f"Severity {incident['severity']}/5 | "
        f"{incident['lanes_blocked']} Lane(s) Blocked | {elapsed}"
    )
 
# ── Layout: 3 Columns ─────────────────────────────────────────────────────────
sidebar_col, map_col, intel_col = st.columns([1.2, 2.5, 1.8])
 
# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR COLUMN
# ═══════════════════════════════════════════════════════════════════════════════
with sidebar_col:
    # Feed Status
    st.subheader("📡 Feed Status")
    st.caption(f"Last update: {feed_state['current_timestamp']}")
    st.caption(f"Segments tracked: {len(feed_state['current_speeds'])}")
 
    st.divider()
 
    # Incident Declaration Form
    st.subheader("🚨 Incident Declaration")
 
    INCIDENT_TYPES = [
        "Major Accident", "Vehicle Fire", "Road Collapse",
        "Flooding", "Hazardous Spill", "Stalled Vehicle"
    ]
 
    incident_type = st.selectbox("Incident Type", INCIDENT_TYPES,
                                  index=INCIDENT_TYPES.index(incident["incident_type"]))
    severity = st.slider("Severity", 1, 5, incident["severity"],
                         help="1=Minor, 3=Moderate, 5=Critical")
    lanes_blocked = st.number_input("Lanes Blocked", 0, 6, incident["lanes_blocked"])
    notes = st.text_area("Notes", incident["notes"], height=80)
 
    st.caption("📍 Click map to set location")
    lat_input = st.number_input("Latitude", value=incident["lat"] or 40.748,
                                 format="%.6f", step=0.001)
    lng_input = st.number_input("Longitude", value=incident["lng"] or -73.985,
                                 format="%.6f", step=0.001)
 
    col_declare, col_clear = st.columns([2, 1])
 
    with col_declare:
        declare_clicked = st.button(
            "🚨 Declare Incident", type="primary", use_container_width=True,
            disabled=incident["declared"]
        )
    with col_clear:
        clear_clicked = st.button(
            "✕ Clear", use_container_width=True,
            disabled=not incident["declared"]
        )
 
    # ── Handle Declare ────────────────────────────────────────────────────────
    if declare_clicked:
        incident.update({
            "declared": True,
            "lat": lat_input, "lng": lng_input,
            "incident_type": incident_type,
            "severity": severity,
            "lanes_blocked": lanes_blocked,
            "notes": notes,
            "declared_at": datetime.now(timezone.utc).isoformat()
        })
 
        with st.spinner("Analysing incident…"):
            try:
                snapshot = get_speed_snapshot(
                    st.session_state.feed_lock,
                    feed_state, SPEED_SNAPSHOT_TOP_N
                )
                nearby = get_nearby_intersections(osm_graph, lat_input, lng_input)
                result = analyze_incident(incident, snapshot, nearby)
                app["llm_output"].update(result)
 
                # Compute diversion path if routes returned
                if result["diversion_routes"]:
                    first_route = result["diversion_routes"][0]
                    try:
                        # Use incident location as origin; first via-street junction as dest
                        # In production, geocode via_streets[0]; for demo use a fixed offset
                        dest_lat = lat_input + 0.015
                        dest_lng = lng_input + 0.010
                        path = compute_diversion(osm_graph, lat_input, lng_input, dest_lat, dest_lng)
                        app["diversion_path"] = path
                    except Exception as e:
                        st.warning(f"Diversion overlay failed: {e}")
                        app["diversion_path"] = None
 
            except LLMError as e:
                st.error(f"AI analysis failed: {e}")
 
        st.rerun()
 
    # ── Handle Clear ──────────────────────────────────────────────────────────
    if clear_clicked:
        app.update(get_default_state())
        st.rerun()
 
# ═══════════════════════════════════════════════════════════════════════════════
# MAP COLUMN
# ═══════════════════════════════════════════════════════════════════════════════
with map_col:
    st.subheader("🗺️ Live Traffic Map")
 
    folium_map = build_map(
        feed_state=feed_state,
        incident=incident,
        diversion_path=app.get("diversion_path")
    )
 
    map_data = st_folium(
        folium_map,
        height=580,
        use_container_width=True,
        returned_objects=["last_clicked"]
    )
 
    # Capture map click → update lat/lng in incident form
    if map_data and map_data.get("last_clicked"):
        clicked = map_data["last_clicked"]
        incident["lat"] = clicked["lat"]
        incident["lng"] = clicked["lng"]
 
    # Map legend
    st.markdown(
        "🟢 Free flow (≥40 mph) &nbsp;&nbsp; "
        "🟡 Slow (20–39 mph) &nbsp;&nbsp; "
        "🔴 Congested (<20 mph) &nbsp;&nbsp; "
        "🔵 Diversion route",
        unsafe_allow_html=False
    )
 
# ═══════════════════════════════════════════════════════════════════════════════
# INTEL COLUMN
# ═══════════════════════════════════════════════════════════════════════════════
with intel_col:
    tab_signal, tab_divert, tab_alerts, tab_chat = st.tabs([
        "🔴 Signal", "🔵 Diversion", "📢 Alerts", "💬 Chat"
    ])
 
    # ── Tab 1: Signal Re-timing ───────────────────────────────────────────────
    with tab_signal:
        st.subheader("Signal Re-Timing")
        retiming = llm_output.get("signal_retiming", [])
        if not retiming:
            st.info("Declare an incident to generate signal recommendations.")
        else:
            if llm_output.get("last_updated"):
                st.caption(f"Generated: {llm_output['last_updated'][:19]}")
            for r in sorted(retiming,
                             key=lambda x: abs(x.get("recommended_green_seconds", 0) -
                                               x.get("current_green_seconds", 0)),
                             reverse=True):
                delta = r.get("recommended_green_seconds", 0) - r.get("current_green_seconds", 0)
                delta_str = f"+{delta}s" if delta > 0 else f"{delta}s"
                with st.container():
                    st.markdown(f"**{r.get('intersection', '—')}**")
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("Current", f"{r.get('current_green_seconds', '—')}s")
                    col_b.metric("Recommended", f"{r.get('recommended_green_seconds', '—')}s",
                                 delta=delta_str)
                    col_c.metric("Change", delta_str)
                    st.caption(r.get("rationale", ""))
                    st.divider()
 
    # ── Tab 2: Diversion Routes ───────────────────────────────────────────────
    with tab_divert:
        st.subheader("Diversion Routes")
        routes = llm_output.get("diversion_routes", [])
        if not routes:
            st.info("Declare an incident to generate diversion recommendations.")
        else:
            for i, route in enumerate(routes):
                with st.expander(
                    f"{'🟢' if route.get('activate_step') == 1 else '🔵'} "
                    f"Step {route.get('activate_step', i+1)}: {route.get('name', f'Route {i+1}')}",
                    expanded=(i == 0)
                ):
                    st.markdown(f"**From:** {route.get('from', '—')}")
                    st.markdown(f"**To:** {route.get('to', '—')}")
                    st.markdown("**Via:**")
                    for street in route.get("via_streets", []):
                        st.markdown(f"  → {street}")
                    st.info(f"⏱ +{route.get('extra_travel_minutes', '?')} minutes extra travel time")
 
                    if st.button(f"Show on map", key=f"route_btn_{i}"):
                        app["active_diversion_index"] = i
                        st.rerun()
 
    # ── Tab 3: Public Alerts ──────────────────────────────────────────────────
    with tab_alerts:
        st.subheader("Public Alert Drafts")
        alerts = llm_output.get("public_alerts", {})
 
        if not any(alerts.values()):
            st.info("Declare an incident to generate public alert drafts.")
        else:
            # VMS
            st.markdown("**📟 Variable Message Sign (VMS)**")
            vms_text = alerts.get("vms", "")
            st.code(vms_text, language=None)
            st.button("📋 Copy VMS", key="copy_vms",
                      on_click=lambda: st.write(vms_text))  # clipboard via JS in prod
 
            st.divider()
 
            # Radio
            st.markdown("**📻 Radio Broadcast**")
            radio_text = alerts.get("radio", "")
            word_count = len(radio_text.split())
            st.text_area("Radio draft", radio_text, height=120, key="radio_display",
                         disabled=True, label_visibility="collapsed")
            st.caption(f"{word_count} words (~{word_count // 130 + 1} min read)")
 
            st.divider()
 
            # Social
            st.markdown("**📱 Social Media (X/Twitter)**")
            social_text = alerts.get("social", "")
            char_count = len(social_text)
            st.text_area("Social draft", social_text, height=80, key="social_display",
                         disabled=True, label_visibility="collapsed")
            char_colour = "red" if char_count > 280 else "green"
            st.markdown(
                f"<span style='color:{char_colour}'>{char_count}/280 characters</span>",
                unsafe_allow_html=True
            )
 
            # Export
            st.divider()
            export_content = _build_export_text(incident, alerts)
            st.download_button(
                label="⬇️ Export All Alerts (.txt)",
                data=export_content,
                file_name=f"incident_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
 
    # ── Tab 4: Chat ───────────────────────────────────────────────────────────
    with tab_chat:
        st.subheader("Incident Chat")
 
        if not incident["declared"]:
            st.info("💬 Declare an incident to begin querying the AI Co-Pilot.")
        else:
            # Chat history display
            chat_container = st.container(height=380)
            with chat_container:
                for msg in chat["messages"]:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])
                        st.caption(msg.get("timestamp", "")[:19])
 
            # Suggested follow-up chips
            if chat["messages"]:
                suggestions = [
                    "Is it safe to open the southbound lane now?",
                    "Which diversion should I activate first?",
                    "Draft a revised social media update"
                ]
                st.markdown("**Suggested queries:**")
                sugg_cols = st.columns(len(suggestions))
                for i, sugg in enumerate(suggestions):
                    if sugg_cols[i].button(sugg, key=f"sugg_{i}", use_container_width=True):
                        _handle_chat_query(sugg, incident, llm_output, chat)
                        st.rerun()
 
            # Chat input
            user_query = st.chat_input("Ask about the incident…")
            if user_query:
                _handle_chat_query(user_query, incident, llm_output, chat)
                st.rerun()
 
            # Clear chat
            if st.button("🗑️ Clear Chat", key="clear_chat"):
                chat["messages"] = []
                st.rerun()
 
 
# ── Helper Functions ───────────────────────────────────────────────────────────
 
def _handle_chat_query(query: str, incident, llm_output, chat) -> None:
    """Add user message, call LLM, add assistant response."""
    ts = datetime.now(timezone.utc).isoformat()
    chat["messages"].append({"role": "user", "content": query, "timestamp": ts})
    try:
        response = query_incident(query, incident, llm_output, chat["messages"])
        chat["messages"].append({
            "role": "assistant", "content": response,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except LLMError as e:
        chat["messages"].append({
            "role": "assistant",
            "content": f"⚠️ AI query failed: {e}. Please try again.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
 
 
def _build_export_text(incident: dict, alerts: dict) -> str:
    """Build the plain-text export content for all three alert variants."""
    lines = [
        "=" * 60,
        "TRAFFIC INCIDENT ALERT EXPORT",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Incident: {incident.get('incident_type', '—')}",
        f"Severity: {incident.get('severity', '—')}/5",
        f"Location: {incident.get('lat', '—')}, {incident.get('lng', '—')}",
        "=" * 60,
        "",
        "── VMS (Variable Message Sign) ──",
        alerts.get("vms", ""),
        "",
        "── RADIO BROADCAST ──",
        alerts.get("radio", ""),
        "",
        "── SOCIAL MEDIA (X/Twitter) ──",
        alerts.get("social", ""),
        "",
        "=" * 60,
    ]
    return "\n".join(lines)
 
 
# ── Auto-refresh for feed updates ─────────────────────────────────────────────
# Rerun every 5 seconds to pick up new feed data
# Uses streamlit-autorefresh if available, else a manual timer
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=5000, key="feed_refresh")
except ImportError:
    pass  # Without autorefresh, user must interact to see feed updates
```
 
---
 
## 3. Data Flow Diagrams
 
### 3.1 Feed Update Flow
 
```
[NYC Speed CSV]
     │
     ▼
load_and_prepare_csv()
  - validate columns
  - parse timestamps
  - decode polylines
  - sort by DataAsOf
     │
     ▼
[Prepared DataFrame in memory]
     │
     ▼
start_feed(df, lock, speed_state, interval=5s)
     │
     ▼
FeedThread (daemon):
  loop:
    row = df.iloc[tick % len(df)]
    acquire(lock)
    speed_state["current_speeds"][linkId] = {speed, name, lat_lngs}
    speed_state["current_timestamp"] = timestamp
    speed_state["tick_count"] += 1
    release(lock)
    sleep(interval)
     │
     ▼ (every 5s, Streamlit reruns via autorefresh)
Main Thread:
  feed_state = st.session_state.feed_speed_state  [lock-safe read]
  map = build_map(feed_state, incident, diversion_path)
  st_folium(map)  → renders updated colour segments
```
 
### 3.2 Incident Declaration Flow
 
```
Officer clicks map → lat/lng captured by st_folium return value
Officer fills form (type, severity, lanes, notes)
Officer clicks [Declare Incident]
     │
     ▼
incident state updated in session_state
     │
     ├──► get_speed_snapshot(lock, feed_state, top_n=10)
     │         Returns: [{name, speed_mph, lat_lngs}, ...]
     │
     ├──► get_nearby_intersections(osm_graph, lat, lng, radius=500m)
     │         Returns: [{name, distance_m, node_id}, ...]
     │
     ▼
prompt_builder.build_incident_prompt(incident, snapshot, intersections)
     │  Returns: JSON string with full schema
     │
     ▼
llm_client.analyze_incident(incident, snapshot, intersections)
     │  → Anthropic API (claude-sonnet-4-6)
     │  ← JSON response
     │  → _parse_incident_response() → LLMOutputState
     │
     ├──► app["llm_output"] updated
     │
     ├──► routing.compute_diversion(graph, origin, dest)
     │         → A* path → [(lat, lng), ...]
     │         → app["diversion_path"] updated
     │
     ▼
st.rerun()
  → Status banner shows
  → Intel panel tabs populate
  → Map re-renders with incident pin + diversion overlay
```
 
### 3.3 Chat Query Flow
 
```
Officer types query in chat input
     │
     ▼
_handle_chat_query(query, incident, llm_output, chat)
     │
     ├──► chat["messages"].append({role:"user", content:query})
     │
     ▼
prompt_builder.build_chat_messages(incident, llm_output, chat_history, query)
     │  Returns: [context_turn, anchor_response, ...rolling_history..., current_query]
     │  Rolling window: last 10 turns max
     │
     ▼
llm_client._call_with_retry(messages)
     │  → Anthropic API
     │  ← Plain text response (no JSON schema for chat)
     │
     ▼
chat["messages"].append({role:"assistant", content:response})
     │
     ▼
st.rerun() → Chat panel re-renders with new message
```
 
---
 
## 4. Prompt Engineering Design
 
### 4.1 Incident Analysis Prompt Design Principles
 
**Why JSON schema in prompt (not system prompt)?**  
The output schema is large (~600 tokens). Placing it in the user turn (alongside data) allows the model to see data and schema simultaneously, reducing hallucination of field names. The system prompt carries behavioural instructions only.
 
**Why low temperature (0.2)?**  
Signal re-timing and diversion recommendations must be consistent. Deterministic responses allow officers to trust that re-running the analysis on similar data yields similar recommendations. Higher temperature introduces creative variance inappropriate for safety-critical suggestions.
 
**Why include `congestion_level` label alongside numeric speed?**  
The model performs better at reasoning about impact when it has both numeric (4.2 mph) and categorical (severe_congestion) representations. This mirrors how a human officer would interpret the data.
 
### 4.2 Prompt Token Budget
 
| Component | Estimated Tokens |
|-----------|-----------------|
| System prompt | ~200 |
| Incident context | ~150 |
| Speed snapshot (10 segments) | ~250 |
| Nearby intersections (8 nodes) | ~150 |
| Output schema definition | ~600 |
| **Total input** | **~1,350** |
| **Expected output** | **~800–1,200** |
| **Total per incident analysis** | **~2,150–2,550** |
 
Well within the 4,000-token budget specified in the PRD.
 
### 4.3 Chat Prompt Token Budget
 
| Component | Estimated Tokens |
|-----------|-----------------|
| Context turn (incident + prior analysis) | ~600 |
| Anchor response | ~100 |
| Rolling history (10 turns × ~50 tokens avg) | ~500 |
| Current query | ~30 |
| **Total input** | **~1,230** |
| **Expected output** | **~200–400** |
 
Well within 8,000-token context limit.
 
### 4.4 Prompt Hardening
 
These patterns are enforced in `prompt_builder.py` to prevent degraded outputs:
 
1. **Schema anchoring**: The full JSON schema is included in every incident prompt. The model cannot omit keys — missing keys cause a parse failure that surfaces in the UI.
2. **Instruction clarity**: "Respond ONLY with a valid JSON object" prevents the model from adding prose before the JSON.
3. **Concrete constraints on alerts**: VMS (≤60 chars/line), Radio (~100 words), Social (≤280 chars) are specified with exact limits, not "concise".
4. **Anti-hedging instruction**: "Never say 'I think' or 'it might be'" in the chat system prompt enforces command language.
 
---
 
## 5. State Management Design
 
### 5.1 State Ownership
 
| State Key | Written by | Read by | Notes |
|-----------|-----------|---------|-------|
| `feed_speed_state` | Feed thread (under lock) | Map builder, prompt builder | External to `app` dict; managed separately |
| `app.incident` | Sidebar form handlers | Map builder, prompt builder, chat | Central incident truth |
| `app.llm_output` | `analyze_incident()` result | All intel tabs | Replaced atomically on new analysis |
| `app.chat.messages` | `_handle_chat_query()` | Chat tab | Append-only; rolling window applied in prompt builder |
| `app.diversion_path` | Routing module | Map builder | `None` when no route computed |
 
### 5.2 State Initialisation Guard
 
```python
if "app" not in st.session_state:
    st.session_state.app = get_default_state()
```
 
This pattern ensures state is initialised exactly once per browser session. Streamlit runs `app.py` top-to-bottom on every interaction; the `if` guard prevents reset.
 
### 5.3 State Mutation Pattern
 
All state mutations happen in event handlers (button clicks, chat input), never in rendering code. Rendering code is read-only. After mutation, `st.rerun()` is called to trigger a re-render.
 
```python
# CORRECT: Mutate in event handler, then rerun
if declare_clicked:
    incident.update({...})      # Mutate
    result = analyze_incident() # Compute
    app["llm_output"].update(result)  # Mutate
    st.rerun()                  # Trigger re-render
 
# INCORRECT: Never mutate during render
folium_map = build_map(...)   # Read-only, no mutation here
```
 
---
 
## 6. Threading & Concurrency Design
 
### 6.1 Lock Strategy
 
A single `threading.Lock()` protects `feed_speed_state`. This is a coarse-grained lock — the entire speed dict is locked during both writes (feed thread) and reads (main thread). Given the frequency (5-second writes, <2-second reads), contention is negligible.
 
```python
# Feed thread write (in _feed_loop):
with lock:
    speed_state["current_speeds"][link_id] = record
    speed_state["current_timestamp"] = timestamp
    speed_state["tick_count"] = tick
 
# Main thread read (in get_speed_snapshot):
with lock:
    speeds = dict(speed_state.get("current_speeds", {}))  # Copy, then release
# ↑ dict() copy is critical: we release the lock immediately and work on the copy
```
 
### 6.2 Thread Lifecycle
 
```
Streamlit session start
        │
        ▼
"feed_thread" not in session_state?
    Yes → start_feed() → thread starts
    No  → thread.is_alive() → if False → restart
        │
        ▼
Thread runs as daemon (auto-killed on process exit)
        │
        ▼
"Clear Incident" does NOT stop thread
(feed continues independent of incident state)
        │
        ▼
Browser close / process shutdown → daemon thread killed by Python
```
 
### 6.3 Avoiding Double-Start
 
The thread is stored in `st.session_state`. Because Streamlit sessions are persistent per browser tab, the thread is checked for liveness before restart, preventing duplicate threads.
 
---
 
## 7. Map Rendering Pipeline
 
### 7.1 Render Trigger Conditions
 
The map rebuilds on every Streamlit rerun. Reruns are triggered by:
- User interaction (button click, form change, chat input)
- `st_autorefresh` (every 5 seconds for feed updates)
 
### 7.2 Rendering Order
 
```
build_map(feed_state, incident, diversion_path)
    │
    ├── 1. Create base Folium.Map (tile layer, center, zoom)
    ├── 2. Iterate speed_state["current_speeds"]
    │       For each segment with ≥2 lat/lng points:
    │         - Compute colour from speed
    │         - Add PolyLine with tooltip
    ├── 3. If diversion_path is not None:
    │       - Add blue dashed PolyLine
    │       - Add CircleMarker at start and end
    └── 4. If incident.declared:
            - Add red Marker with incident popup
    │
    ▼
st_folium(folium_map, height=580, returned_objects=["last_clicked"])
    │
    ▼
map_data = return value (includes last_clicked if user clicked map)
```
 
### 7.3 Performance Notes
 
- **Segment count:** The NYC speed dataset typically has 100–300 active segments per tick. At this count, Folium renders within the 2-second target.
- **If performance degrades:** Filter segments to those within the map's current viewport bounds. OSMnx provides bounding box filtering.
- **Map zoom persistence:** `st_folium` preserves zoom/pan state between renders when the Folium map object uses the same `location` and `zoom_start`. Do not change these on re-render.
 
---
 
## 8. Error Handling Strategy
 
### 8.1 Error Taxonomy
 
| Error Type | Source | Handling |
|-----------|--------|---------|
| `FeedError` | CSV missing columns | Show startup error; halt |
| `RoutingError` | No A* path | Show warning banner; skip overlay |
| `LLMError` | API failure after retries | Show error card in intel panel; preserve prior outputs |
| JSON parse failure | LLM malformed response | Fallback: raw text in narrative; `parse_error: True` |
| OSM download failure | Network error | Load from cache; if no cache, show startup error |
| Thread deadlock (lock timeout) | Concurrency | `acquire(timeout=0.5)`; log and skip tick |
 
### 8.2 Error Display Pattern
 
All errors surface as `st.error()` or `st.warning()` cards in the relevant panel. The app never crashes to an exception page. Use try/except at every LLM call and routing call.
 
```python
try:
    result = analyze_incident(incident, snapshot, nearby)
    app["llm_output"].update(result)
except LLMError as e:
    st.error(f"⚠️ AI analysis failed: {e}")
    # Preserve prior llm_output; do not clear it
```
 
---
 
## 9. Configuration Reference
 
All values live in `config.py`. No developer should ever change anything outside `config.py` to adapt the system to a different city, model, or dataset.
 
| Config Key | Default | What it controls |
|-----------|---------|-----------------|
| `OSM_BBOX` | Manhattan | Road network download area |
| `OSM_CACHE_PATH` | `data/osm_cache/nyc_graph.graphml` | Graph cache location |
| `FORCE_GRAPH_RELOAD` | `False` | Set `True` to re-download OSM |
| `NYC_SPEED_CSV` | `data/nyc_traffic_speed.csv` | Feed data source |
| `FEED_INTERVAL_SECONDS` | `5.0` | Seconds per feed tick |
| `SPEED_FREE_FLOW` | `40` | mph threshold for green |
| `SPEED_SLOW` | `20` | mph threshold for amber |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | LLM model |
| `LLM_MAX_TOKENS` | `2048` | Max response tokens |
| `LLM_TEMPERATURE` | `0.2` | Determinism vs. creativity |
| `LLM_MAX_RETRIES` | `3` | Retry attempts on API error |
| `CHAT_MAX_HISTORY_TURNS` | `10` | Rolling chat window |
| `SPEED_SNAPSHOT_TOP_N` | `10` | Slowest segments in prompt |
| `MAP_DEFAULT_ZOOM` | `13` | Initial map zoom level |
 
---
 
## 10. Full Code Skeletons
 
### 10.1 `requirements.txt`
 
```
streamlit>=1.32.0
streamlit-folium>=0.18.0
folium>=0.16.0
osmnx>=1.9.0
networkx>=3.2.0
pandas>=2.1.0
anthropic>=0.25.0
python-dotenv>=1.0.0
polyline>=2.0.0
streamlit-autorefresh>=1.0.0
```
 
### 10.2 `.env.example`
 
```
# Copy this file to .env and fill in your API key
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```
 
### 10.3 `tests/test_feed_manager.py` (Skeleton)
 
```python
# tests/test_feed_manager.py
import pytest
import threading
import pandas as pd
from modules.feed_manager import load_and_prepare_csv, start_feed, FeedError
 
FIXTURE_CSV = "tests/fixtures/sample_speeds.csv"
 
def test_load_valid_csv():
    df = load_and_prepare_csv(FIXTURE_CSV)
    assert len(df) > 0
    assert "lat_lngs" in df.columns
    assert all(len(x) >= 2 for x in df["lat_lngs"] if x)
 
def test_load_invalid_csv_raises():
    with pytest.raises(FeedError):
        load_and_prepare_csv("tests/fixtures/bad_speeds.csv")
 
def test_feed_updates_state():
    df = load_and_prepare_csv(FIXTURE_CSV)
    lock = threading.Lock()
    state = {"current_speeds": {}, "current_timestamp": "", "tick_count": 0, "is_running": False}
    thread, stop_event = start_feed(df, lock, state, interval=0.1)
    import time; time.sleep(0.5)
    stop_event.set(); thread.join(timeout=2)
    assert state["tick_count"] > 0
    assert len(state["current_speeds"]) > 0
```
 
### 10.4 `tests/test_routing.py` (Skeleton)
 
```python
# tests/test_routing.py
import pytest
import osmnx as ox
from modules.routing import load_graph, compute_diversion, find_nearest_node, RoutingError
 
CACHE = "tests/fixtures/test_graph.graphml"
BBOX = (40.740, -73.995, 40.755, -73.975)  # Small test bbox
 
@pytest.fixture(scope="module")
def graph():
    return load_graph(BBOX, CACHE, force_reload=False)
 
def test_nearest_node_returns_int(graph):
    node = find_nearest_node(graph, 40.748, -73.985)
    assert isinstance(node, int)
 
def test_compute_diversion_returns_path(graph):
    path = compute_diversion(graph, 40.748, -73.990, 40.752, -73.980)
    assert len(path) >= 2
    assert all(len(p) == 2 for p in path)
```
 
### 10.5 `tests/test_prompt_builder.py` (Skeleton)
 
```python
# tests/test_prompt_builder.py
import json
from modules.prompt_builder import build_incident_prompt, build_chat_messages
 
MOCK_INCIDENT = {
    "declared": True, "lat": 40.748, "lng": -73.985,
    "incident_type": "Major Accident", "severity": 4,
    "lanes_blocked": 2, "notes": "Overturned truck",
    "declared_at": "2024-01-15T14:32:00Z"
}
MOCK_SNAPSHOT = [{"name": "FDR Drive NB", "speed_mph": 4.2, "lat_lngs": [[40.748, -73.970]]}]
MOCK_INTERSECTIONS = [{"name": "3rd Ave & E 34th St", "distance_m": 180, "node_id": 123}]
 
def test_incident_prompt_is_valid_json():
    prompt = build_incident_prompt(MOCK_INCIDENT, MOCK_SNAPSHOT, MOCK_INTERSECTIONS)
    data = json.loads(prompt)
    assert "incident" in data
    assert "output_schema" in data
    assert data["incident"]["type"] == "Major Accident"
 
def test_chat_messages_structure():
    messages = build_chat_messages(MOCK_INCIDENT, {
        "signal_retiming": [], "diversion_routes": [],
        "public_alerts": {"vms": "", "radio": "", "social": ""},
        "incident_narrative": "Test narrative", "last_updated": None, "parse_error": False
    }, [], "Is it safe to open the lane?")
    assert messages[-1]["role"] == "user"
    assert "safe" in messages[-1]["content"]
```
 
---
 
## 11. Dependency Installation
 
```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
 
# 2. Install dependencies
pip install -r requirements.txt
 
# 3. Set up environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
 
# 4. Create required directories
mkdir -p data/osm_cache logs exports tests/fixtures
 
# 5. Place NYC speed CSV
# Download from: https://data.cityofnewyork.us/Transportation/DOT-Traffic-Speeds-NBE/i4gi-tjb9
# Save as: data/nyc_traffic_speed.csv
 
# 6. Pre-download OSM graph (recommended before demo)
python -c "
from config import OSM_BBOX, OSM_CACHE_PATH
from modules.routing import load_graph
G = load_graph(OSM_BBOX, OSM_CACHE_PATH, force_reload=True)
print(f'Graph ready: {len(G.nodes)} nodes, {len(G.edges)} edges')
"
 
# 7. Run the app
streamlit run app.py
 
# 8. Run tests
pytest tests/ -v --tb=short
```
 
---
 
*End of Technical Design Document*  
*Version 1.0 — Companion to PRD.md v1.0*
 
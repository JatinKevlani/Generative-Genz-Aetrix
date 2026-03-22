# Product Requirements Document
# LLM Co-Pilot for Traffic Incident Command

**Version:** 1.0  
**Status:** Draft — Ready for Engineering Review  
**Author:** AI Systems Architecture  
**Last Updated:** 2026-03-21  
**Reviewers:** Traffic Engineering Lead, City TMC Director, Public Information Office

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Goals & Success Criteria](#3-goals--success-criteria)
4. [Stakeholders & User Personas](#4-stakeholders--user-personas)
5. [Scope](#5-scope)
6. [Functional Requirements](#6-functional-requirements)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [Technical Architecture](#8-technical-architecture)
9. [Data Architecture](#9-data-architecture)
10. [API Definitions](#10-api-definitions)
11. [UI/UX Specifications](#11-uiux-specifications)
12. [Engineering Tasks — Phased Breakdown](#12-engineering-tasks--phased-breakdown)
13. [Testing Strategy](#13-testing-strategy)
14. [Risk Register](#14-risk-register)
15. [Glossary](#15-glossary)

---

## 1. Executive Summary

Traffic incidents are time-critical, high-cognitive-load events. Officers at Traffic Management Centres (TMCs) currently manage radio feeds, sensor dashboards, camera streams, and printed road maps simultaneously — all in separate tools — while manually drafting response plans under extreme pressure.

This document specifies an **LLM-powered Incident Co-Pilot**: a Streamlit dashboard that ingests a live-replayed NYC traffic speed feed, renders it on an interactive road-network map, and surfaces four categories of AI-generated intelligence — signal re-timing, diversion routing, public alert drafts, and a conversational incident narrative — to reduce officer cognitive load and compress incident clearance time.

The system is designed as a **demonstration-grade prototype with production-ready architecture**, capable of showing measurable response-time improvements against a manual baseline within a single demo session.

---

## 2. Problem Statement

### 2.1 Current State

When a major traffic incident occurs, TMC officers must simultaneously:

- Monitor sensor speed feeds (typically a separate SCADA or vendor dashboard)
- Watch camera streams (often a third-party VMS)
- Read paper or GIS-based road maps to identify alternative routes
- Communicate on radio channels with field units
- Manually compose public alerts for Variable Message Signs (VMS), radio broadcasts, and social media
- Decide signal re-timing sequences based on experience alone

These systems do not share data. No tool synthesises across all sources into a coherent recommendation. Officers perform this synthesis in their heads, under time pressure, leading to:

- Delayed diversion activations (avg. 8–15 min post-incident before rerouting begins)
- Generic or poorly targeted public alerts
- Signal re-timing decisions that are inconsistent across shifts
- Secondary accidents caused by unexpected queue spillback

### 2.2 Core Pain Points (Ranked by Severity)

| # | Pain Point | Impact |
|---|-----------|--------|
| 1 | No integrated situational view | Officers switch between 4+ tools, losing context |
| 2 | Manual diversion planning | No A* routing, relies on memorised road network |
| 3 | Manual alert drafting | 3–5 min lost composing alerts during peak chaos |
| 4 | No conversational query interface | Officers cannot ask "what if" questions of the data |
| 5 | No audit trail of AI recommendations | No learning loop for future incidents |

---

## 3. Goals & Success Criteria

### 3.1 Primary Goals

| Goal | Description |
|------|-------------|
| G1 | Reduce mean time-to-first-diversion-recommendation from ~12 min (manual) to <2 min |
| G2 | Provide actionable signal re-timing plans naming specific intersections and phase durations |
| G3 | Generate publish-ready public alert copy (VMS / Radio / Social) within 30 seconds of incident declaration |
| G4 | Support natural-language conversational queries against live incident data |
| G5 | Render live-replayed traffic speeds on a geographic map with diversion overlays |

### 3.2 Definition of Done (Demo-Ready)

The system is **done** when a single evaluator can:

1. Launch the app with one command (`streamlit run app.py`)
2. Observe NYC traffic speed data replaying at 5-second intervals on a colour-coded map
3. Click "Declare Incident" at any map location and receive all four AI outputs within 10 seconds
4. Ask a follow-up question in the chat panel and receive a contextually accurate response
5. See a diversion route overlaid on the map in a distinct colour
6. Export the session's alert draft as plain text

### 3.3 Key Metrics

| Metric | Target |
|--------|--------|
| Time to first AI recommendation after incident declaration | ≤ 10 seconds |
| LLM token budget per full incident analysis | ≤ 4,000 tokens |
| Map render latency on feed update (5-sec tick) | ≤ 2 seconds |
| App cold-start time | ≤ 15 seconds |
| LLM context window used per turn | ≤ 8,000 tokens (fits claude-sonnet-4-6 comfortably) |
| Concurrent map + feed + LLM without UI freeze | Achieved via threading |

---

## 4. Stakeholders & User Personas

### 4.1 Primary Users

#### Persona 1: Traffic Control Officer (Primary)
- **Name:** Officer Meera S.
- **Context:** Stationed at city TMC, manages 2–4 incidents per shift
- **Pain:** Switches between 5 tools, radio, and phone simultaneously during an incident
- **Needs:** One screen, clear recommendations, no jargon, the ability to ask questions
- **Tech comfort:** Moderate — familiar with digital dashboards but not AI tools
- **Key requirement:** Recommendations must name *specific intersections*, not generic advice

#### Persona 2: City Traffic Operations Manager (Secondary)
- **Name:** Manager Dev P.
- **Context:** Oversees TMC, reviews incident logs, briefs city leadership
- **Pain:** No post-incident analytics; relies on officer recollection for debriefs
- **Needs:** Summary of AI actions taken, timeline of recommendations, exportable logs
- **Key requirement:** Audit trail of every AI recommendation with timestamp

#### Persona 3: Public Information Officer (Secondary)
- **Name:** PIO Anita K.
- **Context:** Publishes road alerts via VMS, city radio, Twitter/X, city website
- **Pain:** Drafts alerts manually while being briefed by radio; prone to errors under pressure
- **Needs:** Ready-to-publish copy in the correct format for each channel, instantly
- **Key requirement:** Alert drafts must be <280 chars for social, ≤3 lines for VMS, broadcast-ready for radio

### 4.2 Indirect Stakeholders

- **City IT Department** — Infrastructure support, security review
- **Road network data providers** — OSM contributors
- **Anthropic** — LLM provider, API rate limits apply

---

## 5. Scope

### 5.1 In Scope (v1.0)

- Live traffic speed replay from NYC dataset at configurable interval (default: 5 seconds)
- OSM road network for a defined NYC bounding box (configurable)
- Interactive Folium map rendered inside Streamlit with colour-coded speed segments
- Incident declaration via map click or sidebar form
- Four LLM output types: signal re-timing, diversion routes, public alerts, incident narrative
- Multi-turn conversational chat with incident context carried across turns
- Diversion route overlay on map using A* (NetworkX)
- Session export of alert drafts as `.txt`
- Configurable LLM parameters (model, temperature) via sidebar

### 5.2 Out of Scope (v1.0)

- Real-time camera stream ingestion
- Real-time radio transcription
- Integration with real signal controllers (SCATS/SCOOT)
- Authentication and user management
- Multi-user / multi-session concurrency
- Mobile-responsive layout
- VMS hardware integration
- Weather or CCTV data feeds
- Persistent database (SQLite / Postgres)
- Production deployment (Docker, cloud hosting)

### 5.3 Future Scope (v2.0 Considerations)

- WebSocket-based live sensor integration
- CCTV stream summary via vision model
- Multi-incident management (queue of active incidents)
- Officer authentication and role-based access
- Persistent incident log with PostgreSQL

---

## 6. Functional Requirements

### 6.1 FR-01: Application Bootstrap

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01.1 | On launch, download OSM road network for defined NYC bounding box using OSMnx | P0 |
| FR-01.2 | Cache downloaded OSM graph to disk to avoid re-download on restart | P0 |
| FR-01.3 | Load NYC traffic speed CSV into memory as a pandas DataFrame at startup | P0 |
| FR-01.4 | Validate that the Anthropic API key is present in environment; show error if missing | P0 |
| FR-01.5 | Display a loading spinner with status messages during bootstrap | P1 |

### 6.2 FR-02: Live Traffic Feed Simulation

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-02.1 | Replay CSV rows as time-stamped speed records at a configurable interval (default: 5 seconds) | P0 |
| FR-02.2 | Each feed tick updates the speed data in `st.session_state` | P0 |
| FR-02.3 | Feed replay runs in a background thread; it must not block the UI | P0 |
| FR-02.4 | Feed speed is adjustable via sidebar slider (1x, 2x, 5x replay) | P1 |
| FR-02.5 | Feed loop restarts from beginning when all rows are consumed | P1 |
| FR-02.6 | Current feed timestamp is displayed in the sidebar | P1 |

### 6.3 FR-03: Map Rendering

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-03.1 | Render NYC road network using Folium on a `streamlit-folium` component | P0 |
| FR-03.2 | Road segments are colour-coded by current speed: green (≥40 mph), amber (20–39), red (<20) | P0 |
| FR-03.3 | Map auto-centres on the NYC bounding box on first load | P0 |
| FR-03.4 | Clicking a map location emits lat/lng coordinates captured for incident declaration | P0 |
| FR-03.5 | When a diversion route is active, overlay it as a distinct blue polyline with 4px weight | P0 |
| FR-03.6 | Incident pin (red marker) is placed at declared location | P0 |
| FR-03.7 | Map re-renders on every feed tick to reflect updated speeds | P0 |
| FR-03.8 | Map renders within 2 seconds of each feed tick | P1 |
| FR-03.9 | Tooltip on road segment hover shows: segment name, current speed, free-flow speed | P1 |

### 6.4 FR-04: Incident Declaration

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-04.1 | Officer can declare an incident by clicking the map (lat/lng auto-populated) | P0 |
| FR-04.2 | Sidebar form fields: Incident Type (dropdown), Severity (1–5 slider), Lanes Blocked (numeric), Notes (text area) | P0 |
| FR-04.3 | "Declare Incident" button triggers LLM analysis immediately | P0 |
| FR-04.4 | Incident state is stored in `st.session_state` and persists across UI interactions | P0 |
| FR-04.5 | "Clear Incident" button resets all incident state and removes overlays | P1 |
| FR-04.6 | Incident type options: Major Accident, Vehicle Fire, Road Collapse, Flooding, Hazardous Spill, Stalled Vehicle | P1 |

### 6.5 FR-05: LLM Analysis — Initial Incident Report

On incident declaration, the system must call the Anthropic API and return **all four output types** in a single structured response.

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-05.1 | **Signal Re-Timing**: Return a list of ≥3 affected intersections with: intersection name, current green phase duration, recommended new duration, and rationale (1 sentence) | P0 |
| FR-05.2 | **Diversion Routes**: Return ≥2 alternative routes with: origin, destination, via-streets in order, estimated additional travel time, and activation sequence step | P0 |
| FR-05.3 | **Public Alert Drafts**: Return three channel-specific alert variants: (a) VMS ≤3 lines / ≤60 chars per line, (b) Radio ≤45 seconds at 130 wpm (~100 words), (c) Social Media ≤280 characters | P0 |
| FR-05.4 | **Incident Narrative**: Return a 100–150 word plain-English summary of current conditions suitable for an officer briefing | P0 |
| FR-05.5 | All four outputs must be returned in a single JSON-parseable LLM response using a structured prompt | P0 |
| FR-05.6 | Parsed outputs populate four dedicated tab panels in the UI without requiring page reload | P0 |
| FR-05.7 | LLM call must complete within 10 seconds; display a spinner with "Analysing incident…" during the call | P0 |
| FR-05.8 | LLM errors (rate limit, timeout) are caught and displayed as a user-facing error card; the app must not crash | P0 |

### 6.6 FR-06: Conversational Incident Query

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-06.1 | Chat panel accepts free-text officer queries post-incident-declaration | P0 |
| FR-06.2 | Each query includes: full incident context, current speed snapshot, prior conversation history (last 10 turns) | P0 |
| FR-06.3 | Responses are streamed into the chat panel character-by-character | P1 |
| FR-06.4 | If no incident is declared, the chat panel shows: "Declare an incident to begin querying." | P0 |
| FR-06.5 | Chat history is displayed in a scrollable panel with user/assistant labels and timestamps | P0 |
| FR-06.6 | Officer can clear chat history without clearing the incident | P1 |
| FR-06.7 | Suggested follow-up queries appear as clickable chips below the last AI response | P1 |

Example supported queries (must work accurately):
- "Is it safe to open the southbound lane now?"
- "What is the estimated clearance time?"
- "Which diversion route should I activate first?"
- "Draft a revised social media alert for 30 minutes post-incident"

### 6.7 FR-07: Diversion Route Overlay

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-07.1 | When the LLM returns a diversion route, compute the actual OSM path using NetworkX A* | P0 |
| FR-07.2 | The computed path is overlaid on the Folium map as a blue polyline | P0 |
| FR-07.3 | Officers can toggle between primary and secondary diversion overlays via radio buttons | P1 |
| FR-07.4 | If A* fails to find a path, display error "Route computation failed: [reason]" and skip overlay | P0 |
| FR-07.5 | Diversion path node count and estimated distance (km) displayed in sidebar | P1 |

### 6.8 FR-08: Alert Export

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-08.1 | "Export Alerts" button downloads all three alert variants as a `.txt` file | P0 |
| FR-08.2 | Exported file is named: `incident_alerts_YYYYMMDD_HHMMSS.txt` | P0 |
| FR-08.3 | File includes: incident metadata, timestamp, and all three alert variants with channel labels | P1 |

---

## 7. Non-Functional Requirements

### 7.1 Performance

| Requirement | Target |
|-------------|--------|
| Feed tick-to-map-update latency | ≤ 2 seconds |
| Initial LLM response (all 4 outputs) | ≤ 10 seconds |
| Chat response latency | ≤ 5 seconds |
| App cold start (including OSM download from cache) | ≤ 15 seconds |
| OSM graph cache load from disk | ≤ 3 seconds |

### 7.2 Reliability

- The feed simulation thread must restart automatically if it crashes.
- All LLM calls must be wrapped in retry logic: 3 attempts with exponential backoff (1s, 2s, 4s).
- JSON parsing of LLM output must gracefully fallback to raw text display if parsing fails.
- No unhandled exceptions should crash the Streamlit app; all errors surface as UI error cards.

### 7.3 Maintainability

- All configuration (bounding box, model name, feed path, replay interval) must be in a single `config.py` file — no magic strings in application code.
- Each module must have a single responsibility (see Architecture section).
- All functions must have type annotations.
- All functions longer than 20 lines must have a docstring.
- No inline API keys; always use `os.environ` or `.env` via `python-dotenv`.

### 7.4 Security

- Anthropic API key must never appear in source code or logs.
- No external HTTP calls beyond the Anthropic API and OSM tile server.
- No user data persisted to disk in v1.0 (stateless session).

### 7.5 Observability

- All LLM requests log: timestamp, prompt token count, response token count, latency (ms).
- Feed thread logs tick count, timestamp, and rows consumed every 10 ticks.
- All logs written to `logs/app.log` using Python `logging` module at INFO level.
- Errors logged at ERROR level with full traceback.

---

## 8. Technical Architecture

### 8.1 System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Streamlit Frontend                          │
│  ┌─────────────┐  ┌──────────────────┐  ┌────────────────────┐ │
│  │  Sidebar     │  │   Map Panel       │  │   Chat Panel       │ │
│  │  - Controls  │  │   Folium/OSM      │  │   Multi-turn LLM   │ │
│  │  - Incident  │  │   Speed overlay   │  │   Query Interface  │ │
│  │    Form      │  │   Diversion line  │  │                    │ │
│  └──────┬───────┘  └────────┬─────────┘  └─────────┬──────────┘ │
│         │                   │                        │            │
│  ┌──────▼───────────────────▼────────────────────────▼──────────┐│
│  │                   st.session_state (shared state bus)         ││
│  └──────┬───────────────────┬────────────────────────┬──────────┘│
└─────────┼───────────────────┼────────────────────────┼───────────┘
          │                   │                         │
┌─────────▼──────┐  ┌─────────▼──────────┐  ┌─────────▼──────────┐
│  Feed Manager  │  │   Map Builder       │  │   LLM Client        │
│  (threading)   │  │   (Folium +         │  │   (Anthropic SDK)   │
│  CSV → speed   │  │    NetworkX A*)     │  │   Incident + Chat   │
│  dict @ 5s     │  │                     │  │   Prompt Builder    │
└─────────┬──────┘  └─────────┬──────────┘  └─────────┬──────────┘
          │                   │                         │
┌─────────▼──────┐  ┌─────────▼──────────┐  ┌─────────▼──────────┐
│  NYC Speed CSV │  │   OSMnx Graph       │  │   Anthropic API    │
│  (local disk)  │  │   (cached .gpickle) │  │   claude-sonnet    │
└────────────────┘  └────────────────────┘  └────────────────────┘
```

### 8.2 Tech Stack

| Layer | Technology | Version | Justification |
|-------|-----------|---------|---------------|
| UI Framework | Streamlit | ≥1.32 | Rapid prototyping, session state, native component support |
| Map Rendering | Folium | ≥0.16 | Leaflet.js wrapper, supports polylines, markers, tooltips |
| Map–Streamlit Bridge | streamlit-folium | ≥0.18 | Click event capture, re-render on state change |
| Road Network | OSMnx | ≥1.9 | OSM graph download, node/edge enrichment |
| Graph Routing | NetworkX | ≥3.2 | A* shortest path on OSM graph |
| Data Processing | pandas | ≥2.1 | CSV ingestion, speed lookup by segment |
| LLM | Anthropic Python SDK | ≥0.25 | claude-sonnet-4-6 with structured prompting |
| Environment Config | python-dotenv | ≥1.0 | `.env` file for API key |
| Logging | Python stdlib logging | — | File + console handlers |
| Background Threading | Python stdlib threading | — | Feed simulation without blocking UI |
| Caching | Streamlit `@st.cache_data` / `@st.cache_resource` | — | OSM graph, CSV load |

### 8.3 Module Structure

```
traffic_copilot/
│
├── app.py                    # Streamlit entry point — layout only, no logic
│
├── config.py                 # All constants: bbox, model, paths, intervals
│
├── modules/
│   ├── __init__.py
│   ├── feed_manager.py       # CSV replay thread, speed state management
│   ├── map_builder.py        # Folium map construction, speed colouring, overlays
│   ├── routing.py            # OSMnx graph loading, A* path computation
│   ├── llm_client.py         # Anthropic API calls, prompt construction, response parsing
│   ├── prompt_builder.py     # Builds structured incident + chat prompts
│   └── state.py              # SessionState schema definitions (TypedDict)
│
├── data/
│   ├── nyc_traffic_speed.csv # NYC DOT speed feed (source: NYC Open Data)
│   └── osm_cache/            # Cached OSMnx graph (.graphml)
│
├── logs/
│   └── app.log               # Runtime logs (gitignored)
│
├── tests/
│   ├── test_feed_manager.py
│   ├── test_routing.py
│   ├── test_llm_client.py
│   └── test_prompt_builder.py
│
├── requirements.txt
├── .env.example
└── README.md
```

### 8.4 Session State Schema

All shared state lives in `st.session_state`. The `state.py` module defines a `TypedDict` for type safety:

```python
class IncidentState(TypedDict):
    declared: bool
    lat: float | None
    lng: float | None
    incident_type: str
    severity: int              # 1–5
    lanes_blocked: int
    notes: str
    declared_at: str           # ISO timestamp

class FeedState(TypedDict):
    current_speeds: dict       # segment_id -> speed_mph
    current_timestamp: str
    tick_count: int
    is_running: bool

class LLMOutputState(TypedDict):
    signal_retiming: list[dict]   # [{intersection, current_phase, recommended_phase, rationale}]
    diversion_routes: list[dict]  # [{name, via_streets, extra_minutes, activate_step}]
    public_alerts: dict           # {vms: str, radio: str, social: str}
    incident_narrative: str
    last_updated: str

class ChatState(TypedDict):
    messages: list[dict]       # [{role, content, timestamp}]
    
class AppState(TypedDict):
    incident: IncidentState
    feed: FeedState
    llm_output: LLMOutputState
    chat: ChatState
    diversion_path: list[tuple] | None   # [(lat, lng), ...]
    map_needs_refresh: bool
```

### 8.5 Threading Model

The feed simulation uses Python `threading.Thread` with a `threading.Event` for graceful shutdown:

```
Main Thread (Streamlit)          Feed Thread
─────────────────────            ────────────────────────────────
st.session_state init  ──────►  start()
                                 loop:
                                   read CSV row
                                   acquire Lock
                                   update session_state.feed
                                   release Lock
                                   sleep(interval)
                                 
Streamlit rerun ◄─── st.rerun() triggered by feed via callback or timer
```

**Critical constraint:** Streamlit's `session_state` is not thread-safe. The feed thread uses a `threading.Lock` when writing speed data. The main thread acquires the same lock when reading for map renders.

---

## 9. Data Architecture

### 9.1 NYC Traffic Speed CSV

**Source:** NYC DOT Real-Time Traffic Speed Data (NYC Open Data)  
**File:** `data/nyc_traffic_speed.csv`

**Required Columns:**

| Column | Type | Description |
|--------|------|-------------|
| `Id` | int | Unique speed record ID |
| `Speed` | float | Current speed in mph |
| `TravelTime` | float | Travel time in seconds |
| `Status` | int | 0 = normal, >0 = incident |
| `DataAsOf` | datetime str | Timestamp of reading |
| `linkId` | int | Road segment identifier |
| `linkName` | str | Human-readable segment name (e.g., "FDR Drive") |
| `EncodedPolyLine` | str | Google-encoded polyline of segment geometry |
| `EncodedPolyLineLvls` | str | Polyline levels |
| `Borough` | str | NYC borough |
| `linkPoints` | str | Raw lat/lng pairs |

**Preprocessing at load time:**
- Parse `DataAsOf` to datetime
- Decode `EncodedPolyLine` to lat/lng coordinate list
- Sort by `DataAsOf` for replay ordering
- Build `linkId → linkName` lookup dict

### 9.2 OSM Graph

**Downloaded via:** OSMnx with `network_type='drive'`  
**Bounding Box (default):** `(40.700, -74.020, 40.780, -73.930)` — Lower/Mid Manhattan  
**Cached as:** `data/osm_cache/nyc_graph.graphml`

Graph nodes carry: `osmid`, `lat`, `lon`, `street_count`  
Graph edges carry: `name`, `length`, `speed_kph`, `travel_time`, `lanes`

**Speed enrichment:** OSMnx's `add_edge_speeds()` and `add_edge_travel_times()` are called after load to ensure A* has travel time weights.

### 9.3 LLM Prompt Data Flow

```
Incident Form  ──►  IncidentContext dict
Feed State     ──►  SpeedSnapshot dict   (top 10 slowest segments)
OSM Graph      ──►  NearbyIntersections  (radius 500m from incident)
Chat History   ──►  MessageHistory list

All above ──► prompt_builder.py ──► Structured JSON prompt ──► Anthropic API
                                                                      │
                                                          Structured JSON response
                                                                      │
                                                          llm_client.parse_response()
                                                                      │
                                                          st.session_state.llm_output
```

---

## 10. API Definitions

### 10.1 LLM Incident Analysis — Prompt Contract

**Function:** `llm_client.analyze_incident(incident: IncidentState, speed_snapshot: dict, nearby_intersections: list) -> LLMOutputState`

**System Prompt:**
```
You are a Traffic Incident Command AI Co-Pilot assisting a traffic control officer.
You have access to live road speed data and the road network graph.
Always respond with specific intersection names, street names, and exact numeric values.
Never give generic advice. Be decisive and precise.
Respond ONLY with a valid JSON object matching the schema provided.
```

**User Prompt Structure (built by `prompt_builder.build_incident_prompt()`):**
```json
{
  "incident": {
    "type": "Major Accident",
    "severity": 4,
    "location": {"lat": 40.748, "lng": -73.985},
    "lanes_blocked": 2,
    "notes": "Overturned truck, debris on road",
    "declared_at": "2024-01-15T14:32:00Z"
  },
  "speed_snapshot": {
    "slowest_segments": [
      {"name": "FDR Drive NB at E 34th St", "speed_mph": 4.2, "normal_mph": 45},
      {"name": "2nd Ave at E 42nd St", "speed_mph": 8.1, "normal_mph": 30}
    ],
    "timestamp": "2024-01-15T14:32:05Z"
  },
  "nearby_intersections": [
    {"name": "3rd Ave & E 34th St", "distance_m": 180},
    {"name": "Lexington Ave & E 36th St", "distance_m": 340}
  ],
  "output_schema": {
    "signal_retiming": [
      {
        "intersection": "string — exact intersection name",
        "current_green_seconds": "integer",
        "recommended_green_seconds": "integer",
        "rationale": "string — one sentence"
      }
    ],
    "diversion_routes": [
      {
        "name": "string — route label",
        "from": "string",
        "to": "string",
        "via_streets": ["string"],
        "extra_travel_minutes": "integer",
        "activate_step": "integer — 1-indexed sequence"
      }
    ],
    "public_alerts": {
      "vms": "string — ≤3 lines, ≤60 chars each, use \\n between lines",
      "radio": "string — ~100 words, broadcast-ready",
      "social": "string — ≤280 chars, include hashtags"
    },
    "incident_narrative": "string — 100-150 words, plain English briefing"
  }
}
```

**Expected Response:** A JSON object with keys: `signal_retiming`, `diversion_routes`, `public_alerts`, `incident_narrative`.

**Fallback Behaviour:** If JSON parsing fails, store raw text in `incident_narrative` and populate other fields with empty defaults. Show a warning banner.

---

### 10.2 LLM Chat Query — Prompt Contract

**Function:** `llm_client.query_incident(query: str, incident: IncidentState, llm_output: LLMOutputState, chat_history: list[dict]) -> str`

**System Prompt:** Same as incident analysis, plus:
```
You are mid-incident. The officer is asking operational questions.
Answer directly. Start with a one-sentence decision, then give supporting detail.
Never say "I think" or "it might be". Use confident, command-appropriate language.
```

**Messages Array:**
```python
[
    {"role": "user", "content": "<full_incident_context_as_json>"},
    {"role": "assistant", "content": "<prior_incident_analysis>"},
    # ...last 10 turns of chat...
    {"role": "user", "content": "<current_officer_query>"}
]
```

**Response:** Plain text string. No JSON required. Streamed if streaming is enabled.

---

### 10.3 Routing API — Internal

**Function:** `routing.compute_diversion(graph: nx.MultiDiGraph, origin_node: int, destination_node: int) -> list[tuple[float, float]]`

**Returns:** Ordered list of `(lat, lng)` tuples forming the A* shortest path.  
**Weight:** `travel_time` edge attribute.  
**Error:** Raises `RoutingError` if no path found.

**Function:** `routing.find_nearest_node(graph, lat, lng) -> int`  
**Returns:** OSM node ID nearest to given coordinates.

---

### 10.4 Feed Manager — Internal

**Function:** `feed_manager.start_feed(df: pd.DataFrame, interval_seconds: float, lock: threading.Lock) -> threading.Thread`  
**Returns:** Running thread. Thread writes to `st.session_state` under lock.

**Function:** `feed_manager.get_current_speeds(lock: threading.Lock) -> dict`  
**Returns:** `{linkId: {"speed": float, "name": str}}` — snapshot safe to read from main thread.

---

## 11. UI/UX Specifications

### 11.1 Layout

The app uses a **3-panel layout**:

```
┌─────────────────────────────────────────────────────────────────┐
│  🚦 Traffic Incident Co-Pilot                    [Status: LIVE] │
├──────────────┬──────────────────────────────┬───────────────────┤
│              │                              │                   │
│   SIDEBAR    │        MAP PANEL             │   INTEL PANEL     │
│   (280px)    │        (fluid)               │   (400px)         │
│              │                              │                   │
│ Feed Status  │  Folium Map                  │ [Tabs]            │
│ Incident     │  - Speed colours             │  Signal | Divert  │
│   Form       │  - Incident pin              │  Alerts | Chat    │
│ Config       │  - Diversion overlay         │                   │
│              │                              │  Chat input bar   │
│              │                              │  at bottom        │
└──────────────┴──────────────────────────────┴───────────────────┘
```

### 11.2 Colour System

| State | Colour | Hex |
|-------|--------|-----|
| Speed: Free flow (≥40 mph) | Green | `#2ECC71` |
| Speed: Slow (20–39 mph) | Amber | `#F39C12` |
| Speed: Congested (<20 mph) | Red | `#E74C3C` |
| Diversion route overlay | Blue | `#3498DB` |
| Incident pin | Dark Red | `#C0392B` |
| UI Primary | Dark Navy | `#1A2B4A` |
| UI Background | Off-white | `#F4F6F9` |

### 11.3 Sidebar Sections

1. **Feed Status Card**
   - Live/Paused indicator (green dot / grey dot)
   - Current data timestamp
   - Tick counter
   - Replay speed slider

2. **Incident Declaration Form** (collapses when not in use)
   - Location fields (lat/lng, auto-filled from map click)
   - Incident type dropdown
   - Severity slider (1–5 with labels: Minor → Critical)
   - Lanes blocked numeric input
   - Notes text area
   - [Declare Incident] button (red, prominent)
   - [Clear Incident] button (grey, smaller)

3. **Configuration** (expander, collapsed by default)
   - LLM Model selector
   - Temperature slider
   - Replay speed selector

### 11.4 Intel Panel Tabs

**Tab 1: 🔴 Signal Re-Timing**
- Table with columns: Intersection | Current Phase | Recommended Phase | Change | Rationale
- Rows sorted by: magnitude of change (largest first)
- Last updated timestamp

**Tab 2: 🔵 Diversion Routes**
- Card per route with: Route name badge, Via streets list, Extra minutes pill, Activate Step badge
- Toggle buttons to show/hide each route on map

**Tab 3: 📢 Public Alerts**
- Three sub-sections with channel label + copy button
- VMS: monospace font, simulates sign display, 3 lines
- Radio: regular text, word count indicator
- Social: text with character counter (0/280)
- [Export Alerts] button at bottom

**Tab 4: 💬 Incident Chat**
- Scrollable chat history (officer messages right-aligned, AI left-aligned)
- Timestamp per message
- Suggested query chips above input (post first AI response)
- Text input + Send button at bottom
- [Clear Chat] small button top-right

### 11.5 Status Banner

Persistent top banner when incident is active:
```
🚨 ACTIVE INCIDENT — Major Accident | Severity 4/5 | 2 Lanes Blocked | 00:14:32 elapsed
```

---

## 12. Engineering Tasks — Phased Breakdown

### Phase 0: Project Setup (Day 1 — ~4 hours)

| Task ID | Task | Owner | Acceptance Criteria |
|---------|------|-------|---------------------|
| P0-T1 | Create repo structure as defined in §8.3 | Eng | All directories and `__init__.py` files present |
| P0-T2 | Write `requirements.txt` with pinned versions | Eng | `pip install -r requirements.txt` succeeds in clean venv |
| P0-T3 | Write `config.py` with all constants | Eng | No other file contains magic strings or hardcoded paths |
| P0-T4 | Write `.env.example` with `ANTHROPIC_API_KEY=` placeholder | Eng | Present in repo, `.env` added to `.gitignore` |
| P0-T5 | Download and place NYC speed CSV in `data/` | Eng | CSV present, columns match §9.1 |
| P0-T6 | Write `README.md` with setup, run, and config instructions | Eng | New developer can run app in <5 min following README |

### Phase 1: Data & Feed Layer (Day 1–2 — ~8 hours)

| Task ID | Task | Owner | Acceptance Criteria |
|---------|------|-------|---------------------|
| P1-T1 | Implement `feed_manager.load_csv()` — load, validate, sort, decode polylines | Eng | Returns clean DataFrame; raises `DataError` if columns missing |
| P1-T2 | Implement `feed_manager.start_feed()` — background thread with lock | Eng | Thread starts, updates `session_state` every N seconds, survives 1000 ticks |
| P1-T3 | Implement `feed_manager.get_current_speeds()` — thread-safe read | Eng | Returns speed dict without deadlock under concurrent access |
| P1-T4 | Implement `routing.load_graph()` — OSMnx download + cache | Eng | First run downloads and caches; subsequent runs load from file in <3s |
| P1-T5 | Implement `routing.find_nearest_node()` | Eng | Returns correct OSM node for known NYC lat/lng within 50m |
| P1-T6 | Implement `routing.compute_diversion()` with A* | Eng | Returns valid lat/lng path for two connected NYC nodes |
| P1-T7 | Write unit tests for P1 tasks | Eng | All tests pass; feed and routing tested in isolation with mock data |

### Phase 2: Map Layer (Day 2–3 — ~8 hours)

| Task ID | Task | Owner | Acceptance Criteria |
|---------|------|-------|---------------------|
| P2-T1 | Implement `map_builder.build_base_map()` — Folium map centred on bbox | Eng | Renders in Streamlit; shows correct NYC area |
| P2-T2 | Implement `map_builder.add_speed_segments()` — colour-coded polylines from CSV data | Eng | Green/amber/red segments visible per speed thresholds |
| P2-T3 | Implement `map_builder.add_incident_pin()` — red marker at incident location | Eng | Marker appears at clicked lat/lng |
| P2-T4 | Implement `map_builder.add_diversion_overlay()` — blue polyline from path list | Eng | Blue line follows OSM edges from routing output |
| P2-T5 | Implement segment tooltip (name, speed, normal speed) | Eng | Tooltip visible on hover for all coloured segments |
| P2-T6 | Wire map click → sidebar lat/lng auto-fill using `st_folium` return value | Eng | Clicking map updates sidebar location fields |
| P2-T7 | Ensure map re-renders on each feed tick without full page reload | Eng | Map updates every 5s; sidebar state persists across re-renders |

### Phase 3: LLM Layer (Day 3–4 — ~10 hours)

| Task ID | Task | Owner | Acceptance Criteria |
|---------|------|-------|---------------------|
| P3-T1 | Implement `prompt_builder.build_incident_prompt()` — assembles full JSON prompt | Eng | Output matches §10.1 schema exactly |
| P3-T2 | Implement `prompt_builder.build_chat_prompt()` — assembles message history with context | Eng | Includes last 10 turns; system prompt prepended |
| P3-T3 | Implement `llm_client.analyze_incident()` — API call, JSON parse, fallback | Eng | Returns `LLMOutputState`; fallback on parse failure; retries 3x |
| P3-T4 | Implement `llm_client.query_incident()` — multi-turn chat call | Eng | Returns string; carries chat history; 5s timeout |
| P3-T5 | Implement response streaming for chat (optional P1) | Eng | Characters stream into UI; no full reload |
| P3-T6 | Implement retry logic with exponential backoff on API errors | Eng | 3 retries on 429/500; user notified after all fail |
| P3-T7 | Implement LLM call logging (tokens, latency) | Eng | `logs/app.log` shows token counts and ms per call |
| P3-T8 | Write unit tests with mocked Anthropic responses | Eng | Tests do not hit real API; all edge cases covered |

### Phase 4: Streamlit UI Assembly (Day 4–5 — ~10 hours)

| Task ID | Task | Owner | Acceptance Criteria |
|---------|------|-------|---------------------|
| P4-T1 | Implement `app.py` layout — 3 panel structure with st.columns | Eng | Layout renders with correct proportions |
| P4-T2 | Implement sidebar feed status card | Eng | Shows live tick count and timestamp |
| P4-T3 | Implement sidebar incident declaration form | Eng | All fields present; validates before declaring |
| P4-T4 | Implement incident active status banner | Eng | Banner shows when incident declared; hides when cleared |
| P4-T5 | Implement Intel Panel — Signal Re-timing tab | Eng | Table renders from LLM output; sorted by change magnitude |
| P4-T6 | Implement Intel Panel — Diversion Routes tab | Eng | Cards render with toggle buttons wiring to map overlays |
| P4-T7 | Implement Intel Panel — Public Alerts tab with copy and export | Eng | Copy button copies to clipboard; export downloads .txt |
| P4-T8 | Implement Intel Panel — Chat tab with history and input | Eng | Chat history scrollable; timestamps shown; input sends on Enter |
| P4-T9 | Implement suggested query chips below chat response | Eng | 3 clickable chips auto-fill the input |
| P4-T10 | Implement "Declare Incident" button trigger → LLM call → populate tabs | Eng | Full flow completes in ≤10s; spinner shown during call |
| P4-T11 | Implement "Clear Incident" — reset all state | Eng | All outputs cleared; map reverts to base state |

### Phase 5: Integration & Polish (Day 5–6 — ~8 hours)

| Task ID | Task | Owner | Acceptance Criteria |
|---------|------|-------|---------------------|
| P5-T1 | Full end-to-end test: feed → incident declare → LLM → map overlay → chat | Eng | All FR-01 through FR-08 satisfied in one session |
| P5-T2 | Performance test: measure tick-to-render and LLM latency | Eng | Meets all NFR targets in §7.1 |
| P5-T3 | Error handling review: kill feed thread, force LLM error, bad OSM path | Eng | All errors surface as UI cards; no crashes |
| P5-T4 | Apply colour system and typography from §11.2 | Eng | UI matches colour spec; no default Streamlit blue |
| P5-T5 | Verify chat context window never exceeds 8,000 tokens | Eng | Token counter in logs confirms limit enforced |
| P5-T6 | Code review: type annotations, docstrings, no magic strings | Eng | All modules pass review checklist |
| P5-T7 | Final README with screenshots and demo script | Eng | README ready for stakeholder demo |

---

## 13. Testing Strategy

### 13.1 Unit Tests

All modules in `modules/` must have corresponding test files in `tests/`. Use `pytest`.

**Mock requirements:**
- Anthropic SDK: mock with `unittest.mock.patch` to avoid real API calls
- OSMnx: use pre-saved test graph (`tests/fixtures/test_graph.graphml`)
- Feed CSV: use `tests/fixtures/sample_speeds.csv` (50 rows)

**Coverage target:** ≥80% line coverage on all `modules/` files

### 13.2 Integration Tests

| Test | Description |
|------|-------------|
| `test_integration_feed_to_map.py` | Feed tick updates speed state → map build uses updated speeds |
| `test_integration_incident_to_llm.py` | Incident declaration → prompt builder → mock LLM → parsed output |
| `test_integration_routing_to_map.py` | Routing computes path → map builder renders overlay |

### 13.3 Manual Demo Test Script

Before any stakeholder demo, run through:

1. `streamlit run app.py` — confirm startup in <15s
2. Observe map loads with colour segments — confirm green/amber/red visible
3. Click a red (congested) segment on the map — confirm lat/lng fills in sidebar
4. Set Incident Type: Major Accident, Severity: 4, Lanes Blocked: 2
5. Click "Declare Incident" — confirm spinner appears, results populate in ≤10s
6. Navigate each tab — confirm all four output types present and non-empty
7. Type in chat: "Is it safe to open the southbound lane now?" — confirm relevant, decisive response
8. Toggle diversion route — confirm blue line appears on map
9. Click "Export Alerts" — confirm file downloads with all three variants
10. Click "Clear Incident" — confirm map and panels reset cleanly

---

## 14. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R1 | Anthropic API rate limit hit during demo | Medium | High | Pre-cache one full incident response in `tests/fixtures/`; add `--demo-mode` flag that uses cached response |
| R2 | OSM download fails or times out | Medium | High | Always cache graph; bundle a pre-downloaded graph in repo |
| R3 | LLM returns malformed JSON | Medium | Medium | Robust fallback: display raw text in narrative tab; do not crash |
| R4 | Feed thread deadlocks with main thread | Low | High | Timeout on lock acquire (500ms); thread watchdog restarts on timeout |
| R5 | NYC CSV segment IDs don't match OSM node IDs | High | Medium | Use coordinate-based nearest-node matching; do not rely on ID overlap |
| R6 | Map re-render causes full Streamlit page reload, losing state | Medium | High | Use `st.cache_resource` for graph; session_state for all mutable data |
| R7 | Chat history grows too large for context window | Medium | Medium | Enforce 10-turn rolling window in `prompt_builder.build_chat_prompt()` |

---

## 15. Glossary

| Term | Definition |
|------|------------|
| TMC | Traffic Management Centre — city facility where officers monitor and manage road conditions |
| VMS | Variable Message Sign — electronic roadside signs displaying traffic alerts |
| A* | A-star algorithm — heuristic graph search used for shortest-path routing |
| OSM | OpenStreetMap — open road network data used by OSMnx |
| Signal Re-timing | Changing the green/red phase durations at traffic signals to manage flow |
| Diversion Route | An alternative path activated to redirect traffic around an incident |
| LLM | Large Language Model — the AI system (Claude) providing natural language reasoning |
| Session State | Streamlit's in-memory key-value store shared across UI interactions within a session |
| Feed Tick | One cycle of the feed simulation; one CSV row consumed and speed state updated |
| Incident Narrative | AI-generated plain-English situational summary of the current incident |
| Phase Duration | The number of seconds a traffic signal remains green for a given direction |
| Free-flow Speed | The expected speed on a road segment under normal (no congestion) conditions |

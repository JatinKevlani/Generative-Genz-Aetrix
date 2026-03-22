# 🚦 Generative-Genz-Aetrix — AI-Powered Traffic Management System

An end-to-end intelligent traffic management platform that combines **computer vision** for real-time vehicle speed detection and number plate recognition, an **LLM-powered co-pilot** for traffic incident command, and a **full-stack web dashboard** for traffic monitoring and incident analysis.

> Built for Ahmedabad and NYC road networks with real-time traffic simulation, AI-driven incident intelligence, and voice-assisted command capabilities.

---

## 📑 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Project Structure](#-project-structure)
- [Module Deep Dive](#-module-deep-dive)
  - [1. Vehicle Detection & Speed Monitoring (`application/`)](#1-vehicle-detection--speed-monitoring-application)
  - [2. Traffic Copilot Backend API (`backend/`)](#2-traffic-copilot-backend-api-backend)
  - [3. Web Dashboard Frontend (`frontend/`)](#3-web-dashboard-frontend-frontend)
  - [4. Streamlit Traffic Co-Pilot (`traffic_copilot/`)](#4-streamlit-traffic-co-pilot-traffic_copilot)
  - [5. Voice Co-Pilot — InterviewGPT (`InterviewGPT/`)](#5-voice-co-pilot--interviewgpt-interviewgpt)
  - [6. Pre-trained Models (`model/`)](#6-pre-trained-models-model)
- [Tech Stack & Libraries](#-tech-stack--libraries)
- [Prerequisites](#-prerequisites)
- [Installation & Setup](#-installation--setup)
- [API Endpoints](#-api-endpoints)
- [How It Works — End to End](#-how-it-works--end-to-end)
- [Environment Variables](#-environment-variables)
- [Future Enhancements](#-future-enhancements)

---

## 🧭 Overview

This project solves a real-world problem: **when a major traffic incident occurs, traffic control officers must simultaneously manage radio calls, sensor feeds, camera streams, and city maps — all under extreme time pressure.** This platform reduces cognitive overload by providing:

| Capability | Description |
|:---|:---|
| **Vehicle Speed Detection** | Real-time speed measurement using YOLOv8 + OpenCV on video feeds |
| **Number Plate Recognition** | Automated licence plate extraction using Haar Cascades + EasyOCR |
| **AI Incident Analysis** | LLM-powered signal re-timing, diversion routing, and public alert generation |
| **Interactive Dashboard** | Live traffic map with incident reporting and AI chat interface |
| **Voice Co-Pilot** | Hands-free voice interaction for officers using LiveKit + Deepgram + Murf AI |

---

## 🏗 System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         USER / TRAFFIC OFFICER                          │
└────────┬──────────────────────┬──────────────────────┬──────────────────┘
         │                      │                      │
    Web Dashboard          Streamlit App          Voice Co-Pilot
   (Next.js + Leaflet)    (traffic_copilot/)    (InterviewGPT/)
         │                      │                      │
         └──────────┬───────────┘                      │
                    │                                  │
         ┌──────────▼──────────┐            ┌──────────▼──────────┐
         │   FastAPI Backend   │            │  LiveKit + Gemini   │
         │    (backend/)       │            │   Voice Pipeline    │
         │  • Claude LLM      │            │  • Deepgram STT     │
         │  • OSMnx Routing   │            │  • Murf TTS         │
         │  • Traffic Sim     │            │  • Google Gemini    │
         └──────────┬──────────┘            └─────────────────────┘
                    │
         ┌──────────▼──────────┐
         │  CV Application     │
         │  (application/)     │
         │  • YOLOv8 Detection │
         │  • Speed Tracking   │
         │  • Plate OCR        │
         └─────────────────────┘
```

---

## 📂 Project Structure

```
Generative-Genz-Aetrix/
│
├── application/                    # Computer vision — vehicle speed & plate detection
│   ├── speed.py                    # Main speed detection pipeline (YOLO + tracking)
│   ├── numplatedetection.py        # Number plate detection & OCR (Haar + EasyOCR)
│   ├── tracker.py                  # Centroid-based multi-object tracker
│   └── requirements.txt           # Dependencies (tkinter, pyrebase4)
│
├── backend/                        # FastAPI backend for traffic incident copilot
│   ├── main.py                     # FastAPI app — endpoints, simulation, Pydantic models
│   ├── llm.py                      # LLM client (Claude via LangChain + LangGraph agent)
│   ├── generate_ahmedabad_speed.py # Synthetic traffic data generator (200 roads × 30 days)
│   ├── test_llm.py                 # LLM integration tests
│   ├── ahmedabad_traffic_mock.csv  # Mock sensor data for simulation
│   └── nyc_traffic_mock.csv        # NYC mock sensor data
│
├── frontend/                       # Next.js web dashboard
│   ├── src/
│   │   ├── app/                    # Next.js App Router (layout, page, globals)
│   │   ├── components/
│   │   │   ├── Dashboard.tsx       # Main dashboard layout & incident form
│   │   │   ├── MapComponent.tsx    # Leaflet map with incident markers
│   │   │   ├── ChatComponent.tsx   # AI chat interface with voice input
│   │   │   ├── SignalRetimingPanel.tsx    # Signal phase change recommendations
│   │   │   ├── DiversionRoutesPanel.tsx  # Diversion route display
│   │   │   └── PublicAlertsPanel.tsx     # VMS, radio, social alert drafts
│   │   └── types.ts               # TypeScript interfaces for API responses
│   ├── package.json                # Node dependencies
│   ├── tailwind.config.ts          # Tailwind CSS configuration
│   └── tsconfig.json               # TypeScript configuration
│
├── traffic_copilot/                # Streamlit-based standalone traffic co-pilot app
│   ├── app.py                      # Streamlit entry point — 3-column layout
│   ├── config.py                   # All configuration constants
│   ├── requirements.txt            # Python dependencies
│   ├── .env.example                # Environment variable template
│   └── modules/
│       ├── state.py                # TypedDict state definitions
│       ├── llm_client.py           # Anthropic SDK client with retry logic
│       ├── prompt_builder.py       # Structured LLM prompt templates
│       ├── feed_manager.py         # Background thread CSV feed simulator
│       ├── routing.py              # OSMnx graph loading + A* routing
│       └── map_builder.py          # Folium map builder with speed segments
│
├── InterviewGPT/                   # Voice co-pilot sub-project (LiveKit)
│   ├── backend/
│   │   ├── src/agent.py            # LiveKit voice agent with traffic instructions
│   │   └── pyproject.toml          # Python dependencies (LiveKit, Gemini, Deepgram, Murf)
│   ├── frontend/                   # Next.js frontend for voice interaction
│   │   ├── app/                    # App Router pages
│   │   ├── components/             # LiveKit UI components
│   │   └── package.json            # Node dependencies
│   └── README.md                   # Detailed setup guide
│
├── model/                          # Pre-trained model files
│   ├── yolov8s.pt                  # YOLOv8 small model weights (22.5 MB)
│   ├── haarcascade_russian_plate_number.xml  # Haar cascade for plate detection
│   └── coco.txt                    # COCO dataset class labels (80 classes)
│
├── Design.md                       # UI/UX design specification
├── PRD.md                          # Product Requirements Document
└── README.md                       # This file
```

---

## 🔬 Module Deep Dive

### 1. Vehicle Detection & Speed Monitoring (`application/`)

This module performs **real-time vehicle speed estimation** and **number plate recognition** from video feeds.

#### `speed.py` — Vehicle Speed Detection Pipeline

The core speed detection system uses a **dual-line crossing method:**

1. **Object Detection** — YOLOv8s model detects vehicles in each frame, filtering for `car` class objects
2. **Object Tracking** — Custom centroid tracker (`tracker.py`) assigns persistent IDs to detected vehicles across frames
3. **Speed Calculation** — Two horizontal reference lines (L1 at `y=322`, L2 at `y=368`) measure the time a vehicle takes to travel between them:
   ```
   speed (m/s) = DISTANCE / elapsed_time
   speed (km/h) = speed (m/s) × 3.6
   ```
4. **Speed Violation Capture** — If `speed > SPEED_LIMIT`, the vehicle's bounding box is cropped and saved for number plate detection
5. **Bidirectional Counting** — Tracks vehicles going both up and down through the frame

**Key functions:**
- `setparams(distance, roadname, speed)` — Configure detection parameters
- `main()` — Run the full detection loop

#### `tracker.py` — Centroid-Based Object Tracker

A lightweight tracker that maintains object identity across frames:

- Stores center points of tracked objects in a dictionary
- Uses **Euclidean distance** (`math.hypot`) to match new detections with existing objects
- Threshold: objects within **35 pixels** are considered the same
- Automatically assigns new IDs to unmatched detections
- Cleans up stale tracking entries every frame

#### `numplatedetection.py` — Number Plate Detection & OCR

Two-stage number plate extraction:

1. **Detection** — Uses OpenCV Haar Cascade classifier (`haarcascade_russian_plate_number.xml`) to locate plate regions
2. **Pre-processing** — Applies Gaussian blur and Canny edge detection for cleaner recognition
3. **OCR** — EasyOCR reads text from the cropped plate image with a detection threshold of 0.7

**Libraries used:** `opencv-python`, `easyocr`, `numpy`, `matplotlib`

---

### 2. Traffic Copilot Backend API (`backend/`)

A **FastAPI** server that provides the REST API for the traffic dashboard, integrating with **Claude (Anthropic)** for intelligent incident analysis.

#### `main.py` — FastAPI Application

**Core Features:**
- **Traffic Simulation Engine** — Background thread replays CSV sensor data, stepping through rows every 5 seconds
- **OSMnx Road Network** — Downloads the Ahmedabad road graph on startup for real routing calculations
- **Incident Management** — Stores reported incidents in-memory and triggers LLM analysis

**Pydantic Models:**
| Model | Purpose |
|:---|:---|
| `IncidentReport` | Incoming incident data (lat, lng, type, severity, notes) |
| `IncidentAnalysisRequest` | Extended request with `lanes_blocked` field |
| `IncidentAnalysisResponse` | Full AI response (signal, diversion, alerts, narrative, route) |
| `SignalRetimingItem` | Intersection + green phase recommendation |
| `DiversionRouteItem` | Named route with via-streets and activation order |
| `PublicAlerts` | VMS, radio, and social media alert drafts |

**Mock Sensors** — 8 simulated sensors across Ahmedabad intersections (SG Highway, Ashram Road, CG Road, Relief Road, etc.)

#### `llm.py` — LLM Client Module

The intelligence engine of the platform:

- **Model:** Claude Sonnet via `langchain-anthropic`
- **Structured Prompts:** Uses `ChatPromptTemplate` for both incident analysis (JSON output) and conversational chat
- **ReAct Agent:** Chat uses `langgraph.prebuilt.create_react_agent` with a `query_historical_traffic` tool that queries the generated Ahmedabad traffic CSV using **DuckDB**
- **Mock Fallbacks:** Provides realistic mock responses when no API key is configured — scales signal retiming by severity multiplier
- **Deepgram Integration:** Speech-to-text endpoint for voice input

#### `generate_ahmedabad_speed.py` — Traffic Data Generator

Generates a synthetic **1.7 million row** traffic speed dataset:

- **200 road links** across 6 zones (West, East, Central, North, South, Expressway)
- **8,640 five-minute intervals** over 30 simulated days
- Realistic speed variation by time-of-day and day-of-week:
  - Weekday peaks: 8–10 AM (40–65% of base speed), 5–8 PM (35–60%)
  - Weekend patterns: slower midday and evening periods
  - Late night: near free-flow (90–105% of base speed)
- Columns mirror the NYC traffic speed CSV format for compatibility

---

### 3. Web Dashboard Frontend (`frontend/`)

A **Next.js 16** application providing the interactive web interface.

#### Component Architecture

| Component | File | Description |
|:---|:---|:---|
| **Dashboard** | `Dashboard.tsx` | Main layout — incident form, map, and intelligence tabs |
| **Map** | `MapComponent.tsx` | Leaflet.js interactive map with incident markers and diversion routes |
| **Chat** | `ChatComponent.tsx` | AI chat interface with voice input (Deepgram STT) |
| **Signal Panel** | `SignalRetimingPanel.tsx` | Signal re-timing recommendations with green phase metrics |
| **Diversion Panel** | `DiversionRoutesPanel.tsx` | Diversion routes with step-by-step activation |
| **Alerts Panel** | `PublicAlertsPanel.tsx` | VMS, radio broadcast, and social media draft alerts |

#### TypeScript Interfaces (`types.ts`)

Strongly-typed API response models:
- `SignalRetiming` — Intersection name, current/recommended green seconds, rationale
- `DiversionRouteItem` — Route name, from/to locations, via streets, extra travel time
- `PublicAlerts` — VMS, radio, social media text
- `IncidentAnalysisResponse` — Combined response with route coordinates
- `Incident` — Incident declaration data

#### Key Dependencies

| Library | Version | Purpose |
|:---|:---|:---|
| `next` | ^16.2.1 | React framework with App Router |
| `react` / `react-dom` | ^19.2.4 | UI rendering |
| `leaflet` / `react-leaflet` | ^1.9.4 / ^5.0.0 | Interactive maps |
| `lucide-react` | ^0.577.0 | Icon library |
| `tailwindcss` | ^4.2.2 | Utility-first CSS |
| `typescript` | ^5.9.3 | Type safety |

---

### 4. Streamlit Traffic Co-Pilot (`traffic_copilot/`)

A **standalone Streamlit application** that provides a complete traffic incident management dashboard.

#### `app.py` — Main Application (517 lines)

**3-Column Layout:**

1. **Sidebar Column** — Feed status, incident declaration form (type, severity, lanes blocked, coordinates), configuration panel
2. **Map Column** — OpenStreetMap embed with geolocation, speed-colored legend (🟢 Free flow ≥40 mph, 🟡 Slow 20–39 mph, 🔴 Congested <20 mph)
3. **Intelligence Column** — 4 tabs: Signal Re-timing, Diversion Routes, Public Alerts, Incident Chat

**Key Features:**
- **Auto-refresh** — 5-second polling for live feed updates via `streamlit-autorefresh`
- **Active Incident Banner** — Displays elapsed time and incident details
- **Lazy Loading** — OSM graph loaded only on first incident declaration
- **Export** — Download alert drafts as `.txt` files

#### Modules

| Module | Lines | Purpose |
|:---|:---|:---|
| `state.py` | 103 | TypedDict state definitions (IncidentState, FeedState, LLMOutputState, ChatState) |
| `llm_client.py` | 152 | Anthropic SDK wrapper with exponential backoff retry (up to 3 retries) |
| `prompt_builder.py` | ~200 | Structured incident analysis and chat prompt templates |
| `feed_manager.py` | 192 | Background thread CSV replay engine with thread-safe speed state |
| `routing.py` | 150 | OSMnx graph loading, A* shortest path, nearby intersection finder (Haversine) |
| `map_builder.py` | ~150 | Folium map with speed-colored segments and diversion overlays |

#### Configuration (`config.py`)

| Category | Key Settings |
|:---|:---|
| **Geographic** | OSM bounding box (Lower/Mid Manhattan), graph cache path |
| **LLM** | Claude Sonnet model, 2048 max tokens, 0.2 temperature, 3 retries |
| **Feed** | 5-second interval, replay speeds (1×, 2×, 5×) |
| **Speed Thresholds** | Free flow ≥40 mph, Slow ≥20 mph, Congested <20 mph |
| **Map** | CartoDB positron tiles, zoom 13, color-coded speed segments |

---

### 5. Voice Co-Pilot — InterviewGPT (`InterviewGPT/`)

A **voice-based** traffic co-pilot that allows officers to interact hands-free.

#### Backend (`InterviewGPT/backend/`)

- **Framework:** LiveKit Agents SDK
- **LLM:** Google Gemini
- **Speech-to-Text:** Deepgram (Nova-2 model)
- **Text-to-Speech:** Murf AI
- **Pipeline:** WebSocket-based real-time voice pipeline

#### Frontend (`InterviewGPT/frontend/`)

- **Framework:** Next.js with App Router + Turbopack
- **UI Components:** LiveKit Components React, Radix UI, Phosphor Icons
- **Animations:** Motion library
- **Styling:** Tailwind CSS v4

---

### 6. Pre-trained Models (`model/`)

| File | Size | Description |
|:---|:---|:---|
| `yolov8s.pt` | 22.5 MB | YOLOv8 Small — pre-trained object detection model for vehicle detection |
| `haarcascade_russian_plate_number.xml` | 78 KB | OpenCV Haar Cascade classifier for number plate region detection |
| `coco.txt` | 699 B | COCO dataset class labels (80 classes including car, truck, bus, motorcycle) |

---

## 🛠 Tech Stack & Libraries

### Computer Vision & ML

| Library | Purpose |
|:---|:---|
| **OpenCV** (`cv2`) | Video capture, frame processing, drawing, image manipulation |
| **Ultralytics YOLOv8** | Real-time object detection on video frames |
| **EasyOCR** | Optical character recognition for number plates |
| **NumPy** | Array operations for image processing |
| **pandas** | DataFrame for detection results |

### Backend & API

| Library | Purpose |
|:---|:---|
| **FastAPI** | High-performance REST API framework |
| **Uvicorn** | ASGI server for FastAPI |
| **Pydantic** | Data validation and serialization |
| **LangChain** (`langchain-core`, `langchain-anthropic`) | LLM prompt templates and model integration |
| **LangGraph** | ReAct agent for tool-augmented chat |
| **DuckDB** | In-process SQL for querying traffic CSV data |
| **OSMnx** | Download and analyze OpenStreetMap road networks |
| **NetworkX** | Graph algorithms (shortest path, A* routing) |
| **httpx** | Async HTTP client for Deepgram API |
| **python-dotenv** | Environment variable management |

### Frontend

| Library | Purpose |
|:---|:---|
| **Next.js 16** | React framework with App Router |
| **React 19** | UI component library |
| **TypeScript** | Static type checking |
| **Leaflet / react-leaflet** | Interactive map rendering |
| **Tailwind CSS 4** | Utility-first CSS framework |
| **Lucide React** | Icon library |

### Streamlit Dashboard

| Library | Purpose |
|:---|:---|
| **Streamlit** | Python web app framework for dashboards |
| **Folium / streamlit-folium** | Interactive maps with speed-colored road segments |
| **Anthropic SDK** | Direct Anthropic API client |
| **polyline** | Google Encoded Polyline decoding |
| **streamlit-autorefresh** | Auto-polling for live feed updates |

### Voice Co-Pilot

| Library | Purpose |
|:---|:---|
| **LiveKit Agents** | Real-time voice pipeline framework |
| **Google Gemini** | LLM for conversational AI |
| **Deepgram** | Speech-to-text transcription |
| **Murf AI** | High-quality text-to-speech |
| **LiveKit Client SDK** | Frontend WebRTC integration |

---

## ✅ Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **npm / pnpm**
- **Git**

### API Keys Required

| Service | Used By | Purpose |
|:---|:---|:---|
| Anthropic (Claude) | `backend/`, `traffic_copilot/` | AI incident analysis and chat |
| Deepgram | `backend/`, `InterviewGPT/` | Speech-to-text transcription |
| Google Gemini | `InterviewGPT/` | Voice co-pilot LLM |
| Murf AI | `InterviewGPT/` | Text-to-speech |
| LiveKit Cloud | `InterviewGPT/` | Real-time voice pipeline |

---

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/JatinKevlani/Generative-Genz-Aetrix.git
cd Generative-Genz-Aetrix
```

### 2. Vehicle Detection Application

```bash
cd application
pip install opencv-python ultralytics easyocr numpy pandas
python speed.py
```

> Ensure a video file exists at `model/cars.mp4`, or update the `VIDEO` path in `speed.py` to use a webcam or IP camera stream.

### 3. Backend API Server

```bash
cd backend
pip install fastapi uvicorn pydantic pandas networkx osmnx httpx python-dotenv langchain-core langchain-anthropic langgraph duckdb
```

Create a `.env` file:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key
```

Generate the Ahmedabad traffic dataset (optional, for historical queries):

```bash
python generate_ahmedabad_speed.py
```

Start the server:

```bash
python main.py
# → API available at http://localhost:8000
```

### 4. Frontend Dashboard

```bash
cd frontend
npm install
npm run dev
# → Dashboard available at http://localhost:3000
```

### 5. Streamlit Traffic Co-Pilot

```bash
cd traffic_copilot
pip install -r requirements.txt
```

Create a `.env` file:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key
```

```bash
streamlit run app.py
# → Dashboard available at http://localhost:8501
```

### 6. Voice Co-Pilot (InterviewGPT)

See the detailed setup guide in [`InterviewGPT/README.md`](InterviewGPT/README.md).

```bash
# Backend
cd InterviewGPT/backend
pip install uv && uv sync
uv run python src/agent.py dev

# Frontend
cd InterviewGPT/frontend
pnpm install && pnpm dev
# → Available at http://localhost:3000
```

---

## 📡 API Endpoints

### Backend API (`http://localhost:8000`)

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/api/live` | Get live traffic feed (sensors, incidents, diversion route) |
| `POST` | `/api/report-incident` | Report a new traffic incident |
| `POST` | `/api/analyze-incident` | Full AI analysis — signal retiming, diversions, alerts, narrative |
| `POST` | `/api/chat` | Free-text query with traffic context (ReAct agent with tools) |
| `POST` | `/api/speech-to-text` | Audio file transcription via Deepgram |

### Example — Analyze Incident

```bash
curl -X POST http://localhost:8000/api/analyze-incident \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 23.0300,
    "lng": 72.5070,
    "incident_type": "Major Accident",
    "severity": 4,
    "lanes_blocked": 2,
    "notes": "Multi-vehicle collision on SG Highway"
  }'
```

**Response** includes:
- **Signal Re-timing:** 3–5 intersection recommendations with exact green phase changes
- **Diversion Routes:** 1–2 alternate routes with activation sequence
- **Public Alerts:** Ready-to-publish VMS, radio, and social media drafts
- **Incident Narrative:** 100–150 word briefing summary
- **Route Coordinates:** GPS coordinates for map overlay

---

## ⚡ How It Works — End to End

### 1. Vehicle Speed Detection Flow

```
Video Feed → YOLOv8 Detection → Centroid Tracking → Line Crossing Timer
→ Speed Calculation → Violation Check → Crop Vehicle → Haar Cascade
→ Number Plate Region → EasyOCR → Plate Text Output
```

### 2. Incident Analysis Flow

```
Officer declares incident (via Dashboard / Streamlit / Voice)
                    ↓
Backend receives incident data (lat, lng, type, severity, lanes)
                    ↓
OSMnx loads Ahmedabad road graph (cached after first load)
                    ↓
LLM (Claude) receives: incident details + sensor readings + nearby intersections
                    ↓
AI generates structured JSON:
  ├── Signal re-timing (intersection → green phase changes)
  ├── Diversion routes (named routes with via-streets)
  ├── Public alerts (VMS, radio, social media)
  └── Incident narrative (briefing summary)
                    ↓
NetworkX computes A* shortest path for diversion overlay
                    ↓
Results displayed on Dashboard / Streamlit map
```

### 3. Chat Query Flow (ReAct Agent)

```
Officer asks question → FastAPI /api/chat endpoint
                    ↓
LangGraph ReAct agent receives query + traffic context
                    ↓
Agent decides whether to use tools:
  └── query_historical_traffic → DuckDB SQL on 1.7M row CSV
                    ↓
Agent generates actionable response with Ahmedabad-specific intelligence
```

---

## 🔐 Environment Variables

### Backend (`backend/.env`)

```env
ANTHROPIC_API_KEY=sk-ant-...          # Claude API access
DEEPGRAM_API_KEY=...                  # Speech-to-text
```

### Traffic Copilot (`traffic_copilot/.env`)

```env
ANTHROPIC_API_KEY=sk-ant-...          # Claude API access
```

### InterviewGPT Backend (`InterviewGPT/backend/.env`)

```env
LIVEKIT_URL=ws://127.0.0.1:7880
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
GOOGLE_API_KEY=...                    # Gemini LLM
DEEPGRAM_API_KEY=...                  # Speech-to-text
MURF_API_KEY=...                      # Text-to-speech
```

### InterviewGPT Frontend (`InterviewGPT/frontend/.env.local`)

```env
NEXT_PUBLIC_LIVEKIT_URL=wss://...
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

---

## 🔮 Future Enhancements

- 🎥 Integration with **live CCTV camera feeds** for real-time speed detection at scale
- 🗺️ **Folium-based** map with speed-colored road segments on the FastAPI dashboard
- 📊 Historical incident analysis and **pattern recognition** across time periods
- 🚔 Multi-agency coordination support (police, fire, EMS)
- 📱 Mobile-responsive incident reporting interface
- 🤖 Automated post-incident report generation
- 🔄 Real-time sensor data integration (replacing CSV simulation)

---

## 👥 Contributors

Built by **Team Generative GenZ** for the Aetrix hackathon.

---

## 📄 License

This project is provided for educational and hackathon purposes.

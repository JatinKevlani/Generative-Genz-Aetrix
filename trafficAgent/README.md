# 🚦 Traffic Incident Co-Pilot — LLM-Powered Command Assistant

An AI-powered voice co-pilot that assists traffic control officers during major incidents by providing real-time, actionable intelligence through natural language.

Built with **Python + LiveKit (backend)** and **Next.js (frontend)**.

---

## 🧠 What It Does

When a major traffic incident happens, officers must simultaneously manage radio calls, sensor feeds, camera streams, and city maps — all under extreme time pressure. This co-pilot reduces cognitive overload by generating four types of real-time intelligence:

| Intelligence Type | What It Provides |
| :--- | :--- |
| **Signal Re-timing** | Names specific intersections and recommends exact phase duration changes |
| **Diversion Routes** | 2–3 alternative routes with activation sequence and traffic redistribution |
| **Public Alerts** | Ready-to-publish drafts for VMS, radio broadcasts, and social media |
| **Priority Matrix** | Incident severity classification and resource dispatch order |

---

## 🎯 Who Uses It

- Traffic control officers managing major incidents
- City traffic management centers
- Public information officers publishing road alerts

---

## 🧱 Tech Stack

### Backend

- Python
- LiveKit Agents
- Google Gemini (LLM)
- Deepgram (Speech-to-Text)
- Murf (Text-to-Speech)
- WebSockets

### Frontend

- Next.js (App Router)
- React
- Tailwind CSS
- LiveKit Client SDK
- TypeScript

### Future Extensions (from Problem Statement)

| Technology | Purpose |
| :--- | :--- |
| Streamlit | Dashboard rendering with map, sidebar, and chat panel |
| Folium + streamlit-folium | Speed-colored road segments and diversion overlays |
| OSMnx + NetworkX | Real street graph download and A* routing |
| pandas + threading | Live feed simulation (replay traffic speed data) |

---

## 📂 Project Structure

```
TrafficCoPilot/
├── backend/
│   ├── pyproject.toml
│   ├── src/
│   │   ├── agent.py          # Traffic Co-Pilot agent (LLM instructions + voice pipeline)
│   │   └── __init__.py
│   └── uv.lock
├── frontend/
│   ├── app/
│   │   ├── (app)/
│   │   │   ├── layout.tsx     # App header and branding
│   │   │   └── page.tsx
│   │   ├── api/
│   │   │   └── connection-details/
│   │   │       └── route.ts
│   │   └── layout.tsx
│   ├── app-config.ts          # App configuration (title, accent, features)
│   ├── components/
│   │   ├── app/
│   │   │   ├── welcome-view.tsx       # Welcome screen with traffic icon
│   │   │   ├── preconnect-message.tsx  # "Co-Pilot standing by" message
│   │   │   ├── session-view.tsx
│   │   │   └── ...
│   │   └── livekit/
│   ├── package.json
│   └── ...
└── README.md
```

---

## ⚙️ Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **Git**
- **pip & npm/pnpm**
- A **LiveKit Cloud account**
- API keys for:
  - Google Gemini
  - Deepgram
  - Murf AI

---

## 🧩 Setup Guide

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/JatinKevlani/InterviewGPT.git
cd InterviewGPT
```

---

### 2️⃣ Backend Setup (Python)

```bash
cd backend
pip install uv
uv sync
```

Create `.env` inside `backend/`:

```env
LIVEKIT_URL=ws://127.0.0.1:7880
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret

GOOGLE_API_KEY=your_google_gemini_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key
MURF_API_KEY=your_murf_api_key
```

> ⚠️ Never commit `.env` to GitHub.

Run the backend:

```bash
uv run python src/agent.py dev
```

---

### 3️⃣ Frontend Setup (Next.js)

```bash
cd frontend
npm install -g pnpm
pnpm install
```

Create `.env.local` inside `frontend/`:

```env
NEXT_PUBLIC_LIVEKIT_URL=wss://<your-livekit-project>.livekit.cloud
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_APP_CONFIG_ENDPOINT=
SANDBOX_ID=
```

Run the frontend:

```bash
pnpm dev
```

App will be available at `http://localhost:3000`.

---

## 🎯 How the App Works

1. Officer opens the web app and connects their microphone
2. Clicks **"Start Incident Session"**
3. Reports the incident by voice (location, type, severity, lanes blocked, etc.)
4. The AI Co-Pilot generates:
   - Signal re-timing suggestions for nearby intersections
   - Diversion route recommendations with activation sequence
   - Ready-to-publish public alert drafts (VMS, radio, social media)
   - Response priority matrix with dispatch order
5. Officer can ask follow-up questions or report changes in conditions
6. Co-Pilot updates recommendations in real time

---

## 🔐 Environment Variables Summary

### Backend

```env
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
GOOGLE_API_KEY=
DEEPGRAM_API_KEY=
MURF_API_KEY=
```

### Frontend

```env
NEXT_PUBLIC_LIVEKIT_URL=
NEXT_PUBLIC_BACKEND_URL=
SANDBOX_ID=
```

---

## 🚀 Why It Matters

- Reduces cognitive overload on officers during high-stakes incidents
- Faster, better-informed decisions lead to shorter clearance times
- Generates specific, actionable recommendations instead of raw dashboard data
- Fewer secondary accidents through proactive diversion management
- Demonstrates measurable response time savings vs. manual coordination

---

## 🧠 Future Enhancements

- Integration with live sensor feeds and camera streams
- Map-based dashboard with Folium/Streamlit for visual incident management
- OSMnx-powered real street graph routing for diversion calculations
- Historical incident analysis and pattern recognition
- Multi-agency coordination support (police, fire, EMS)
- Automated post-incident reports

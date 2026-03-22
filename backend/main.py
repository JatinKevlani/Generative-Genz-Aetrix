from fastapi import FastAPI, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
import threading
import time
import os
import networkx as nx
import osmnx as ox
import httpx
from dotenv import load_dotenv

load_dotenv()

from llm import analyze_incident as llm_analyze_incident, generate_chat_reply

app = FastAPI(title="Traffic Incident Copilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pydantic Models ──────────────────────────────────────────────────────────


class QueryRequest(BaseModel):
    query: str


class IncidentReport(BaseModel):
    lat: float
    lng: float
    incident_type: str
    severity: int
    notes: str = ""
    timestamp: str = ""


class IncidentAnalysisRequest(BaseModel):
    lat: float
    lng: float
    incident_type: str
    severity: int = Field(ge=1, le=5)
    lanes_blocked: int = Field(ge=0, le=6, default=1)
    notes: str = ""


class SignalRetimingItem(BaseModel):
    intersection: str
    current_green_seconds: int
    recommended_green_seconds: int
    rationale: str


class DiversionRouteItem(BaseModel):
    name: str
    from_local: str
    to_local: str
    via_streets: list[str]
    extra_travel_minutes: int
    activate_step: int

class PublicAlerts(BaseModel):
    vms: str
    radio: str
    social: str

class IncidentAnalysisResponse(BaseModel):
    signal_retiming: list[SignalRetimingItem]
    diversion_routes: list[DiversionRouteItem]
    public_alerts: PublicAlerts
    incident_narrative: str
    route_coordinates: list[list[float]] = []


# ── Simulated State ──────────────────────────────────────────────────────────

MOCK_SENSORS = [
    {"sensor_id": "S-101", "location": "SG Highway & Iskcon Cross Roads", "speed_kmph": 40, "status": "Normal", "alert": ""},
    {"sensor_id": "S-102", "location": "Ashram Road & Income Tax Circle", "speed_kmph": 22, "status": "Congested", "alert": ""},
    {"sensor_id": "S-103", "location": "CG Road & Swastik Cross Roads", "speed_kmph": 50, "status": "Normal", "alert": ""},
    {"sensor_id": "S-104", "location": "Relief Road & Kalupur Crossing", "speed_kmph": 15, "status": "Congested", "alert": ""},
    {"sensor_id": "S-105", "location": "132 Ft Ring Road & Shivranjani Cross Roads", "speed_kmph": 55, "status": "Normal", "alert": ""},
    {"sensor_id": "S-106", "location": "Drive-In Road & Gurukul Cross Roads", "speed_kmph": 30, "status": "Slow", "alert": ""},
    {"sensor_id": "S-107", "location": "Sarkhej-Gandhinagar Highway & Thaltej Cross Roads", "speed_kmph": 18, "status": "Congested", "alert": ""},
    {"sensor_id": "S-108", "location": "Nehru Bridge & Sabarmati Riverfront", "speed_kmph": 45, "status": "Normal", "alert": ""},
]

CLASS_STATE = {
    "current_step": 0,
    "max_steps": 0,
    "traffic_data": [],
    "incident_active": False,
    "route": [],
    "graph": None,
    "reported_incidents": [],
}


def load_data():
    df = pd.read_csv("ahmedabad_traffic_mock.csv")
    CLASS_STATE["traffic_data"] = df.to_dict("records")
    CLASS_STATE["max_steps"] = len(df)


def simulation_worker():
    while True:
        if CLASS_STATE["current_step"] < CLASS_STATE["max_steps"] - 1:
            CLASS_STATE["current_step"] += 1
            current_row = CLASS_STATE["traffic_data"][CLASS_STATE["current_step"]]
            if current_row.get("alert") == "CRITICAL_ACCIDENT":
                CLASS_STATE["incident_active"] = True
        time.sleep(5)


@app.on_event("startup")
def startup_event():
    load_data()
    try:
        point = (23.0225, 72.5714)
        graph = ox.graph_from_point(point, dist=500, network_type="drive")
        CLASS_STATE["graph"] = graph

        nodes = list(graph.nodes())
        if len(nodes) >= 2:
            route = nx.shortest_path(graph, nodes[0], nodes[-1], weight="length")
            route_coords = [
                [graph.nodes[node]["y"], graph.nodes[node]["x"]] for node in route
            ]
            CLASS_STATE["route"] = route_coords
    except Exception as e:
        print("OSMnx failed to load:", e)

    threading.Thread(target=simulation_worker, daemon=True).start()


# ── Endpoints ────────────────────────────────────────────────────────────────


@app.get("/api/live")
def get_live_feeds():
    step = CLASS_STATE["current_step"]
    current_data = (
        CLASS_STATE["traffic_data"][step] if CLASS_STATE["traffic_data"] else {}
    )
    return {
        "step": step,
        "traffic": current_data,
        "sensors": MOCK_SENSORS,
        "incident_active": CLASS_STATE["incident_active"]
        or len(CLASS_STATE["reported_incidents"]) > 0,
        "diversion_route": CLASS_STATE["route"],
        "reported_incidents": CLASS_STATE["reported_incidents"],
    }


@app.post("/api/report-incident")
def report_incident(report: IncidentReport):
    incident_data = report.model_dump()
    CLASS_STATE["reported_incidents"].append(incident_data)
    CLASS_STATE["incident_active"] = True
    return {
        "status": "ok",
        "incident": incident_data,
        "total_incidents": len(CLASS_STATE["reported_incidents"]),
    }


@app.post("/api/analyze-incident", response_model=IncidentAnalysisResponse)
async def analyze_incident(req: IncidentAnalysisRequest):
    """Analyze an incident and return complete incident intelligence."""
    results = await llm_analyze_incident(
        lat=req.lat,
        lng=req.lng,
        incident_type=req.incident_type,
        severity=req.severity,
        lanes_blocked=req.lanes_blocked,
        notes=req.notes,
        sensors=MOCK_SENSORS,
    )
    # Compute diversion route coordinates using OSMnx
    route_coords: list[list[float]] = []
    graph = CLASS_STATE.get("graph")
    if graph is not None:
        try:
            origin_node = ox.nearest_nodes(graph, req.lng, req.lat)
            nodes = list(graph.nodes())
            # Pick a destination node far from origin
            dest_node = nodes[-1] if nodes[0] == origin_node else nodes[0]
            route = nx.shortest_path(graph, origin_node, dest_node, weight="length")
            route_coords = [
                [graph.nodes[n]["y"], graph.nodes[n]["x"]] for n in route
            ]
        except Exception as e:
            print(f"Route computation failed: {e}")
            route_coords = CLASS_STATE.get("route", [])
    else:
        route_coords = CLASS_STATE.get("route", [])

    return IncidentAnalysisResponse(
        signal_retiming=[SignalRetimingItem(**item) for item in results.get("signal_retiming", [])],
        diversion_routes=[DiversionRouteItem(**item) for item in results.get("diversion_routes", [])],
        public_alerts=PublicAlerts(**results.get("public_alerts", {"vms": "", "radio": "", "social": ""})),
        incident_narrative=results.get("incident_narrative", ""),
        route_coordinates=route_coords,
    )


@app.post("/api/chat")
async def chat_endpoint(req: QueryRequest, background_tasks: BackgroundTasks):
    step = CLASS_STATE["current_step"]
    current_data = (
        CLASS_STATE["traffic_data"][step] if CLASS_STATE["traffic_data"] else {}
    )
    context = (
        f"Sensor {current_data.get('sensor_id')} at {current_data.get('location')} "
        f"reading {current_data.get('speed_kmph')} km/h. "
        f"Status: {current_data.get('status')}. Alert: {current_data.get('alert')}."
    )
    status = current_data.get("status", "")

    reply_text = await generate_chat_reply(req.query, context, status)
    return {"reply": reply_text}


@app.post("/api/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    """Transcribe audio using Deepgram API."""
    deepgram_key = os.getenv("DEEPGRAM_API_KEY", "")
    if not deepgram_key:
        return {"transcript": "", "error": "DEEPGRAM_API_KEY not set"}

    audio_bytes = await audio.read()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true",
                headers={
                    "Authorization": f"Token {deepgram_key}",
                    "Content-Type": audio.content_type or "audio/webm",
                },
                content=audio_bytes,
                timeout=15.0,
            )
            data = resp.json()
            transcript = (
                data.get("results", {})
                .get("channels", [{}])[0]
                .get("alternatives", [{}])[0]
                .get("transcript", "")
            )
            return {"transcript": transcript}
    except Exception as e:
        return {"transcript": "", "error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


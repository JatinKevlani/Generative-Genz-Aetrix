from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
import threading
import time
import os
import networkx as nx
import osmnx as ox

from llm import analyze_signal_retiming, generate_chat_reply

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


class IncidentAnalysisResponse(BaseModel):
    signal_retiming: list[SignalRetimingItem]


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
    """Analyze an incident and return signal re-timing recommendations."""
    results = await analyze_signal_retiming(
        lat=req.lat,
        lng=req.lng,
        incident_type=req.incident_type,
        severity=req.severity,
        lanes_blocked=req.lanes_blocked,
        notes=req.notes,
        sensors=MOCK_SENSORS,
    )
    return IncidentAnalysisResponse(
        signal_retiming=[SignalRetimingItem(**item) for item in results]
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


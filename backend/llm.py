# llm.py
"""
LLM Client Module
==================
Handles all LLM interactions for the Traffic Incident Copilot:
- Signal re-timing analysis (structured JSON output)
- Conversational chat (plain text output)
- Mock fallbacks when no API key is configured

Public API:
    analyze_signal_retiming(req, sensors) -> list[dict]
    generate_chat_reply(query, context) -> str
"""
import json
import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic

# ── Config ───────────────────────────────────────────────────────────────────

MODEL = "claude-sonnet-4-20250514"
ANALYSIS_TEMPERATURE = 0.2
CHAT_TEMPERATURE = 0.0

# ── Prompt Templates ────────────────────────────────────────────────────────

INCIDENT_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an AI Traffic Incident Copilot embedded in Ahmedabad's Integrated Traffic Management Centre (ITMC).\n"
        "Your task is to analyze traffic incidents in Ahmedabad, Gujarat, India, and generate actionable intelligence.\n\n"
        "Rules:\n"
        "1. Name SPECIFIC intersections and roads using real Ahmedabad names (e.g., SG Highway, Ashram Road).\n"
        "2. Provide exact green phase duration changes in seconds.\n"
        "3. Be decisive — use command language.\n"
        "4. Calibrate urgency to severity (5 = critical/terse, 1 = measured/thorough).\n"
        "5. Return 3-5 intersection recommendations, and 1-2 diversion routes.\n\n"
        "Current sensor readings:\n{sensor_context}\n\n"
        "Respond ONLY with valid JSON matching this schema — no preamble:\n"
        '{{\n'
        '  "signal_retiming": [\n'
        '    {{\n'
        '      "intersection": "exact intersection name",\n'
        '      "current_green_seconds": integer,\n'
        '      "recommended_green_seconds": integer,\n'
        '      "rationale": "one sentence"\n'
        '    }}\n'
        '  ],\n'
        '  "diversion_routes": [\n'
        '    {{\n'
        '      "name": "route label",\n'
        '      "from_local": "string",\n'
        '      "to_local": "string",\n'
        '      "via_streets": ["string"],\n'
        '      "extra_travel_minutes": integer,\n'
        '      "activate_step": integer\n'
        '    }}\n'
        '  ],\n'
        '  "public_alerts": {{\n'
        '    "vms": "≤3 lines, ≤60 chars each, use \\n",\n'
        '    "radio": "~100 words",\n'
        '    "social": "≤280 chars"\n'
        '  }},\n'
        '  "incident_narrative": "100-150 words plain English briefing summary"\n'
        '}}'
    ),
    (
        "user",
        "INCIDENT DECLARED:\n"
        "Type: {incident_type}\n"
        "Severity: {severity}/5\n"
        "Location: {lat}, {lng}\n"
        "Lanes Blocked: {lanes_blocked}\n"
        "Notes: {notes}\n\n"
        "Generate full incident analysis and recommendations."
    ),
])

CHAT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an AI Traffic Incident Copilot for Ahmedabad, Gujarat, India. You assist traffic command officers. "
        "Current traffic context: {context}. "
        "Provide brief, actionable intelligence consisting of signal re-timing, "
        "diversions, or public alerts. Use Ahmedabad road names and km/h for speeds.",
    ),
    ("user", "{query}"),
])


# ── LLM Helpers ─────────────────────────────────────────────────────────────

def _get_api_key() -> str | None:
    """Return the Anthropic API key from environment, or None."""
    return os.getenv("ANTHROPIC_API_KEY")


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` fences from LLM output."""
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    return clean


# ── Signal Re-Timing ────────────────────────────────────────────────────────

def _get_mock_incident_analysis(
    incident_type: str,
    severity: int,
) -> dict:
    """Return realistic mock full incident analysis scaled by severity."""
    severity_multiplier = severity / 3.0

    signal_retiming = [
        {
            "intersection": "SG Highway & Iskcon Cross Roads",
            "current_green_seconds": 45,
            "recommended_green_seconds": 45 + int(20 * severity_multiplier),
            "rationale": (
                f"Primary corridor adjacent to {incident_type.lower()}. "
                "Extend green to flush queued southbound traffic toward Satellite."
            ),
        },
        {
            "intersection": "Ashram Road & Income Tax Circle",
            "current_green_seconds": 40,
            "recommended_green_seconds": 40 + int(15 * severity_multiplier),
            "rationale": (
                "Secondary spillback corridor along Sabarmati riverfront. "
                "Increase throughput to absorb diverted eastbound traffic."
            ),
        },
        {
            "intersection": "CG Road & Swastik Cross Roads",
            "current_green_seconds": 35,
            "recommended_green_seconds": 35 + int(25 * severity_multiplier),
            "rationale": (
                "Primary diversion route receiving rerouted traffic from SG Highway. "
                "Significantly extend green phase."
            ),
        },
    ]
    
    diversion_routes = [
        {
            "name": "Primary Diversion via CG Road",
            "from_local": "Navrangpura",
            "to_local": "Paldi",
            "via_streets": ["CG Road", "Parimal Garden", "Paldi Cross Roads"],
            "extra_travel_minutes": 12,
            "activate_step": 1
        },
        {
            "name": "Secondary Diversion via 132 Ft Ring Road",
            "from_local": "Vastrapur",
            "to_local": "Shyamal",
            "via_streets": ["IIM Road", "132 Ft Ring Road"],
            "extra_travel_minutes": 18,
            "activate_step": 2
        }
    ]
    
    public_alerts = {
        "vms": f"{incident_type.upper()} AT SG HIGHWAY\nHEAVY DELAYS EXPECTED\nUSE CG ROAD OR RING ROAD",
        "radio": f"Attention Ahmedabad motorists. A severe {incident_type.lower()} has been reported on the SG Highway near Iskcon Cross Roads causing major delays of up to 45 minutes. Emergency services are en route. Local authorities strongly urge all commuters to divert through CG Road or the 132 Ft Ring Road towards Shyamal. Please avoid the area until further notice, and stay tuned for updates.",
        "social": f"🚨 TRAFFIC ALERT 🚨 A {incident_type.lower()} has occurred on SG Highway at Iskcon Cross Roads. Expect heavy congestion. Please find alternate routes via CG Road. 🚗 #AhmedabadTraffic #AHMUpdates"
    }

    return {
        "signal_retiming": signal_retiming,
        "diversion_routes": diversion_routes,
        "public_alerts": public_alerts,
        "incident_narrative": f"A severity {severity} {incident_type.lower()} has resulted in severe queue spillbacks down the SG Highway. Multiple lanes are blocked, directly disrupting the primary north-south artery. Traffic control is advised to rapidly flush secondary parallel routes like CG Road and implement immediate diversion warnings."
    }


async def analyze_incident(
    *,
    lat: float,
    lng: float,
    incident_type: str,
    severity: int,
    lanes_blocked: int,
    notes: str,
    sensors: list[dict],
) -> dict:
    """
    Generate complete incident intelligence via LLM.

    Falls back to mock data if no API key is set or the LLM call fails.

    Returns:
        Dict mapped to the full incident intelligence schema.
    """
    api_key = _get_api_key()

    if api_key:
        try:
            sensor_context = "\n".join(
                f"- {s['location']}: {s['speed_kmph']} km/h ({s['status']})"
                for s in sensors
            )

            llm = ChatAnthropic(
                model=MODEL,
                temperature=ANALYSIS_TEMPERATURE,
                api_key=api_key,
            )
            chain = INCIDENT_ANALYSIS_PROMPT | llm
            response = chain.invoke({
                "sensor_context": sensor_context,
                "incident_type": incident_type,
                "severity": severity,
                "lat": lat,
                "lng": lng,
                "lanes_blocked": lanes_blocked,
                "notes": notes or "None provided",
            })

            data = json.loads(_strip_markdown_fences(response.content))
            return data

        except Exception as e:
            print(f"LLM analysis failed, falling back to mock: {e}")

    return _get_mock_incident_analysis(incident_type, severity)

# ── Historical Traffic Data Tool ─────────────────────────────────────────────

from langchain_core.tools import tool
import duckdb
import pandas as pd

@tool
def query_historical_traffic(road_name: str, zone: str | None = None) -> str:
    """
    Query the historical traffic speed dataset for Ahmedabad to get average speeds.
    Use this tool when you need baseline historical traffic data for a road.
    
    Args:
        road_name: The name or partial name of the road (e.g. 'SG Highway', 'Ashram Rd').
        zone: Optional zone (e.g. 'West', 'East', 'North', 'South', 'Central', 'Expressway').
    """
    csv_path = os.path.join(os.path.dirname(__file__), "ahmedabad_traffic_speed.csv")
    if not os.path.exists(csv_path):
        return "Error: ahmedabad_traffic_speed.csv not found on the server."
        
    query = f"SELECT linkName, AVG(Speed) as avg_speed, MAX(Speed) as max_speed, MIN(Speed) as min_speed FROM read_csv_auto('{csv_path}') WHERE linkName ILIKE '%{road_name}%'"
    if zone:
        query += f" AND Borough = '{zone}'"
    query += " GROUP BY linkName LIMIT 10"
    
    try:
        res = duckdb.query(query).df()
        if res.empty:
            return f"No historical data found for '{road_name}'."
        # Round the floats for cleaner output
        res = res.round(2)
        return res.to_string(index=False)
    except Exception as e:
        return f"Error querying dataset: {str(e)}"

# ── Chat ─────────────────────────────────────────────────────────────────────

def _get_mock_chat_reply(query: str, status: str) -> str:
    """Return a simulated LLM reply based on keyword matching."""
    q = query.lower()
    if "re-time" in q or "signal" in q:
        return (
            "[Simulated LLM] Recommend extending southbound green phase at "
            "SG Highway & Iskcon Cross Roads by 15s to flush congestion."
        )
    if "divert" in q or "route" in q:
        return (
            "[Simulated LLM] Recommend diverting westbound traffic via CG Road. "
            "Expected delay reduction: 12 mins."
        )
    if "alert" in q or "public" in q:
        return (
            "[Simulated LLM] DRAFT ALERT: 'Major accident at SG Highway & Iskcon Cross Roads. "
            "Expect heavy delays. Please use CG Road or 132 Ft Ring Road.'"
        )
    return (
        f"[Simulated LLM] Acknowledged. Current situation: "
        f"{status}. How else can I assist?"
    )


async def generate_chat_reply(query: str, context: str, status: str = "") -> str:
    """
    Answer a free-text query using the LLM with traffic context.

    Falls back to keyword-matched mock replies when no API key is set.

    Args:
        query: The officer's question.
        context: Formatted string of current sensor data.
        status: Current traffic status (used for mock fallback).

    Returns:
        Plain text response string.
    """
    api_key = _get_api_key()

    if api_key:
        try:
            llm = ChatAnthropic(
                model=MODEL,
                temperature=CHAT_TEMPERATURE,
            )
            from langgraph.prebuilt import create_react_agent
            from langchain_core.messages import SystemMessage, HumanMessage
            
            agent_executor = create_react_agent(llm, tools=[query_historical_traffic])
            
            system_msg = SystemMessage(content=(
                f"You are an AI Traffic Incident Copilot for Ahmedabad, Gujarat, India. "
                f"You assist traffic command officers. Current traffic context: {context}. "
                "Provide brief, actionable intelligence consisting of signal re-timing, "
                "diversions, or public alerts. Use Ahmedabad road names and km/h for speeds. "
                "You have access to a tool for querying historical traffic data. Use it whenever "
                "baseline measurements, past history, or speed comparisons are requested."
            ))
            user_msg = HumanMessage(content=query)
            
            response = agent_executor.invoke({"messages": [system_msg, user_msg]})
            return response["messages"][-1].content
        except Exception as e:
            return f"[LLM Error]: {str(e)}"

    return _get_mock_chat_reply(query, status)

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
    "incident_narrative": "100-150 word plain-English situational summary."
}


def _severity_label(severity: int) -> str:
    labels = {1: "Minor", 2: "Low", 3: "Moderate", 4: "High", 5: "Critical"}
    return labels.get(severity, "Unknown")


def _congestion_label(speed_mph: float) -> str:
    if speed_mph >= 40:
        return "free_flow"
    elif speed_mph >= 20:
        return "slow"
    return "severe_congestion"


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
            "location": {"lat": incident["lat"], "lng": incident["lng"]},
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
            {"name": inter["name"], "distance_from_incident_m": inter["distance_m"]}
            for inter in nearby_intersections
        ],
        "instructions": (
            "Respond ONLY with a valid JSON object matching the output_schema below. "
            "No preamble, no explanation outside the JSON. "
            "All street names must be real NYC street names."
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
        [context turn, anchor response, ...rolling history..., current query]

    Rolling window: last CHAT_MAX_HISTORY_TURNS turns.
    """
    from config import CHAT_MAX_HISTORY_TURNS

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

    narrative_preview = llm_output.get("incident_narrative", "") or ""
    anchor_response = {
        "role": "assistant",
        "content": (
            f"Incident acknowledged. {narrative_preview[:200]}... "
            "Signal re-timing, diversion, and alert recommendations are ready. "
            "Ask me anything about current conditions."
        )
    }

    history_window = chat_history[-(CHAT_MAX_HISTORY_TURNS * 2):]
    history_messages = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history_window
    ]

    current_query = {"role": "user", "content": query}
    return [context_message, anchor_response] + history_messages + [current_query]

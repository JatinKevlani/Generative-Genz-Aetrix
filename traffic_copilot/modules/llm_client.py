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
    LLM_MAX_RETRIES, LLM_RETRY_BASE_DELAY
)
from modules.state import IncidentState, LLMOutputState, ChatMessage
from modules.prompt_builder import (
    build_incident_prompt, build_chat_messages, SYSTEM_PROMPT
)

logger = logging.getLogger(__name__)


class LLMError(Exception):
    pass


def _get_client() -> anthropic.Anthropic:
    """Create and return an Anthropic client using the env API key."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise LLMError("ANTHROPIC_API_KEY is not set in environment.")
    return anthropic.Anthropic(api_key=api_key)


def _call_with_retry(messages: list[dict]) -> anthropic.types.Message:
    """
    Call the Anthropic API with exponential backoff retry.
    Raises LLMError after max retries.
    """
    client = _get_client()
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

            logger.info(
                f"LLM call OK | attempt={attempt + 1} | "
                f"in={response.usage.input_tokens} out={response.usage.output_tokens} tokens | {elapsed_ms}ms"
            )
            return response

        except anthropic.RateLimitError as e:
            last_error = e
            delay = LLM_RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(f"Rate limit hit (attempt {attempt + 1}). Retrying in {delay}s.")
            time.sleep(delay)

        except anthropic.APIStatusError as e:
            last_error = e
            delay = LLM_RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(f"API error {e.status_code} (attempt {attempt + 1}). Retrying in {delay}s.")
            time.sleep(delay)

    raise LLMError(f"LLM call failed after {LLM_MAX_RETRIES} attempts: {last_error}")


def _parse_incident_response(raw_text: str) -> LLMOutputState:
    """
    Parse the LLM's JSON response into LLMOutputState.
    Falls back to raw narrative on parse failure.
    """
    try:
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
            "incident_narrative": raw_text,
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

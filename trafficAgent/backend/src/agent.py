import logging

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RoomInputOptions,
    WorkerOptions,
    cli,
    metrics,
    tokenize,
    # function_tool,
    # RunContext
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("traffic-copilot")

load_dotenv(".env.local")


class TrafficCoPilot(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are an advanced AI Co-Pilot for Traffic Incident Command, designed to assist traffic control officers during major incidents on the road network.

Your role is to provide real-time, actionable intelligence when a traffic incident occurs — reducing cognitive overload and enabling faster, better-informed decisions.

When an officer reports an incident, you must gather essential details through calm, professional questioning:
- Location (road, intersection, mile marker)
- Type of incident (collision, vehicle breakdown, hazmat spill, road obstruction, weather event)
- Number of vehicles involved
- Lanes blocked (direction and count)
- Injuries reported (yes/no/unknown)
- Current traffic conditions in the area
- Time the incident was reported

Once you have sufficient information, you generate FOUR types of intelligence:

1. **Signal Re-timing Suggestions**
   - Name specific nearby intersections by their real street names
   - Recommend exact phase duration changes (e.g., "Extend green on Main St northbound from 45s to 70s")
   - Prioritize intersections closest to the incident that can absorb diverted traffic
   - Suggest temporary signal mode changes if needed (e.g., flashing yellow for low-priority cross streets)

2. **Diversion Route Recommendations**
   - Provide 2–3 alternative routes with specific street names
   - Specify activation sequence (which diversion to activate first)
   - Estimate traffic redistribution percentages across diversion routes
   - Flag any capacity concerns on diversion routes (school zones, construction, narrow roads)
   - Include estimated additional travel time for each diversion

3. **Ready-to-Publish Public Alert Drafts**
   - **Variable Message Sign (VMS):** Short, all-caps, 3-line messages (max 18 chars per line)
   - **Radio Broadcast Script:** 15–20 second read, formal but clear, with specific road names and suggested alternatives
   - **Social Media Post:** Concise post with incident location, expected duration, and suggested alternatives (include hashtags)
   - All alerts should include estimated clearance time when available

4. **Response Priority Matrix**
   - Classify incident severity: CRITICAL / MAJOR / MODERATE / MINOR
   - Determine dispatch priority order for resources (e.g., EMS first, then fire, then tow, then traffic unit)
   - Estimate clearance time based on incident type and severity
   - Flag if secondary incident risk is elevated and recommend preventive measures

Communication guidelines:
- Stay calm, concise, and professional at all times — officers are under time pressure
- Use clear, unambiguous language suitable for radio communication
- One topic at a time — do not overwhelm with all four outputs simultaneously
- Ask clarifying questions if critical details are missing before generating recommendations
- When asked to update, adjust recommendations based on new information
- Speak in short, direct sentences — you are communicating via voice in a high-stakes environment
- Avoid jargon that a field officer might not understand
- If the officer asks you to repeat or clarify, do so immediately and concisely

If the officer asks you to focus on a specific output (e.g., "just give me the diversion routes"), provide only that output.

If the officer reports a change in conditions (e.g., "another lane just opened" or "EMS is on scene"), immediately update your recommendations.

You are not a general assistant — you are a specialized traffic incident co-pilot. Stay focused on incident management at all times.""",
        )

    # To add tools, use the @function_tool decorator.
    # Example: Add tools for signal re-timing lookup, route calculation, alert generation, etc.
    # @function_tool
    # async def calculate_diversion_route(self, context: RunContext, origin: str, destination: str):
    #     """Calculate optimal diversion route between two points.
    #
    #     Args:
    #         origin: Starting intersection or road name
    #         destination: Target intersection or road name
    #     """
    #     logger.info(f"Calculating diversion route from {origin} to {destination}")
    #     return "Diversion route calculated successfully."


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    # Logging setup
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using Deepgram STT, Google Gemini LLM, and Murf TTS
    session = AgentSession(
        # Speech-to-text (STT) — converts officer's voice commands to text
        stt=deepgram.STT(model="nova-3"),
        # Large Language Model (LLM) — processes incident data and generates intelligence
        llm=google.LLM(
                model="gemini-2.5-flash",
            ),
        # Text-to-speech (TTS) — delivers recommendations via voice
        tts=murf.TTS(
                voice="en-US-matthew", 
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True
            ),
        # VAD and turn detection for natural voice interaction
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # Allow the LLM to generate a response while waiting for the end of turn
        preemptive_generation=True,
    )

    # Metrics collection for pipeline performance monitoring
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # Start the session with the Traffic Co-Pilot agent
    await session.start(
        agent=TrafficCoPilot(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # Join the room and connect to the officer
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))

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

from dotenv import load_dotenv

load_dotenv()

from config import (
    NYC_SPEED_CSV, OSM_BBOX, OSM_CACHE_PATH, FORCE_GRAPH_RELOAD,
    FEED_INTERVAL_SECONDS, SPEED_SNAPSHOT_TOP_N, ANTHROPIC_MODEL
)
from modules.state import get_default_state
from modules.feed_manager import load_and_prepare_csv, start_feed, get_speed_snapshot
from modules.routing import load_graph, compute_diversion, get_nearby_intersections

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
if "incidents_list" not in st.session_state:
    st.session_state.incidents_list = []
if "feed_lock" not in st.session_state:
    st.session_state.feed_lock = threading.Lock()
if "feed_speed_state" not in st.session_state:
    st.session_state.feed_speed_state = {
        "current_speeds": {}, "current_timestamp": "—",
        "tick_count": 0, "is_running": False
    }


# ── One-time Resource Loading ─────────────────────────────────────────────────
@st.cache_resource
def load_csv():
    """Load CSV once; cache across reruns. This is fast (~1 second)."""
    return load_and_prepare_csv(NYC_SPEED_CSV)


@st.cache_resource
def load_osm_graph():
    """Load OSM graph once; cache across reruns. First run downloads (~2-5 min)."""
    return load_graph(OSM_BBOX, OSM_CACHE_PATH, FORCE_GRAPH_RELOAD)


# Load CSV immediately (fast) — graph loaded lazily on demand
speed_df = load_csv()
osm_graph = None  # Loaded on demand when incident is declared

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
incidents_list = st.session_state.incidents_list

# ── Header ────────────────────────────────────────────────────────────────────
col_title, col_status = st.columns([4, 1])
with col_title:
    st.title("🚦 Traffic Incident Co-Pilot")
with col_status:
    status_colour = "🟢" if feed_state["is_running"] else "🔴"
    st.metric(
        "Feed",
        f"{status_colour} {'LIVE' if feed_state['is_running'] else 'STOPPED'}",
        f"Tick {feed_state['tick_count']}"
    )

# ── Active Incident Banner ────────────────────────────────────────────────────
if len(incidents_list) > 0:
    latest = incidents_list[-1]
    elapsed = ""
    if latest.get("declared_at"):
        delta = datetime.now(timezone.utc) - datetime.fromisoformat(latest["declared_at"])
        minutes, seconds = divmod(int(delta.total_seconds()), 60)
        hours, minutes = divmod(minutes, 60)
        elapsed = f"{hours:02d}:{minutes:02d}:{seconds:02d} elapsed"
    count_label = f"{len(incidents_list)} Active Incident{'s' if len(incidents_list) > 1 else ''}"
    st.error(
        f"🚨 {count_label} — Latest: {latest['incident_type']} | "
        f"Severity {latest['severity']}/5 | "
        f"{latest['lanes_blocked']} Lane(s) Blocked | {elapsed}"
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

    incident_type = st.selectbox(
        "Incident Type", INCIDENT_TYPES,
        index=INCIDENT_TYPES.index(incident["incident_type"])
    )
    severity = st.slider(
        "Severity", 1, 5, incident["severity"],
        help="1=Minor, 3=Moderate, 5=Critical"
    )
    lanes_blocked = st.number_input("Lanes Blocked", 0, 6, incident["lanes_blocked"])
    notes = st.text_area("Notes", incident["notes"], height=80)

    st.caption("📍 Click map to set location, or enter manually:")
    lat_input = st.number_input(
        "Latitude", value=incident["lat"] or 40.748,
        format="%.6f", step=0.001
    )
    lng_input = st.number_input(
        "Longitude", value=incident["lng"] or -73.985,
        format="%.6f", step=0.001
    )

    col_declare, col_clear = st.columns([2, 1])

    with col_declare:
        declare_clicked = st.button(
            "🚨 Declare Incident", type="primary", use_container_width=True
        )
    with col_clear:
        clear_clicked = st.button(
            "✕ Clear All", use_container_width=True,
            disabled=len(incidents_list) == 0
        )

    # ── Handle Declare ────────────────────────────────────────────────────────
    if declare_clicked:
        new_incident = {
            "declared": True,
            "lat": lat_input, "lng": lng_input,
            "incident_type": incident_type,
            "severity": severity,
            "lanes_blocked": int(lanes_blocked),
            "notes": notes,
            "declared_at": datetime.now(timezone.utc).isoformat()
        }

        # Add to the incidents list
        incidents_list.append(new_incident)

        # Also update the current incident state for LLM analysis
        incident.update(new_incident)

        with st.spinner("Analysing incident… (loading road network on first use)"):
            try:
                # Lazy-load OSM graph on first incident declaration
                osm_graph_local = load_osm_graph()

                snapshot = get_speed_snapshot(
                    st.session_state.feed_lock,
                    feed_state, SPEED_SNAPSHOT_TOP_N
                )
                nearby = get_nearby_intersections(osm_graph_local, lat_input, lng_input)
                result = analyze_incident(incident, snapshot, nearby)
                app["llm_output"].update(result)

                # Compute diversion path if routes returned
                if result["diversion_routes"]:
                    try:
                        dest_lat = lat_input + 0.015
                        dest_lng = lng_input + 0.010
                        path = compute_diversion(
                            osm_graph_local, lat_input, lng_input, dest_lat, dest_lng
                        )
                        app["diversion_path"] = path
                    except Exception as e:
                        st.warning(f"Diversion overlay failed: {e}")
                        app["diversion_path"] = None

            except LLMError as e:
                st.error(f"AI analysis failed: {e}")

        st.rerun()

    # ── Handle Clear ──────────────────────────────────────────────────────────
    if clear_clicked:
        st.session_state.incidents_list = []
        app.update(get_default_state())
        st.rerun()

    # ── Configuration Expander ────────────────────────────────────────────────
    st.divider()
    with st.expander("⚙️ Configuration", expanded=False):
        st.text(f"Model: {ANTHROPIC_MODEL}")
        st.text(f"Feed interval: {FEED_INTERVAL_SECONDS}s")
        api_key_set = bool(os.environ.get("ANTHROPIC_API_KEY"))
        if api_key_set:
            st.success("✅ Anthropic API key configured")
        else:
            st.error("❌ ANTHROPIC_API_KEY not set in .env")

# ═══════════════════════════════════════════════════════════════════════════════
# MAP COLUMN
# ═══════════════════════════════════════════════════════════════════════════════
with map_col:
    st.subheader("🗺️ Live Traffic Map")

    # Use the incident location if declared, otherwise default coords
    default_lat = incident["lat"] or 40.748
    default_lng = incident["lng"] or -73.985

    # JavaScript + HTML component that fetches browser geolocation
    # and renders an OpenStreetMap iframe centered on the user's location
    map_html = f"""
    <div id="map-container" style="width:100%; height:580px; border-radius:12px; overflow:hidden; background:#1e293b; display:flex; align-items:center; justify-content:center;">
        <div id="loading" style="color:#94a3b8; font-family:sans-serif; text-align:center;">
            <div style="font-size:24px; margin-bottom:8px;">📍</div>
            <div>Requesting live location…</div>
        </div>
    </div>
    <script>
        (function() {{
            var container = document.getElementById('map-container');
            var loading = document.getElementById('loading');
            var defaultLat = {default_lat};
            var defaultLng = {default_lng};

            function showMap(lat, lng) {{
                var bbox = (lng - 0.005) + ',' + (lat - 0.003) + ',' + (lng + 0.005) + ',' + (lat + 0.003);
                var src = 'https://www.openstreetmap.org/export/embed.html?bbox=' + bbox + '&layer=mapnik&marker=' + lat + ',' + lng;
                container.innerHTML = '<iframe src="' + src + '" style="width:100%; height:100%; border:none; border-radius:12px;" title="Location map" loading="lazy"></iframe>';
            }}

            if (navigator.geolocation) {{
                navigator.geolocation.getCurrentPosition(
                    function(position) {{
                        showMap(position.coords.latitude, position.coords.longitude);
                    }},
                    function() {{
                        showMap(defaultLat, defaultLng);
                    }},
                    {{ enableHighAccuracy: true, timeout: 10000 }}
                );
            }} else {{
                showMap(defaultLat, defaultLng);
            }}
        }})();
    </script>
    """
    import streamlit.components.v1 as components
    components.html(map_html, height=590)

    # Map legend
    st.markdown(
        "🟢 Free flow (≥40 mph) &nbsp;&nbsp; "
        "🟡 Slow (20–39 mph) &nbsp;&nbsp; "
        "🔴 Congested (<20 mph) &nbsp;&nbsp; "
        "🔵 Diversion route",
        unsafe_allow_html=True
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
            for r in sorted(
                retiming,
                key=lambda x: abs(
                    x.get("recommended_green_seconds", 0) - x.get("current_green_seconds", 0)
                ),
                reverse=True
            ):
                delta = (
                    r.get("recommended_green_seconds", 0) - r.get("current_green_seconds", 0)
                )
                delta_str = f"+{delta}s" if delta > 0 else f"{delta}s"
                with st.container():
                    st.markdown(f"**{r.get('intersection', '—')}**")
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("Current", f"{r.get('current_green_seconds', '—')}s")
                    col_b.metric(
                        "Recommended",
                        f"{r.get('recommended_green_seconds', '—')}s",
                        delta=delta_str
                    )
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
                    f"Step {route.get('activate_step', i + 1)}: "
                    f"{route.get('name', f'Route {i + 1}')}",
                    expanded=(i == 0)
                ):
                    st.markdown(f"**From:** {route.get('from', route.get('from_location', '—'))}")
                    st.markdown(f"**To:** {route.get('to', route.get('to_location', '—'))}")
                    st.markdown("**Via:**")
                    for street in route.get("via_streets", []):
                        st.markdown(f"  → {street}")
                    st.info(f"⏱ +{route.get('extra_travel_minutes', '?')} minutes extra travel time")

                    if st.button("Show on map", key=f"route_btn_{i}"):
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

            st.divider()

            # Radio
            st.markdown("**📻 Radio Broadcast**")
            radio_text = alerts.get("radio", "")
            word_count = len(radio_text.split())
            st.text_area(
                "Radio draft", radio_text, height=120, key="radio_display",
                disabled=True, label_visibility="collapsed"
            )
            st.caption(f"{word_count} words (~{max(1, word_count // 130)} min read)")

            st.divider()

            # Social
            st.markdown("**📱 Social Media (X/Twitter)**")
            social_text = alerts.get("social", "")
            char_count = len(social_text)
            st.text_area(
                "Social draft", social_text, height=80, key="social_display",
                disabled=True, label_visibility="collapsed"
            )
            char_colour = "red" if char_count > 280 else "green"
            st.markdown(
                f"<span style='color:{char_colour}'>{char_count}/280 characters</span>",
                unsafe_allow_html=True
            )

            # Export
            st.divider()
            export_content = _build_export_text(incident, alerts) if "incident" in dir() else ""
            st.download_button(
                label="⬇️ Export All Alerts (.txt)",
                data=_build_export_text(incident, alerts),
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

def _handle_chat_query(query: str, incident: dict, llm_output: dict, chat: dict) -> None:
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
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=5000, key="feed_refresh")
except ImportError:
    pass

# modules/map_builder.py
"""
Map Builder
===========
Constructs the Folium map for each render tick.
Called on every feed update and any incident state change.

Public API:
    build_map(feed_state, incident, diversion_path) -> folium.Map
"""
import folium
import logging
from modules.state import IncidentState, FeedState
from config import (
    OSM_BBOX, MAP_TILE_PROVIDER, MAP_DEFAULT_ZOOM,
    COLOUR_FREE_FLOW, COLOUR_SLOW, COLOUR_CONGESTED, COLOUR_DIVERSION,
    SEGMENT_WEIGHT, DIVERSION_WEIGHT, SPEED_FREE_FLOW, SPEED_SLOW
)

logger = logging.getLogger(__name__)


def _speed_to_colour(speed_mph: float) -> str:
    """Map speed value to a hex colour string."""
    if speed_mph >= SPEED_FREE_FLOW:
        return COLOUR_FREE_FLOW
    elif speed_mph >= SPEED_SLOW:
        return COLOUR_SLOW
    return COLOUR_CONGESTED


def build_map(
    feed_state: FeedState,
    incident: IncidentState,
    diversion_path: list[tuple[float, float]] | None = None
) -> folium.Map:
    """
    Build the complete Folium map for the current application state.

    Args:
        feed_state: Current speed data for all road segments
        incident: Current incident state (may be undeclared)
        diversion_path: Optional list of (lat, lng) tuples for diversion overlay

    Returns:
        Configured folium.Map instance ready for streamlit_folium render
    """
    south, west, north, east = OSM_BBOX
    center_lat = (south + north) / 2
    center_lng = (west + east) / 2

    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=MAP_DEFAULT_ZOOM,
        tiles=MAP_TILE_PROVIDER,
        control_scale=True
    )

    # ── Speed Segments ────────────────────────────────────────────────────────
    speeds = feed_state.get("current_speeds", {})
    segment_count = 0

    for link_id, record in speeds.items():
        lat_lngs = record.get("lat_lngs", [])
        if len(lat_lngs) < 2:
            continue

        colour = _speed_to_colour(record["speed"])
        speed_val = record["speed"]
        status = (
            "Free flow" if colour == COLOUR_FREE_FLOW
            else "Slow" if colour == COLOUR_SLOW
            else "Congested"
        )
        tooltip_html = (
            f"<b>{record['name']}</b><br>"
            f"Speed: {speed_val:.1f} mph<br>"
            f"Status: {status}"
        )

        folium.PolyLine(
            locations=lat_lngs,
            color=colour,
            weight=SEGMENT_WEIGHT,
            opacity=0.8,
            tooltip=folium.Tooltip(tooltip_html, sticky=False)
        ).add_to(m)
        segment_count += 1

    logger.debug(f"Map: rendered {segment_count} speed segments")

    # ── Diversion Overlay ─────────────────────────────────────────────────────
    if diversion_path and len(diversion_path) >= 2:
        folium.PolyLine(
            locations=diversion_path,
            color=COLOUR_DIVERSION,
            weight=DIVERSION_WEIGHT,
            opacity=0.9,
            dash_array="10 5",
            tooltip=folium.Tooltip("Recommended Diversion Route", sticky=False)
        ).add_to(m)

        folium.CircleMarker(
            location=diversion_path[0],
            radius=8,
            color=COLOUR_DIVERSION,
            fill=True,
            tooltip="Diversion Start"
        ).add_to(m)
        folium.CircleMarker(
            location=diversion_path[-1],
            radius=8,
            color=COLOUR_DIVERSION,
            fill=True,
            tooltip="Diversion End"
        ).add_to(m)

    # ── Incident Pin ──────────────────────────────────────────────────────────
    if incident["declared"] and incident["lat"] and incident["lng"]:
        icon = folium.Icon(color="red", icon="exclamation-sign", prefix="glyphicon")
        popup_html = (
            f"<b>🚨 {incident['incident_type']}</b><br>"
            f"Severity: {incident['severity']}/5<br>"
            f"Lanes blocked: {incident['lanes_blocked']}<br>"
            f"<i>{incident['notes']}</i>"
        )
        folium.Marker(
            location=[incident["lat"], incident["lng"]],
            icon=icon,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip="Active Incident"
        ).add_to(m)

    return m

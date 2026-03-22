# modules/feed_manager.py
"""
Feed Manager
============
Loads the NYC traffic speed CSV and replays it in a background thread,
updating shared speed state at each tick.

Public API:
    load_and_prepare_csv(path) -> pd.DataFrame
    start_feed(df, lock, speed_state, interval) -> tuple[Thread, Event]
    stop_feed(thread, stop_event) -> None
    get_speed_snapshot(lock, speed_state, top_n) -> list[dict]
"""
import threading
import time
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class FeedError(Exception):
    pass


REQUIRED_COLUMNS = {
    "Id", "Speed", "TravelTime", "Status", "DataAsOf",
    "linkId", "linkName", "EncodedPolyLine", "Borough"
}


def _safe_decode_polyline(encoded: str) -> list:
    """Decode a Google-encoded polyline string to [[lat, lng], ...] pairs."""
    try:
        import polyline as pl
        result = [[lat, lng] for lat, lng in pl.decode(encoded)]
        if len(result) >= 2:
            return result
    except Exception:
        pass
    return []


def _parse_link_points(link_points: str) -> list:
    """
    Parse linkPoints string into [[lat, lng], ...] list.
    Format: 'lat,lng lat,lng ...' or 'lat,lng,lat,lng,...'
    """
    if not isinstance(link_points, str) or not link_points.strip():
        return []
    try:
        # Try comma-separated pairs: "40.7484,-73.9736,40.7490,-73.9732"
        parts = [p.strip() for p in link_points.replace('"', '').split(',')]
        if len(parts) >= 4 and len(parts) % 2 == 0:
            coords = []
            for i in range(0, len(parts), 2):
                coords.append([float(parts[i]), float(parts[i + 1])])
            if len(coords) >= 2:
                return coords
    except Exception:
        pass
    return []


def load_and_prepare_csv(path: str) -> pd.DataFrame:
    """
    Load the NYC speed CSV, validate columns, decode polylines,
    and sort by timestamp for replay ordering.

    Raises FeedError if required columns are missing.
    Returns a prepared DataFrame with a decoded 'lat_lngs' column.
    """
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise FeedError(f"CSV missing required columns: {missing}")

    df["DataAsOf"] = pd.to_datetime(df["DataAsOf"], errors="coerce")
    df = df.dropna(subset=["DataAsOf", "Speed", "linkId"])
    df = df.sort_values("DataAsOf").reset_index(drop=True)

    # Try decoding encoded polyline; fallback to linkPoints column
    def get_lat_lngs(row: pd.Series) -> list:
        coords = _safe_decode_polyline(str(row.get("EncodedPolyLine", "")))
        if len(coords) < 2 and "linkPoints" in row.index:
            coords = _parse_link_points(str(row.get("linkPoints", "")))
        return coords

    df["lat_lngs"] = df.apply(get_lat_lngs, axis=1)
    df = df[df["lat_lngs"].map(len) > 0]

    logger.info(
        f"Feed loaded: {len(df)} records, "
        f"{df['DataAsOf'].min()} → {df['DataAsOf'].max()}"
    )
    return df


def _feed_loop(
    df: pd.DataFrame,
    lock: threading.Lock,
    speed_state: dict,
    stop_event: threading.Event,
    interval: float
) -> None:
    """
    Internal thread target. Iterates through DataFrame rows every interval seconds,
    updating speed_state under lock.
    """
    total = len(df)
    tick = 0

    while not stop_event.is_set():
        idx = tick % total
        row = df.iloc[idx]

        link_id = int(row["linkId"])
        record = {
            "speed": float(row["Speed"]),
            "name": str(row["linkName"]),
            "lat_lngs": row["lat_lngs"]
        }
        timestamp = row["DataAsOf"].isoformat()

        with lock:
            speed_state["current_speeds"][link_id] = record
            speed_state["current_timestamp"] = timestamp
            speed_state["tick_count"] = tick
            speed_state["is_running"] = True

        if tick % 10 == 0:
            logger.info(
                f"Feed tick {tick}: linkId={link_id}, "
                f"speed={record['speed']} mph, ts={timestamp}"
            )

        tick += 1
        stop_event.wait(interval)

    with lock:
        speed_state["is_running"] = False
    logger.info("Feed thread stopped cleanly.")


def start_feed(
    df: pd.DataFrame,
    lock: threading.Lock,
    speed_state: dict,
    interval: float = 5.0
) -> tuple[threading.Thread, threading.Event]:
    """
    Start the feed replay thread.

    Returns:
        (thread, stop_event) — call stop_event.set() to stop the thread.
    """
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_feed_loop,
        args=(df, lock, speed_state, stop_event, interval),
        daemon=True,
        name="FeedSimulator"
    )
    thread.start()
    logger.info(f"Feed thread started. Interval: {interval}s")
    return thread, stop_event


def stop_feed(thread: threading.Thread, stop_event: threading.Event) -> None:
    """Signal the feed thread to stop and wait for it to finish."""
    stop_event.set()
    thread.join(timeout=10)


def get_speed_snapshot(
    lock: threading.Lock,
    speed_state: dict,
    top_n: int = 10
) -> list[dict]:
    """
    Return the top_n slowest segments from current speed state.
    Thread-safe read.
    """
    with lock:
        speeds = dict(speed_state.get("current_speeds", {}))

    sorted_segments = sorted(speeds.values(), key=lambda x: x["speed"])
    return [
        {"name": seg["name"], "speed_mph": seg["speed"], "lat_lngs": seg["lat_lngs"]}
        for seg in sorted_segments[:top_n]
    ]

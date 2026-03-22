# config.py

# ── Geographic ────────────────────────────────────────────────────────────────
# Bounding box: (south, west, north, east) — Lower/Mid Manhattan
OSM_BBOX = (40.700, -74.020, 40.780, -73.930)
OSM_CACHE_PATH = "data/osm_cache/nyc_graph.graphml"
FORCE_GRAPH_RELOAD = False  # Set True to re-download OSM

# ── Data ──────────────────────────────────────────────────────────────────────
NYC_SPEED_CSV = "data/nyc_traffic_speed.csv"

# ── Feed Simulation ───────────────────────────────────────────────────────────
FEED_INTERVAL_SECONDS = 5.0
FEED_REPLAY_SPEEDS = {
    "1×": 1.0,
    "2×": 0.5,
    "5×": 0.2
}

# ── Speed Thresholds (mph) ────────────────────────────────────────────────────
SPEED_FREE_FLOW = 40
SPEED_SLOW = 20

# ── Map ───────────────────────────────────────────────────────────────────────
MAP_TILE_PROVIDER = "CartoDB positron"
MAP_DEFAULT_ZOOM = 13
COLOUR_FREE_FLOW = "#2ECC71"
COLOUR_SLOW = "#F39C12"
COLOUR_CONGESTED = "#E74C3C"
COLOUR_DIVERSION = "#3498DB"
SEGMENT_WEIGHT = 3
DIVERSION_WEIGHT = 5

# ── LLM ──────────────────────────────────────────────────────────────────────
ANTHROPIC_MODEL = "claude-sonnet-4-5"
LLM_MAX_TOKENS = 2048
LLM_TEMPERATURE = 0.2
LLM_TIMEOUT_SECONDS = 30
LLM_MAX_RETRIES = 3
LLM_RETRY_BASE_DELAY = 1.0

# Chat context window management
CHAT_MAX_HISTORY_TURNS = 10
SPEED_SNAPSHOT_TOP_N = 10

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE = "logs/app.log"
LOG_LEVEL = "INFO"

# ── Export ────────────────────────────────────────────────────────────────────
ALERT_EXPORT_DIR = "exports/"

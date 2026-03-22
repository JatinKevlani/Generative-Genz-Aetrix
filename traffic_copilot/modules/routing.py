# modules/routing.py
"""
Routing Module
==============
Handles OSM road network loading and A* diversion path computation.

Public API:
    load_graph(bbox, cache_path, force_reload) -> nx.MultiDiGraph
    find_nearest_node(graph, lat, lng) -> int
    compute_diversion(graph, origin_lat, origin_lng, dest_lat, dest_lng) -> list[tuple[float, float]]
    get_nearby_intersections(graph, lat, lng, radius_m) -> list[dict]
"""
import math
import os
import logging
import networkx as nx
import osmnx as ox

logger = logging.getLogger(__name__)


class RoutingError(Exception):
    pass


def load_graph(
    bbox: tuple[float, float, float, float],
    cache_path: str,
    force_reload: bool = False
) -> nx.MultiDiGraph:
    """
    Load the OSM drive network for the given bounding box.
    Uses disk cache if available and force_reload is False.

    Args:
        bbox: (south, west, north, east) in decimal degrees
        cache_path: Path to .graphml cache file
        force_reload: If True, ignore cache and re-download

    Returns:
        NetworkX MultiDiGraph with speed and travel_time edge attributes
    """
    if not force_reload and os.path.exists(cache_path):
        logger.info(f"Loading OSM graph from cache: {cache_path}")
        G = ox.load_graphml(cache_path)
        logger.info(f"Graph loaded: {len(G.nodes)} nodes, {len(G.edges)} edges")
        return G

    logger.info(f"Downloading OSM graph for bbox: {bbox}")
    south, west, north, east = bbox
    G = ox.graph_from_bbox(
        bbox=(north, south, east, west),
        network_type="drive",
        simplify=True
    )
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    ox.save_graphml(G, cache_path)
    logger.info(f"Graph saved to cache: {cache_path}")
    return G


def find_nearest_node(graph: nx.MultiDiGraph, lat: float, lng: float) -> int:
    """
    Find the OSM node ID nearest to the given coordinates.

    Returns:
        OSM node ID (int)
    """
    node_id = ox.nearest_nodes(graph, X=lng, Y=lat)
    return int(node_id)


def compute_diversion(
    graph: nx.MultiDiGraph,
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float
) -> list[tuple[float, float]]:
    """
    Compute the A* shortest path between two coordinates using travel_time weight.

    Returns:
        Ordered list of (lat, lng) tuples forming the path.

    Raises:
        RoutingError if no path exists between the nodes.
    """
    try:
        origin_node = find_nearest_node(graph, origin_lat, origin_lng)
        dest_node = find_nearest_node(graph, dest_lat, dest_lng)

        path_nodes = nx.astar_path(
            graph, origin_node, dest_node, weight="travel_time"
        )

        path_coords = [
            (graph.nodes[node]["y"], graph.nodes[node]["x"])
            for node in path_nodes
        ]
        logger.info(
            f"Diversion computed: {len(path_nodes)} nodes, "
            f"{origin_node} → {dest_node}"
        )
        return path_coords

    except nx.NetworkXNoPath as e:
        raise RoutingError(f"No path between nodes: {e}") from e
    except Exception as e:
        raise RoutingError(f"Routing failed: {e}") from e


def get_nearby_intersections(
    graph: nx.MultiDiGraph,
    lat: float,
    lng: float,
    radius_m: float = 500.0
) -> list[dict]:
    """
    Return intersections (degree >= 3 nodes) within radius_m metres of (lat, lng).

    Returns:
        List of dicts: [{name, distance_m, node_id}]
    """

    def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    nearby = []
    for node_id, data in graph.nodes(data=True):
        if graph.degree(node_id) < 3:
            continue
        dist = haversine(lat, lng, data["y"], data["x"])
        if dist <= radius_m:
            edges = list(graph.edges(node_id, data=True))
            street_names = list({e[2].get("name", "") for e in edges if e[2].get("name")})
            name = " & ".join(street_names[:2]) if street_names else f"Node {node_id}"
            nearby.append({"name": name, "distance_m": round(dist), "node_id": node_id})

    nearby.sort(key=lambda x: x["distance_m"])
    return nearby[:8]

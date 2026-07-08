# -*- coding: utf-8 -*-
"""
assistant/automation/maps.py — Google Maps & Apple Maps routing for BARVIS.

Supports:
 - Directions from A to B (driving, walking, transit)
 - Location search
 - Nearby POI search (coffee, petrol, hospital, etc.)
 - ETA queries via Google Maps URL
"""

import subprocess
import urllib.parse
import logging

logger = logging.getLogger(__name__)


def _open_url(url: str) -> None:
    subprocess.run(["open", url], capture_output=True, timeout=5)


# ─── Google Maps (opens in default browser) ───────────────────────────────────

def google_maps_directions(origin: str, destination: str, mode: str = "driving") -> str:
    """
    Open Google Maps with turn-by-turn directions.
    mode: driving | walking | bicycling | transit
    """
    o_enc = urllib.parse.quote(origin)
    d_enc = urllib.parse.quote(destination)
    travelmode = {"car": "driving", "walk": "walking", "bike": "bicycling",
                  "bus": "transit", "train": "transit"}.get(mode, mode)
    url = (
        f"https://www.google.com/maps/dir/{o_enc}/{d_enc}"
        f"/?travelmode={travelmode}"
    )
    _open_url(url)
    return f"Google Maps is open with directions from {origin} to {destination}."


def google_maps_search(location: str) -> str:
    """Open Google Maps showing a specific location."""
    enc = urllib.parse.quote(location)
    url = f"https://www.google.com/maps/search/{enc}"
    _open_url(url)
    return f"Opened Google Maps for {location}."


def google_maps_nearby(place_type: str, location: str = "") -> str:
    """Search for nearby places (e.g. 'coffee shops near me')."""
    query = f"{place_type} near {location}" if location else f"{place_type} near me"
    enc = urllib.parse.quote(query)
    url = f"https://www.google.com/maps/search/{enc}"
    _open_url(url)
    return f"Showing {place_type} nearby on Google Maps."


# ─── Apple Maps (opens the native Maps app) ───────────────────────────────────

def apple_maps_directions(origin: str, destination: str, mode: str = "d") -> str:
    """
    Open Apple Maps with directions.
    mode: d=driving, w=walking, r=transit
    """
    o_enc = urllib.parse.quote(origin)
    d_enc = urllib.parse.quote(destination)
    url = f"maps://?saddr={o_enc}&daddr={d_enc}&dirflg={mode}"
    _open_url(url)
    return f"Apple Maps is open with a route from {origin} to {destination}."


def apple_maps_search(location: str) -> str:
    """Open Apple Maps at a specific location."""
    enc = urllib.parse.quote(location)
    url = f"maps://?q={enc}"
    _open_url(url)
    return f"Opened Maps for {location}."


# ─── Smart router: picks Google or Apple Maps ─────────────────────────────────

def open_directions(origin: str, destination: str, prefer_google: bool = True) -> str:
    """Route from origin to destination. Uses Google Maps by default."""
    if prefer_google:
        return google_maps_directions(origin, destination)
    else:
        return apple_maps_directions(origin, destination)


def open_location(location: str, prefer_google: bool = True) -> str:
    """Open a location in maps."""
    if prefer_google:
        return google_maps_search(location)
    else:
        return apple_maps_search(location)


# ─── Intent parser: extract origin + destination from natural speech ──────────

def parse_route_intent(statement: str):
    """
    Extract (origin, destination) from phrases like:
      - "from X to Y"
      - "get me from X to Y"
      - "distance from X to Y"
      - "directions from X to Y"
      - "how do I get from X to Y"
    Returns (origin, destination) or (None, None).
    """
    import re
    stmt = statement.lower()

    # "from X to Y" pattern
    m = re.search(
        r'\bfrom\s+(.+?)\s+to\s+(.+?)(?:\s+by\s+\w+|\.?\s*$)',
        stmt
    )
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # "between X and Y" pattern
    m = re.search(r'\bbetween\s+(.+?)\s+and\s+(.+?)(?:\.?\s*$)', stmt)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # "navigate to X" or "take me to X" (no origin → use current location)
    m = re.search(r'(?:navigate to|take me to|directions? to|go to)\s+(.+?)(?:\.?\s*$)', stmt)
    if m:
        return "My location", m.group(1).strip()

    return None, None


def parse_travel_mode(statement: str) -> str:
    """Extract preferred travel mode from statement."""
    stmt = statement.lower()
    if any(w in stmt for w in ["walk", "on foot", "walking"]):
        return "walking"
    if any(w in stmt for w in ["transit", "bus", "train", "subway", "metro"]):
        return "transit"
    if any(w in stmt for w in ["bike", "cycling", "bicycle"]):
        return "bicycling"
    return "driving"

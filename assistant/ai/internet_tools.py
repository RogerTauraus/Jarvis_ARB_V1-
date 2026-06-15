"""
internet_tools.py — Connectivity check and web search tools for JARVIS.
Provides online/offline detection and DuckDuckGo-powered search without opening a browser.
"""

import logging
import socket
import requests

logger = logging.getLogger(__name__)

DDG_API = "https://api.duckduckgo.com/"
TIMEOUT = 5  # seconds


def is_online() -> bool:
    """Check internet connectivity by attempting DNS resolution."""
    try:
        socket.setdefaulttimeout(TIMEOUT)
        socket.getaddrinfo("8.8.8.8", 53)
        return True
    except (socket.gaierror, OSError):
        return False


def web_search(query: str) -> str:
    """
    Search the web using DuckDuckGo Instant Answer API.
    Returns a text summary without opening any browser.
    Falls back gracefully if no internet or API failure.
    """
    if not is_online():
        return "I'm currently offline and cannot search the web."

    try:
        params = {
            "q": query,
            "format": "json",
            "no_redirect": "1",
            "skip_disambig": "1",
        }
        response = requests.get(DDG_API, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()

        # Try Abstract first, then Answer, then RelatedTopics
        result = (
            data.get("AbstractText")
            or data.get("Answer")
            or _extract_related(data.get("RelatedTopics", []))
        )

        if result:
            return result[:500]  # cap length for speech
        return f"I searched for '{query}' but couldn't find a concise answer. Try a more specific query."

    except requests.RequestException as e:
        logger.error(f"Web search failed: {e}")
        return "I had trouble searching the web. Please check your connection."
    except Exception as e:
        logger.error(f"Unexpected web search error: {e}")
        return "Something went wrong while searching."


def _extract_related(topics: list) -> str:
    """Extract text from the first RelatedTopic entry."""
    for topic in topics:
        if isinstance(topic, dict) and topic.get("Text"):
            return topic["Text"]
    return ""

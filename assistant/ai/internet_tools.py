"""
internet_tools.py — Connectivity check, web search, and smart web answers for JARVIS.

smart_web_answer() pipeline:
  1. DuckDuckGo Instant Answer API (no scraping, instant)
  2. DDGS full search → get top URLs
  3. Fetch first result HTML → extract main text
  4. LLM summarizes into 2-3 spoken sentences
"""

import logging
import socket
import requests
import re

logger = logging.getLogger(__name__)

DDG_API = "https://api.duckduckgo.com/"
TIMEOUT = 6  # seconds


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
    Quick DuckDuckGo Instant Answer lookup.
    Returns a short text snippet without opening any browser.
    """
    if not is_online():
        return "I'm offline and can't search the web right now."
    try:
        params = {"q": query, "format": "json", "no_redirect": "1", "skip_disambig": "1"}
        data = requests.get(DDG_API, params=params, timeout=TIMEOUT).json()
        result = (
            data.get("AbstractText") or
            data.get("Answer") or
            _extract_related(data.get("RelatedTopics", []))
        )
        if result:
            return result[:500]
        return ""
    except Exception as e:
        logger.error(f"DDG instant answer error: {e}")
        return ""


def _extract_related(topics: list) -> str:
    for topic in topics:
        if isinstance(topic, dict) and topic.get("Text"):
            return topic["Text"]
    return ""


def _extract_page_text(url: str, max_chars: int = 3000) -> str:
    """Fetch a URL and extract readable text (strips HTML tags)."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=8, allow_redirects=True)
        resp.raise_for_status()
        html = resp.text

        # Remove script/style/nav blocks
        for tag in ["script", "style", "nav", "header", "footer", "aside", "noscript"]:
            html = re.sub(rf"<{tag}[^>]*>.*?</{tag}>", " ", html, flags=re.DOTALL | re.IGNORECASE)

        # Strip HTML tags
        text = re.sub(r"<[^>]+>", " ", html)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception as e:
        logger.debug(f"Page fetch error for {url}: {e}")
        return ""


def _ddgs_search_urls(query: str, max_results: int = 3) -> list[str]:
    """Use DDGS library to get top search result URLs."""
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return [r.get("href", "") for r in results if r.get("href")]
    except Exception as e:
        logger.debug(f"DDGS search error: {e}")
        return []


def _llm_summarize(question: str, context: str) -> str:
    """Ask LLM to answer the question using web context. Spoken-friendly output."""
    from dotenv import load_dotenv
    import os
    _env = os.path.join(os.path.dirname(__file__), '..', '..', 'API', 'agent.env')
    load_dotenv(_env)

    prompt = (
        f"Using only the information below, answer this question in 2-3 natural spoken sentences. "
        f"No lists, no markdown. Sound like a knowledgeable friend explaining something.\n\n"
        f"Question: {question}\n\n"
        f"Web content:\n{context[:2500]}"
    )
    # Groq
    try:
        from groq import Groq
        key = os.getenv("GROQ_API_KEY", "")
        if key:
            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You answer questions using web content. Be concise, spoken-friendly, and informative."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3,
            )
            return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.debug(f"LLM summarize Groq error: {e}")
    return ""


def smart_web_answer(query: str) -> str:
    """
    Full pipeline:
    1. DDG Instant Answer (fast, no scraping)
    2. If empty → DDGS top URLs → fetch page → LLM summarize
    Returns a spoken answer or a helpful fallback.
    """
    if not is_online():
        return "I'm offline — can't search the web right now."

    # Step 1: Instant answer
    instant = web_search(query)
    if instant and len(instant) > 40:
        # Summarize even the instant answer to keep it spoken-friendly
        summary = _llm_summarize(query, instant)
        return summary if summary else instant[:300]

    # Step 2: Full search + page fetch
    urls = _ddgs_search_urls(query, max_results=3)
    if not urls:
        return f"I searched for '{query}' but couldn't find a clear answer. Try asking differently."

    for url in urls:
        page_text = _extract_page_text(url)
        if page_text and len(page_text) > 200:
            summary = _llm_summarize(query, page_text)
            if summary:
                return summary

    return f"I found some results for '{query}' but couldn't extract a clean answer. Want me to open the search in Chrome instead?"


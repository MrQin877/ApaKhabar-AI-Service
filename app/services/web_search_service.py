import re
from html import unescape
from urllib.parse import quote, quote_plus
from xml.etree import ElementTree

import requests

from app.core.config import get_settings
from app.schemas.tools import WebSearchInput, WebSearchResult


class WebSearchError(RuntimeError):
    pass


class WebSearchService:
    endpoint = "https://api.search.brave.com/res/v1/web/search"
    google_news_endpoint = "https://news.google.com/rss/search"
    wikipedia_endpoint = "https://id.wikipedia.org/w/api.php"
    fictional_markers = re.compile(
        r"\b(fiksi|fictional|hypothetical|hipotetis|satire|parodi|parody|"
        r"creative concept|konsep kreatif|alternate universe)\b",
        re.IGNORECASE,
    )
    current_markers = re.compile(
        r"\b(latest|current|recent|today|yesterday|breaking|terbaru|terkini|"
        r"hari ini|kemarin|baru saja|sekarang|202[4-9])\b",
        re.IGNORECASE,
    )
    historical_markers = re.compile(
        r"\b(sejarah|history|historical|asal[- ]?usul|profil|profile|"
        r"latar belakang|perkembangan|warisan)\b",
        re.IGNORECASE,
    )
    generation_prefix = re.compile(
        r"^(?:tolong\s+)?(?:buat(?:kan)?|tulis(?:kan)?|generate|create|write)\s+"
        r"(?:(?:sebuah|an?|the)\s+)?(?:(?:berita|news|artikel|article)\s+)?"
        r"(?:tentang|about|mengenai)?\s*",
        re.IGNORECASE,
    )

    @classmethod
    def should_search(cls, query: str, has_approved_evidence: bool) -> bool:
        if not query.strip() or cls.fictional_markers.search(query):
            return False
        return not has_approved_evidence or bool(cls.current_markers.search(query))

    @classmethod
    def discovery_input(cls, query: str) -> WebSearchInput:
        """Expand a broad real-world topic into a useful current-news query."""
        cleaned = " ".join(query.split())
        cleaned = cls.generation_prefix.sub("", cleaned).strip(" .,:;-") or cleaned
        if cls.historical_markers.search(cleaned):
            subject = cls.historical_markers.sub("", cleaned)
            subject = re.sub(r"\b(?:about|tentang|mengenai)\b", "", subject, flags=re.I)
            subject = " ".join(subject.split()).strip(" .,:;-")
            return WebSearchInput(
                query=f'"{subject}" sejarah profil' if subject else cleaned,
                count=7,
                freshness=None,
            )
        broad_topic = len(cleaned.split()) <= 3 and not cls.current_markers.search(
            cleaned
        )
        return WebSearchInput(
            query=f"{cleaned} berita terbaru" if broad_topic else cleaned,
            count=5,
            freshness="pw" if broad_topic else None,
        )

    @staticmethod
    def is_configured() -> bool:
        # Brave is preferred when configured; Google News RSS is the keyless
        # discovery fallback.
        return True

    @classmethod
    def search(cls, payload: WebSearchInput) -> list[WebSearchResult]:
        settings = get_settings()
        if not settings.brave_search_api_key:
            return cls._search_google_news(payload)

        params: dict[str, str | int] = {
            "q": payload.query,
            "count": payload.count,
            "country": payload.country.upper(),
            "search_lang": payload.search_language,
            "safesearch": "moderate",
            "extra_snippets": "true",
        }
        if payload.freshness:
            params["freshness"] = payload.freshness

        try:
            response = requests.get(
                cls.endpoint,
                params=params,
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": settings.brave_search_api_key,
                },
                timeout=settings.web_search_timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise WebSearchError("Web search is temporarily unavailable.") from exc

        return [
            WebSearchResult(
                title=item.get("title") or "Untitled source",
                url=item["url"],
                snippet=item.get("description") or "",
                published_at=item.get("age") or item.get("page_age"),
            )
            for item in response.json().get("web", {}).get("results", [])
            if item.get("url")
        ]

    @classmethod
    def _search_google_news(cls, payload: WebSearchInput) -> list[WebSearchResult]:
        settings = get_settings()
        locale = "id" if payload.search_language.startswith("id") else "en"
        country = "ID" if locale == "id" else payload.country.upper()
        url = (
            f"{cls.google_news_endpoint}?q={quote_plus(payload.query)}"
            f"&hl={locale}&gl={country}&ceid={country}:{locale}"
        )

        try:
            response = requests.get(
                url,
                headers={"User-Agent": "ApaKhabar-News-Discovery/1.0"},
                timeout=settings.web_search_timeout_seconds,
            )
            response.raise_for_status()
            root = ElementTree.fromstring(response.content)
        except (requests.RequestException, ElementTree.ParseError) as exc:
            raise WebSearchError("Web search is temporarily unavailable.") from exc

        results: list[WebSearchResult] = []
        for item in root.findall("./channel/item")[: payload.count]:
            link = (item.findtext("link") or "").strip()
            if not link:
                continue
            description = unescape(item.findtext("description") or "")
            description = re.sub(r"<[^>]+>", " ", description)
            description = " ".join(description.split())
            source = item.find("source")
            results.append(
                WebSearchResult(
                    title=(item.findtext("title") or "Untitled source").strip(),
                    url=link,
                    snippet=description,
                    published_at=(item.findtext("pubDate") or None),
                    source=(source.text or "Google News")
                    if source is not None
                    else "Google News",
                )
            )
        if results or not cls.historical_markers.search(payload.query):
            return results
        return cls._search_wikipedia(payload)

    @classmethod
    def _search_wikipedia(cls, payload: WebSearchInput) -> list[WebSearchResult]:
        """Keyless background-source fallback for historical/profile requests."""
        settings = get_settings()
        query = cls.historical_markers.sub("", payload.query.replace('"', ""))
        query = " ".join(query.split()).strip() or payload.query
        try:
            response = requests.get(
                cls.wikipedia_endpoint,
                params={
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": query,
                    "gsrlimit": min(payload.count, 5),
                    "prop": "extracts",
                    "exintro": "1",
                    "explaintext": "1",
                    "format": "json",
                    "utf8": "1",
                },
                headers={"User-Agent": "ApaKhabar-News-Discovery/1.0"},
                timeout=settings.web_search_timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise WebSearchError("Background source search is unavailable.") from exc

        pages = response.json().get("query", {}).get("pages", {})
        return [
            WebSearchResult(
                title=page.get("title") or "Wikipedia",
                url=f"https://id.wikipedia.org/wiki/{quote(page.get('title', '').replace(' ', '_'))}",
                snippet=(page.get("extract") or "")[:1200],
                source="Wikipedia bahasa Indonesia",
            )
            for page in pages.values()
            if page.get("title") and page.get("extract")
        ][: payload.count]

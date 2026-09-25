import requests
from app.schemas.agent import ToolAction


class EditorialTools:
    """Finite tool dispatcher; model output cannot select arbitrary Python functions."""
    def __init__(self, settings, registry, knowledge_factory):
        self.settings, self.registry, self.knowledge_factory = settings, registry, knowledge_factory

    def execute(self, action: ToolAction, request, sources, active_skills):
        if action.action == "search_information":
            if not action.query.strip():
                raise ValueError("Search requires a query")
            return self.knowledge_factory().search(action.query, request.owner_id, request.eligible_information_ids)
        if action.action == "inspect_source":
            if action.source_id not in sources:
                raise ValueError("Source is not in this run's approved evidence")
            return sources[action.source_id]
        if action.action == "read_skill":
            if action.skill not in active_skills:
                raise ValueError("Skill is not active for this step")
            return self.registry.resource(action.skill, action.resource)
        if action.action == "web_search":
            if not request.allow_web or not self.settings.web_search_url:
                raise ValueError("Web discovery is not enabled")
            # Configured adapter contract: POST {query, limit} -> {results: [{title,url,snippet}]}.
            headers = {"Authorization": f"Bearer {self.settings.web_search_api_key}"} if self.settings.web_search_api_key else {}
            response = requests.post(self.settings.web_search_url, headers=headers, json={"query": action.query, "limit": 5}, timeout=20)
            response.raise_for_status()
            result = []
            from urllib.parse import urlparse
            import hashlib
            for item in response.json().get("results", [])[:5]:
                url = str(item.get("url", ""))
                if urlparse(url).scheme not in {"http", "https"}:
                    continue
                result.append({"source_id": "web:" + hashlib.sha256(url.encode()).hexdigest()[:20],
                    "title": str(item.get("title", ""))[:500], "url": url, "snippet": str(item.get("snippet", ""))[:5000], "approved": False})
            return result
        raise ValueError("Unknown or non-executable tool")

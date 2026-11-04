import os

from ddgs import DDGS

from dayloom.registry import connectors


@connectors.register
class PublicSearch:
    def search(self, query, max_results):
        proxy = (
            os.environ.get("https_proxy")
            or os.environ.get("HTTPS_PROXY")
            or os.environ.get("all_proxy")
            or os.environ.get("ALL_PROXY")
        )
        return DDGS(timeout=10, proxy=proxy, verify=True).text(
            query, max_results=max_results, backend="duckduckgo", safesearch="moderate"
        )

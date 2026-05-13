from flotilla.tools.decorated_flotilla_tool import DecoratedFlotillaTool
from flotilla.tools.tool_decorators import tool_call
import requests

REQUEST_TIMEOUT_SECONDS = 10


class CitySearchTool(DecoratedFlotillaTool):

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        super().__init__()

    @property
    def name(self) -> str:
        return "City Search Tool"

    @property
    def llm_description(self) -> str:
        return """
Search for cities that match a partial, misspelled, or ambiguous name.

Use this tool when the user's location is unclear or could refer to
multiple cities. After selecting the correct city, use that city name
with the weather tools.

Input:
- name: a partial or approximate city name.

Returns:
A list of candidate cities that match the provided name.
"""

    @tool_call
    def city_search(self, name: str) -> str:
        url = f"{self.base_url}/v1/search.json"
        params = {"key": self.api_key, "q": name}
        return requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS).text

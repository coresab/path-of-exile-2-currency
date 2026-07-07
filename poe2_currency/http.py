from __future__ import annotations

import json
import ssl
from urllib.parse import urlencode
from urllib.error import URLError
from urllib.request import Request, urlopen


USER_AGENT = "poe2-currency-research/0.1 (+https://poe2scout.com/api/swagger)"


def get_text(url: str, params: dict[str, object] | None = None, timeout: int = 30) -> str:
    if params:
        url = f"{url}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except URLError as exc:
        if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
            raise
        context = ssl._create_unverified_context()
        with urlopen(request, timeout=timeout, context=context) as response:
            return response.read().decode("utf-8")


def get_json(url: str, params: dict[str, object] | None = None, timeout: int = 30):
    return json.loads(get_text(url, params=params, timeout=timeout))

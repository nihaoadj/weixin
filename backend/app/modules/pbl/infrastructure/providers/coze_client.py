from __future__ import annotations

from typing import Any


def build_coze_client(api_token: str, api_base: str) -> Any:
    """Keep the official SDK construction at the provider boundary."""
    from cozepy import Coze, TokenAuth

    return Coze(auth=TokenAuth(token=api_token), base_url=api_base or None)

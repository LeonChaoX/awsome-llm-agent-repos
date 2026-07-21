"""Feishu custom bot channel."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Mapping

from .base import Channel, NotificationError, growth_text, post_json, ranking_mode, safe_text


def signing_fields(secret: str, timestamp: int | None = None) -> dict[str, str]:
    if not secret:
        return {}
    timestamp = timestamp or int(time.time())
    key = f"{timestamp}\n{secret}".encode("utf-8")
    signature = base64.b64encode(hmac.new(key, b"", hashlib.sha256).digest()).decode("ascii")
    return {"timestamp": str(timestamp), "sign": signature}


@dataclass(frozen=True)
class FeishuChannel(Channel):
    webhook: str
    signing_secret: str = ""

    name = "feishu"
    required_secrets = ("FEISHU_WEBHOOK_URL",)

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "FeishuChannel":
        return cls(env.get("FEISHU_WEBHOOK_URL", ""), env.get("FEISHU_SIGNING_SECRET", ""))

    def build_payload(self, report: dict[str, Any]) -> dict[str, Any]:
        elements: list[dict[str, Any]] = [
            {
                "tag": "markdown",
                "content": f"**{report['date']} · {ranking_mode(report)}**\nOpen-source intelligence for LLM & Agent builders.",
            },
            {"tag": "hr"},
        ]
        for index, repo in enumerate(report["repositories"], 1):
            elements.append(
                {
                    "tag": "markdown",
                    "content": (
                        f"**{index}. [{repo['full_name']}]({repo['html_url']})**\n"
                        f"{safe_text(repo['description'])}\n"
                        f"⭐ {repo['stars']:,}  ·  📈 7d {growth_text(repo)}  ·  {repo['language']}"
                    ),
                }
            )
        elements.extend(
            [
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [{"tag": "plain_text", "content": "Agent Radar · Powered by GitHub Actions"}],
                },
            ]
        )
        return {
            "msg_type": "interactive",
            **signing_fields(self.signing_secret),
            "card": {
                "config": {"wide_screen_mode": True, "enable_forward": True},
                "header": {
                    "template": "blue",
                    "title": {"tag": "plain_text", "content": "Agent Radar · Daily LLM & Agent Top 10"},
                },
                "elements": elements,
            },
        }

    def send(self, report: dict[str, Any]) -> None:
        response = post_json("Feishu", self.webhook, self.build_payload(report))
        result = json.loads(response.body or "{}")
        if result.get("code", result.get("StatusCode", 0)) != 0:
            raise NotificationError("Feishu rejected the message")


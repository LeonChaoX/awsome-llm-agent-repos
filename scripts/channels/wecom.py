"""WeCom group robot channel."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from .base import Channel, NotificationError, growth_text, post_json, ranking_mode, safe_text


@dataclass(frozen=True)
class WeComChannel(Channel):
    webhook: str

    name = "wecom"
    required_secrets = ("WECOM_WEBHOOK_URL",)

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "WeComChannel":
        return cls(env.get("WECOM_WEBHOOK_URL", ""))

    def build_payload(self, report: dict[str, Any]) -> dict[str, Any]:
        lines = [
            "# Agent Radar · Daily LLM & Agent Top 10",
            f"> {report['date']} · {ranking_mode(report)}",
            "",
        ]
        for index, repo in enumerate(report["repositories"], 1):
            lines.extend(
                [
                    f"**{index}. [{repo['full_name']}]({repo['html_url']})**",
                    f"{safe_text(repo['description'], 80)}",
                    f"> ⭐ {repo['stars']:,} · 📈 7d {growth_text(repo)} · {repo['language']}",
                ]
            )
        return {"msgtype": "markdown", "markdown": {"content": "\n".join(lines)}}

    def send(self, report: dict[str, Any]) -> None:
        response = post_json("WeCom", self.webhook, self.build_payload(report))
        result = json.loads(response.body or "{}")
        if result.get("errcode") != 0:
            raise NotificationError("WeCom rejected the message")


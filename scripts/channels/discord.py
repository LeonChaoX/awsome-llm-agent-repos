"""Discord webhook channel."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .base import Channel, NotificationError, growth_text, post_json, ranking_mode, safe_text


@dataclass(frozen=True)
class DiscordChannel(Channel):
    webhook: str

    name = "discord"
    required_secrets = ("DISCORD_WEBHOOK_URL",)

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "DiscordChannel":
        return cls(env.get("DISCORD_WEBHOOK_URL", ""))

    def build_payload(self, report: dict[str, Any]) -> dict[str, Any]:
        embeds = []
        for index, repo in enumerate(report["repositories"], 1):
            embeds.append(
                {
                    "title": f"{index}. {repo['full_name']}",
                    "url": repo["html_url"],
                    "description": safe_text(repo["description"], 180),
                    "color": 0x2563EB,
                    "fields": [
                        {"name": "Stars", "value": f"{repo['stars']:,}", "inline": True},
                        {"name": "7d growth", "value": growth_text(repo), "inline": True},
                        {"name": "Language", "value": repo["language"], "inline": True},
                    ],
                }
            )
        return {
            "username": "Agent Radar",
            "content": f"**Daily LLM & Agent Top 10** · {report['date']} · {ranking_mode(report)}",
            "embeds": embeds,
            "allowed_mentions": {"parse": []},
        }

    def send(self, report: dict[str, Any]) -> None:
        response = post_json("Discord", self.webhook, self.build_payload(report))
        if response.status not in (200, 204):
            raise NotificationError("Discord rejected the message")


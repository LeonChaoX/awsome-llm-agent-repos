"""Slack incoming webhook channel."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .base import Channel, NotificationError, growth_text, post_json, ranking_mode, safe_text


@dataclass(frozen=True)
class SlackChannel(Channel):
    webhook: str

    name = "slack"
    required_secrets = ("SLACK_WEBHOOK_URL",)

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "SlackChannel":
        return cls(env.get("SLACK_WEBHOOK_URL", ""))

    def build_payload(self, report: dict[str, Any]) -> dict[str, Any]:
        blocks: list[dict[str, Any]] = [
            {"type": "header", "text": {"type": "plain_text", "text": "Agent Radar · Daily LLM & Agent Top 10"}},
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"*{report['date']}* · {ranking_mode(report)}"}],
            },
            {"type": "divider"},
        ]
        for index, repo in enumerate(report["repositories"], 1):
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*{index}. <{repo['html_url']}|{repo['full_name']}>*\n"
                            f"{safe_text(repo['description'])}\n"
                            f"⭐ {repo['stars']:,}  ·  📈 7d {growth_text(repo)}  ·  `{repo['language']}`"
                        ),
                    },
                }
            )
        return {"text": "Agent Radar daily LLM & Agent Top 10", "blocks": blocks}

    def send(self, report: dict[str, Any]) -> None:
        response = post_json("Slack", self.webhook, self.build_payload(report))
        if response.body.strip().lower() != "ok":
            raise NotificationError("Slack rejected the message")


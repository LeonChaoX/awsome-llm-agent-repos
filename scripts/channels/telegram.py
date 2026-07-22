"""Telegram Bot API channel."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from typing import Any, Mapping

from .base import Channel, NotificationError, growth_text, post_json, ranking_mode, safe_text


@dataclass(frozen=True)
class TelegramChannel(Channel):
    token: str
    chat_id: str

    name = "telegram"
    required_secrets = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "TelegramChannel":
        return cls(env.get("TELEGRAM_BOT_TOKEN", ""), env.get("TELEGRAM_CHAT_ID", ""))

    def build_payload(self, report: dict[str, Any]) -> dict[str, Any]:
        lines = [
            "<b>Agent Radar · Daily LLM &amp; Agent Top 10</b>",
            f"<i>{html.escape(report['date'])} · {html.escape(ranking_mode(report))}</i>",
            "",
        ]
        for index, repo in enumerate(report["repositories"], 1):
            lines.extend(
                [
                    f"<b>{index}. <a href=\"{html.escape(repo['html_url'], quote=True)}\">{html.escape(repo['full_name'])}</a></b>",
                    html.escape(safe_text(repo["description"], 80)),
                    f"⭐ {repo['stars']:,} · 📈 7d {growth_text(repo)} · {html.escape(repo['language'])}",
                    "",
                ]
            )
        lines.append("<i>Agent Radar · Powered by GitHub Actions</i>")
        return {
            "chat_id": self.chat_id,
            "text": "\n".join(lines),
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

    def send(self, report: dict[str, Any]) -> None:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        response = post_json("Telegram", url, self.build_payload(report))
        result = json.loads(response.body or "{}")
        if not result.get("ok"):
            raise NotificationError("Telegram rejected the message")


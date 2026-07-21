"""Generic JSON webhook channel for custom integrations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .base import Channel, NotificationError, post_json


@dataclass(frozen=True)
class GenericWebhookChannel(Channel):
    webhook: str

    name = "generic"
    required_secrets = ("GENERIC_WEBHOOK_URL",)

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "GenericWebhookChannel":
        return cls(env.get("GENERIC_WEBHOOK_URL", ""))

    def build_payload(self, report: dict[str, Any]) -> dict[str, Any]:
        return {"event": "agent_radar.daily_digest", "schema_version": 1, "data": report}

    def send(self, report: dict[str, Any]) -> None:
        response = post_json("Generic webhook", self.webhook, self.build_payload(report))
        if not 200 <= response.status < 300:
            raise NotificationError("Generic webhook rejected the message")

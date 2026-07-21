"""Shared notification channel primitives."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping


class NotificationError(RuntimeError):
    """A channel request failed without exposing its credential-bearing URL."""


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: str


def post_json(service: str, url: str, payload: dict[str, Any]) -> HttpResponse:
    """POST JSON while keeping secret URLs out of exceptions and logs."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return HttpResponse(response.status, response.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        raise NotificationError(f"{service} returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise NotificationError(f"{service} could not be reached") from exc


def safe_text(value: str, limit: int = 120) -> str:
    translations = str.maketrans({"[": "［", "]": "］", "<": "＜", ">": "＞"})
    value = " ".join(str(value).translate(translations).split())
    return value if len(value) <= limit else value[: limit - 1] + "…"


def growth_text(repo: Mapping[str, Any]) -> str:
    prefix = "" if repo["growth_exact"] else "~"
    return f"+{prefix}{repo['weekly_growth']:,}"


def ranking_mode(report: Mapping[str, Any]) -> str:
    repos = report["repositories"]
    return "measured 7-day growth" if all(repo["growth_exact"] for repo in repos) else "estimated growth · snapshot warming up"


class Channel(ABC):
    name: str
    required_secrets: tuple[str, ...]

    @classmethod
    @abstractmethod
    def from_env(cls, env: Mapping[str, str]) -> "Channel":
        raise NotImplementedError

    @classmethod
    def configuration_error(cls, env: Mapping[str, str]) -> str | None:
        present = [name for name in cls.required_secrets if env.get(name)]
        if present and len(present) != len(cls.required_secrets):
            missing = ", ".join(name for name in cls.required_secrets if not env.get(name))
            return f"{cls.name} is partially configured; missing {missing}"
        return None

    @classmethod
    def is_configured(cls, env: Mapping[str, str]) -> bool:
        return all(env.get(name) for name in cls.required_secrets)

    @abstractmethod
    def build_payload(self, report: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def send(self, report: dict[str, Any]) -> None:
        raise NotImplementedError

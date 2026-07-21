#!/usr/bin/env python3
"""Render and send the daily repository ranking to a Feishu custom bot."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--webhook", default=os.environ.get("FEISHU_WEBHOOK_URL", ""))
    parser.add_argument("--secret", default=os.environ.get("FEISHU_SIGNING_SECRET", ""))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def signing_fields(secret: str, timestamp: int | None = None) -> dict[str, str]:
    if not secret:
        return {}
    timestamp = timestamp or int(time.time())
    key = f"{timestamp}\n{secret}".encode("utf-8")
    signature = base64.b64encode(hmac.new(key, b"", hashlib.sha256).digest()).decode("ascii")
    return {"timestamp": str(timestamp), "sign": signature}


def safe_text(value: str, limit: int = 120) -> str:
    value = " ".join(value.replace("[", "［").replace("]", "］").split())
    return value if len(value) <= limit else value[: limit - 1] + "…"


def build_payload(report: dict[str, Any], secret: str = "") -> dict[str, Any]:
    repos = report["repositories"]
    exact_count = sum(1 for repo in repos if repo["growth_exact"])
    mode = "真实 7 日增长" if exact_count == len(repos) else "增长估算（快照积累中）"
    elements: list[dict[str, Any]] = [
        {
            "tag": "markdown",
            "content": f"**{report['date']} · {mode}**\n按 Star 增长速度与 LLM/Agent 相关性综合排序。",
        },
        {"tag": "hr"},
    ]
    for index, repo in enumerate(repos, 1):
        growth_mark = "" if repo["growth_exact"] else "约 "
        elements.append(
            {
                "tag": "markdown",
                "content": (
                    f"**{index}. [{repo['full_name']}]({repo['html_url']})**\n"
                    f"{safe_text(repo['description'])}\n"
                    f"⭐ {repo['stars']:,}  ·  📈 7日 +{growth_mark}{repo['weekly_growth']:,}  "
                    f"·  {repo['language']}"
                ),
            }
        )
    elements.extend(
        [
            {"tag": "hr"},
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": "数据来自 GitHub Search API；新部署满 7 天后自动使用真实快照差值。",
                    }
                ],
            },
        ]
    )
    return {
        "msg_type": "interactive",
        **signing_fields(secret),
        "card": {
            "config": {"wide_screen_mode": True, "enable_forward": True},
            "header": {
                "template": "blue",
                "title": {"tag": "plain_text", "content": "GitHub 本周最火 LLM & Agent 项目 Top 10"},
            },
            "elements": elements,
        },
    }


def send(webhook: str, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        webhook,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Feishu webhook failed ({exc.code}): {detail}") from exc
    if result.get("code", result.get("StatusCode", 0)) != 0:
        raise RuntimeError(f"Feishu rejected the message: {result}")


def main() -> int:
    args = parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))
    payload = build_payload(report, args.secret)
    if args.dry_run or not args.webhook:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        if not args.webhook and not args.dry_run:
            print("FEISHU_WEBHOOK_URL is not configured; skipped sending", file=sys.stderr)
        return 0
    send(args.webhook, payload)
    print("Feishu message sent successfully")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


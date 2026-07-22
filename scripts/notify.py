#!/usr/bin/env python3
"""Send one Agent Radar report to every configured notification channel."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Mapping

from channels import CHANNELS, NotificationError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON report created by collect_repos.py")
    parser.add_argument(
        "--channel",
        action="append",
        choices=sorted(CHANNELS),
        dest="channels",
        help="Only process this channel; may be repeated",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print payloads without sending")
    return parser.parse_args()


def configured_channels(env: Mapping[str, str], selected: list[str] | None = None):
    names = selected or list(CHANNELS)
    errors = []
    instances = []
    for name in names:
        channel_type = CHANNELS[name]
        error = channel_type.configuration_error(env)
        if error:
            errors.append(error)
        elif channel_type.is_configured(env):
            instances.append(channel_type.from_env(env))
    if errors:
        raise NotificationError("; ".join(errors))
    return instances


def main() -> int:
    args = parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))

    if args.dry_run:
        names = args.channels or list(CHANNELS)
        payloads = {name: CHANNELS[name].from_env({}).build_payload(report) for name in names}
        # ASCII-safe JSON keeps dry runs portable across Windows GBK terminals.
        print(json.dumps(payloads, ensure_ascii=True, indent=2))
        return 0

    channels = configured_channels(os.environ, args.channels)
    if not channels:
        print("No notification channel configured; collection completed without delivery")
        return 0

    failures = []
    for channel in channels:
        try:
            channel.send(report)
            print(f"Delivered to {channel.name}")
        except Exception as exc:
            failures.append(f"{channel.name}: {exc}")
            print(f"Delivery failed for {channel.name}", file=sys.stderr)
    if failures:
        raise NotificationError("; ".join(failures))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

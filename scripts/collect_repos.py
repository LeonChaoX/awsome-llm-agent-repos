#!/usr/bin/env python3
"""Collect recent LLM/Agent repositories and rank them by star growth."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


API_URL = "https://api.github.com/search/repositories"
STATE_VERSION = 1
SNAPSHOT_RETENTION_DAYS = 21
DEFAULT_LOOKBACK_DAYS = 180
MAX_CANDIDATES = 600

SEARCH_PHRASES = (
    "llm in:name,description",
    '"large language model" in:name,description',
    '"ai agent" in:name,description',
    "agentic in:name,description",
    '"multi-agent" in:name,description',
    "mcp agent in:name,description",
    "rag llm in:name,description",
)

TERM_WEIGHTS = {
    "llm": 4,
    "large language model": 5,
    "ai agent": 5,
    "agentic": 4,
    "multi-agent": 5,
    "multi agent": 5,
    "agent framework": 5,
    "mcp": 3,
    "model context protocol": 5,
    "rag": 2,
    "retrieval augmented generation": 4,
    "autonomous agent": 5,
}


@dataclass(frozen=True)
class Growth:
    value: int
    exact: bool
    observed_days: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, default=Path("state/stars.json"))
    parser.add_argument("--output", type=Path, default=Path("output/repos.json"))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--lookback-days", type=int, default=DEFAULT_LOOKBACK_DAYS)
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    return parser.parse_args()


def github_request(query: str, token: str, sort: str = "stars") -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {"q": query, "sort": sort, "order": "desc", "per_page": 100}
    )
    request = urllib.request.Request(
        f"{API_URL}?{params}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "awsome-llm-agent-repos-action",
            "X-GitHub-Api-Version": "2022-11-28",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response).get("items", [])
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 429) and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"GitHub Search API failed ({exc.code}): {detail}") from exc
    return []


def collect_candidates(token: str, lookback_days: int) -> list[dict[str, Any]]:
    since = date.today() - timedelta(days=lookback_days)
    qualifiers = f"created:>={since.isoformat()} archived:false fork:false"
    candidates: dict[str, dict[str, Any]] = {}
    for phrase in SEARCH_PHRASES:
        for item in github_request(f"{phrase} {qualifiers}", token):
            candidates[item["full_name"].lower()] = item
    return list(candidates.values())[:MAX_CANDIDATES]


def searchable_text(repo: dict[str, Any]) -> str:
    fields: Iterable[str] = (
        str(repo.get("name") or ""),
        str(repo.get("description") or ""),
        " ".join(repo.get("topics") or []),
    )
    return " ".join(fields).lower()


def relevance_score(repo: dict[str, Any]) -> int:
    text = searchable_text(repo)
    score = 0
    for term, weight in TERM_WEIGHTS.items():
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text):
            score += weight
    return score


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": STATE_VERSION, "snapshots": []}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"Invalid state file {path}: {exc}") from exc
    if state.get("version") != STATE_VERSION or not isinstance(state.get("snapshots"), list):
        raise RuntimeError(f"Unsupported state format in {path}")
    return state


def calculate_growth(
    full_name: str,
    current_stars: int,
    created_at: str,
    snapshots: list[dict[str, Any]],
    today: date,
) -> Growth:
    history: list[tuple[date, int]] = []
    for snapshot in snapshots:
        stars = snapshot.get("stars", {}).get(full_name)
        if stars is not None:
            history.append((date.fromisoformat(snapshot["date"]), int(stars)))
    history.sort()

    cutoff = today - timedelta(days=7)
    baselines = [(day, stars) for day, stars in history if day <= cutoff]
    if baselines:
        baseline_day, baseline_stars = baselines[-1]
        return Growth(max(0, current_stars - baseline_stars), True, (today - baseline_day).days)

    if history:
        baseline_day, baseline_stars = history[0]
        observed_days = (today - baseline_day).days
        if observed_days > 0:
            estimate = round(max(0, current_stars - baseline_stars) * 7 / observed_days)
            return Growth(estimate, False, observed_days)

    created = datetime.fromisoformat(created_at.replace("Z", "+00:00")).date()
    age_days = max(1, (today - created).days)
    estimate = round(current_stars * 7 / max(7, age_days))
    return Growth(max(0, estimate), False, 0)


def rank_repositories(
    candidates: list[dict[str, Any]],
    state: dict[str, Any],
    limit: int,
    today: date | None = None,
) -> list[dict[str, Any]]:
    today = today or date.today()
    ranked: list[dict[str, Any]] = []
    for repo in candidates:
        relevance = relevance_score(repo)
        if relevance < 4:
            continue
        growth = calculate_growth(
            repo["full_name"],
            int(repo.get("stargazers_count", 0)),
            repo["created_at"],
            state["snapshots"],
            today,
        )
        # Growth dominates. Relevance breaks close ties without overpowering momentum.
        score = math.log1p(growth.value) * 100 + relevance
        ranked.append(
            {
                "full_name": repo["full_name"],
                "html_url": repo["html_url"],
                "description": repo.get("description") or "暂无简介",
                "language": repo.get("language") or "Unknown",
                "stars": int(repo.get("stargazers_count", 0)),
                "forks": int(repo.get("forks_count", 0)),
                "created_at": repo["created_at"],
                "updated_at": repo["updated_at"],
                "topics": repo.get("topics") or [],
                "weekly_growth": growth.value,
                "growth_exact": growth.exact,
                "observed_days": growth.observed_days,
                "relevance": relevance,
                "score": round(score, 3),
            }
        )
    ranked.sort(key=lambda item: (item["score"], item["stars"]), reverse=True)
    return ranked[:limit]


def update_state(
    state: dict[str, Any], candidates: list[dict[str, Any]], today: date
) -> dict[str, Any]:
    snapshots = [item for item in state["snapshots"] if item.get("date") != today.isoformat()]
    snapshots.append(
        {
            "date": today.isoformat(),
            "stars": {repo["full_name"]: int(repo.get("stargazers_count", 0)) for repo in candidates},
        }
    )
    oldest = today - timedelta(days=SNAPSHOT_RETENTION_DAYS)
    snapshots = [item for item in snapshots if date.fromisoformat(item["date"]) >= oldest]
    snapshots.sort(key=lambda item: item["date"])
    return {"version": STATE_VERSION, "snapshots": snapshots}


def main() -> int:
    args = parse_args()
    if args.limit < 1 or args.limit > 20:
        raise SystemExit("--limit must be between 1 and 20")
    today = date.today()
    state = load_state(args.state)
    candidates = collect_candidates(args.token, args.lookback_days)
    if not candidates:
        raise RuntimeError("GitHub search returned no candidate repositories")
    repositories = rank_repositories(candidates, state, args.limit, today)
    if len(repositories) < args.limit:
        raise RuntimeError(f"Only {len(repositories)} relevant repositories were found")

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date": today.isoformat(),
        "ranking_basis": "7-day star growth; estimates are used until enough snapshots exist",
        "repositories": repositories,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.state.parent.mkdir(parents=True, exist_ok=True)
    args.state.write_text(
        json.dumps(update_state(state, candidates, today), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Selected {len(repositories)} repositories from {len(candidates)} candidates")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # concise error for Actions logs
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


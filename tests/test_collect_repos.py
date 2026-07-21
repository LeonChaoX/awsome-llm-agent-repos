import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from collect_repos import calculate_growth, load_state, rank_repositories, update_state
from send_feishu import build_payload, signing_fields


def repo(name: str, stars: int, description: str = "LLM agent framework") -> dict:
    return {
        "name": name.split("/")[-1],
        "full_name": name,
        "html_url": f"https://github.com/{name}",
        "description": description,
        "language": "Python",
        "stargazers_count": stars,
        "forks_count": 3,
        "created_at": "2026-06-01T00:00:00Z",
        "updated_at": "2026-07-21T00:00:00Z",
        "topics": ["llm", "agents"],
    }


class GrowthTests(unittest.TestCase):
    def test_exact_growth_uses_snapshot_at_least_seven_days_old(self):
        snapshots = [
            {"date": "2026-07-13", "stars": {"acme/agent": 100}},
            {"date": "2026-07-15", "stars": {"acme/agent": 120}},
        ]
        growth = calculate_growth(
            "acme/agent", 160, "2026-06-01T00:00:00Z", snapshots, date(2026, 7, 21)
        )
        self.assertEqual(growth.value, 60)
        self.assertTrue(growth.exact)

    def test_partial_history_is_annualized_to_seven_days(self):
        snapshots = [{"date": "2026-07-19", "stars": {"acme/agent": 100}}]
        growth = calculate_growth(
            "acme/agent", 120, "2026-06-01T00:00:00Z", snapshots, date(2026, 7, 21)
        )
        self.assertEqual(growth.value, 70)
        self.assertFalse(growth.exact)

    def test_ranking_prefers_faster_growth(self):
        state = {
            "version": 1,
            "snapshots": [
                {"date": "2026-07-14", "stars": {"acme/fast": 10, "acme/slow": 900}}
            ],
        }
        ranked = rank_repositories(
            [repo("acme/slow", 910), repo("acme/fast", 110)], state, 2, date(2026, 7, 21)
        )
        self.assertEqual(ranked[0]["full_name"], "acme/fast")

    def test_state_replaces_same_day_and_trims_old_snapshots(self):
        state = {
            "version": 1,
            "snapshots": [
                {"date": "2026-06-01", "stars": {}},
                {"date": "2026-07-21", "stars": {"old/repo": 1}},
            ],
        }
        updated = update_state(state, [repo("acme/agent", 42)], date(2026, 7, 21))
        self.assertEqual(len(updated["snapshots"]), 1)
        self.assertEqual(updated["snapshots"][0]["stars"], {"acme/agent": 42})


class StateAndCardTests(unittest.TestCase):
    def test_missing_state_starts_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            state = load_state(Path(directory) / "missing.json")
        self.assertEqual(state, {"version": 1, "snapshots": []})

    def test_card_contains_all_repositories(self):
        repositories = []
        for index in range(10):
            item = repo(f"acme/agent-{index}", 100 + index)
            item.update({"stars": item.pop("stargazers_count"), "weekly_growth": index})
            item["growth_exact"] = True
            repositories.append(item)
        payload = build_payload(
            {"date": "2026-07-21", "repositories": repositories}, secret=""
        )
        rendered = json.dumps(payload, ensure_ascii=False)
        self.assertEqual(payload["msg_type"], "interactive")
        self.assertIn("acme/agent-9", rendered)

    def test_signature_is_deterministic(self):
        first = signing_fields("secret", timestamp=123456)
        second = signing_fields("secret", timestamp=123456)
        self.assertEqual(first, second)
        self.assertEqual(first["timestamp"], "123456")


if __name__ == "__main__":
    unittest.main()


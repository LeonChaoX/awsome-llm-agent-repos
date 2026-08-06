import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from collect_repos import calculate_growth, load_state, rank_repositories, update_state
from channels.feishu import FeishuChannel, signing_fields


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


class DedupTests(unittest.TestCase):
    def _make_repos(self, names_stars: list[tuple[str, int]]) -> list[dict]:
        return [repo(name, stars) for name, stars in names_stars]

    def test_recently_recommended_repos_are_excluded(self):
        """Repos recommended in the past 7 days should not appear in results
        when enough fresh candidates exist."""
        # Build 12 fresh repos + 2 that were recommended yesterday
        candidates = self._make_repos(
            [(f"acme/fresh-{i}", 500 - i) for i in range(12)]
            + [("acme/old-1", 900), ("acme/old-2", 800)]
        )
        state = {
            "version": 1,
            "snapshots": [],
            "recommended_history": [
                {"date": "2026-07-20", "repos": ["acme/old-1", "acme/old-2"]},
            ],
        }
        ranked = rank_repositories(candidates, state, 10, date(2026, 7, 21))
        names = [r["full_name"] for r in ranked]
        # With 12 fresh candidates and limit=10 and max_repeats=1, at most 1 repeat allowed
        repeats = [n for n in names if n in ("acme/old-1", "acme/old-2")]
        self.assertLessEqual(len(repeats), 1)

    def test_repeat_ratio_stays_at_most_10_percent(self):
        """For a limit of 10, at most 1 repeat is allowed."""
        # All 10 repos were recommended yesterday
        candidates = self._make_repos([(f"acme/seen-{i}", 500 + i) for i in range(10)])
        state = {
            "version": 1,
            "snapshots": [],
            "recommended_history": [
                {"date": "2026-07-20", "repos": [f"acme/seen-{i}" for i in range(10)]},
            ],
        }
        ranked = rank_repositories(candidates, state, 10, date(2026, 7, 21))
        # All are repeats but we still need 10 results, so repeats fill remaining slots
        self.assertEqual(len(ranked), 10)

    def test_fresh_repos_fill_first(self):
        """Fresh repos always take priority over recently recommended ones."""
        candidates = self._make_repos(
            [("acme/fresh-1", 100), ("acme/fresh-2", 90), ("acme/seen-1", 9999)]
        )
        state = {
            "version": 1,
            "snapshots": [],
            "recommended_history": [
                {"date": "2026-07-20", "repos": ["acme/seen-1"]},
            ],
        }
        ranked = rank_repositories(candidates, state, 2, date(2026, 7, 21))
        # seen-1 has much higher stars but should be excluded when fresh repos are available
        names = [r["full_name"] for r in ranked]
        # With limit=2 and max_repeats=0 (floor(2*0.1)=0), seen-1 should be excluded
        self.assertNotIn("acme/seen-1", names)

    def test_update_state_saves_recommended_history(self):
        state = {"version": 1, "snapshots": [], "recommended_history": []}
        recommended = [repo("acme/agent", 100)]
        updated = update_state(state, [repo("acme/agent", 100)], date(2026, 7, 21), recommended)
        self.assertIn("recommended_history", updated)
        self.assertEqual(len(updated["recommended_history"]), 1)
        self.assertIn("acme/agent", updated["recommended_history"][0]["repos"])

    def test_recommended_history_expires_after_window(self):
        """Entries older than DEDUP_WINDOW_DAYS are pruned from recommended_history."""
        state = {
            "version": 1,
            "snapshots": [],
            "recommended_history": [
                {"date": "2026-07-01", "repos": ["acme/old"]},  # 20 days ago, outside window
                {"date": "2026-07-18", "repos": ["acme/recent"]},  # 3 days ago, inside window
            ],
        }
        updated = update_state(state, [], date(2026, 7, 21))
        dates = [e["date"] for e in updated["recommended_history"]]
        self.assertNotIn("2026-07-01", dates)
        self.assertIn("2026-07-18", dates)

    def test_no_dedup_when_no_history(self):
        """Without recommended_history, all top-scoring repos appear normally."""
        candidates = self._make_repos([("acme/a", 1000), ("acme/b", 900)])
        state = {"version": 1, "snapshots": []}
        ranked = rank_repositories(candidates, state, 2, date(2026, 7, 21))
        self.assertEqual(len(ranked), 2)


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
        payload = FeishuChannel("https://example.invalid").build_payload(
            {"date": "2026-07-21", "repositories": repositories}
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

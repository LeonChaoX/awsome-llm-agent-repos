import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from channels import CHANNELS, NotificationError
from channels.discord import DiscordChannel
from channels.feishu import FeishuChannel
from channels.generic import GenericWebhookChannel
from channels.slack import SlackChannel
from channels.telegram import TelegramChannel
from channels.wecom import WeComChannel
from notify import configured_channels


def report() -> dict:
    repositories = []
    for index in range(10):
        repositories.append(
            {
                "full_name": f"acme/agent-{index}",
                "html_url": f"https://github.com/acme/agent-{index}",
                "description": "A focused LLM agent framework for production workflows.",
                "language": "Python",
                "stars": 1000 + index,
                "weekly_growth": 100 + index,
                "growth_exact": index % 2 == 0,
            }
        )
    return {"date": "2026-07-21", "repositories": repositories}


class PayloadTests(unittest.TestCase):
    def test_every_builtin_channel_renders_all_ten_repositories(self):
        channels = [
            FeishuChannel("https://example.invalid"),
            SlackChannel("https://example.invalid"),
            TelegramChannel("token", "chat"),
            WeComChannel("https://example.invalid"),
            DiscordChannel("https://example.invalid"),
            GenericWebhookChannel("https://example.invalid"),
        ]
        for channel in channels:
            with self.subTest(channel=channel.name):
                rendered = json.dumps(channel.build_payload(report()), ensure_ascii=False)
                self.assertIn("acme/agent-0", rendered)
                self.assertIn("acme/agent-9", rendered)

    def test_discord_uses_the_supported_embed_limit(self):
        payload = DiscordChannel("https://example.invalid").build_payload(report())
        self.assertEqual(len(payload["embeds"]), 10)
        self.assertEqual(payload["allowed_mentions"], {"parse": []})

    def test_telegram_uses_html_and_disables_link_previews(self):
        payload = TelegramChannel("token", "chat").build_payload(report())
        self.assertEqual(payload["parse_mode"], "HTML")
        self.assertTrue(payload["disable_web_page_preview"])

    def test_generic_webhook_has_a_versioned_envelope(self):
        payload = GenericWebhookChannel("https://example.invalid").build_payload(report())
        self.assertEqual(payload["event"], "agent_radar.daily_digest")
        self.assertEqual(payload["schema_version"], 1)

    def test_untrusted_descriptions_cannot_inject_chat_mentions(self):
        unsafe = report()
        unsafe["repositories"][0]["description"] = "Release <!channel> <@all> [spoof](url)"
        for channel in (SlackChannel("x"), WeComChannel("x"), FeishuChannel("x")):
            rendered = json.dumps(channel.build_payload(unsafe), ensure_ascii=False)
            self.assertNotIn("<!channel>", rendered)
            self.assertNotIn("<@all>", rendered)

    def test_platform_payload_limits_have_headroom(self):
        sample = report()
        telegram = TelegramChannel("token", "chat").build_payload(sample)
        wecom = WeComChannel("x").build_payload(sample)
        feishu = FeishuChannel("x").build_payload(sample)
        slack = SlackChannel("x").build_payload(sample)
        self.assertLess(len(telegram["text"]), 4096)
        self.assertLess(len(wecom["markdown"]["content"]), 4096)
        self.assertLess(len(json.dumps(feishu, ensure_ascii=False).encode("utf-8")), 20_000)
        self.assertLess(len(slack["blocks"]), 50)


class ConfigurationTests(unittest.TestCase):
    def test_empty_environment_configures_no_channels(self):
        self.assertEqual(configured_channels({}), [])

    def test_multiple_channels_are_auto_discovered(self):
        channels = configured_channels(
            {
                "FEISHU_WEBHOOK_URL": "https://example.invalid/feishu",
                "SLACK_WEBHOOK_URL": "https://example.invalid/slack",
            }
        )
        self.assertEqual([channel.name for channel in channels], ["feishu", "slack"])

    def test_partial_telegram_configuration_fails_clearly(self):
        with self.assertRaisesRegex(NotificationError, "TELEGRAM_CHAT_ID"):
            configured_channels({"TELEGRAM_BOT_TOKEN": "secret"})

    def test_registry_names_are_stable(self):
        self.assertEqual(
            set(CHANNELS), {"feishu", "slack", "telegram", "wecom", "discord", "generic"}
        )


if __name__ == "__main__":
    unittest.main()

# Notification channel guide

_Provider-specific setup for Agent Radar forks._

---

## 🔐 Store credentials safely

Create credentials in the destination platform, then store them under `Settings → Secrets and variables → Actions → New repository secret`. GitHub encrypts Actions Secrets and makes them available to the workflow when a run is queued.[^1]

Never paste a webhook or bot token into an issue, pull request, workflow file, screenshot, or chat. If one is exposed, rotate it immediately.

You may configure several providers. `scripts/notify.py` detects complete configurations and delivers to every configured channel; a partially configured provider fails with the missing Secret name.

## 📨 Feishu

1. Open the target group
2. Select `Settings → Bots → Add bot → Custom bot`
3. Copy the V2 webhook URL
4. Add it as `FEISHU_WEBHOOK_URL`
5. If signature verification is enabled, add its key as `FEISHU_SIGNING_SECRET`

Agent Radar sends an interactive card. Feishu recommends treating the webhook as a secret and supports keyword, IP allowlist, and signature security controls.[^2]

```text
FEISHU_WEBHOOK_URL       required
FEISHU_SIGNING_SECRET    optional
```

## 💬 Slack

1. Create or select a Slack app
2. Enable **Incoming Webhooks**
3. Add a webhook to the destination channel
4. Save the URL as `SLACK_WEBHOOK_URL`

The message uses Slack blocks with a plain-text fallback. Slack documents that an incoming webhook URL is specific to a workspace channel and must be kept secret.[^3]

```text
SLACK_WEBHOOK_URL        required
```

## ✈️ Telegram

1. Message `@BotFather` and create a bot with `/newbot`
2. Save the returned token as `TELEGRAM_BOT_TOKEN`
3. Add the bot to a group or start a direct conversation
4. Send one message to that conversation
5. Use the Bot API `getUpdates` method locally to find the numeric chat ID
6. Save that value as `TELEGRAM_CHAT_ID`

Agent Radar uses the official HTTP Bot API and `sendMessage` with HTML formatting.[^4]

```text
TELEGRAM_BOT_TOKEN       required
TELEGRAM_CHAT_ID         required
```

> 📌 **Group chats:** Telegram group IDs are commonly negative numbers. Preserve the minus sign when saving the Secret.

## 🏢 WeCom

Personal WeChat does not provide a general-purpose incoming group webhook. This provider targets **WeCom / Enterprise WeChat** group robots.

1. Open a WeCom group
2. Select `Group settings → Group robot → Add robot`
3. Copy the webhook URL
4. Save it as `WECOM_WEBHOOK_URL`

The provider sends a compact markdown digest to stay within group-robot message limits. See the [WeCom group robot documentation][wecom-docs] for account-specific availability.

```text
WECOM_WEBHOOK_URL        required
```

## 🎮 Discord

1. Open `Server Settings → Integrations → Webhooks`
2. Create a webhook and choose a destination channel
3. Copy the URL
4. Save it as `DISCORD_WEBHOOK_URL`

Agent Radar sends one rich embed per repository and disables all mention parsing. Discord documents webhook execution and payload fields in its developer reference.[^5]

```text
DISCORD_WEBHOOK_URL      required
```

## 🔌 Generic webhook

Set `GENERIC_WEBHOOK_URL` to any HTTPS endpoint that accepts JSON. Agent Radar posts the complete report in a stable, versioned envelope:

```json
{
  "event": "agent_radar.daily_digest",
  "schema_version": 1,
  "data": {
    "date": "2026-07-21",
    "repositories": []
  }
}
```

Return any `2xx` status to acknowledge delivery. This adapter works well with n8n, Zapier, Make, serverless functions, and private notification gateways.

```text
GENERIC_WEBHOOK_URL      required
```

## 🧪 Verify delivery

Run `Actions → Agent Radar Daily → Run workflow`. The **Deliver to configured channels** step logs only provider names and success states; credential-bearing URLs are never logged.

For local payload inspection without network requests:

```bash
python scripts/notify.py output/repos.json --dry-run
python scripts/notify.py output/repos.json --dry-run --channel telegram
```

## 🧯 Troubleshoot

| Symptom | Likely cause | Resolution |
| ------- | ------------ | ---------- |
| No provider detected | Secret name differs | Copy the exact uppercase name from this guide |
| Telegram partial-config error | Token or chat ID missing | Add both required Secrets |
| Feishu rejects message | Signature or security policy mismatch | Check signing Secret, keyword policy, and IP allowlist |
| Slack returns an error | Webhook revoked or wrong workspace | Rotate the incoming webhook |
| WeCom rejects markdown | Robot removed or webhook rotated | Create a new group robot URL |
| One channel fails | Provider-specific request rejected | Other channels are still attempted; inspect the named failure |

## 🔗 References

[^1]: GitHub. "Secrets reference." _GitHub Docs_. https://docs.github.com/en/actions/reference/security/secrets

[^2]: Feishu. "Custom bot usage guide." _Feishu Open Platform_. https://open.feishu.cn/document/ukTMukTMukTM/ucTM5YjL3ETO24yNxkjN

[^3]: Slack. "Sending messages using incoming webhooks." _Slack API_. https://api.slack.com/messaging/webhooks

[^4]: Telegram. "Telegram Bot API." https://core.telegram.org/bots/api

[^5]: Discord. "Webhook resource." _Discord Developer Documentation_. https://docs.discord.com/developers/resources/webhook

[wecom-docs]: https://developer.work.weixin.qq.com/document/path/91770 "WeCom group robot configuration"

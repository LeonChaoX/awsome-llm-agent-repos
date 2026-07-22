# Deploy Agent Radar from a fork

_A complete setup, verification, customization, and recovery guide._

---

## 🚀 Deploy

### Fork the repository

Use GitHub's [Fork page](https://github.com/LeonChaoX/awsome-llm-agent-repos/fork). Keep the default branch named `main`; scheduled workflows only run from the default branch.[^1]

### Enable GitHub Actions

Open the fork's **Actions** tab and select **I understand my workflows, go ahead and enable them**. Workflows are disabled in a new fork until its owner opts in.[^2]

### Add credentials

Open `Settings → Secrets and variables → Actions`. Add at least one provider configuration from the [channel guide](CHANNELS.md). Secrets belong in the fork, because credentials from the upstream repository are never copied into it.

### Grant workflow write access

The workflow declares `contents: write` so it can maintain the `data` branch. If your account overrides workflow permissions, open `Settings → Actions → General → Workflow permissions`, select **Read and write permissions**, and save.

### Run once manually

Open `Actions → Agent Radar Daily → Run workflow`, choose `main`, and start the run. Verify these steps:

| Step | Expected result |
| ---- | --------------- |
| Restore star snapshots | Creates an empty state on the first run |
| Collect and rank repositories | Selects the configured number of repositories |
| Deliver to configured channels | Lists each successful provider by name |
| Publish report artifact | Uploads `repos.json` for seven days |
| Save star snapshots | Creates or updates the `data` branch |

## ⚙️ Customize

### Repository count and candidate age

Add repository variables under `Settings → Secrets and variables → Actions → Variables`:

| Name | Default | Validation |
| ---- | ------: | ---------- |
| `REPOSITORY_LIMIT` | `10` | Integer from `1` to `20` |
| `LOOKBACK_DAYS` | `180` | Positive integer |

### Delivery schedule

GitHub cron expressions use UTC. Edit `.github/workflows/daily-radar.yml`:

```yaml
on:
  schedule:
    - cron: "0 2 * * *" # 10:00 Asia/Shanghai
```

Scheduled workflows may be delayed during periods of high Actions load.[^3] If exact-to-the-minute delivery matters, GitHub-hosted cron is not a hard real-time scheduler.

### Multiple channels

Add every desired provider Secret. No list or feature flag is needed—the notifier discovers complete configurations. Removing a provider's Secret disables only that provider.

## 🔎 Observe

Every run produces:

- Step-level logs without credential values
- A downloadable `agent-radar-<run number>` report artifact
- A `data` branch commit containing `stars.json`
- A message in every configured destination

The `data` branch is operational state. Do not merge it into `main` and do not manually rewrite the snapshot schema.

## 🧯 Recover

### No message, but the run is green

No channel was fully configured when the run started. Verify Secret names, then queue a new run; repository Secrets are read when the workflow is queued.[^4]

### Snapshot push is denied

Enable **Read and write permissions** under the repository's Actions settings. Organization policies may override a fork's setting.

### Snapshot state is corrupt

Delete only the `data` branch and run the workflow again. The ranking returns to estimated cold-start mode and rebuilds state safely. Never delete `main`.

### GitHub Search is rate-limited

The workflow automatically uses its short-lived `GITHUB_TOKEN`; users do not need to create a personal access token. Re-run later if GitHub returns a temporary rate-limit response.

### Scheduled run did not appear

Confirm that:

1. The workflow exists on the fork's default branch
2. Actions are enabled in the fork
3. The repository has not been inactive long enough for GitHub to disable scheduled workflows
4. The cron expression is valid UTC syntax

## 🔗 References

[^1]: GitHub. "Events that trigger workflows." _GitHub Docs_. https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule

[^2]: GitHub. "Workflows in forked repositories." _GitHub Docs_. https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflows-in-forked-repositories

[^3]: GitHub. "Troubleshooting workflows." _GitHub Docs_. https://docs.github.com/en/actions/how-tos/troubleshoot-workflows#delayed-scheduled-workflows

[^4]: GitHub. "Secrets reference." _GitHub Docs_. https://docs.github.com/en/actions/reference/security/secrets#when-github-actions-reads-secrets

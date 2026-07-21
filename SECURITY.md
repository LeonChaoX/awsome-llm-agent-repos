# Security policy

_How to report vulnerabilities and protect notification credentials._

---

## 🛡️ Supported version

Security fixes are applied to the latest commit on `main`. Fork owners should sync upstream regularly because webhook handling and workflow permissions can change over time.

## 🚨 Report a vulnerability

Do not disclose a vulnerability, real webhook, bot token, chat ID, or exploit path in a public issue.

Use the repository's **Security → Report a vulnerability** flow. Include:

- A concise impact statement
- Reproduction steps with fake credentials
- Affected files and commit
- Suggested mitigation, if known

If private reporting is unavailable, open a minimal issue asking the maintainer to establish a private channel. Do not include sensitive details in that issue.

## 🔐 Credential exposure

If a credential appears in a commit, log, issue, screenshot, or chat:

1. Rotate or revoke it at the provider immediately
2. Replace the GitHub Actions Secret with the new value
3. Re-run the workflow to verify delivery
4. Report the exposure privately if project code or logs contributed to it

Deleting a message or rewriting Git history is not a substitute for rotation because copies and caches may remain.

## 📦 Security model

- Provider credentials exist only as GitHub Actions Secrets and step environment variables
- Notification errors omit credential-bearing URLs
- CI for pull requests does not reference delivery Secrets
- The `data` branch stores only public repository names and Star counts
- The generic webhook contains only the public report artifact

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for trust boundaries and failure behavior.

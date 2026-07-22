# Contributing to Agent Radar

_A lightweight path from idea to a safe, tested pull request._

---

## 🤝 Ways to contribute

- Add a notification provider
- Improve repository discovery or ranking
- Add tests for platform edge cases
- Improve English or Chinese documentation
- Report false-positive repositories with evidence
- Simplify the Fork onboarding experience

Use the relevant issue template before large changes so maintainers and contributors can align on scope.

## 🛠️ Development setup

Agent Radar requires Python `3.10+` and has no third-party dependencies.

```bash
git clone https://github.com/<your-account>/awsome-llm-agent-repos.git
cd awsome-llm-agent-repos
git remote add upstream https://github.com/LeonChaoX/awsome-llm-agent-repos.git
python -m unittest discover -s tests -v
```

Create a focused branch:

```bash
git checkout -b feature/short-description
```

## ✅ Quality bar

Every pull request must:

- Keep runtime dependencies at zero unless an approved design issue says otherwise
- Preserve the distinction between estimated and measured growth
- Keep webhook URLs and tokens out of code, fixtures, logs, and errors
- Include deterministic tests for behavior changes
- Update user-facing documentation with code changes
- Pass Python `3.10`, `3.11`, `3.12`, and `3.13` CI

Run before committing:

```bash
python -m compileall -q scripts tests
python -m unittest discover -s tests -v
git diff --check
```

## 🧩 Provider contributions

Follow [docs/ADDING_A_CHANNEL.md](docs/ADDING_A_CHANNEL.md). New providers need official platform documentation, payload tests, safe error handling, workflow Secret mapping, and setup instructions.

## 📝 Pull requests

Keep a pull request limited to one coherent change. Its description should cover:

- The problem and intended user
- The implementation and key trade-offs
- Tests and manual verification
- Documentation changes
- Any credential or workflow-permission impact

Do not include real tokens, webhook URLs, private chat IDs, or production payloads. Maintainers may close a pull request containing exposed credentials to limit further propagation.

## 🧭 Project principles

When trade-offs are unclear, prefer:

1. Honest metrics over impressive-looking numbers
2. Fork simplicity over infrastructure complexity
3. Standard-library code over dependency weight
4. Explicit failure over silent message loss
5. Official APIs over scraping platform clients

Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).

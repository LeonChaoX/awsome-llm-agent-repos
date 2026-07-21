# Add a notification channel

_A focused contributor guide for extending Agent Radar's delivery layer._

---

## 🎯 Provider contract

Every provider subclasses `Channel` and implements three operations:

1. Load credentials from an environment mapping
2. Build a platform-specific JSON payload from the report
3. Send the payload and validate the platform response

The shared `post_json` function provides a timeout and prevents credential-bearing URLs from appearing in exceptions.

## 🛠️ Implement

Create `scripts/channels/example.py`:

```python
from dataclasses import dataclass
from typing import Any, Mapping

from .base import Channel, NotificationError, post_json


@dataclass(frozen=True)
class ExampleChannel(Channel):
    webhook: str

    name = "example"
    required_secrets = ("EXAMPLE_WEBHOOK_URL",)

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "ExampleChannel":
        return cls(env.get("EXAMPLE_WEBHOOK_URL", ""))

    def build_payload(self, report: dict[str, Any]) -> dict[str, Any]:
        return {"text": f"Agent Radar · {report['date']}"}

    def send(self, report: dict[str, Any]) -> None:
        response = post_json("Example", self.webhook, self.build_payload(report))
        if not 200 <= response.status < 300:
            raise NotificationError("Example rejected the message")
```

Register the class in `scripts/channels/__init__.py`, then map its Secret in the **Deliver to configured channels** workflow step.

## 🧪 Test

Add payload coverage to `tests/test_channels.py`. Tests must verify:

- All ten repositories render
- Credentials are absent from serialized payloads
- Platform limits are respected
- Partial multi-Secret configurations fail with the missing name
- Response validation rejects platform-level errors

Run the full suite:

```bash
python -m compileall -q scripts tests
python -m unittest discover -s tests -v
python scripts/notify.py output/repos.json --dry-run --channel example
```

Never make a live provider request in unit tests.

## 📝 Document

Update these surfaces in the same pull request:

- Provider table in `README.md`
- Provider table in `README.zh-CN.md`
- Setup steps in `docs/CHANNELS.md`
- Secret mapping in `.github/workflows/daily-radar.yml`
- Channel count badge if the provider is built in

Link to the platform's official webhook documentation and state whether the URL or token is sensitive.

## ✅ Review checklist

- [ ] Uses only the Python standard library
- [ ] Keeps URLs and tokens out of errors and logs
- [ ] Escapes platform-specific markup
- [ ] Fits documented message-size and block limits
- [ ] Disables mentions or previews when appropriate
- [ ] Validates both HTTP and platform response status
- [ ] Adds deterministic payload tests
- [ ] Updates English and Chinese discovery docs

Read [CONTRIBUTING.md](../CONTRIBUTING.md) before opening the pull request.

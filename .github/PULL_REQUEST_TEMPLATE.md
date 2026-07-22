# Pull request

_Describe a focused, tested, and credential-safe contribution._

---

## What changed

<!-- Explain the user-visible outcome and key implementation choices. -->

## Why

<!-- Link the issue and describe the problem this solves. -->

## Verification

- [ ] `python -m compileall -q scripts tests`
- [ ] `python -m unittest discover -s tests -v`
- [ ] Payload dry-run completed when notification code changed
- [ ] No real credential or private identifier appears in the diff or logs

## Documentation

- [ ] English user documentation updated
- [ ] Chinese user documentation updated when onboarding changed
- [ ] No documentation change is required

## Risk

<!-- Note ranking, state-schema, workflow-permission, or credential-handling impact. -->

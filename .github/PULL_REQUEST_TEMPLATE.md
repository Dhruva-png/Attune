## Summary

<!-- What does this change, and why? Link an issue if there is one. -->

## Which layer(s) does this touch?

<!-- Helps reviewers reason about the architecture rules in CONTRIBUTING.md -->

- [ ] `core` (domain — should have zero new third-party deps)
- [ ] `vision` / `behaviour` / `analytics`
- [ ] `database` / `llm` / `reports`
- [ ] `api` / `dashboard`
- [ ] `demo` / `scripts` / docs only

## Checklist

- [ ] `ruff check attune tests` passes
- [ ] `mypy attune` passes
- [ ] `lint-imports` passes (architectural layering contracts)
- [ ] `pytest` passes
- [ ] `pytest -m "performance or integration" --no-cov` passes
- [ ] If an API endpoint changed: `docs/architecture/openapi.snapshot.json` regenerated (see
      [CONTRIBUTING.md](../CONTRIBUTING.md#writing-tests))
- [ ] Relevant doc in `docs/architecture/` updated in this PR, not a follow-up

## Test plan

<!-- How did you verify this works? New tests added, manual QA steps, screenshots, etc. -->

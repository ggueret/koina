# Changelog

All notable changes to koina are documented here.
## [0.1.0] - 2026-06-11

### Features

- Provider-neutral agentic toolset

### Bug Fixes

- *(grep)* Treat pattern as literal, not rg flags
- *(ci)* Drop redundant zizmor SARIF upload step
- *(read)* Bound read, reject non-regular files
- *(bash)* Cap output memory, keep stderr
- *(grep)* Return paths relative to the search dir

### Refactor

- Tighten the public API ahead of 0.1.0

### Documentation

- Add brand assets and wordmark
- Make the wordmark the README h1
- Soften the observability "zero cost" claim

### Styling

- Format with ruff

### Testing

- Add coverage via pytest-cov

### Miscellaneous Tasks

- Add MIT LICENSE and packaging metadata
- Route ruff/mypy/pytest caches to .cache/
- Set Development Status to Beta
- Add lint, typecheck and test workflow
- Add repo baseline config
- *(deps)* Bump codecov-action to v7.0.0
- Add scorecard and zizmor supply-chain audits
- Drop persisted credentials in checkout steps
- Explicit ruff lint and examples as a dep-group
- Add a build gate and macOS to the test matrix
- Add the OIDC release pipeline
- Add a Dependabot cooldown for action updates
- Align the release workflow with the project convention
- Point the Changelog URL to GitHub Releases

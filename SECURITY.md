# Security policy

## Reporting a vulnerability

Please do not disclose suspected vulnerabilities in a public issue. Use a [private GitHub security advisory](https://github.com/sudoHG/codex-grok-search/security/advisories/new) and include the affected version, operating system, Grok Build version, reproduction steps, and potential impact.

Do not include Grok authentication files, tokens, private search queries, retained result artifacts, or repository contents in a report. Replace sensitive values with minimal synthetic examples.

## Supported versions

Security fixes are applied to the latest published release. The Skill does not use the Grok Build version string as a security boundary; it validates the actual isolated runtime configuration and fails closed when execution surfaces or the inspect schema drift.

## Security boundary

This project isolates Grok from the user's current repository and limits the tools exposed during research. Queries, search results, and public pages still pass through xAI services. See [Privacy isolation and security boundaries](README.md#privacy-isolation-and-security-boundaries) for the complete threat model and limitations.

# Bridge and isolation reference

## First principle

The wrapper has two product responsibilities:

1. Run the user's request through Grok Build.
2. Keep Grok outside the user's current project and preserve its complete answer.

It does not judge research quality. Platform matching, URL scheme, dates, fields, Markdown shape, source mix, and Grok's conclusions are not local pass/fail gates.

## Isolation

Each run uses a private directory under `~/.cache/codex-grok-search/runs/`, outside the current repository, as Grok's `--cwd`. The wrapper writes only the request, raw CLI output, diagnostics, manifest, and final Grok answer there.

Grok receives a temporary `HOME`, `GROK_HOME`, and `TMPDIR`. Only the user's Grok authentication file and a minimal configuration disabling Cursor, Claude, and Codex compatibility imports are copied into that temporary home. The user's project, project `AGENTS.md`, MCP configuration, unrelated environment variables, and API keys are not passed to Grok.

The wrapper does not run `grok models`, `grok inspect`, a CLI version gate, a closed-schema check, or local Reddit page verification before returning an answer. These checks previously caused successful searches to be discarded.

## Output

The formal Grok call requests a JSON CLI envelope only so the wrapper can extract its `text` field. The text itself is free-form and is saved verbatim to `result.md`. If stdout is not a JSON envelope, non-empty stdout is saved directly.

If Grok exits non-zero after producing usable text, that text is returned with `status: partial`. Only a run with no usable answer is reported as failed.

An exact-session export is attempted only when the formal call returns no text. It exists to recover a completed Grok answer, not to validate or rewrite it.

## Authentication

The wrapper starts the actual search without a separate authentication preflight. This avoids false “not logged in” failures and extra latency. If the real search returns no answer and explicitly reports an authentication error, the wrapper returns `grok_not_authenticated`.

The temporary authentication copy is written back only when it remains valid JSON, allowing normal token refreshes to persist without exposing the user's project.

## Retention

Runs are retained for seven days by default and cleaned only at the start of a later invocation or by the explicit `cleanup` command. `--keep-run` prevents automatic cleanup. There is no maximum-run capacity gate.

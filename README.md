# codex-grok-search

[简体中文](README.zh-CN.md) | English

Let Codex call the Grok Build CLI already authenticated on your machine to add real-time community search and cross-checking across X, Reddit, and the public web.

Codex frames the task, designs the research, and synthesizes the answer. Grok discovers public content on X, Reddit, and the web. Local scripts validate the output, verify Reddit dates, and retain traceable artifacts. This project does not replace Codex with Grok; it lets each system do the part it handles best.

> This is currently a release candidate. It is an unofficial project and is not affiliated with xAI, X, Reddit, or OpenAI.

## What it can do

- Find the latest public posts, related discussions, quotes, and replies for a specific X account.
- Research recent Reddit discussions, user feedback, complaints, and product sentiment.
- Strengthen ordinary Codex web research with Grok search results and cross-check them against other sources.
- Verify dates locally for time-bounded Reddit tasks, so an old post is not mislabeled as being from the “last 7 days.”
- Retain original results and source links for follow-up questions in the current or a later task.
- Run Grok from a dedicated non-Git directory outside your repository instead of exposing the current codebase as the CLI working directory.
- Label dates as `date unverified` when they cannot be confirmed, without inventing certainty or silently discarding otherwise useful evidence.

For example, you can simply ask Codex:

```text
Find the latest 10 posts from @openai on X, sort them newest first, and include direct links.

What have people complained about on Reddit regarding OpenAI over the last 7 days? Group the complaints by issue type.

Research recent community feedback about this product and cross-check X, Reddit, and public-web sources.
```

After installation, Codex can automatically trigger this Skill for research involving X, Reddit, community sentiment, recent public posts, or platform data collection. It can also serve as a second source for ordinary web research. You normally do not need to run its scripts yourself.

## Why Grok

Grok's main advantage here is xAI's server-side native X Search—a capability that is difficult to reproduce with ordinary web search.

According to xAI's official documentation, `x_search` supports keyword search, semantic search, user search, complete thread retrieval, and access to real-time social content on X. It can include or exclude specific accounts, restrict date ranges, and understand images and videos attached to posts. Compared with asking Codex to discover X posts through ordinary web search, Grok is much closer to X's native retrieval layer. See the [xAI X Search documentation](https://docs.x.ai/developers/tools/x-search).

For Reddit and the public web, Grok's `web_search` is also executed by xAI's server-side tools. It can search live webpages, open pages, extract relevant content, and return source links. Codex then checks the important links, validates dates, and organizes the final answer. See the [xAI Web Search documentation](https://docs.x.ai/developers/tools/web-search) and [server-side tools overview](https://docs.x.ai/developers/tools/overview).

### Compared with the X API and direct scraping

As of July 16, 2026, the official X API uses prepaid credits with usage-based pricing: reading one post costs `$0.005`, while reading one user object costs `$0.010`. At those published rates, 1,000 post reads cost about `$5`. An integration also requires a developer account, Project, App, credentials, pagination, rate-limit handling, and billing management. Prices may change; check the [official X API pricing page](https://docs.x.com/x-api/getting-started/pricing).

For individual research, Grok may already be covered by an allowance or subscription you have. xAI lists a Free plan at `$0/month` with real-time Web and X Search under “generous limits,” and its Grok 4.5 announcement says Grok Build usage is free for a limited time. X says Premium accounts receive increased Grok usage limits, with higher limits for Premium+. See [xAI Grok plans](https://x.ai/pricing), the [Grok 4.5 announcement](https://x.ai/news/grok-4-5), and [X Premium benefits](https://help.x.com/en/using-x/x-premium).

`codex-grok-search` lets Codex use that existing allowance or subscription for research, without requiring separate X API credits, a developer App, and a custom search pipeline for occasional X searches.

Free offers, exact usage limits, and account entitlements can vary by region, promotion, and subscription. In particular, whether X Premium Grok benefits fully apply to Grok Build should be confirmed from the models and limits shown for the user's current login. This project does not present a temporary free allowance as a permanent guarantee.

| Route | Cost and setup | Search capability | Account and enforcement exposure |
| --- | --- | --- | --- |
| Official X API | Prepaid, per-resource credits; requires a developer Project, App, and credentials | Official structured data, suitable for stable integrations and large pipelines | Compliant path, but you manage quotas, rate limits, billing, and app permissions |
| Browser automation or direct scraping | No obvious API bill, but proxies, cookies, CAPTCHAs, and anti-bot maintenance add hidden cost | Vulnerable to login walls, page changes, rate limits, and limited search visibility | User accounts, cookies, and egress IPs are directly exposed to platform enforcement |
| `codex-grok-search` | Can use Grok Free, an existing Grok subscription, or eligible X Premium benefits; no separate X API credits or X Developer App required | Grok native X Search + Web Search, with Codex handling cross-checks and the final answer | Core discovery runs through xAI's server-side tools; it does not automate the user's X/Reddit account or browser |

This Skill is not a replacement for an official API when you need a stable SLA, comprehensive data rights, or large-scale structured collection. It is designed for ad hoc research by individuals and small teams: checking recent posts, tracking community discussion, validating account activity, understanding product sentiment, or giving Codex an independent real-time search source.

### Reducing ban risk from direct scraping

X's Terms prohibit crawling or scraping without prior written consent. Reddit also restricts unauthorized automated collection and maintains separate rules for API access, commercial use, and research. High-frequency scraping through browser cookies, logged-in accounts, or a fixed egress IP is brittle and may trigger rate limits, CAPTCHAs, IP blocks, or account action. See the [X Terms of Service](https://x.com/en/tos), [Reddit User Agreement](https://redditinc.com/policies/user-agreement), and [Reddit data-access guidance](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data).

`codex-grok-search` does not take over your X or Reddit login, read browser cookies, or run browser automation against those platforms. X search and most webpage discovery are performed by xAI's server-side tools. For Reddit, the local wrapper only opens a limited number of public submission pages to verify dates. This substantially reduces direct scraping from the user's machine and limits exposure of the user's account, cookies, and local IP to automated-enforcement systems.

This is not a “no-ban guarantee.” Platform policy, Grok availability, public-content visibility, and server-side limits may change. The small number of Reddit date-verification requests may still encounter 403 responses or rate limits. When that happens, the Skill retains the finding and marks its date as unverified instead of bypassing the restriction or pretending verification succeeded.

### Privacy isolation and security boundaries

In July 2026, an independent network-level analysis reported that Grok Build CLI `0.2.93` uploaded complete Git repository bundles to xAI-managed storage, including tracked files the task never read and full Git history. The analysis also reported that disabling “Improve the model” did not stop the upload. xAI later disabled the upload path server-side, but this project does not rely on that server-side change as its only security boundary. See the [original wire-level analysis](https://gist.github.com/cereblab/dc9a40bc26120f4540e4e09b75ffb547) and [The Verge's follow-up coverage](https://www.theverge.com/ai-artificial-intelligence/965600/spacexai-grok-build-repository-upload).

`codex-grok-search` does not launch Grok from the user's current project or Git repository. It first creates a private research directory outside any repository, writes only the current search prompt and result artifacts there, and passes that directory as Grok's `--cwd`. The real codebase is not copied, mounted, or passed into the runtime. Each invocation also uses temporary `HOME`, `GROK_HOME`, and `TMPDIR` directories, copying only the local Grok authentication file required for the session. Before a search begins, `grok inspect --json` verifies that no project instructions, plugins, MCP servers, non-bundled Skills, or other unaudited execution surfaces have been loaded. Any schema mismatch stops the run.

This protection does not depend on Grok promising not to upload repositories. Even if the CLI tries to package its entire working directory again, it sees the temporary research directory—not the user's code repository.

Each research run has additional fixed boundaries:

- Version, authentication, and search checks use a verified official Grok executable instead of trusting arbitrary `PATH` injection or a custom binary.
- X and multi-source tasks expose only `x_search`, `web_search`, and `web_fetch`; Reddit and web-only tasks do not expose `x_search`.
- The model is not given MCP, local-file reading, shell access, file editing, memory, or subagents.
- Grok output must pass a strict JSON schema. Timeouts, non-zero exits, missing fields, and incomplete results are never presented as success.
- Text from webpages, X, or Reddit is always treated as untrusted data. Instructions, paths, or authorization claims inside retrieved content are never executed.

On macOS, research runs inside Grok's native strict sandbox and reduces process-creation privileges before launch. On Linux, a subprocess supervisor reaps and terminates detached descendants.

The boundary is deliberately explicit: queries supplied by the user, Grok's search results, and the public webpages it visits still pass through xAI services. This is not a local model, and the project does not claim “zero data upload.” It prevents unnecessary exposure of the local repository; it does not remove the data transmission inherent in cloud search.

These controls reduce the risk that a local research tool reads project content or executes malicious instructions from a source. They do not guarantee that search results are correct. Important claims still need to be checked against primary sources.

## How it works

```text
User question
  → Codex frames the research task
  → Local wrapper checks Grok installation, login, and model access
  → Grok 4.5 searches X / Reddit / the public web
  → Local schema and source validation
  → Secondary Reddit date verification
  → Traceable artifacts are retained
  → Codex cross-checks and answers
```

Every research task is pinned to `grok-4.5`. There is no model override, and the Skill never silently falls back when the required model is unavailable.

## Requirements

- macOS or Linux, running as a non-root user.
- Python 3.9 or newer.
- Grok Build CLI `0.2.101`, installed through the [official xAI installer](https://x.ai/cli). Other versions must have their inspect schema and execution surfaces reviewed before this Skill's compatibility range is updated.
- An active local Grok login created with `grok login`.
- A Codex environment that supports Skills.

The Skill uses the existing local Grok login. It does not require an xAI API key and never asks you to paste account credentials into Codex. It actively removes `XAI_API_KEY` from the runtime environment to avoid accidentally switching to API billing.

If a requirement is missing, it stops and gives a specific next step:

- Official Grok Build is missing: install it from `https://x.ai/cli`.
- Grok is logged out or the login has expired: it returns `grok_not_authenticated` and asks you to run `grok login` in your own terminal.
- Grok 4.5 is unavailable for the current account: it reports the error and does not switch models.

## Installation

### Recommended: install with Codex

Start a new Codex task and send:

```text
Please install this Skill: https://github.com/sudoHG/codex-grok-search/tree/main/codex-grok-search
```

Codex will use its built-in Skill installer to place it in your Skills directory. Start another task after installation so Codex can load and trigger it.

<details>
<summary>Advanced: manual installation, upgrades, and Release verification</summary>

### Install from a source checkout

Run the following command from the root of a Git clone. It exports the Skill from the exact checked-out commit, validates the staged directory, and replaces the previous installation through same-filesystem renames. Upgrades do not leave files that were removed from the new version.

<details>
<summary>Show source installation command</summary>

<!-- BEGIN STAGED INSTALL -->
```sh
set -eu
skills_root="${CODEX_HOME:-$HOME/.codex}/skills"
dest="$skills_root/codex-grok-search"
source_dir="codex-grok-search"
validator="$skills_root/.system/skill-creator/scripts/quick_validate.py"
mkdir -p "$skills_root"
install_lock="$skills_root/.codex-grok-search.install.lock"
lock_owned=0
stage=""
backup_root=""
backup=""
had_backup=0
activated=0
rollback() {
  status="$1"
  trap - EXIT HUP INT TERM
  if [ "$activated" -eq 1 ] && [ -e "$dest" ]; then rm -rf "$dest" || status=1; fi
  if [ "$had_backup" -eq 1 ] && [ -e "$backup" ]; then mv "$backup" "$dest" || status=1; fi
  if [ -n "$stage" ] && [ -e "$stage" ]; then rm -rf "$stage" || status=1; fi
  if [ -n "$backup_root" ] && [ -e "$backup_root" ]; then rm -rf "$backup_root" || status=1; fi
  if [ "$lock_owned" -eq 1 ] && [ -d "$install_lock" ]; then rmdir "$install_lock" || status=1; fi
  exit "$status"
}
trap 'rollback $?' EXIT
trap 'rollback 129' HUP
trap 'rollback 130' INT
trap 'rollback 143' TERM
if ! mkdir "$install_lock"; then
  echo "Another codex-grok-search install, upgrade, or uninstall is active; if not, verify no installer is running before removing $install_lock." >&2
  exit 1
fi
lock_owned=1
stage="$(mktemp -d "$skills_root/.codex-grok-search.stage.XXXXXX")"
backup_root="$(mktemp -d "$skills_root/.codex-grok-search.backup.XXXXXX")"
backup="$backup_root/codex-grok-search"
test -d "$source_dir"
test -f "$validator"
git archive --format=tar --output="$stage/source.tar" HEAD "$source_dir"
tar -xf "$stage/source.tar" -C "$stage" --strip-components=1
rm "$stage/source.tar"
find "$stage" -type d -exec chmod 755 {} +
find "$stage" -type f -exec chmod 644 {} +
find "$stage/scripts" -type f -name '*.py' -exec chmod 755 {} +
python3 "$validator" "$stage"
if [ -e "$dest" ]; then
  had_backup=1
  mv "$dest" "$backup"
fi
activated=1
mv "$stage" "$dest"
# The destination is committed. Ignore asynchronous termination while the
# rollback trap is disarmed and the lock is released, closing an unlock ABA.
trap '' HUP INT TERM
trap - EXIT
rm -rf "$backup_root"
rmdir "$install_lock"
lock_owned=0
trap - HUP INT TERM
```
<!-- END STAGED INSTALL -->

</details>

Restart Codex or start a new task after installation so Skills are reloaded.

### Install from a Release

Download these two required `v0.1.0-rc.2` assets from the GitHub Release page into the same directory:

- `codex-grok-search-v0.1.0-rc.2.zip`
- `SHA256SUMS`

`codex-grok-search-v0.1.0-rc.2.tar.gz` is an optional equivalent archive. The command below validates only the selected ZIP, so the tarball is not required. It then validates the Skill structure and fully replaces the old installation. Any checksum, validation, or activation failure preserves or restores the previous installation instead of merging old and new files.

<details>
<summary>Show Release installation command</summary>

<!-- BEGIN RELEASE INSTALL -->
```sh
set -eu
version="v0.1.0-rc.2"
archive="codex-grok-search-${version}.zip"
checksums="SHA256SUMS"
skills_root="${CODEX_HOME:-$HOME/.codex}/skills"
dest="$skills_root/codex-grok-search"
validator="$skills_root/.system/skill-creator/scripts/quick_validate.py"
test -f "$archive"
test -f "$checksums"
test -f "$validator"
checksum_line="$(awk -v file="$archive" '$2 == file {print}' "$checksums")"
test -n "$checksum_line"
printf '%s\n' "$checksum_line" | shasum -a 256 -c -
mkdir -p "$skills_root"
install_lock="$skills_root/.codex-grok-search.install.lock"
lock_owned=0
stage=""
backup_root=""
backup=""
had_backup=0
activated=0
rollback() {
  status="$1"
  trap - EXIT HUP INT TERM
  if [ "$activated" -eq 1 ] && [ -e "$dest" ]; then rm -rf "$dest" || status=1; fi
  if [ "$had_backup" -eq 1 ] && [ -e "$backup" ]; then mv "$backup" "$dest" || status=1; fi
  if [ -n "$stage" ] && [ -e "$stage" ]; then rm -rf "$stage" || status=1; fi
  if [ -n "$backup_root" ] && [ -e "$backup_root" ]; then rm -rf "$backup_root" || status=1; fi
  if [ "$lock_owned" -eq 1 ] && [ -d "$install_lock" ]; then rmdir "$install_lock" || status=1; fi
  exit "$status"
}
trap 'rollback $?' EXIT
trap 'rollback 129' HUP
trap 'rollback 130' INT
trap 'rollback 143' TERM
if ! mkdir "$install_lock"; then
  echo "Another codex-grok-search install, upgrade, or uninstall is active; if not, verify no installer is running before removing $install_lock." >&2
  exit 1
fi
lock_owned=1
stage="$(mktemp -d "$skills_root/.codex-grok-search.release.XXXXXX")"
backup_root="$(mktemp -d "$skills_root/.codex-grok-search.backup.XXXXXX")"
backup="$backup_root/codex-grok-search"
mkdir "$stage/unpack"
unzip -q "$archive" -d "$stage/unpack"
source_dir="$stage/unpack/codex-grok-search"
test -d "$source_dir"
find "$source_dir" -type d -exec chmod 755 {} +
find "$source_dir" -type f -exec chmod 644 {} +
find "$source_dir/scripts" -type f -name '*.py' -exec chmod 755 {} +
python3 "$validator" "$source_dir"
mv "$source_dir" "$stage/codex-grok-search"
rm -rf "$stage/unpack"
if [ -e "$dest" ]; then
  had_backup=1
  mv "$dest" "$backup"
fi
activated=1
mv "$stage/codex-grok-search" "$dest"
rm -rf "$stage"
# The destination is committed. Ignore asynchronous termination while the
# rollback trap is disarmed and the lock is released, closing an unlock ABA.
trap '' HUP INT TERM
trap - EXIT
rm -rf "$backup_root"
rmdir "$install_lock"
lock_owned=0
trap - HUP INT TERM
```
<!-- END RELEASE INSTALL -->

</details>

Download the assets from the [v0.1.0-rc.2 Release page](https://github.com/sudoHG/codex-grok-search/releases/tag/v0.1.0-rc.2). Restart Codex or start a new task after installation.

</details>

## Direct CLI use

Normally, let Codex invoke the Skill automatically. For diagnostics or retained-result inspection, you can also run:

```sh
python3 codex-grok-search/scripts/run_search.py run \
  --platform x \
  --since 7d \
  "How have people evaluated this product launch over the last week?"

python3 codex-grok-search/scripts/run_search.py list
python3 codex-grok-search/scripts/run_search.py show RUN_ID
python3 codex-grok-search/scripts/run_search.py cleanup
```

The main platform modes for `run` are `x`, `reddit`, `web`, and multi-source research. Codex should still open important primary links, separate fact from inference, and cross-check consequential claims before writing the final answer.

## Result retention and cleanup

Each run stores private artifacts under:

```text
~/.cache/codex-grok-search/runs/
```

Default policy:

- Unpinned runs are retained for 7 days.
- At most 20 runs are retained.
- Cleanup happens at the start of a later invocation, never immediately after an answer is returned.
- Active and pinned runs are never silently deleted.
- If all 20 slots are pinned or active, a new task returns `cache_capacity_exhausted` instead of damaging existing data.
- Uninstalling the Skill preserves the cache by default, so later questions and manual inspection remain possible.

Queries and search results may reveal your research interests. The cache is private to the current local user. Do not use secrets, passwords, or private credentials as search queries.

## Uninstall

Remove the Skill while preserving retained research:

<!-- BEGIN UNINSTALL -->
```sh
set -eu
skills_root="${CODEX_HOME:-$HOME/.codex}/skills"
dest="$skills_root/codex-grok-search"
install_lock="$skills_root/.codex-grok-search.install.lock"
lock_owned=0
retired_root=""
cleanup_uninstall() {
  status="$1"
  trap - EXIT HUP INT TERM
  if [ -n "$retired_root" ] && [ -e "$retired_root" ]; then rm -rf "$retired_root" || status=1; fi
  if [ "$lock_owned" -eq 1 ] && [ -d "$install_lock" ]; then rmdir "$install_lock" || status=1; fi
  exit "$status"
}
trap 'cleanup_uninstall $?' EXIT
trap 'cleanup_uninstall 129' HUP
trap 'cleanup_uninstall 130' INT
trap 'cleanup_uninstall 143' TERM
mkdir -p "$skills_root"
if ! mkdir "$install_lock"; then
  echo "Another codex-grok-search install, upgrade, or uninstall is active; if not, verify no installer is running before removing $install_lock." >&2
  exit 1
fi
lock_owned=1
retired_root="$(mktemp -d "$skills_root/.codex-grok-search.uninstall.XXXXXX")"
if [ -e "$dest" ]; then mv "$dest" "$retired_root/codex-grok-search"; fi
rm -rf "$retired_root"
retired_root=""
# The uninstall is committed. Ignore asynchronous termination while the
# cleanup trap is disarmed and the lock is released, closing an unlock ABA.
trap '' HUP INT TERM
trap - EXIT
rmdir "$install_lock"
lock_owned=0
trap - HUP INT TERM
```
<!-- END UNINSTALL -->

Delete the cache manually only when you no longer need historical results:

```sh
rm -rf "$HOME/.cache/codex-grok-search"
```

## Date and source rules

- Reddit dates are checked by a separate local verifier rather than accepted from model output alone.
- At most 20 Reddit URLs are actively fetched for verification. Additional candidates are retained and marked `verification_limit_exceeded`.
- A result whose absolute date cannot be confirmed is labeled `date unverified` and cannot support a strict time-window claim.
- Every source link must match an allowed platform URL. Invalid URLs, control characters, unknown fields, or session mismatches cause the result to be rejected.
- Search coverage is best-effort and is not guaranteed to exhaust all matching platform content.

## Development validation

```sh
python3 -m unittest discover -s tests -v
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" codex-grok-search
```

## Reproducible Release builds

The tracked `scripts/build_release.py` is the only Release-asset build entrypoint. It reads the `codex-grok-search/` tree directly from a specified Git commit, rejects symlinks and special files, and generates ZIP, tar.gz, and `SHA256SUMS` with fixed metadata. It never reads untracked working-tree files or inherits the caller's Git `tar.umask`. Directories and Git executable files are normalized to `0755`; other regular files are normalized to `0644`.

```sh
python3 scripts/build_release.py \
  --commit HEAD \
  --version v0.1.0-rc.2 \
  --output-dir /tmp/codex-grok-search-v0.1.0-rc.2
```

Repeated builds from the same Git commit and Python version should produce byte-identical copies of all three assets. Release notes should record the full commit SHA and the Python version used for the build.

This release candidate has passed unit tests, structure validation, real X and Reddit canaries, and reproducible-asset checks. The GitHub Release assets are built from the tagged repository commit and verified again before the draft is published.

## License

[MIT](LICENSE)

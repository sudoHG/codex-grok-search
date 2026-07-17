# codex-grok-search

[![CI](https://img.shields.io/github/actions/workflow/status/sudoHG/codex-grok-search/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/sudoHG/codex-grok-search/actions/workflows/ci.yml) [![Release](https://img.shields.io/github/v/release/sudoHG/codex-grok-search?style=flat-square&label=release)](https://github.com/sudoHG/codex-grok-search/releases/latest) [![Downloads](https://img.shields.io/github/downloads/sudoHG/codex-grok-search/total?style=flat-square&label=downloads)](https://github.com/sudoHG/codex-grok-search/releases) [![Stars](https://img.shields.io/github/stars/sudoHG/codex-grok-search?style=flat-square&label=stars)](https://github.com/sudoHG/codex-grok-search/stargazers) [![License](https://img.shields.io/github/license/sudoHG/codex-grok-search?style=flat-square)](LICENSE) [![README views](https://hits.sh/github.com/sudoHG/codex-grok-search.svg?style=flat-square&label=README%20views)](https://hits.sh/github.com/sudoHG/codex-grok-search/)

[English](README.md) | 简体中文

让 Codex 调用你本机已经登录的 Grok Build，快速搜索 X、Reddit 和公开网页；只有明确提出时才升级为深度核验。

Codex 负责理解任务、设计检索和整理结论；Grok 负责发现 X、Reddit 与网页上的公开内容；本地脚本负责校验输出、核对 Reddit 日期并保留可追溯的结果。它不是用 Grok 替代 Codex，而是让两者各自做更擅长的部分。

> 当前稳定版本：`v0.1.2`。项目非官方，与 xAI、X、Reddit 或 OpenAI 均无隶属关系。

## 它能做什么

- 搜索指定 X 账号的最新公开帖子、相关讨论、引用和回复。
- 调研 Reddit 最近出现的讨论、用户反馈、抱怨和产品口碑。
- 默认直接给出 Grok 快速结果；真正需要时，再明确要求跨来源深度核验。
- 对带有时间范围的 Reddit 任务做本地日期验证，避免把窗口外的旧帖子误写成“最近 7 天”。
- 保留原始结果和来源链接，方便当前任务或后续任务继续追问。
- 在仓库之外的独立非 Git 目录中运行 Grok，避免把当前代码仓库作为 CLI 的工作目录暴露。
- 日期无法确认时明确标记“日期未验证”，不伪造确定性，也不会仅因无法验证就静默丢弃结果。

例如，你可以直接对 Codex 说：

```text
找一下 @openai 最近 10 条 X 帖子，按时间倒序整理并附原帖链接。

看看最近 7 天 Reddit 上对 OpenAI 有哪些集中吐槽，按问题类型归纳。

调研这个产品最近的社区反馈，X、Reddit 和公开网页互相交叉验证。
```

安装后，涉及 X、Reddit、社区舆情、近期公开帖子或数据抓取的调研任务应自动触发本 Skill；普通网页调研也可以把它作为补充搜索源。你通常不需要直接运行脚本。

## 为什么是 Grok

因为 Grok 不是“另一个通用网页搜索模型”。它拥有 xAI 提供的服务端原生 X Search，这是它在这套组合里最难被替代的能力。

xAI 的官方文档明确说明，`x_search` 可以在 X 上执行关键词搜索、语义搜索、用户搜索和完整 thread 获取，并访问实时社交内容；它还支持指定账号、排除账号、日期范围，以及帖子图片和视频理解。相比让 Codex 用普通网页搜索去碰运气，Grok 更接近 X 平台内部的原生检索层。参见 [xAI X Search 文档](https://docs.x.ai/developers/tools/x-search)。

对于 Reddit 和普通网页，Grok 的 `web_search` 同样由 xAI 在服务端执行，能够实时搜索网页、打开页面、提取相关内容并返回来源链接。quick 模式下 Codex 直接组织答案，只在用户明确要求深度调研时追加核验。参见 [xAI Web Search 文档](https://docs.x.ai/developers/tools/web-search)和[xAI 服务端工具说明](https://docs.x.ai/developers/tools/overview)。

### 和 X API、直接抓取相比

截至 2026 年 7 月 16 日，X 官方 API 采用预购 credits 的按量计费模式：读取一条帖子收费 `$0.005`，读取一个用户对象收费 `$0.010`。按当前单价，读取 1,000 条帖子约为 `$5`；接入时还需要开发者账号、Project、App、认证凭据、分页、限流和计费管理。价格可能调整，应以 [X API 官方价格页](https://docs.x.com/x-api/getting-started/pricing)为准。

而 Grok 当前有一条更适合个人调研的成本路径：xAI 的 Free 方案为 `$0/月`，官方描述是在“较宽松的额度”内提供实时 Web 与 X Search；xAI 还在 Grok 4.5 发布公告中注明，Grok Build 的 Grok 4.5 目前可以限时免费使用。与此同时，X 官方说明 Premium 会员拥有更高的 Grok 使用额度，Premium+ 的额度更高。参见 [xAI Grok 方案](https://x.ai/pricing)、[Grok 4.5 公告](https://x.ai/news/grok-4-5)和 [X Premium 权益说明](https://help.x.com/en/using-x/x-premium)。

这正是 `codex-grok-search` 的实际价值：把用户已经拥有的免费额度、Grok 订阅额度或 X Premium 附带的 Grok 权益，转化为 Codex 可自动调用的搜索与调研能力，而不必为了偶发的 X 调研再单独购买 X API credits、维护开发者 App 和实现一套搜索管道。

免费政策、具体次数和不同产品间的账号权益可能随地区、活动与套餐调整；尤其是 X Premium 的 Grok 权益能否完整用于 Grok Build，应以用户登录后显示的当前模型权限和使用上限为准。本项目不会把阶段性免费额度宣传成永久承诺。

| 路线 | 成本与接入 | 搜索能力 | 账号与风控暴露 |
| --- | --- | --- | --- |
| X 官方 API | 按资源付费并预购 credits；需要开发者项目、App 和凭据 | 官方结构化数据，适合稳定产品集成和大规模管道 | 合规路径，但需要自行处理额度、限流、账单和应用权限 |
| 浏览器自动化或直接抓取 | 看起来没有 API 账单，但维护代理、Cookie、验证码和反爬绕过都有隐性成本 | 容易受登录墙、页面变化、限流和搜索可见性影响 | 用户账号、Cookie 和出口 IP 直接暴露给平台风控 |
| `codex-grok-search` | 可利用 Grok Free、现有 Grok 订阅或符合条件的 X Premium 权益；不要求另购 X API credits 或配置 X Developer App | Grok 原生 X Search + Web Search，默认快速回答，可选深度核验 | 主要搜索由 xAI 服务端执行，不自动操作用户的 X/Reddit 账号或浏览器 |

本 Skill 的目标不是替代需要稳定 SLA、完整数据授权或大规模结构化采集的官方 API。它更适合个人和小团队的临时调研：查最新帖子、跟踪社区讨论、验证账号动态、了解产品口碑，或者为 Codex 增加一个独立的实时搜索源。

### 降低直接抓取带来的封禁风险

X 的服务条款明确禁止未经书面许可的 crawling 或 scraping；Reddit 也禁止未经许可的自动化数据收集，并对 API、商业使用和研究访问设置了单独规则。直接使用浏览器 Cookie、登录账号或固定出口 IP 高频抓取，既不稳定，也可能触发限流、验证码、IP 阻断或账号处置。参见 [X 服务条款](https://x.com/en/tos)、[Reddit 用户协议](https://redditinc.com/policies/user-agreement)和[Reddit 数据访问说明](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data)。

`codex-grok-search` 不接管你的 X 或 Reddit 登录，不读取浏览器 Cookie，也不在本机运行平台页面自动化。X 搜索和主要网页发现由 xAI 的服务端工具执行；Reddit 结果只会在本地对有限数量的公开原帖页面做日期复核。这可以显著减少由用户机器直接发起的抓取量，以及账号、Cookie 和本机 IP 暴露给自动化风控的机会。

但它不是“防封保证”：平台政策、Grok 可用性、公开内容可见范围和服务端限额仍可能变化；少量 Reddit 日期验证请求也可能遇到 403 或限流。遇到限制时，Skill 会保留结果并标记日期未验证，而不是绕过平台限制或伪装成功。

### 隐私隔离与安全边界

2026 年 7 月，研究者对 Grok Build CLI `0.2.93` 的网络流量分析显示：它曾把完整的 Git 仓库包上传到 xAI 管理的存储，包括没有被任务读取的已跟踪文件和 Git 历史；关闭“Improve the model”也没有阻止该上传。xAI 后来在服务端禁用了这条上传路径，但这个变化不应被当作本项目的唯一安全边界。参见[原始线缆级分析](https://gist.github.com/cereblab/dc9a40bc26120f4540e4e09b75ffb547)和 [The Verge 的事件跟进](https://www.theverge.com/ai-artificial-intelligence/965600/spacexai-grok-build-repository-upload)。

`codex-grok-search` 不在用户当前项目或 Git 仓库中启动 Grok。它先在仓库之外创建仅当前用户可访问的独立研究目录，只写入本次搜索 prompt 和结果文件，再把该目录设为 Grok 的 `--cwd`。真实代码仓库不会被复制、挂载或传入这个运行环境。一个轻量的 `grok models` 预检会在专用非 Git 目录中运行，让官方 CLI 正常刷新用户的 `~/.grok` 登录状态；这个步骤没有项目 cwd，也不会继承无关 secrets。随后的隔离检查和正式搜索仍使用临时 `HOME`、`GROK_HOME` 和 `TMPDIR`，其中只包含刷新后的认证文件和锁定配置，并在搜索前用 `grok inspect --json` 检查是否加载了项目指令、插件、MCP、非内置 Skill 或其他未审计执行面；只要结构不匹配就会停止。

这个保护不依赖 Grok 的“不上传仓库”承诺：即使 CLI 再次尝试打包整个工作目录，它面对的也只是本次临时研究目录，而不是用户的代码仓库。

正式研究还有以下固定边界：

- 版本检查、登录检查和搜索只使用经验证的官方 Grok 可执行文件，不信任任意 `PATH` 注入或自定义二进制。
- X 快速任务只开放 `x_search`；X 深度任务和多来源任务才可能同时开放 `web_search` 与 `web_fetch`。Reddit/网页任务不开放 `x_search`。
- 不向模型开放 MCP、本地文件读取、Shell、文件编辑、记忆或子代理。
- Grok 输出必须通过封闭 JSON 结构校验；超时、非零退出、字段缺失或不完整结果都不会被伪装成成功。
- 来自网页、X 或 Reddit 的文本始终被视为不可信数据，其中出现的指令、路径或授权声明不会被执行。

在 macOS 上，正式研究命令使用 Grok 的原生 strict sandbox，并在启动前降低进程创建权限；在 Linux 上，由子进程监管器回收和终止脱离的后代进程。

边界也需要说清：用户主动提供的查询内容、Grok 为搜索生成的结果以及它访问的公开网页仍会经过 xAI 服务；本项目不是本地模型，也不宣传“零数据上传”。它解决的是不必要的本地仓库暴露，而不是消除云端搜索本身的数据传输。

这些措施降低了本地研究工具读取项目内容或执行来源中恶意指令的风险，但不能保证搜索结果本身正确。只有当结论的重要性值得额外时间和工具成本时，再明确要求 `deep` 核验。

## 工作方式

```text
用户问题
  → Codex 拆解研究任务
  → 本地包装器检查 Grok 安装、登录和模型权限
  → Grok 4.5 搜索 X / Reddit / 公开网页
  → 本地结构与来源校验
  → Reddit 日期二次验证
  → 保存可追溯结果
  → Codex 直接回答（只有明确要求深度核验时才继续交叉比对）
```

默认 `quick` 深度不会让 Codex 再打开结果链接、追加网页搜索或控制交互式浏览器。只有你明确要求核验或更高置信度调研时才使用 `deep`。除非用户主动提出，否则永远不调用用户的个人浏览器。

所有研究任务固定使用 `grok-4.5`，不提供模型覆盖参数，也不会在模型不可用时静默降级。

## 使用条件

- macOS 或 Linux，使用非 root 账号运行。
- Python 3.9 或更高版本。
- 通过 [xAI 官方安装器](https://x.ai/cli) 安装的 Grok Build CLI。Skill 不锁定或拒绝 CLI 版本，而是在每次搜索前校验实际的隔离运行配置。
- 已在本机执行 `grok login` 并保持登录。
- 支持 Skills 的 Codex 环境。

本 Skill 使用本机现有的 Grok 登录状态，不需要 xAI API Key，也不会要求你把账号凭据粘贴给 Codex。运行时会主动移除 `XAI_API_KEY`，避免意外走 API 计费。

如果环境不满足要求，它会明确停止并给出下一步：

- 未安装官方 Grok Build：提示前往 `https://x.ai/cli` 安装。
- Grok 未登录或登录已失效：返回 `grok_not_authenticated`，提示你在自己的终端运行 `grok login`。
- 当前账号无法使用 Grok 4.5：明确报错，不切换到其他模型。

## 安装

### 推荐：让 Codex 安装

新建一个 Codex 任务并发送：

```text
请安装这个 Skill：https://github.com/sudoHG/codex-grok-search/tree/main/codex-grok-search
```

Codex 会使用内置 Skill 安装器把它安装到你的 Skills 目录。安装完成后再新建一个任务，即可自动触发。

<details>
<summary>高级：手动安装、升级或校验发布包</summary>

### 从源码仓库安装

下面的命令必须在 Git clone 的仓库根目录运行。它从当前已检出的精确提交导出 Skill，先完成结构校验，再以同文件系统重命名的方式替换旧版本；升级时不会残留已经从新版本删除的旧文件。

<details>
<summary>展开安装命令</summary>

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

安装完成后，重启 Codex 或新建一个任务，让 Codex 重新加载 Skills。

### 从 Release 安装

从 GitHub Release 页面下载下列两个必需的 `v0.1.2` 资产，并放在同一个目录：

- `codex-grok-search-v0.1.2.zip`
- `SHA256SUMS`

`codex-grok-search-v0.1.2.tar.gz` 是可选的内容相同备用格式。下面的命令只校验并安装你选择的 ZIP，不要求同时下载 tar.gz；随后验证 Skill 结构并完整替换旧版本。任何校验或切换失败都会保留或恢复原安装，不会把新旧文件合并。

<details>
<summary>展开 Release 安装命令</summary>

<!-- BEGIN RELEASE INSTALL -->
```sh
set -eu
version="v0.1.2"
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

请从 [v0.1.2 Release 页面](https://github.com/sudoHG/codex-grok-search/releases/tag/v0.1.2)下载资产。安装完成后，重启 Codex 或新建一个任务。

</details>

## 直接使用命令行

通常应让 Codex 自动调用。排查问题或查看历史结果时，也可以直接运行：

```sh
python3 codex-grok-search/scripts/run_search.py run \
  --platform x \
  --depth quick \
  --since 7d \
  "最近一周人们如何评价这个产品发布？"

python3 codex-grok-search/scripts/run_search.py list
python3 codex-grok-search/scripts/run_search.py show RUN_ID
python3 codex-grok-search/scripts/run_search.py cleanup
```

`run` 支持的主要平台模式是 `x`、`reddit`、`web` 和多来源调研。`--depth quick` 是默认值，优先快速返回，不逐条交叉核验；`--depth deep` 才要求 Grok 做更广的验证。quick 模式下，Codex 不应再独立打开结果链接或调用浏览器。

## 结果保存与清理

每次运行会在以下目录保存私有结果：

```text
~/.cache/codex-grok-search/runs/
```

默认策略：

- 未固定的运行结果保留 7 天。
- 最多保留 20 次运行。
- 清理发生在下一次调用开始时，不会在刚回答完问题后立刻删除。
- 正在使用或已经固定的运行不会被静默删除。
- 如果 20 个位置全部被固定或占用，新任务会返回 `cache_capacity_exhausted`，而不是破坏旧数据。
- 卸载 Skill 默认保留缓存，便于后续追问或人工检查。

查询和搜索结果可能暴露你的研究兴趣，缓存目录仅供本机当前用户访问。不要把秘密、密码或私有凭据作为搜索内容。

## 卸载

只移除 Skill，不删除研究缓存：

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

确认不再需要历史结果后，才手动删除缓存：

```sh
rm -rf "$HOME/.cache/codex-grok-search"
```

## 日期与来源规则

- Reddit 日期由本地验证器单独核对，而不是只相信模型生成的日期。
- 最多主动抓取并验证 20 个 Reddit URL；超出上限的候选仍会保留，并标记 `verification_limit_exceeded`。
- 无法确认绝对日期的结果标记为“日期未验证”，不能用来支撑严格的时间窗口结论。
- 所有来源链接都必须是允许的平台 URL；无效 URL、控制字符、未知字段或会话不匹配会导致结果被拒绝。
- 搜索覆盖是尽力而为，不承诺穷尽平台上的全部内容。

## 开发验证

```sh
python3 -m unittest discover -s tests -v
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" codex-grok-search
```

## 可复现发布构建

仓库提交 `scripts/build_release.py` 是 Release 资产的唯一构建入口。它直接读取指定 Git commit 的 `codex-grok-search/` tree，拒绝符号链接和特殊文件，并用固定元数据生成 ZIP、tar.gz 与 `SHA256SUMS`；不读取工作树中的未跟踪文件，也不继承调用者的 Git `tar.umask`。目录和 Git executable 文件固定为 `0755`，其他普通文件固定为 `0644`。

```sh
python3 scripts/build_release.py \
  --commit HEAD \
  --version v0.1.2 \
  --output-dir /tmp/codex-grok-search-v0.1.2
```

同一 Python 版本和同一 Git commit 的重复构建应得到字节级相同的三个资产。发布时应在 Release notes 中记录完整 commit SHA 和构建环境的 Python 版本。

当前稳定版本已经完成单元测试、结构校验、真实 X / Reddit canary 和可复现资产检查。GitHub Release 资产从带 tag 的仓库提交构建，并在正式发布前再次校验。

## 许可证

[MIT](LICENSE)

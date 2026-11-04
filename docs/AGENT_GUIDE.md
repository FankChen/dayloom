# Agent 使用与设备连接

[简体中文](#agent-使用与设备连接) | [English](#agent-usage-and-device-connections)

这是 v0.4 Agent 源码开发预览的使用说明，不是正式安装包或商业平台接入声明。
已有数据的用户应先阅读 [OPERATIONS.md](OPERATIONS.md)，停止旧 API 和 worker，备份数据库及凭据密钥后再升级。

## 当前能做什么

| 能力 | 当前实现 | 不能据此宣称 |
| --- | --- | --- |
| 多步执行 | 模型规划一个工具调用，等待真实结果，再决定下一步、询问用户或结束；运行与步骤持久化 | 模型汇报完成不等于任意业务已经成功，仍须核对工具证据 |
| 网络搜集 | `SearchWeb` 返回公开搜索来源与摘要；`ReadWebPage` 使用独立、受限的浏览器读取已允许网页 | 搜索摘要不等于全文核验；本次环境的实际公网搜索未成功，浏览器执行仍需部署 |
| 工作成果 | `SaveArtifact` 保存 Markdown 文本与来源，可查看和下载 | 不是任意磁盘读写，也不执行生成的内容 |
| 邮件 | 复用已连接 SMTP、精确内容审批与实际执行结果 | SMTP 接受不等于收件人已收到，尚无 Gmail/Graph OAuth |
| 电脑工具 | 标准 MCP 发现、工具选择、逐次审批调用；第一方服务提供能力查看、允许网站打开、批准目录软件下载 | 不提供任意 Shell，不自动安装软件；打开页面不等于购票或下单 |
| 手机和商业应用 | 可连接用户有权使用的兼容 MCP 服务 | 尚无第一方 Android/iOS 任意应用控制，也未接入电影票、外卖或支付平台 |

## 完成第一个目标

1. 从导航进入 **智能体 / Agent**。根网址默认进入这里，原有今日、任务和对话仍可使用。
2. 连接支持 JSON object 响应的真实模型；已有模型连接可复用。未配置时点击“连接支持智能体的模型”，不会自动改成演示模式。
3. 输入希望获得的结果，例如“对比三个公开来源，整理成带链接的笔记”。观影、外卖和软件模板只是目标起点，不代表已接入对应商家。
4. 检查“本次目标允许的工具”。不可用工具会提示需要连接或部署配置；只选择本次需要的能力。
5. 确认模型数据分享与可能的调用费用。可另行允许所选只读工具自动执行；搜索词会发送到搜索服务。设备调用不会因此自动获批。
6. 点击“启动智能体”。执行步骤会显示规划说明、具体参数、待审批、工具结果及后续动作。写入、发信和所有设备调用仍需逐项批准准确内容。
7. 需要补充信息时点击“继续运行”；需要停止时使用暂停或停止按钮。到“工作成果”查看保存的内容和来源，再下载 Markdown。

默认允许 8 次模型规划，单次运行总上限为 24 次；最终汇总也占一次规划。
授权默认一小时。继续运行会重新确认模型分享、续期一小时并取消旧的待执行提案，不会静默增加预算。
工作区模型连接的每日请求额度仍生效；次数和输出 token 限制不是金额上限。
执行进程离线时运行停留在队列。已开始的外部操作不能保证撤回；结果不明时必须先核对，不自动重发。

## 不使用真实模型的演示

仅在明确需要离线验收时，在仓库根目录启动：

```bash
DAYLOOM_MODEL_PROVIDER=DemoProvider npm run dev
```

界面会持续标注“离线规则演示”。在允许 `SaveArtifact` 的目标中，它只提议保存一份标注为演示的文本，审批后真实写入数据库并可下载。
这能检查运行、审批、刷新恢复和成果路径，但不搜索、不订票、不下单、不安装，也不是语言模型能力测试。

## 连接电脑工具服务

工具运行位置是 **MCP 服务所在的电脑或设备**，不是自动控制当前浏览器所在设备。
手机打开网页不会授予控制其他 App 的权限；远程 Dayloom 的 `127.0.0.1` 也不是你的个人电脑。

先在希望使用工具的电脑上准备本项目源码、Python 3.12 和 uv，并安装锁定依赖。
第一方服务仍是源码工具，没有已验证的 EXE、APK 或原生安装程序；应以普通交互用户身份运行，不使用管理员或 root。
使用密码管理器生成至少 32 个随机字符的设备令牌，直接填入本机终端或受保护环境，不要发送到聊天、反馈或提交到仓库。

Linux/macOS 的 Bash 启动示例：

```bash
uv sync --locked --python 3.12
read -r -s -p "Device token: " DAYLOOM_DEVICE_TOKEN
export DAYLOOM_DEVICE_TOKEN
PYTHONPATH=backend uv run --locked python -m dayloom.device_server
```

Windows PowerShell 的源码运行方式如下；Windows 真实浏览器和下载行为仍需实机验收：

```powershell
uv sync --locked --python 3.12
$deviceSecret = Read-Host "Device token" -AsSecureString
$env:DAYLOOM_DEVICE_TOKEN = [System.Net.NetworkCredential]::new("", $deviceSecret).Password
$env:PYTHONPATH = "backend"
uv run --locked python -m dayloom.device_server
```

服务默认只监听 `127.0.0.1:19888`，MCP 地址为 `http://127.0.0.1:19888/mcp`，启用令牌和 Host/Origin 检查。
若 Dayloom 与设备服务在同一台电脑，在 Dayloom 的受保护本地环境中加入以下配置，并重启 API 与 worker：

```dotenv
DAYLOOM_MCP_ALLOWED_SERVERS=["http://127.0.0.1:19888/mcp"]
```

1. 进入 **工具与设备 → 连接设备服务**，填写名称、已批准地址和设备令牌。保存只加密记录，不联系设备。
2. 点击“发现设备工具”，明确同意联系该设备。发现不会调用工具，也不会自动授权。
3. 只勾选你需要的工具并保存。再次发现会清除旧工具权限；配置修改会递增连接版本，让旧提案失效。
4. 为目标选择 `ListDeviceTools` 和 `CallDeviceTool`。模型先读取所选工具的参数结构，再提出具体调用；每次设备操作都需要审批。

远端设备接入还需要设备主人配置可达的受保护网络与 HTTPS 服务。第一方服务不提供一键公网暴露，也不应直接公开端口。
第三方 MCP 工具拥有其服务进程的实际权限；Dayloom 的审批不等于对第三方服务提供沙箱。
持有设备令牌的人可直接使用该服务。请求中的操作编号用于关联审计，不是独立的数字签名或购买授权证明。

## 第一方设备能力的配置

默认不允许打开任何网站，软件下载目录也为空。部署者可在设备服务的受保护环境中配置：

```dotenv
DAYLOOM_DEVICE_PORT=19888
DAYLOOM_DEVICE_ALLOWED_ORIGINS=["https://www.example.org"]
DAYLOOM_DEVICE_MAX_DOWNLOAD_BYTES=200000000
DAYLOOM_DEVICE_DOWNLOAD_TIMEOUT_SECONDS=45
DAYLOOM_DEVICE_SOFTWARE={}
```

- `device_info` 返回服务所在系统及已配置能力，不扫描个人文件或浏览器账号。
- `open_url` 只接受已允许来源的 HTTPS 地址，交给该电脑的浏览器。登录、选择商品、购票和支付仍由用户在可信应用中完成。
- `download_software` 只接受配置目录中的软件 ID，不接受模型任意指定下载地址或目标路径。下载校验 SHA-256，拒绝重定向、超限、覆盖已有文件与符号链接，并在失败后删除临时文件。
- 下载默认保存到用户的 `Downloads/Dayloom`；可通过 `DAYLOOM_DEVICE_DOWNLOAD_DIR` 改为专用目录。无执行权限提升、无自动运行或安装。

`DAYLOOM_DEVICE_SOFTWARE` 中每个软件条目必须含以下字段。下面是结构占位示例，域名与全零哈希不可作为真实配置：

```json
{
  "approved-package": {
    "title": "Approved package",
    "url": "https://downloads.example.org/package.bin",
    "filename": "package.bin",
    "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
  }
}
```

地址和哈希应来自你信任的正式发行渠道，不能由模型编造。匹配哈希只证明内容符合批准版本，不等于恶意软件扫描或发布者签名验证。
软件安装需要额外设计 OS 权限、发布者验证、回滚与用户确认，不属于本轮自动执行能力。

## 网络和故障处理

- 搜索由 `DAYLOOM_WEB_SEARCH_ENABLED` 控制，默认开启，`DAYLOOM_WEB_SEARCH_DAILY_LIMIT` 默认 50。查询只经现有网络和 TLS 校验，不绕过网络策略。
- MCP 地址必须精确出现在服务器允许列表中。HTTPS 是默认要求，HTTP 仅允许回环地址；不跟随设备服务重定向。
- `DAYLOOM_DEVICE_DAILY_LIMIT` 默认 30，分别约束设备发现与调用。远端工具的只读标记不能绕过逐次审批。
- 模型配置变化会在下一次规划前要求重新确认。连接版本或工具结构变化会阻止旧设备调用；越界工具、步数耗尽和中断的规划会暂停。
- 已发出的远端调用断线或返回无法确认副作用的错误时，标记 `outcome_unknown`。先查看设备实际状态并记录核对结果，禁止直接重复提交。
- 本轮一次实际公开搜索返回 `DDGSException`，没有验证公网搜索成功。接入实现和替身测试不能代替部署网络中的真实检索验收。

## 升级与验证

`0006_agents` 增加 `agent_runs`、`agent_steps`、`artifacts` 及操作关联字段。旧任务和审批保留已通过 SQLite 迁移回归；不要运行旧 worker 处理新版本数据库。
生产 PostgreSQL 仍须由独立迁移角色更新 schema、安装新表 RLS 并授权应用角色，运行时检查通过后再启动。

基线是旧 `/api/chat`：工具执行后模型不会继续。本版测试覆盖“工具结果 → 再规划 → 新工具 → 成果”，并明确使用模拟模型而非声称真实智能能力提升。
本机 MCP 服务的发现、选择工具、逐次审批和 `device_info` 实际 HTTP 调用已经验收；真实商家、真实手机控制、实际安装和支付没有验收。
详细证据及浏览器下载环境限制见 [VERIFICATION.md](VERIFICATION.md)。

---

# Agent Usage and Device Connections

This guide covers the v0.4 Agent source preview, not a production installer or a commercial-platform integration claim.
Existing users must first read [OPERATIONS.md](OPERATIONS.md), stop the old API and worker, and back up the database and credential key before upgrading.

## Current Capabilities

| Capability | Current implementation | Not implied |
| --- | --- | --- |
| Multi-step execution | The model proposes one tool, waits for its real result, then acts again, asks the user or finishes; runs and steps persist | A model's completion message is not proof of arbitrary business success; inspect tool evidence |
| Web research | `SearchWeb` returns public source links and snippets; `ReadWebPage` uses a separately deployed restricted browser for approved pages | Snippets are not full-page verification; live public search did not succeed in this environment, and browser execution needs deployment |
| Work artifacts | `SaveArtifact` stores Markdown and source links for viewing/download | No arbitrary filesystem access or execution of generated content |
| Email | Existing SMTP connections, exact-content approval and execution results are reused | SMTP acceptance is not delivery; Gmail/Graph OAuth is still absent |
| Computer tools | Standard MCP discovery, tool selection and per-call approval; first-party capabilities include inspection, approved websites and curated downloads | No arbitrary shell or automatic installation; opening a page is not booking or ordering |
| Phones and commercial apps | Compatible MCP services that the user is authorized to operate can be connected | No first-party arbitrary Android/iOS app control or movie-ticket, delivery or payment integration yet |

## Complete a First Goal

1. Open **Agent** from navigation. The root URL now starts here; Today, Tasks and chat remain available.
2. Connect a real model supporting JSON object responses, or reuse an existing connection. The setup link is explicit; missing configuration never silently switches to demo mode.
3. Describe the desired result, such as comparing three public sources and saving a linked note. Movie, food and software templates are starting goals, not installed merchant integrations.
4. Review the tools allowed for this goal. Unavailable capabilities show connection/deployment requirements; select only what is needed.
5. Consent to model data sharing and possible costs. Separately, you may authorize selected read-only tools to run automatically; search queries leave the workspace. Device calls are not automatically approved.
6. Start the Agent. Its steps show public planning summaries, exact parameters, approvals, tool results and follow-up actions. Writes, email and all device calls still require exact per-action approval.
7. Continue with clarification when asked, or pause/stop the run. Open Work artifacts to inspect saved content and sources and download Markdown.

The default budget is 8 model planning calls, with a total per-run maximum of 24; final summarization also uses a planning step.
Authorization lasts one hour. Continuing reconfirms model sharing, renews one hour and cancels old pending proposals; it never silently increases the budget.
Workspace model-connection daily quotas still apply. Request/token limits are not monetary spending caps.
An offline worker leaves runs queued. Already-started external effects cannot be guaranteed to stop; uncertain results need reconciliation, not automatic replay.

## Demo Without a Real Model

Only for an intentional offline check, start from the repository root:

```bash
DAYLOOM_MODEL_PROVIDER=DemoProvider npm run dev
```

The UI continuously labels this as an offline rules demo. With `SaveArtifact` allowed, it proposes a clearly labeled demonstration note, actually saves it after approval and makes it downloadable.
This exercises runs, approval, reload recovery and artifacts. It does not research, book, order, install or evaluate a language model.

## Connect a Computer Tool Service

Tools run on the **computer or device hosting the MCP service**, not automatically on the device displaying the page.
Opening the website on a phone grants no control over other apps. A remote Dayloom server's `127.0.0.1` is not your personal computer.

Prepare this source project, Python 3.12 and uv on the intended tool-host computer and install locked dependencies.
The first-party service is still source-only, without verified EXE/APK/native installers. Run it as an ordinary interactive user, not administrator or root.
Generate a device token of at least 32 random characters in a password manager and enter it directly in a protected local environment or terminal. Never send it in chat, feedback or commits.

Linux/macOS Bash example:

```bash
uv sync --locked --python 3.12
read -r -s -p "Device token: " DAYLOOM_DEVICE_TOKEN
export DAYLOOM_DEVICE_TOKEN
PYTHONPATH=backend uv run --locked python -m dayloom.device_server
```

Windows PowerShell source invocation follows; actual Windows browser/download behavior still needs device acceptance:

```powershell
uv sync --locked --python 3.12
$deviceSecret = Read-Host "Device token" -AsSecureString
$env:DAYLOOM_DEVICE_TOKEN = [System.Net.NetworkCredential]::new("", $deviceSecret).Password
$env:PYTHONPATH = "backend"
uv run --locked python -m dayloom.device_server
```

By default the service listens only on `127.0.0.1:19888`, at `http://127.0.0.1:19888/mcp`, with bearer-token and Host/Origin checks.
When Dayloom and the device service share a computer, add this to Dayloom's protected environment and restart its API and worker:

```dotenv
DAYLOOM_MCP_ALLOWED_SERVERS=["http://127.0.0.1:19888/mcp"]
```

1. Open **Tools and devices > Connect device service**, then enter its name, approved address and token. Saving encrypts configuration without contacting the device.
2. Discover tools with explicit consent. Discovery neither executes tools nor grants permission automatically.
3. Select only required tools and save. Rediscovery clears previous permissions; configuration changes increment the version and invalidate stale proposals.
4. Allow `ListDeviceTools` and `CallDeviceTool` for the goal. The model inspects the exact tool schema before proposing a call; every device action needs approval.

Remote access additionally requires the device owner to configure a reachable protected network and HTTPS service. The first-party service does not provide one-click public exposure; do not expose its port directly.
Third-party MCP tools retain their process's actual permissions; Dayloom approval is not a sandbox for the third-party service.
A holder of the device token can call that service directly. Action IDs correlate audit records; they are not independent digital signatures or purchase-authority proofs.

## Configure First-Party Capabilities

No website is allowed by default and the software catalog is empty. The device owner can configure:

```dotenv
DAYLOOM_DEVICE_PORT=19888
DAYLOOM_DEVICE_ALLOWED_ORIGINS=["https://www.example.org"]
DAYLOOM_DEVICE_MAX_DOWNLOAD_BYTES=200000000
DAYLOOM_DEVICE_DOWNLOAD_TIMEOUT_SECONDS=45
DAYLOOM_DEVICE_SOFTWARE={}
```

- `device_info` returns the host operating system and configured capabilities, without scanning personal files or browser accounts.
- `open_url` accepts only HTTPS URLs on approved origins and hands them to that computer's browser. Login, selection, booking and payment stay in the trusted application with the user.
- `download_software` accepts only a configured software ID, not arbitrary model-supplied URLs or paths. It checks SHA-256 and rejects redirects, limits violations, existing destinations and symlinks, removing temporary files on failure.
- Downloads default to the user's `Downloads/Dayloom`; `DAYLOOM_DEVICE_DOWNLOAD_DIR` can select a dedicated directory. No privilege elevation, automatic execution or installation occurs.

Each `DAYLOOM_DEVICE_SOFTWARE` entry needs the following fields. This is a structural placeholder; the example domain and zero hash are not a real configuration:

```json
{
  "approved-package": {
    "title": "Approved package",
    "url": "https://downloads.example.org/package.bin",
    "filename": "package.bin",
    "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
  }
}
```

Obtain the URL and hash from a trusted official distribution, never from an invented model value. Matching a pinned hash is not malware scanning or publisher-signature verification.
Installation requires separate OS-permission, publisher-verification, rollback and confirmation design and is not automated in this iteration.

## Networking and Recovery

- `DAYLOOM_WEB_SEARCH_ENABLED` controls search and defaults to true; `DAYLOOM_WEB_SEARCH_DAILY_LIMIT` defaults to 50. Existing networking and TLS verification remain in use; network policy is not bypassed.
- MCP addresses must exactly match the server allowlist. HTTPS is required except for loopback HTTP; device-service redirects are not followed.
- `DAYLOOM_DEVICE_DAILY_LIMIT` defaults to 30 and separately limits discovery and invocation. Remote read-only annotations cannot bypass per-call approval.
- Model changes require renewed confirmation before the next planning call. Connection-version or schema changes block stale device calls; out-of-scope tools, exhausted steps and interrupted planning pause runs.
- A disconnected dispatched call or an error whose side effects cannot be determined becomes `outcome_unknown`. Check the device and record the outcome before any continuation; do not submit the same operation blindly.
- One live public-search probe returned `DDGSException` in this environment, so successful live search is not verified. Implementation and mocked tests do not replace acceptance on the deployment network.

## Upgrade and Verification

`0006_agents` adds `agent_runs`, `agent_steps`, `artifacts` and action association. SQLite upgrade tests preserve existing tasks and approvals; never use an old worker with the new database version.
Production PostgreSQL still requires a separate migration role, RLS on the new tables and application-role grants before runtime checks and startup.

The baseline is the existing `/api/chat`, which does not replan after tool execution. New tests cover tool results, replanning, further tools and artifacts with a controlled model, not claims of improved live-model intelligence.
Actual local MCP discovery, tool selection, per-call approval and the `device_info` HTTP call were verified. Real merchants, phone control, installation and payment were not.
See [VERIFICATION.md](VERIFICATION.md) for detailed evidence and browser-download limitations.
# Dayloom

[简体中文](#简体中文) | [English](#english)

## 简体中文

一个可自托管的个人行动助手。记录想法、整理任务，结合日历安排每日计划，
并明确批准助手能够执行的具体操作。

Dayloom 是独立项目，与 Meta Muse 或 Today AI 无关联。
仓库以私有形式创建，是否公开发布由仓库所有者另行决定。

**当前源码里程碑：v0.2 开发预览（2026-11-02）。**
这是在 v0.1 基础上的功能更新，不是正式安装包或商店发布版本。

### v0.1 已实现功能

- 响应式工作界面，包含 Today、Inbox、Tasks、Memories、Activity 和 Settings 六个视图。
- 持久化任务管理，支持优先级、预计耗时、截止日期、状态及编辑冲突检查。
- 确定性的每日规划器，结合导入的日历事件、可用时间预算和本地时间安排任务。
- 可编辑的记忆，支持来源标记、过期时间、删除及 JSON 导出。
- 明确标识的离线演示模式，以及兼容 OpenAI Chat Completions 的模型适配器。
- 助手提出的操作必须经过用户明确批准，批准与具体操作内容绑定。
- 独立后台工作进程，支持持久化任务队列、执行租约、有限次数的恢复尝试和审计记录。
- 三个本地工具：创建任务、保存记忆和生成每日简报。
- 通过持续维护的日历解析库导入 ICS 日历，支持重复事件。
- 本地单用户模式使用 SQLite，Docker 部署方案使用 PostgreSQL。
- 已生成 Capacitor Android 和 iOS 源码工程，供后续原生客户端开发使用。

### v0.2 开发预览更新

- OIDC/PKCE 登录、个人工作区、可撤销会话、轮换刷新令牌及 Alembic 数据迁移。
- Settings 中配置个人模型 API，服务端加密保存密钥，限制服务地址、每日请求数和输出 token。
- SMTP 邮件提案与逐条审批，以及绑定固定内容、有限次数和到期时间的定时授权。
- 外部执行前持久化发送意图；结果不确定时停止自动重试，支持记录人工核对结果。
- 独立浏览器 worker 的受限公开网页读取接口，默认关闭；不支持登录、任意点击或下单。
- Android Keystore / iOS Keychain 桥接源码、原生登录回跳，以及 Android 自选来源通知采集源码。
- 手动原生构建工作流：Android 调试包或所有者签名包、iOS 未签名模拟器构建；尚无已验证安装包。

**升级注意：** 先停止旧 API 和 worker，备份数据库以及凭据加密密钥，再按
[docs/OPERATIONS.md](docs/OPERATIONS.md) 执行对应环境的迁移流程。
旧记录仍归属原本地工作区，新账号不会自动继承这些数据。

**本地验证：** 41 项后端测试通过，1 项真实 PostgreSQL 测试因环境缺失而跳过；
静态检查、前端生产构建和 Android/iOS 源码同步通过。
真实服务联调、原生编译签名与真机验收尚未完成，商品购买未实现。
完整证据和限制见 [docs/VERIFICATION.md](docs/VERIFICATION.md)。

当前默认不连接任何模型，也不会悄悄退回演示模式。请在 Settings 连接模型。
仅需离线演示时，显式设置 `DAYLOOM_MODEL_PROVIDER=DemoProvider` 后重启。
离线演示模式不需要模型 API 密钥，使用的是简单规则，而不是大语言模型。
普通笔记会生成任务提案，`remember: ...` 会生成记忆提案，
`plan my day` 会生成每日简报提案。它不会推断日期，也不会拆解复杂请求。
系统不会自动插入示例数据；需要手动选择 **Load sample workspace**。

账号部署、密钥管理及当前限制见 [docs/OPERATIONS.md](docs/OPERATIONS.md)。
源码实现不等于已通过生产部署、真实服务或原生设备验收。

### 快速开始

环境要求：Node.js 24 LTS（最低 22.12）、npm、uv 和 Python 3.12。
在仓库根目录执行：

```bash
uv sync --locked --python 3.12
npm --prefix apps/web ci
npm run dev
```

打开 http://127.0.0.1:5178。启动器会同时启动监听 8078 端口的 API、后台工作进程和前端。
开发服务仅监听本机回环地址。按 Ctrl+C 停止启动器。
数据库位于已被 Git 忽略的 `data/` 目录，不要将其提交到仓库。

可通过 `DAYLOOM_DEV_WEB_PORT` 和 `DAYLOOM_DEV_API_PORT` 修改端口。
执行 `npm run build` 生成生产构建；API 服务可托管构建后的静态客户端。

### 接入模型

推荐在 **Settings → Model connection** 配置当前工作区的模型服务、模型名和密钥。
只允许管理员批准的 HTTPS 服务来源；保存不会调用模型，**Test connection** 会发起真实请求。
设置每日请求数和单次输出 token 上限，这些限制不是费用金额保证。

本地单工作区也可参考 [.env.example](.env.example) 创建 `.env`，配置服务端模型：

```dotenv
DAYLOOM_MODEL_PROVIDER=OpenAIProvider
DAYLOOM_MODEL_BASE_URL=https://api.openai.com/v1
DAYLOOM_MODEL_NAME=gpt-4.1-mini
DAYLOOM_MODEL_API_KEY=
```

仅在本地输入密钥，不要将其发送到聊天中或提交到仓库。
上面的模型名称只是示例，并非固定要求。所配置的 API 必须支持 Chat Completions
和 JSON 对象响应。修改服务端配置后需要重启服务。

勾选聊天中的授权选项，表示允许向该模型服务发送当前消息、最近八条消息、
最多 20 个未完成任务的标题、最多 25 条有效记忆，以及已连接的发件地址。
密钥由用户提交后在服务端加密保存，不会通过配置读取或导出接口返回。
模型请求设有超时和输出大小限制，每次响应最多包含五个操作提案。
无效的模型输出不会创建操作。测试不会调用真实模型服务。

### 使用 PostgreSQL 自托管

在本地设置 `DAYLOOM_ACCESS_TOKEN`、`DAYLOOM_DB_PASSWORD` 和 API/worker 共享的
`DAYLOOM_CREDENTIAL_KEY`。加密密钥生成和保存方式见 [docs/OPERATIONS.md](docs/OPERATIONS.md)。
数据库密码会用于连接 URI，因此应使用 URL 安全的值，例如随机生成的十六进制字符串。
缺少这些配置时，Compose 会拒绝启动。

```bash
docker compose up --build -d
```

打开 http://127.0.0.1:8000 并输入工作区访问令牌。
数据库位于 Docker 内部网络中，数据通过命名卷持久化。
后台工作进程会等待 API 完成数据库结构初始化后再启动。升级前请备份数据库。

远程使用需要 HTTPS 反向代理、显式配置的 `DAYLOOM_ALLOWED_ORIGINS` JSON 数组及访问令牌。
不要对外暴露未受保护的开发代理。此 Compose 配置仍是单工作区配置。
多账号配置使用 OIDC、独立数据库运行角色和强制 RLS，必须先通过真实 PostgreSQL 隔离验收。
安全说明见 [SECURITY.md](SECURITY.md)。

### 开发与验证

```bash
npm run check
npm test
cd apps/web
npx playwright install chromium
npm run test:e2e
```

浏览器测试使用 18878 和 18078 端口启动隔离的服务与数据库，不会删除日常开发工作区的数据。
CI 已配置桌面和手机视口测试，但手机视口测试不等于原生设备测试。
已完成的本地检查及尚未验证的环境见 [docs/VERIFICATION.md](docs/VERIFICATION.md)。

模型、连接器、工具、身份适配器、路由和执行器采用以类名注册的注册表、模块自动发现和构造函数依赖注入。
通过新增模块并使用对应注册表的 `@register` 扩展功能，不要在 API 路由中添加提供商切换分支。
架构边界与扩展规则见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

### 移动端路线

详见 [docs/MOBILE.md](docs/MOBILE.md)。Web 客户端目前已可使用。
Capacitor 提供生成原生安装包的开发路径，但不代表应用已经具备上架条件。
安全令牌存储、登录回跳和 Android 通知桥接已有源码，尚未通过原生编译或真机验证。
原生日历访问、推送通知和分享扩展仍待实现。iOS 不支持读取其他 App 的通知。
当前 Web manifest 仅提供安装元数据，尚未实现离线执行。

### 当前边界

- 邮件仅支持 TLS SMTP/app password，未实现 Gmail/Graph OAuth；SMTP 接受不等于送达。
- 定时邮件使用已授权的固定内容，不会自动生成新的日报内容。没有商品购买功能。
- 浏览器仅支持获批来源的公开网页读取，必须部署隔离 worker 和强制出站策略。
- Android 通知默认关闭、按来源选择、加密留在设备；单条转为任务需用户主动操作。iOS 无跨 App 通知读取。
- 日历导入是覆盖未来 32 天的快照，不是实时 OAuth 同步。
- 任务可标记为阻塞，但尚未实现通用事件触发、自动跟进或任务依赖关系。
- 每日规划采用规则基线，不是已经验证优于基线的模型方案，也不是优化求解器。
- 删除记忆只会删除该记忆记录，不会删除原始对话或操作内容。
  删除整个工作区会移除应用记录，但不会删除备份或模型服务商保留的副本。
- 后台工作进程必须持续在线。关闭浏览器不影响后台执行，关闭服务所在主机则会中断执行。
- 本地操作在同一事务中提交；外部执行结果不确定时标记 `outcome_unknown`，不自动重发。
  不宣称外部副作用 exactly-once，人工核对记录也不是独立服务商证明。
- 已有版本化迁移；升级前备份。真实 PostgreSQL/Keycloak、模型、SMTP、浏览器及原生设备仍需部署验收。
- 完整账号注销、KMS、Temporal/LangGraph、金额预算、离线同步和商店分发尚未完成。

### 许可证

原创代码采用 MIT 许可证，第三方依赖保留各自的许可证。
工作区位图和 PNG 格式的 Web 应用图标由 [scripts/generate_assets.py](scripts/generate_assets.py) 生成。
原生模板资源、字体和其他声明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## English

A self-hosted personal action assistant. Capture a thought, turn it into a task,
plan around your calendar, and approve exactly what the assistant may do.

Dayloom is an independent project. It is not affiliated with Meta Muse or Today AI.
This repository starts private; publishing it is a separate owner decision.

**Current source milestone: v0.2 development preview (2026-11-02).**
This extends v0.1; it is not a production binary or an app-store release.

### What works in v0.1

- A responsive workspace with Today, Inbox, Tasks, Memories, Activity and Settings.
- Persistent tasks with priorities, estimates, deadlines, status and optimistic edit checks.
- A deterministic daily planner that respects imported calendar events, capacity and local time.
- Editable memory with source labels, expiration, deletion and JSON export.
- A clearly labeled offline demo and an OpenAI-compatible chat-completions adapter.
- Proposed actions that require explicit approval of the exact payload.
- A separate worker with persisted jobs, leases, bounded recovery and audit records.
- Three local tools: create a task, save a memory, and prepare a daily brief.
- Recurring ICS calendar imports through a maintained calendar parser.
- SQLite for a single local user; PostgreSQL for the Docker deployment.
- Generated Capacitor Android and iOS source projects for native client development.

### v0.2 development preview updates

- OIDC/PKCE sign-in, personal workspaces, revocable sessions, rotating refresh tokens and Alembic migrations.
- Workspace model configuration in Settings, encrypted credentials, approved origins, daily request limits and output-token limits.
- Exact-content SMTP approval and finite, expiring schedules with pause controls.
- Durable external-effect intent, no automatic replay of uncertain outcomes, and owner-reported reconciliation.
- A separate, restricted public-page browser reader, disabled by default; no login, arbitrary clicking or checkout.
- Android Keystore / iOS Keychain bridge source, native login callbacks and opt-in Android notification capture source.
- A manual native build workflow for Android debug or owner-signed artifacts and unsigned iOS simulator builds; no verified installable release yet.

**Upgrade notes:** Stop the old API and worker, back up the database and credential
encryption key, then follow the migration procedure for your environment in
[docs/OPERATIONS.md](docs/OPERATIONS.md). Existing records stay in the legacy
local workspace; newly created accounts do not automatically inherit them.

**Local verification:** 41 backend tests passed and 1 real PostgreSQL test was
skipped because its service was unavailable. Static checks, the web production
build and Android/iOS source synchronization passed. Live integrations, native
compilation/signing and device acceptance remain unverified; purchasing is not
implemented. See [docs/VERIFICATION.md](docs/VERIFICATION.md) for the full evidence
and limitations.

The default has no model connection and never silently falls back to demo mode.
Connect a model in Settings. For an explicit offline demo, set
`DAYLOOM_MODEL_PROVIDER=DemoProvider` and restart.
No model API key is required to try the offline demo. It uses simple rules, not an LLM.
It accepts a note as a candidate task, `remember: ...` as a candidate memory, and
`plan my day` as a candidate daily brief. It does not infer dates or split complex requests.
No demo records are silently inserted: choose **Load sample workspace** explicitly.

See [docs/OPERATIONS.md](docs/OPERATIONS.md) for account deployment and credential
handling. Implemented source is not proof of production, live-provider or native-device readiness.

### Quick start

Requirements: Node.js 24 LTS (minimum 22.12), npm, uv, and Python 3.12.
Run the following from the repository root:

```bash
uv sync --locked --python 3.12
npm --prefix apps/web ci
npm run dev
```

Open http://127.0.0.1:5178. The launcher starts the API on 8078, the worker and
the frontend. All development listeners bind to loopback. Ctrl+C stops the launcher.
The database lives in the ignored `data/` directory. Do not commit it.

Use `DAYLOOM_DEV_WEB_PORT` and `DAYLOOM_DEV_API_PORT` to choose different ports.
Production build: `npm run build`. The API can serve the resulting static client.

### Connect a model

Use **Settings → Model connection** to configure your workspace endpoint, model
and key. Only administrator-approved HTTPS origins are allowed. Saving does not
call the provider; **Test connection** makes a real request. Daily request and
maximum output-token limits are not currency-denominated spending guarantees.

The local single-workspace profile also supports server configuration through an
ignored `.env`, using [.env.example](.env.example) as the field reference:

```dotenv
DAYLOOM_MODEL_PROVIDER=OpenAIProvider
DAYLOOM_MODEL_BASE_URL=https://api.openai.com/v1
DAYLOOM_MODEL_NAME=gpt-4.1-mini
DAYLOOM_MODEL_API_KEY=
```

Enter the key locally; never send it in chat or commit it. The model name is an
example, not a requirement. The configured API must support Chat Completions and
JSON object responses. Restart the service after changing server configuration.

The chat consent checkbox authorizes sending the current message, the last eight
messages, up to 20 active task titles, up to 25 active memories and connected
sender addresses to that provider. Submitted keys are encrypted on the server
and are never returned by configuration reads or exports.
There is a request timeout, a bounded output size and at most five proposals per reply.
Invalid model output does not create actions. No live model call is made by tests.

### Self-host with PostgreSQL

Set `DAYLOOM_ACCESS_TOKEN`, `DAYLOOM_DB_PASSWORD` and a shared API/worker
`DAYLOOM_CREDENTIAL_KEY` locally. See [docs/OPERATIONS.md](docs/OPERATIONS.md)
for key generation and handling. Use a URL-safe database
password, such as a randomly generated hexadecimal value, because it is used in a
database URI. Compose refuses to start without these settings.

```bash
docker compose up --build -d
```

Open http://127.0.0.1:8000 and enter the workspace access token. The database is on
an internal Docker network and is persisted in a named volume. The worker waits
for the API to initialize the schema. Back up the database before upgrading.

Remote use requires an HTTPS reverse proxy, an explicit `DAYLOOM_ALLOWED_ORIGINS`
JSON array and an access token. Do not expose the unprotected development proxy.
This Compose profile remains single-workspace. Multi-account deployment uses
OIDC, a separate runtime database role and forced RLS; real PostgreSQL isolation
verification is required first. Read [SECURITY.md](SECURITY.md).

### Development and verification

```bash
npm run check
npm test
cd apps/web
npx playwright install chromium
npm run test:e2e
```

Browser tests start an isolated service and database on ports 18878 and 18078;
they do not delete the normal development workspace. CI is configured to run
both desktop and mobile viewport tests. A mobile viewport test is not a native-device
test. See [docs/VERIFICATION.md](docs/VERIFICATION.md) for completed local checks
and explicitly unverified environments.

Models, connectors, tools, identity adapters, routes and executors use class-name
registries, module discovery and constructor injection. Add a module with its
registry's `@register`; do not add provider switches to API routes.
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for boundaries and extension rules.

### Mobile route

See [docs/MOBILE.md](docs/MOBILE.md). The web client is functional now. Capacitor
provides a path to native packages, not a promise of App Store readiness. Native
secure storage, login callbacks and Android notification bridges have source
implementations but are not yet compiled or device-verified. Calendar access,
push and share extensions remain follow-ups. iOS cannot read other apps' notifications.
The current web manifest provides install metadata; offline execution is not implemented.

### Deliberate limits

- Mail uses TLS SMTP/app passwords, not Gmail/Graph OAuth; acceptance is not delivery confirmation.
- Scheduled mail repeats authorized fixed content, not dynamically generated summaries. Purchasing is not implemented.
- Browser execution is limited to approved public-page reads and requires an isolated runner with enforced egress policy.
- Android notification capture is opt-in, source-selected and encrypted locally; uploading an item as a task is explicit. No cross-app notification access on iOS.
- Calendar imports are snapshots covering the next 32 days, not live OAuth sync.
- Tasks can be marked blocked; general event triggers, automatic follow-ups and dependencies are not implemented.
- Planning is the rule baseline, not a measured model improvement or an optimizer.
- Memory deletion removes that memory record, not original chats/action payloads.
  Whole-workspace deletion removes application records, not backups or provider copies.
- The worker must stay online. Closing a browser is fine; shutting down its host is not.
- Local effects commit atomically. Uncertain external effects stop at `outcome_unknown`
  without automatic replay; owner-reported reconciliation is not independent provider evidence.
  External exactly-once execution is not claimed.
- Versioned migrations are included; back up before upgrading. Real PostgreSQL/Keycloak,
  model, SMTP, browser and native-device deployment still need validation.
- Full account deletion, KMS, Temporal/LangGraph, monetary budgets, offline sync and store distribution remain unfinished.

### License

Original code is MIT licensed. Third-party dependencies retain their own licenses.
The workspace bitmap and PNG web app icons are generated by [scripts/generate_assets.py](scripts/generate_assets.py).
Native template assets, fonts and other notices are listed in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
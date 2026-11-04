# 未发布账户与原生构建运维

[简体中文](#未发布账户与原生构建运维) | [English](#unreleased-account-and-native-build-operations)

本文描述当前实现，不代表目标架构中的全部功能。不要使用本地开发配置开设公共服务，
也不要将生成的原生项目称为已签名发布版本。

## 本地配置

现有启动器仍支持本地单工作区配置。使用变更后的后端打开现有数据库前，
先停止旧 API 和 worker，并通过 SQLite backup API 备份数据库。启动时会执行 Alembic 迁移。
现有记录保留在旧本地工作区；新账户获得不同工作区，不会继承这些数据。

除非配置了 `DAYLOOM_CREDENTIAL_KEY`，本地模型、邮件和设备凭据使用被 Git 忽略的
`data/credentials.key` 加密，文件权限仅允许所有者访问。
请单独安全备份该密钥；丢失后将无法使用已加密凭据。绝不能将其提交到版本控制。

## 语言与引导设置

共享 Web 客户端支持英语和简体中文。登录前、设置页及内置 `/guide` 页面均可选择语言。
语言选择保存在当前浏览器/设备上，不属于账户设置，也不会改写任务标题、记忆或模型回复。
该功能不翻译其他语种、原生系统对话框或服务商返回的内容。

默认入口是 Agent 工作台；未配置模型也不会强制跳转教程，今日与手动任务仍可使用。引导从导航或设置主动进入。
引导复用真实的模型连接表单和审批控件。预设是可编辑示例，并由
`DAYLOOM_MODEL_ALLOWED_ORIGINS` 过滤；提供预设不代表账户或模型一定兼容。
API 必须支持 Chat Completions 和 JSON object 响应。

保存凭据不会请求模型。连接测试需要明确同意可能产生的费用，且不发送工作区上下文。
首次聊天另行征求上下文和潜在服务商费用的同意。两个步骤都不会自动批准操作。
要执行已批准任务，必须保持 API 和 worker 运行。

引导的本地存储按工作区 ID 隔离，仅包含步骤和完成标记，不包含 API key、聊天草稿或记住的测试授权。
刷新或重新进入引导后需要重新测试；存储失败不阻止设置，但刷新后可能无法保留进度。
v0.3 不增加数据库迁移。

## Agent 与设备执行

v0.4 增加 `0006_agents`，包含运行、步骤、成果和操作关联字段。升级前停止旧 API/worker，备份数据库及凭据密钥；
不要让旧 worker 与新 schema 混用。生产模式需要迁移角色创建新表、安装强制 RLS 并为应用角色授予所需权限。
SQLite 的旧记录保留和重复迁移回归已经通过；真实 PostgreSQL 仍须独立验收。

Agent 使用现有数据库 worker 和注册式后台作业，不依赖 Temporal 或 LangGraph。
默认 8 次规划、最多 24 次，一小时授权；每轮只执行一个工具后再规划。
模型配置变化需在下一次规划前重新确认；暂停会撤回尚未执行的排队授权，已开始的外部操作不保证可撤回。
中断规划和不确定工具结果不会被盲目自动重放。

`DAYLOOM_WEB_SEARCH_ENABLED` 默认开启，`DAYLOOM_WEB_SEARCH_DAILY_LIMIT` 默认 50。
搜索使用现有代理和 TLS 校验，可能受部署网络或服务商限制；一次真实搜索失败不能用替身测试掩盖。
`DAYLOOM_MCP_ALLOWED_SERVERS` 默认空列表，按完整地址允许设备服务；HTTPS 为默认要求，HTTP 仅限回环。
`DAYLOOM_DEVICE_DAILY_LIMIT` 默认 30，分别限制设备发现与调用。设备令牌按工作区、连接编号和地址绑定加密。

发现工具不会执行或自动授权；重新发现会清除旧工具权限。设备调用校验已选工具、参数模式和连接版本，始终需要逐项审批。
第一方电脑服务默认仅回环监听，要求至少 32 字符令牌，并限制网站来源及软件下载目录。
工具运行在服务所在设备，不会自动控制当前浏览器或手机。第三方服务必须按其真实 OS 权限独立隔离。
启动和配置详见 [AGENT_GUIDE.md](AGENT_GUIDE.md)。不要公开测试服务或把模型生成的地址/校验值直接当作可信软件下载目录。

## 账户开发配置

附带的 Keycloak 配置仅用于回环地址上的开发，需要开发者已获授权使用的 Docker daemon。
它不会配置公共生产身份提供方、SMTP 密码找回或验证邮件投递。

1. 在本地设置 `DAYLOOM_IDENTITY_ADMIN_PASSWORD`，然后启动
   `docker compose -f compose.identity.yaml up -d`。
2. 在本地创建 32 字节 Fernet 密钥并设置 `DAYLOOM_CREDENTIAL_KEY`。
   在自己的终端执行 `uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`；
   不要将输出发送到聊天或保存到版本控制中。
3. 在被忽略的本地环境中配置 `DAYLOOM_AUTH_BACKEND=OidcAccess`、
   `DAYLOOM_OIDC_ISSUER=http://127.0.0.1:8089/realms/dayloom`、
   `DAYLOOM_OIDC_CLIENT_ID=dayloom`、`DAYLOOM_OIDC_ALLOW_HTTP=true` 和
   `DAYLOOM_PUBLIC_URL=http://127.0.0.1:5178`。
4. 运行 `npm run dev`。登录按钮会打开身份提供方，在那里注册测试账户。
   不要在这个本地 realm 中使用真实生产密码。
5. 在设置中保存模型端点、模型名和密钥，再明确执行测试。
   测试会发出真实服务商请求，并计入每日请求上限。账户模式不会自动回退到演示模式。

原生登录需要设备可达的 HTTPS API 和 HTTPS 身份提供方、匹配的重定向注册，
以及编译客户端中相同的公共 API URL。手机不能使用开发电脑的回环地址。
原生自定义 scheme 通过独立的 PKCE verifier 保护；该 URL 返回的是一次性票据，而不是 bearer 凭据。
经过验证的 universal/app links 仍是发布加固的后续事项。

## 模型与邮件连接

只能选择管理员批准的 HTTPS 模型 origin 和 SMTP 主机。不要把不可信或私有网络主机加入允许名单。
默认模型适配器使用 Chat Completions 和 JSON object 输出；不兼容的 API 会明确报错。
限制项是每日请求次数和最大输出 token 数，不是以货币计价的账单保证，也不代表已核对服务商发票。

SMTP 凭据加密保存，配置/导出 API 不会返回凭据。服务商支持时，使用特定账户的应用专用密码。
服务商政策可能完全禁用基于密码的 SMTP；当前 SMTP 连接器不能替代尚未完成的 Gmail/Microsoft OAuth 集成。
创建邮件连接不会发送邮件。准备邮件会创建绑定审批的操作。SMTP 受理不代表送达确认。

定时邮件使用冻结的准确内容、有限运行次数和有效期，不是由模型生成的周期摘要。
先预览，再明确授权计划；原始单次提议会被消耗，避免它又被单独批准。
暂停会取消排队执行，并在仍可阻止时阻断后续提交。服务商已经受理的外部操作不能通过暂停撤回。
结果不明的操作不会自动重试。所有者报告的处理结果会明确标注，不能视为独立送达验证。

当前实现的调度器基于数据库。Temporal/LangGraph、动态内容授权、通用补偿和完整外部操作账本
仍属于目标架构工作，不能将这些依赖或能力暗示为已经实现。

## 生产账户配置

`DAYLOOM_PRODUCTION=true` 要求 OIDC、PostgreSQL、HTTPS 公共/issuer URL，以及外部提供的加密密钥。
数据库所有者/迁移角色与应用角色分开。应用角色不能是 superuser、具有 BYPASSRLS 或成为表所有者。
部署前由所有者执行 `PYTHONPATH=backend uv run python -m dayloom.bootstrap` 应用迁移，
然后仅向应用角色授予所需 schema usage 和表 CRUD 权限。
模式版本或工作区 RLS 检查不正确时，API/worker 会拒绝启动。

迁移与应用数据库 URL 必须是不同的本地秘密。运行时初始化不会使用应用角色迁移生产模式。
用户所属表安装 PostgreSQL RLS，并在限定范围的 session 中设置事务局部工作区上下文。
开放多账户前，部署环境必须通过真实 PostgreSQL 集成测试。
CI 包含真实 PostgreSQL 角色/隔离门槛，SQLite 测试不能证明该门槛已通过。

为身份提供方配置准确的重定向 URL、验证邮箱和找回邮件投递、适当的 passkey/MFA、
受限注册、外部身份关联策略及生产后端数据库。
Dayloom 内部会话撤销立即生效；身份提供方全局退出/后通道撤销尚未实现。
完整账户删除和隐私生命周期是发布前置条件。

当前凭据存储使用应用加密密钥，不是 KMS 信封加密。通过秘密管理器提供密钥，
并依照经过审查的迁移流程保护/轮换。
在宣称生产就绪前，仍需要 KMS 集成、用户内容静态加密、安全审查、保留期任务、监控和恢复演练。

现有 `compose.yaml` 仍用于本地单工作区部署。现在必须提供共享的 `DAYLOOM_CREDENTIAL_KEY`，
让 API 和 worker 能解密同一份凭据；它不是生产多账户部署清单。

## 浏览器 worker

已实现的能力是经批准读取公共网页，不包括任意点击、账户登录或结账。
仅在允许的环境中安装可选 Python `browser` extra 并准备 Chromium。
不要绕过企业的浏览器下载政策。

在独立、非 root、启用沙箱的环境中，通过 Uvicorn 运行
`dayloom.browser_server:create_app --factory`。
配置相同的 `DAYLOOM_BROWSER_SHARED_TOKEN`（至少 32 个字符），并在浏览器 worker 中明确设置
`DAYLOOM_BROWSER_ALLOWED_ORIGINS` 和 `DAYLOOM_BROWSER_EGRESS_PROXY`。
在 API/任务 worker 中设置 `DAYLOOM_BROWSER_RUNNER_URL`。不要将 runner 公开暴露。
未配置 runner 时，该能力保持禁用。

出口代理和网络策略必须阻断直接出站连接、私有/回环/link-local/元数据 IPv4 与 IPv6 目标、
DNS rebinding，以及未批准的重定向/子资源。仅指定代理 URL 不能证明网络已隔离。
浏览器禁用 JavaScript、service worker、上传和表单提交，每次操作都使用全新浏览器。
因此部分现代网站无法完整渲染；这是有意限定且明确告知的能力范围。

## Android 与 iOS 产物

`Native packages` 工作流需要手动触发，并提供已部署的 HTTPS API URL。
未启用发布签名时，它会生成明确标注的内部 debug APK，并编译未签名的 iOS 模拟器应用。
这些都不是应用商店发布版本。

要生成已签名 Android APK/AAB，所有者需要配置仓库 secrets
`DAYLOOM_ANDROID_KEYSTORE_BASE64`、`DAYLOOM_ANDROID_STORE_PASSWORD`、
`DAYLOOM_ANDROID_KEY_ALIAS` 和 `DAYLOOM_ANDROID_KEY_PASSWORD`，再明确选择签名 Android 模式。
签名身份及备份由所有者控制。工作流上传私有 CI 产物，不会发布 release 或改变仓库可见性。
产物七天后过期。

iOS TestFlight/App Store 发布仍需要 Apple 开发者团队、provisioning/signing，以及经过真机测试的 archive。
模拟器产物不能安装到普通 iPhone 上。原生桥代码必须编译成功并通过真机测试，
才能确认安全存储或通知行为。

Android 通知采集仅在本地进行，默认关闭，来源由用户从通知监听器当前可见的来源中选择。
采集内容加密保存，最多 100 条，保留不超过 24 小时，并过滤常见认证码内容。
模式过滤无法保证识别所有敏感内容；不要选中敏感应用。权限丢失会清空采集内容并关闭采集。
将一条采集内容上传为任务需要用户明确操作。iOS 不提供跨应用通知读取。
共享 Web UI 现已支持英语和简体中文。
推送投递、原生分享扩展、离线任务同步、更多语种及原生系统本地化仍是后续工作。

## 尚未实现的购买功能

没有启用或宣称任何真实购买集成。实现结账前，必须先选定获授权的商户 API、
客户/支付授权、沙箱凭据、准确报价和预算规则。浏览器阅读器不能提交订单。
通用支付 SDK 不代表有权向任意商户购买，真实购买需要单独明确批准。

---

# Unreleased Account and Native Build Operations

This document describes the current implementation, not all features in the
target architecture. Do not start a public service using the local development
profile or claim that a generated native project is a signed release.

## Local profile

The existing launcher still supports a local, single-workspace profile. Before
starting the changed backend against an existing database, stop its old API and
worker and back up SQLite using the SQLite backup API. Startup runs Alembic
migrations. Existing records stay in the legacy local workspace; new accounts
receive different workspaces and do not inherit that data.

Local model/mail credentials use an encryption key in the ignored
`data/credentials.key` with owner-only permissions unless
`DAYLOOM_CREDENTIAL_KEY` is configured. Back up the key separately and securely:
losing it makes encrypted credentials unusable. Never commit it.

## Language and guided setup

The shared web client supports English and Simplified Chinese. Language selection
is available before sign-in, in Settings and in the embedded `/guide` route. It is
stored on the current browser/device, not in account settings, and does not rewrite
task titles, memories or model replies. Other locales, native system dialogs and
provider-supplied content are not translated by this feature.

Agent is the default entry. Missing model configuration does not force a guide redirect;
Today and manual tasks remain available. Enter the guide explicitly from navigation or Settings. It reuses the actual model
connection form and approval controls. Presets are editable examples filtered by
`DAYLOOM_MODEL_ALLOWED_ORIGINS`; a preset is not proof of account/model compatibility.
The API must support Chat Completions and JSON object responses.

Saving credentials makes no model request. The connection test requires explicit
cost consent and sends no workspace context. The first chat has separate consent
for its context and potential provider charges. Neither step auto-approves actions.
Keep the API and worker running for approved tasks to execute.

Local guide storage is scoped by workspace ID and contains only a step and completion
flag. It never contains an API key, chat draft or remembered test authorization.
Reloading or returning to the guide requires a new test; storage failure does not
block setup, but progress may not survive a reload. v0.3 adds no database migration.

## Agent and Device Execution

v0.4 adds `0006_agents` with runs, steps, artifacts and action association. Stop the old API/worker and back up the database and credential key before upgrading.
Do not mix an old worker with the new schema. Production requires the migration role to create tables, install forced RLS and grant application-role permissions.
SQLite data preservation and repeat migration regressions passed; real PostgreSQL still requires independent acceptance.

Agent uses the existing database worker and registered background jobs, not Temporal or LangGraph.
The default is 8 planning calls, at most 24, with one-hour authority and one tool before each replan.
Model changes require renewed confirmation before the next plan. Pause revokes queued authority but cannot guarantee recall of already-started external effects.
Interrupted planning and uncertain tool outcomes are not blindly replayed.

`DAYLOOM_WEB_SEARCH_ENABLED` defaults to true; `DAYLOOM_WEB_SEARCH_DAILY_LIMIT` defaults to 50.
Search retains existing proxy and TLS verification and may be limited by networking/providers; a failed live search is not hidden by mocked tests.
`DAYLOOM_MCP_ALLOWED_SERVERS` defaults to an empty list and approves exact service addresses. HTTPS is required except for loopback HTTP.
`DAYLOOM_DEVICE_DAILY_LIMIT` defaults to 30 and separately limits discovery/invocation. Device credentials are encrypted and bound to workspace, connection ID and endpoint.

Discovery neither executes nor auto-authorizes tools, and rediscovery clears previous permissions. Device calls validate selection, schema and connection version and always require per-call approval.
The first-party computer service is loopback-only by default, requires a token of at least 32 characters and restricts website origins and the software catalog.
Tools run on the service-host device, not automatically in the current browser or phone. Third-party services need isolation appropriate to their OS permissions.
See [AGENT_GUIDE.md](AGENT_GUIDE.md) for setup. Never publish test services or trust model-invented download addresses/hashes as a software catalog.

## Account development profile

The included Keycloak profile is for loopback development only. It needs a Docker
daemon the developer is already authorized to use. It does not configure a public
production identity provider, SMTP password recovery or verified-email delivery.

1. Set `DAYLOOM_IDENTITY_ADMIN_PASSWORD` locally and start
   `docker compose -f compose.identity.yaml up -d`.
2. Create a 32-byte Fernet key locally and set `DAYLOOM_CREDENTIAL_KEY`. Generate
   it in your own terminal with `uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`;
   do not send the output in chat or store it in version control.
3. Configure `DAYLOOM_AUTH_BACKEND=OidcAccess`,
   `DAYLOOM_OIDC_ISSUER=http://127.0.0.1:8089/realms/dayloom`,
   `DAYLOOM_OIDC_CLIENT_ID=dayloom`, `DAYLOOM_OIDC_ALLOW_HTTP=true`, and
   `DAYLOOM_PUBLIC_URL=http://127.0.0.1:5178` in the ignored local environment.
4. Run `npm run dev`. The sign-in button opens the identity provider. Register
   test accounts there. Never use real production passwords in this local realm.
5. In Settings, save a model endpoint/model/key, then explicitly test it. The
   test makes a real provider request and counts toward the daily request limit.
   Account mode has no automatic demo fallback.

For native login, use a reachable HTTPS API and HTTPS identity provider, matching
redirect registration, and the same public API URL in the compiled client. A
phone cannot use the development machine's loopback address. The native custom
scheme is protected by a separate PKCE verifier; a one-time ticket, not a bearer
credential, is returned through that URL. Verified universal/app links remain a
release-hardening follow-up.

## Model and mail connections

Only administrator-approved HTTPS model origins and SMTP hosts are selectable.
Do not add untrusted or private-network hosts to the allowlists. The default
model adapter uses Chat Completions with JSON object output; incompatible APIs
fail visibly. Limits are daily request counts and maximum output tokens, not a
currency-denominated billing guarantee or provider invoice reconciliation.

SMTP credentials are encrypted and never returned through configuration/export
APIs. Use an account-specific app password where the provider supports it.
Provider policy may disable password-based SMTP entirely; the current SMTP
connector does not replace Gmail/Microsoft OAuth integrations, which remain
unfinished. Creating a mail connection does not send anything. Preparing a mail
creates an approval-bound action. SMTP acceptance is not delivery confirmation.

Scheduled mail uses exact frozen content, finite runs and an expiry. It is not a
model-generated recurring summary. Preview and explicitly authorize the schedule;
the original one-off proposal is consumed so it cannot also be approved separately.
Pause cancels queued executions and blocks later commits where still possible.
An external operation already accepted by a provider cannot be recalled by pause.
Uncertain effects are not retried automatically. Owner-reported resolution is
labeled as such and is not independent delivery verification.

The scheduler is database-backed in this implementation. Temporal/LangGraph,
dynamic content mandates, generalized compensation and a full effect ledger are
still target-architecture work, not dependencies silently claimed as implemented.

## Production account profile

`DAYLOOM_PRODUCTION=true` requires OIDC, PostgreSQL, HTTPS public/issuer URLs and
an externally supplied encryption key. Use separate database owner/migration and
application roles. Never configure the application role as superuser, BYPASSRLS,
or table owner. Apply migrations with the owner before deployment using
`PYTHONPATH=backend uv run python -m dayloom.bootstrap`, then grant only required
schema usage and table CRUD to the application role. The API/worker refuse to
start if the schema version or workspace RLS checks are wrong.

Migration and application database URLs must be different local secrets. Runtime
initialization does not migrate production schemas using the application role.
PostgreSQL RLS is installed for user-owned tables and transaction-local workspace
context is set on scoped sessions. The live PostgreSQL integration test must pass
in the deployment environment before exposing multiple accounts. CI adds a real
PostgreSQL role/isolation gate; a SQLite test does not prove that gate.

Configure the identity provider with exact redirect URLs, verified email and
recovery delivery, passkeys/MFA as appropriate, restricted registration, external
identity linking policy, and a production backing database. Session revocation
inside Dayloom is immediate; global identity-provider logout/backchannel revocation
is not implemented. Full account deletion and privacy lifecycle are release gates.

The current credential store uses an application encryption key, not KMS envelope
encryption. Provide that key through a secret manager and protect/rotate it with a
reviewed migration procedure. KMS integration, at-rest user-content encryption,
security review, retention jobs, monitoring and restore drills are still required
before describing this implementation as production-ready.

The existing `compose.yaml` remains a local single-workspace deployment. It now
requires one shared `DAYLOOM_CREDENTIAL_KEY` so API and worker can decrypt the same
credentials; it is not the production multi-account deployment manifest.

## Browser worker

The implemented capability is approved public-page reading, not arbitrary
clicking, account login or checkout. Install the optional `browser` Python extra
and provision Chromium only in an environment that permits it. Do not bypass
corporate browser-download policy.

Run `dayloom.browser_server:create_app --factory` under Uvicorn in a separate,
non-root, sandbox-enabled environment. Configure matching
`DAYLOOM_BROWSER_SHARED_TOKEN` values (at least 32 characters), explicit
`DAYLOOM_BROWSER_ALLOWED_ORIGINS`, and `DAYLOOM_BROWSER_EGRESS_PROXY` on the worker.
Set `DAYLOOM_BROWSER_RUNNER_URL` on the API/work worker. Do not expose the runner
publicly. No runner configuration means the capability remains disabled.

The egress proxy and network policy must block direct outbound connections,
private/loopback/link-local/metadata IPv4 and IPv6 destinations, DNS rebinding and
unapproved redirects/subresources. Merely specifying a proxy URL does not prove
network isolation. The browser has JavaScript, service workers, uploads and form
submission disabled and uses a fresh browser per operation. Some modern sites
will therefore not render completely; this is intentional, visible scope.

## Android and iOS artifacts

The `Native packages` workflow is manual. Provide a deployed HTTPS API URL.
Without release signing enabled it creates a clearly labeled internal debug APK
and compiles an unsigned iOS simulator app. These are not store releases.

For a signed Android APK/AAB, the owner configures repository secrets
`DAYLOOM_ANDROID_KEYSTORE_BASE64`, `DAYLOOM_ANDROID_STORE_PASSWORD`,
`DAYLOOM_ANDROID_KEY_ALIAS`, and `DAYLOOM_ANDROID_KEY_PASSWORD`, then explicitly
selects signed Android mode. Keep the signing identity and backups under owner
control. The workflow uploads private CI artifacts and does not publish releases
or change repository visibility. Artifacts expire after seven days.

iOS TestFlight/App Store release still requires an Apple developer team,
provisioning/signing and a device-tested archive. The simulator artifact cannot be
installed on an ordinary iPhone. The native bridge code must compile and pass real
device tests before its secure-storage or notification behavior is certified.

Android notification capture is local-only, disabled by default, based on user
selected sources currently visible to the notification listener. Capture is
encrypted, capped at 100 events, retained at most 24 hours and filtered for common
authentication-code content. Pattern filtering cannot guarantee detection of all
sensitive content; keep sensitive apps unselected. Permission loss clears capture
and disables it. Uploading one captured item as a task is an explicit user action.
iOS cross-app notification reading is not available. The shared web UI now supports
English and Simplified Chinese. Push delivery, native share extensions, offline task
synchronization, additional locales and native-system localization remain follow-ups.

## Unimplemented commerce

No live purchase integration is enabled or claimed. Selecting an authorized
merchant API, customer/payment grants, sandbox credentials, exact quotation and
budget rules is necessary before implementing checkout. The browser reader
cannot submit orders. A generic payment SDK is not authorization to buy from
arbitrary merchants, and real purchases need separate explicit approval.
# 验证记录

[简体中文](#验证记录) | [English](#verification)

以下是尚未发布实现在 Linux 上的本地验证记录，日期为 2026-11-02。
这些结果是开发证据，不是生产、原生设备或应用商店认证。
部署前置条件和限制见[运维文档](OPERATIONS.md)。

## v0.3 语言与新手引导

- 格式化改动的前端文件后，`npm run check` 通过：Ruff、Oxlint、五个新增 Node 单元测试、
  TypeScript 和 Vite 生产构建。
- `cap sync` 成功将最终 v0.3 Web 构建复制到 Android 和 iOS 项目。
  这是资源/插件同步，不是原生编译、签名或真机验收。
- 使用 `uv run --locked pytest backend/tests -q`，后端回归仍为
  **41 项通过，1 项 PostgreSQL 测试跳过**。
- 单元测试覆盖每个静态翻译调用的简体中文条目、插值/英语回退且不改写用户内容、
  按工作区隔离的引导存储、不含秘密的进度序列化、格式错误的进度及存储被阻止的情况。
- Playwright 发现 **14 个桌面/移动端测试实例**。新增场景涵盖语言持久化及引导设置，
  包括重试、同意、密钥清除、刷新/重新测试和明确的本地审批。
  发现用例不等于执行；主机已有的 Chromium 限制仍阻止获得独立测试套件结果。
- 集成验收使用新建、隔离的 `data/preview-v03.db`，初始未配置模型。
  检查了空工作区引导、跳过/恢复、中文持久化、切回英语，以及已有任务标题保持不变。
- 服务商预设填入可编辑示例，切换服务商会清除已输入的合成密钥。
  真实后端保存了合成连接，但配置读取不返回密钥，引导进度也不存储密钥。
- 受控 HTTP 响应覆盖连接测试失败、重试/成功、独立的首次聊天同意，以及刷新后回到测试。
  未发出真实服务商请求，也未将已保存连接视为已经验证。
- 合成模型回复引用了真实本地 `CreateTask` 提议。批准前：零任务、提议待处理、零次尝试。
  点击引导中的批准按钮后：恰好一个任务、提议成功、真实 worker 尝试一次。
  完成引导仅持久化 `{ "step": 4, "completed": true }`。
- 随后移除了合成连接和生成的测试任务，预览恢复为 `UnconfiguredProvider`。
  无害的本地审计/操作历史保留。未使用真实凭据、邮件、购买或付费模型调用。
- 所有七条路由均在实际 CSS 尺寸 **1440 x 900** 和 **390 x 844** 下检查，
  页面无水平溢出。中文 API 表单适配移动视口，切换步骤后焦点移到固定栏下方的标题。
  下文所述集成浏览器隐藏视图/指针限制仍适用；这不是完整的指针、屏幕阅读器或原生设备无障碍认证。

## v0.2 已通过的本地检查

- 后端使用 `uv run pytest backend/tests -q`，结果为 **41 项通过，1 项跳过**。
  跳过的是真实 PostgreSQL 集成测试，不是成功完成的隔离测试。
- 原有任务/记忆/规划/日历行为、准确内容审批、乐观并发编辑、本地 worker 恢复、导出和删除回归测试。
- 按工作区隔离的读取、别名、写入和 worker；拒绝跨工作区修改；保留旧记录的版本化 SQLite 迁移。
- 使用模拟 HTTP transport 的已签名 OIDC Authorization Code/PKCE 交换，
  signature/issuer/audience/nonce 校验，绑定原生 PKCE 的一次性票据，cookie CSRF 保护、会话轮换及撤销。
  使用真实 OAuth 类，但测试中的身份提供方不是真实在线服务。
- 加密的工作区模型凭据、不返回秘密的 API 读取、已批准端点检查、明确的外部上下文同意、
  请求配额，以及不隐式回退到演示模式。
- 使用受控测试替身验证 SMTP：审批、连接撤销、不重放的结果不明操作恢复、
  固定内容有限次数计划、来源提议消耗、暂停，以及所有者报告结果的处理。
- 使用测试替身验证浏览器 runner 认证及已批准 origin/重定向边界。
  这些测试不能证明真实 Chromium 或网络隔离有效。
- `npm run check`：Ruff lint/format、Oxlint、TypeScript 和 Vite 生产构建。
  改动的前端源码已格式化，并重新运行前端检查。
- 在 `apps/web` 中执行 `npx cap sync`：最终 Web 资源和 App/Browser 插件已同步到两个原生项目。
  这不是原生编译结果。
- Compose/workflow/identity-realm 和原生 manifest/plist 结构检查。
  两个原生 CI job 的实际 URL 校验代码均已测试：接受 HTTPS，拒绝 HTTP、userinfo、query-string 和 fragment 输入。

## v0.2 集成浏览器验收

升级预览使用 `data/preview-v02.db`，通过 SQLite backup API 从现有本地数据库创建。
迁移后原有五个任务全部保留。原数据库和之前的开发服务均未改动。

- 使用合成密钥保存模型配置，检查读取不泄露秘密后断开连接。
  未点击连接测试按钮，也未调用真实服务商。
- 保存合成 SMTP 连接且不泄露凭据。授权前邮件提议保持待处理，执行尝试为零。
- 审查准确内容计划，授权次日执行一次后暂停。
  API 核验确认生成运行次数为零，被消耗的来源提议已取消且尝试为零，没有活动的测试计划。
  随后断开合成邮箱连接。
- 实际 CSS 视口为 1440 x 900 和 390 x 844：设置和活动页面布局检查未发现水平溢出。
  移动端模型对话框及控件位于视口内。已检查可获取的桌面/移动端截图。
- 部分最终控件通过 DOM 事件触发，因为集成浏览器在后台隐藏，指针点击超时。
  状态断言使用实际 UI handler 和在线预览 API。
  隐藏视图截图可能过时或被裁切；这些检查不是完整的指针交互测试套件。

没有发送真实邮件、进行购买、开通付费服务或公开发布。
此前记录的 2026-10-30 v0.1 浏览器检查覆盖原有六个视图、任务/记忆 CRUD 及本地提议审批/执行，
不能作为原生或账户模式行为的新证据。

## 未验证或未实现

- 独立 Playwright 执行：主机企业政策阻止 Chromium 下载。
  集成浏览器检查是独立证据，不代表 CLI 测试套件通过。
- Docker 镜像/Compose 部署、真实 PostgreSQL RLS/运行时角色行为，以及 Keycloak 部署。
  Docker socket 访问被拒绝，未尝试提权。CI 包含专门的 PostgreSQL 服务/角色测试门槛。
- 真实模型、SMTP 和隔离浏览器执行。未使用真实凭据。
  服务商兼容性、投递及网络/DNS 隔离仍是部署前置条件。
- Android/iOS 编译、签名、可安装产物、实际安全存储、原生回调处理、通知采集和真机无障碍。
  本地缺少 Android SDK/Java；iOS 编译需要 macOS/Xcode。
- 未触发手动原生工作流。不宣称远程 CI 成功、已有签名 APK/AAB、TestFlight 构建或达到上架条件。
- 购买、Gmail/Graph OAuth、动态内容自动化、完整账户删除、身份提供方后通道退出、KMS、
  Temporal/LangGraph、货币计费额度、推送、分享扩展和离线同步仍未完成。
- 不宣称支持多 worker SQLite、外部 exactly-once 效果或公共生产就绪。
  定义了 PostgreSQL 策略不等于已证明隔离有效。

## 环境说明

测试会输出上游 Authlib/Starlette 关于未来 HTTPX 迁移的警告。
多项目编辑器的 Python 环境在部分文件中报告 SQLAlchemy 导入无法解析；
项目本地 `uv` 环境可以解析这些依赖且测试通过。
未更改整个工作区的解释器，以免影响其他项目。

CI 为具备相应环境的运行器提供浏览器、PostgreSQL 和手动原生工作流。
本地检查不代表这些远程 job 已执行。

---

# Verification

Unreleased implementation verified locally on Linux, 2026-11-02. These results
are development evidence, not production, native-device or store certification.
See [OPERATIONS.md](OPERATIONS.md) for deployment prerequisites and limitations.

## v0.3 Language and Onboarding

- `npm run check` passed after formatting the changed frontend files: Ruff,
  Oxlint, the five new Node unit tests, TypeScript and the Vite production build.
- `cap sync` copied the final v0.3 web build into both Android and iOS projects
  successfully. This is asset/plugin synchronization, not native compilation,
  signing or device acceptance.
- Backend regression remained **41 passed, 1 PostgreSQL skipped** with
  `uv run --locked pytest backend/tests -q`.
- Unit coverage checks every static translation call for a Simplified Chinese
  entry, interpolation/English fallback without user-content rewriting, per-workspace
  guide storage, secret-free progress serialization, malformed progress and blocked storage.
- Playwright discovered **14 desktop/mobile test instances**. The added scenarios
  cover language persistence and guided setup, including retry, consent, key clearing,
  reload/retest and explicit local approval. Discovery is not execution; the host's
  existing Chromium restriction still prevents a standalone suite result.
- Integrated acceptance used a new isolated `data/preview-v03.db`, with the model
  initially unconfigured. Empty-workspace onboarding, skip/resume, Chinese persistence,
  switching back to English and preservation of an existing task title were checked.
- Provider presets populated editable examples and switching providers cleared the
  entered synthetic key. The real backend saved the synthetic connection without
  returning its key through configuration reads or storing it in tutorial progress.
- Controlled HTTP responses exercised a failed connection test, retry/success,
  separate first-chat consent and returning to the test after reloading. No live
  provider request was made and a saved connection was not treated as verified.
- A synthetic model reply referenced a real local `CreateTask` proposal. Before
  approval: zero tasks, pending proposal, zero attempts. After the guide's approval
  button: exactly one task, succeeded proposal, one attempt from the real worker.
  Completing the guide persisted only `{ "step": 4, "completed": true }`.
- The synthetic connection and generated test task were removed afterward; the
  preview returned to `UnconfiguredProvider`. Harmless local audit/action history
  remains. No real credentials, email, purchase or paid model call were used.
- All seven routes were checked at actual CSS sizes of **1440 x 900** and
  **390 x 844**, without horizontal document overflow. The Chinese API form fit
  the mobile viewport, and a step change focused its heading below the fixed bar.
  Integrated-browser hidden-view/pointer limitations below still apply; this is
  not a complete pointer, screen-reader or native-device accessibility certification.

## v0.2 Passed Local Checks

- Backend: **41 passed, 1 skipped** using `uv run pytest backend/tests -q`.
  The skip is the real PostgreSQL integration test, not a successful isolation run.
- Original task/memory/planning/calendar behavior, exact-content approvals,
  optimistic edits, local worker recovery, export and deletion regression tests.
- Workspace-scoped reads, aliases, writes and workers; cross-workspace mutation
  rejection; versioned SQLite migration retaining legacy records.
- Signed OIDC Authorization Code/PKCE exchange with mocked HTTP transport,
  signature/issuer/audience/nonce validation, native PKCE-bound single-use ticket,
  cookie CSRF protection, session rotation and revocation. Real OAuth classes are
  used; the identity provider itself is not a live service in these tests.
- Encrypted workspace model credentials, secret-free API reads, approved endpoint
  checks, explicit external-context consent, request quotas and no implicit demo fallback.
- SMTP with a controlled test double: approval, connection revocation, ambiguous
  effect recovery without replay, fixed-content finite schedules, source-proposal
  consumption, pause and owner-reported outcome handling.
- Browser runner authentication and approved-origin/redirect boundaries with test
  doubles. These tests do not establish real Chromium or network isolation.
- `npm run check`: Ruff lint/format, Oxlint, TypeScript and Vite production build.
  The changed frontend sources were formatted and the frontend gates rerun.
- `npx cap sync` in `apps/web`: final web assets and App/Browser plugins synchronized
  into both native projects. This is not a native compilation result.
- Compose/workflow/identity-realm and native manifest/plist structural checks.
  Both native CI jobs' actual URL guard code was exercised with accepted HTTPS
  and rejected HTTP, userinfo, query-string and fragment inputs.

## v0.2 Integrated Browser Acceptance

The upgraded preview used `data/preview-v02.db`, created with SQLite's backup API
from the existing local database. All five original tasks remained after migration.
The original database and previous development service were left untouched.

- Model configuration saved with a synthetic key, checked for secret-free reads
  and disconnected. No connection-test button or live provider call was used.
- Synthetic SMTP connection saved without credential disclosure. A mail proposal
  remained pending with zero execution attempts before authorization.
- An exact-content schedule was reviewed, authorized for the following day with
  a one-run limit, and paused. API verification confirmed zero generated runs,
  the consumed source proposal cancelled with zero attempts, and no active test
  schedule. The synthetic mailbox was disconnected afterward.
- Actual CSS viewports of 1440 x 900 and 390 x 844: Settings and Activity layout
  checks found no horizontal overflow. The mobile model dialog and its controls
  fit within the viewport. Available desktop/mobile screenshots were inspected.
- Some final controls were activated through DOM events because the integrated
  browser was background-hidden and pointer clicks timed out. State assertions
  used the actual UI handlers and live preview API. Screenshots from a hidden view
  can be stale or clipped; these checks are not a full pointer-interaction suite.

No real email, purchase, paid service provisioning or public publication occurred.
The previously recorded v0.1 browser checks on 2026-10-30 covered the original
six views, task/memory CRUD and local proposal approval/execution; they are not
new evidence for native or account-mode behavior.

## Not Verified or Not Implemented

- Standalone Playwright execution: this host's corporate policy blocks Chromium
  downloads. The integrated browser checks are separate, not a CLI suite pass.
- Docker image/Compose deployment, real PostgreSQL RLS/runtime-role behavior and
  Keycloak deployment. Docker socket access was denied; no privilege escalation
  was attempted. CI contains a dedicated PostgreSQL service/role test gate.
- Live model, SMTP and isolated-browser execution. No real credentials were used.
  Provider compatibility, delivery and network/DNS isolation remain deployment gates.
- Android/iOS compilation, signing, installable artifacts, actual secure storage,
  native callback handling, notification capture and real-device accessibility.
  Android SDK/Java were unavailable locally; iOS compilation needs macOS/Xcode.
- The manual native workflow was not dispatched. No remote CI success, signed
  APK/AAB, TestFlight build or store readiness is claimed.
- Purchasing, Gmail/Graph OAuth, dynamic-content automation, full account deletion,
  identity-provider backchannel logout, KMS, Temporal/LangGraph, monetary billing
  limits, push, share extensions and offline synchronization remain unfinished.
- Multi-worker SQLite, external exactly-once effects and public production readiness
  are not claimed. A PostgreSQL policy definition is not proof of effective isolation.

## Environment Notes

Tests emit upstream Authlib/Starlette warnings about their future HTTPX migration.
The multi-project editor's Python environment reports unresolved SQLAlchemy imports
in some files; the project-local `uv` environment resolves them and passes tests.
No workspace-wide interpreter change was made to affect unrelated projects.

CI includes browser, PostgreSQL and manual native workflows for appropriately
provisioned environments. Local checks do not imply those remote jobs have run.
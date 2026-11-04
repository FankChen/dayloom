# 用户实测反馈与下一步计划

[简体中文](#用户实测反馈与下一步计划) | [English](#user-feedback-and-next-steps)

首轮反馈日期：2026-11-03。用户随后授权开始 Agent 大版本。当前 v0.4 首轮源码已实现，属于尚未正式发布的开发预览；后续商业平台、手机和分发计划仍不代表已实现。

当前使用与设备连接说明见 [AGENT_GUIDE.md](AGENT_GUIDE.md)。已落地持久化多步运行、成果、MCP 工具接入和工作台；真实交易、手机控制与低门槛安装包仍是后续工作。

## 总体判断

核心问题不是任务功能不够多，而是普通用户从进入产品到获得实际结果的路径不完整。
Dayloom 应以“调用具体工具完成一件事”为主线，任务只是可选的记录方式，不应成为所有请求的默认终点。
第 8 条是产品方向的最高优先级；第 1、4 条是使用门槛；第 2、3、5、6、7 条是本轮先修的信任和交互问题。

## 八条反馈的处理

| 编号 | 判断 | 本轮处理或下一步方案 |
| --- | --- | --- |
| 1 下载太麻烦 | 分发方式问题，先设计 | 普通用户优先通过一个受控 Web 入口访问；源码安装保留给开发者。再评估带运行环境的本地安装包，不把更多终端命令当成解决方案。 |
| 2 今日强制跳教程 | 立即修 | 未配置模型也留在今日，以可主动点击的连接入口替代静默跳转；任务和日程仍可使用。 |
| 3 话术生硬 | 立即修，支持渠道另行配置 | 解释当前服务尚未开放、可选的下一步，以及已有数据不受影响。技术配置收在详情中，不将安全限制伪称为“功能开发中”。 |
| 4 只有 API 接入教程 | 已补 API 说明与 Agent 使用指南 | 已补官方 API 获取说明和完整的目标、工具、审批、成果与设备连接文档；内置模型连接教程仍保留。 |
| 5 打勾无确认、撤回难找 | 立即修 | 今日与任务页共用完成确认；取消不写入状态，已完成列表提供明确的“撤回完成”，恢复为待办。 |
| 6 邮箱授权码不明、不能编辑 | 立即修 | 解释授权码与登录密码的区别；原地编辑保留连接编号并递增版本；独立、明确同意的登录验证不发送邮件，区分验证成功、登录被拒绝和网络失败。 |
| 7 回复偶尔跑到问题上方 | 局部修复，加回归 | 修复同时间戳的问答排序，页面和模型历史保持一致。更完整的并发对话和工具结果归属在下一阶段使用轮次与执行编号设计。 |
| 8 只能建任务、偏离初衷 | 核心方向，首轮已实现 | Agent 已成为默认入口，具备结果驱动的多步运行、审批、成果和 MCP 设备接入；先验证完整流程，再扩具体商家与手机能力。 |

联系方式应由部署者配置，可选择反馈链接、邮箱或电话，不把作者手机号写死到所有部署中。
如果源码仓库是私有的，其 GitHub issues 不能作为普通用户唯一的反馈入口。

## 当前能力与缺口

代码已注册 `CreateTask`、`SaveMemory`、`PrepareBrief`、`SendEmail`、`ReadWebPage`、`SearchWeb`、`SaveArtifact`、`ListDeviceTools` 和 `CallDeviceTool`。
邮件需要有效连接与准确内容审批；网页读取需要管理员启用隔离浏览器、允许目标来源并落实网络隔离。
这些外部工具的源码和模拟测试，不等于已经完成真实服务验收。

原先工具入口和结果组织不足的问题已通过 Agent 工作台开始解决。下一步缺口是部署网络中的真实检索、真实模型能力、首发设备和商业平台集成，而不是继续扩大任务功能。
优先复用现有注册表、审批、队列和执行器；新增工具通过独立模块与注册装饰器接入，不在核心入口堆工具分支。

## 建议推进顺序

1. **此前小修：继续用户复测。** 今日入口、任务确认/撤回、邮箱编辑/验证和对话排序已完成。此前小修不涉及迁移，但新的 v0.4 需要 `0006_agents`，升级前必须备份并停旧进程。
2. **当前阶段：Agent 首轮验收。** 多步运行、工具工作台、成果与 MCP 接入已实现。用真实模型和获准设备检查可用性、权限、失败处理和成果；不要把离线演示当作能力评估。
3. **随后：低门槛试用与完整教程。** 普通用户从一个邀请制 Web 地址开始，不安装 Git、Node 或 Python；自托管者保留单独部署说明。新教程覆盖选择工具、提供材料、核对影响、授权、查看结果、处理失败，而不是强制先买 API。
4. **通过实测后再扩展。** 根据目标用户选择邮箱 OAuth、日历连接、文件处理或本地安装包。原生包、任意网站操作、购买和支付分别需要设计、环境与安全验收，不承诺自动纳入本轮。

## 工具版最小范围

| 流程 | 用户输入 | 预期结果 | 必须保留的边界 |
| --- | --- | --- | --- |
| 网页资料整理 | 指定公开 HTTPS 网页和整理要求 | 有来源链接的整理结果，可保存或导出为工作区成果 | 网页读取仍限定已允许来源，资料不能变成工具指令。成果保存已实现；真实检索与模型质量仍需验收。 |
| 内容整理并发邮件 | 用户材料或已批准的网页内容、收件人和目标 | 可修改的纯文本草稿；批准准确内容后执行并展示发送结果 | 保存配置不等于登录验证，登录验证不等于发送，SMTP 接受不等于已投递；结果不明时不得盲目重发。 |

工具页面应复用工具元数据和参数模式，显示所需连接、数据去向、外部影响、审批要求及可否重试。
不通过隐藏切换成演示模型来制造成功，不用生成一个任务冒充已经完成用户要求。

## 验收标准

- 对同一组用户材料与配置，先记录当前 v0.3 的操作步骤和失败点，再对比新流程；不把模拟结果算作真实服务完成。
- 新用户无需终端即可进入获准的试用环境，并能完成一个有可见结果的工具流程。
- 两条主流程均覆盖成功、未配置、拒绝授权、可恢复失败和结果不明；结果能追溯到原问题和实际工具调用。
- 刷新后能看到已持久化的执行状态；重复点击不会重复发送，撤销操作明确区分“尚未执行”与“已经产生外部效果”。
- 桌面和手机上的中英文按钮、表单、状态与错误信息可读且不重叠；不能连接时有可执行的下一步。
- Web 试用上线前通过身份隔离、HTTPS、密钥保护、备份和真实 PostgreSQL 等部署门槛，不能直接公开本地单用户服务。

## 需要确认的决策

- **首批场景：** 建议先确认上面的网页整理和邮件两条流程，暂缓购买与任意网站自动操作。
- **首批用户：** 建议先做小范围邀请试用，再决定是否提供本地优先版本及优先支持的操作系统。
- **模型费用：** 默认仍可使用自带 API；托管试用额度需要另外确认预算、额度与滥用控制，不把请求次数限制描述为金额上限。
- **支持渠道：** 由部署者选择可访问的反馈地址及是否公开联系电话，不依赖用户拥有私有源码仓库权限。

本轮证据与未验证边界见 [VERIFICATION.md](VERIFICATION.md)，部署约束见 [OPERATIONS.md](OPERATIONS.md)。
本轮实现授权不等于云资源开通、真实邮件发送、商家交易、仓库公开或原生发布授权。

---

# User Feedback and Next Steps

Initial feedback date: 2026-11-03. The user subsequently authorized the Agent major update. The first v0.4 source implementation is a development preview, not a formal release; later commerce, phone and distribution plans are not implemented claims.

See [AGENT_GUIDE.md](AGENT_GUIDE.md) for current usage and device connections. Persisted multi-step runs, artifacts, MCP tools and the workbench are implemented; real transactions, phone control and easy installers remain future work.

## Overall Assessment

The main problem is not a shortage of task features. The path from entering the product to obtaining a useful result is incomplete for ordinary users.
Dayloom should center on completing real work with specific tools. A task is an optional record, not the default destination of every request.
Item 8 is the highest product priority; items 1 and 4 are adoption barriers; items 2, 3, 5, 6 and 7 are the trust and interaction fixes addressed first.

## Handling All Eight Issues

| Item | Assessment | Current change or proposed next step |
| --- | --- | --- |
| 1 Downloading is complicated | Distribution problem; design first | Prefer one controlled Web entry for ordinary users and retain source installation for developers. Evaluate bundled local installers afterward rather than adding more terminal commands. |
| 2 Today redirects abruptly | Fix now | Stay on Today without a configured model; replace silent navigation with an explicit connection link. Tasks and planning remain available. |
| 3 Unfriendly wording | Fix now; configure support separately | Explain that this server has not enabled the provider, offer next steps and reassure users that existing data is unaffected. Keep technical configuration in details; do not mislabel a security restriction as a feature under development. |
| 4 The guide only covers API setup | API help and Agent usage guide added | Official API acquisition and the full goal/tool/approval/artifact/device workflow are documented; the embedded model-connection guide remains available. |
| 5 Completion lacks confirmation and reopening is hard to find | Fix now | Today and Tasks share a confirmation control. Cancel leaves the task unchanged; Completed has an explicit reopening action that restores ready status. |
| 6 App passwords are unclear and mail cannot be edited | Fix now | Explain app passwords versus normal sign-in passwords; edit connections in place with the same ID and a new version. Separate, explicitly consented sign-in checks send no email and distinguish success, rejected authentication and network failures. |
| 7 Replies sometimes precede questions | Targeted fix with regression coverage | Stabilize equal-timestamp ordering for both the page and model history. Design turn and execution identifiers for fuller concurrent-conversation and tool-result association in the next phase. |
| 8 Task creation misses the original goal | Core direction; first implementation complete | Agent is now the default entry, with result-driven multi-step runs, approval, artifacts and MCP device connections. Verify complete workflows before expanding merchant and phone capabilities. |

Support details should be deployment-configurable: feedback URL, email or phone, without hard-coding the author's number into every deployment.
If the source repository is private, its GitHub issues cannot be the only feedback channel for ordinary users.

## Existing Capabilities and Gaps

The code registers `CreateTask`, `SaveMemory`, `PrepareBrief`, `SendEmail`, `ReadWebPage`, `SearchWeb`, `SaveArtifact`, `ListDeviceTools` and `CallDeviceTool`.
Mail requires a valid connection and exact-content approval. Web reading requires an enabled isolated browser, approved origins and enforced network isolation.
External-tool source and mocked tests are not evidence of live-service acceptance.

The Agent workbench starts addressing the former entry-point and result-organization gaps. The remaining work is live search on the deployment network, real-model capability, target devices and commercial integrations, not more task features.
Reuse the current registries, approval system, queue and executors. New tools belong in independent registered modules, not branching ladders in core entry points.

## Recommended Sequence

1. **Earlier fixes: continue user retesting.** Today entry, task confirmation/reopening, mail editing/verification and ordering are implemented. Those fixes needed no migration, but v0.4 requires `0006_agents`, a backup and stopping old processes before upgrade.
2. **Current phase: accept the first Agent implementation.** Multi-step runs, the workbench, artifacts and MCP connections exist. Verify availability, authority, failures and results with a real model and authorized device; the offline demo is not a capability evaluation.
3. **Then: low-friction trials and a complete guide.** Ordinary users start from one invitation-only Web address, without Git, Node or Python installation. Self-hosters retain separate deployment instructions. Teach tool selection, inputs, impact review, authorization, results and failure handling rather than requiring API purchases first.
4. **Expand after user acceptance.** Choose email OAuth, calendar connections, file processing or local installers based on the audience. Native packages, arbitrary website operation, purchasing and payments each need separate design, environments and safety acceptance; they are not promised in this iteration.

## Minimal Tool Scope

| Workflow | User input | Expected result | Required boundaries |
| --- | --- | --- | --- |
| Organize webpage material | A specific public HTTPS page and the desired analysis | Source-linked output that can be saved or exported as a workspace artifact | Page reads remain origin-restricted and material cannot become tool instructions. Artifact saving exists; live search and model quality still require acceptance. |
| Organize content and send email | User material or approved webpage content, recipients and purpose | An editable plain-text draft, followed by exact-content approval, execution and a visible result | Saving is not sign-in verification, verification is not sending, and SMTP acceptance is not delivery. Never blindly replay uncertain external effects. |

The tool view should reuse metadata and parameter schemas and show required connections, data destinations, external effects, approval requirements and retry availability.
Do not silently switch to a demo model to manufacture success or present a generated task as completed work.

## Acceptance Criteria

- Record the current v0.3 steps and failure points for the same user material and configuration before comparing the new workflow. Mocked results are not live-service completion.
- A new user enters an authorized trial without a terminal and completes one tool workflow with a visible result.
- Both workflows cover success, missing configuration, declined authorization, recoverable failure and uncertain outcome; results trace back to the question and actual tool calls.
- Persisted execution state survives reload. Repeated clicks cannot duplicate sending, and cancellation distinguishes work not yet executed from an external effect already produced.
- Chinese and English controls, forms, states and errors remain readable without overlap on desktop and mobile; connection failures offer actionable next steps.
- Web trials must pass identity isolation, HTTPS, credential protection, backup and real PostgreSQL deployment gates. Do not publicly expose local single-user mode.

## Decisions to Confirm

- **Initial workflows:** recommend webpage organization and email, deferring purchases and arbitrary website automation.
- **Initial audience:** recommend a small invitation-only trial before deciding on a local-first edition and supported operating-system priority.
- **Model cost:** BYOK remains available. Hosted trial credit requires a separate budget, quota and abuse-control decision; request limits are not monetary spending limits.
- **Support channel:** deployment owners choose an accessible feedback address and whether to publish a contact number, without requiring private-source-repository access.

See [VERIFICATION.md](VERIFICATION.md) for evidence and remaining gaps, and [OPERATIONS.md](OPERATIONS.md) for deployment constraints.
Implementation authorization is not authorization for cloud provisioning, live email, merchant transactions, repository publication or native releases.
# Dayloom

[简体中文](#简体中文) | [English](#english)

[从零使用 Dayloom：下载、安装与第一个任务](#从零使用-dayloom) | [Use Dayloom from scratch](#use-dayloom-from-scratch)

## 简体中文

一个可自托管的个人行动助手。记录想法、整理任务，结合日历安排每日计划，
并明确批准助手能够执行的具体操作。

Dayloom 是独立项目，与 Meta Muse 或 Today AI 无关联。
仓库以私有形式创建，是否公开发布由仓库所有者另行决定。

**当前源码里程碑：v0.3 开发预览（2026-11-02）。**
这是在 v0.2 基础上的语言与入门体验更新，不是正式安装包或商店发布版本。

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

### v0.3 开发预览更新

- 支持 English / 简体中文切换，覆盖导航、主要页面、表单、日期与操作状态；不改写用户内容。
- 登录页、设置页和教程均可切换语言，选择保存在当前浏览器或设备。
- 新增五步内嵌教程：认识应用、连接 API、测试连接、首次对话、核对并审批提案。
- 未配置模型的新空工作区自动进入教程；支持稍后继续、返回上一步和重新开始。
- 提供 OpenAI、DeepSeek、Google Gemini 的可编辑示例及密钥控制台入口，仅显示服务器允许的来源。
- 保存配置不会调用模型。测试与首次对话分别要求明确授权，失败可重试，提案仍需逐条审批。
- 教程进度按工作区保存在本机，只含步骤与完成标记；不保存密钥或对话草稿，重新进入后需重新测试。

**升级注意：** 先停止旧 API 和 worker，备份数据库以及凭据加密密钥，再按
[docs/OPERATIONS.md](docs/OPERATIONS.md) 执行对应环境的迁移流程。
旧记录仍归属原本地工作区，新账号不会自动继承这些数据。

**本地验证：** 5 项前端单元测试、41 项后端测试通过，1 项真实 PostgreSQL 测试因环境缺失而跳过；
静态检查、前端生产构建通过。内嵌浏览器核对了语言持久化、教程授权和真实本地任务审批执行。
独立 Playwright 套件因本机 Chromium 下载限制未执行，不能将测试发现成功视为套件通过。
真实服务联调、原生编译签名与真机验收尚未完成，商品购买未实现。
完整证据和限制见 [docs/VERIFICATION.md](docs/VERIFICATION.md)。

当前默认不连接任何模型，也不会悄悄退回演示模式。可从“使用教程”或“设置”连接模型。
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

### 从零使用 Dayloom

本教程从下载、安装一直讲到完成第一个任务。**前五步不需要购买模型 API 或填写密钥。**
如果管理员已经给你一个 Dayloom 网址，直接用浏览器打开、按其要求登录，再从第 5 步开始。
当前提供的是源码开发预览，没有已验证的 APK、IPA 或 EXE 安装包；GitHub ZIP 也不是安装程序。

#### 第 1 步：准备电脑和终端

准备能联网的电脑和浏览器。终端负责执行命令，浏览器负责打开 Dayloom 网页。
Linux 打开“终端”；macOS 打开“应用程序 → 实用工具 → 终端”。
Windows 推荐先按 [微软说明](https://learn.microsoft.com/zh-cn/windows/wsl/install) 安装 WSL2 Ubuntu：
在管理员 PowerShell 中执行下面的命令，按提示重启并设置 Ubuntu 用户名和密码。

```powershell
wsl --install -d Ubuntu
```

之后从开始菜单打开 **Ubuntu**，下面的 Bash 命令都在这个终端执行，不是在 PowerShell 中。
Node.js、uv 和项目文件也放在 Ubuntu 环境内，不要混用 Windows 工具。
受管理的电脑请先获得管理员许可。Linux 已有本地验证，macOS、Windows/WSL2 全新安装尚未验收。

#### 第 2 步：安装运行工具

需要 **Node.js 24 LTS（自带 npm）** 和 **uv（管理 Python）**。
macOS 可从 [Node.js 官网](https://nodejs.org/en/download) 安装对应芯片的版本。
Linux / WSL Ubuntu 可使用 [nvm 官方安装方法](https://github.com/nvm-sh/nvm#installing-and-updating)：

```bash
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
. "$HOME/.nvm/nvm.sh"
nvm install 24
nvm alias default 24
```

按 [uv 官方安装说明](https://docs.astral.sh/uv/getting-started/installation/) 安装 uv：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

上述安装命令会下载并执行脚本，执行前请确认官方来源和本机安装政策。
如果缺少 curl，先通过系统包管理器安装；不要关闭证书校验。
关闭并重新打开终端，逐行检查工具并安装 Python：

```bash
node --version
npm --version
uv --version
uv python install 3.12
```

前三条应显示版本号，Node.js 推荐 `v24.x`，最低 `22.12`；最后一条应成功安装 Python 3.12 或提示已有。
不需要安装 Docker、独立数据库，也不用手动创建或激活虚拟环境。

#### 第 3 步：下载 Dayloom 源码

1. 登录已获授权的 GitHub 账号，打开 [Dayloom 仓库](https://github.com/FankChen/dayloom)。私有仓库需要所有者授予访问权限。
2. 选择包含所需版本的分支，点击绿色 **Code → Download ZIP**，然后解压。
3. 找到同时包含 `README.md`、`package.json`、`apps/` 和 `backend/` 的那层文件夹，将其命名为 `dayloom`，放在用户主目录。

下文使用 `~/dayloom`，其中 `~` 是主目录；使用其他位置时，把 `cd` 路径改成实际位置，含空格的路径加双引号。
WSL 用户可在 Ubuntu 终端执行下面两行，用文件管理器打开 Ubuntu 主目录，再放入解压后的文件夹：

```bash
cd ~
explorer.exe .
```

已经安装 Git 并完成私有仓库认证时，也可用下面的方式**代替 ZIP 下载**：

```bash
cd ~
git clone https://github.com/FankChen/dayloom.git
```

GitHub 返回 404 或 `Repository not found` 时先检查账号和权限。Git HTTPS 不能直接使用网页登录密码，
参照 [GitHub 认证说明](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github)，不要把令牌写进 URL 或聊天。
内嵌教程需要包含 v0.3 的源码，本地尚未推送的修改不会出现在 GitHub 下载中。

#### 第 4 步：安装依赖并启动

在终端**逐行执行**，每行完成再执行下一行；出现错误先停下排查。首次依赖下载可能需要几分钟：

```bash
cd ~/dayloom
uv sync --locked --python 3.12
npm --prefix apps/web ci
npm run dev
```

这四行依次进入项目、安装后端依赖、安装网页依赖、启动服务。
全新下载且没有额外环境配置时，默认本地单用户模式，**不用注册、不用复制 `.env`、不用填 API 密钥**。
启动器自动初始化数据库，并一起运行 API、后台 worker 和网页。

等待启动完成，在**同一台电脑**的浏览器打开 **http://127.0.0.1:5178**。
成功标志是网页正常显示、终端没有随后出现的进程退出或启动错误；只打印网址不代表就绪。
保持终端开启，持续出现 `200 OK` 或 Vite 更新日志是正常现象，不是输入提示。
需要其他命令时另开终端；自行改过端口时使用实际地址。

#### 第 5 步：先完成一个不需要 API 的任务

1. 新空工作区通常自动打开“使用教程”。选好语言，点击“稍后继续”，再进入 **任务 / Tasks**。
2. 点击新建任务按钮（英文界面为 **New task**）打开表单，输入 `整理今天的笔记`，预计耗时设为 `15` 分钟，
  其他选项保留默认值，再点击创建按钮（**Create task**）。
3. 在列表确认任务已保存；实际做完后，点击任务左侧的勾选按钮标记完成。
  完成后，该任务会从进行中（**Active**）列表消失。
4. 切换到已完成（**Completed**）或全部任务（**All tasks**）筛选，再刷新网页确认记录仍在。

手动管理任务不调用模型，也不用审批助手提案。**今日 / Today** 查看每日安排，**记忆 / Memories** 管理长期信息，
**动态 / Activity** 查看操作记录。可在 **设置 → 语言** 切换中英文；空工作区不会自动填入示例数据。

#### 第 6 步（可选）：连接真实 AI

打开 **使用教程 / Getting started** 或 **http://127.0.0.1:5178/guide**，按下方“第一次使用”的五步引导操作。
API 基础地址填服务商的兼容接口（例如 `https://api.openai.com/v1`），不是聊天网站，也不要追加 `/chat/completions`。
模型 ID 必须是你的 API 账号有权调用的模型，API 密钥不是网页登录密码。

可尝试：“请创建一个任务：整理明天会议需要的资料，预计 20 分钟。”
阅读共享上下文说明并明确同意后发送，核对提案，再批准内容正确的操作，到任务页检查实际结果。
**保存不等于连接成功，模型回复不等于创建任务，已批准不等于已执行。** worker 必须在线。

测试与聊天可能计费，聊天产品会员通常不含 API 额度，Dayloom 不自动充值。
先设置较低的每日请求数、输出 token 上限和服务商预算提醒；这些应用限制不是金额消费上限。
密钥只放在连接表单，不要放进对话、截图或仓库。共享上下文及加密方式详见下方“接入模型”。
不连接真实 API 时，显式 `DemoProvider` 仅为规则演示，不是真实 AI。

#### 第 7 步：关闭、下次启动和保留数据

关闭浏览器不停止后台；回到启动终端按 **Ctrl+C** 才会停止本机服务。主机关闭后后台也无法继续执行。
下次在**同一个项目目录**运行下面两行即可，不用再次下载或安装依赖，也不要重复启动多个实例：

```bash
cd ~/dayloom
npm run dev
```

默认数据库是 `data/dayloom.db`，本地凭据加密密钥是 `data/credentials.key`。
先停止 API 和 worker，再把**整个 `data/` 目录**备份到私人的安全位置；外部配置的 `DAYLOOM_CREDENTIAL_KEY` 要另行安全备份。
丢失加密密钥可能导致凭据无法解密，数据库和密钥都不要上传 GitHub。
清除浏览器数据只会清除语言和教程进度，不会删除服务器数据库；换源码目录通常会使用另一份数据库。
升级前按 [docs/OPERATIONS.md](docs/OPERATIONS.md) 备份并迁移。

#### 常见问题：按现象排查

| 现象 | 处理方式 |
| --- | --- |
| 找不到 `node` / `npm` / `uv` | 重开终端，检查第 2 步版本输出；WSL 工具要安装在 Ubuntu 内。 |
| 找不到 `package.json` / `Missing script: dev` | 进入同时包含 `apps/`、`backend/` 和根 `package.json` 的项目目录，不要在 ZIP 内运行。 |
| 下载超时、代理或证书错误 | 检查网络与组织要求的代理、证书配置，再重试失败步骤；不要关闭 TLS 校验。 |
| 端口占用、网页打不开 | 检查是否已有实例、启动进程是否退出、地址端口是否正确；不要误停其他服务。 |
| 出现登录或访问令牌页面 | 检查是否为管理员部署或已有环境配置，按管理员要求登录，不要猜默认密码或移除保护。 |
| API 测试失败 | 检查额度、模型权限、基础地址、密钥和服务器允许域名；不要公开密钥。 |
| 已批准但没结果 | 检查操作状态与 worker 日志；先核对失败或不确定结果，不要盲目重复外部操作。 |
| 手机打不开本机地址 | 手机的 `127.0.0.1` 指向手机自身；跨设备需要带认证的 HTTPS 部署，不要暴露开发服务。 |

需要备用端口时，先 Ctrl+C 停止旧实例，再在项目根目录执行以下命令，打开 **http://127.0.0.1:5199**：

```bash
DAYLOOM_DEV_WEB_PORT=5199 DAYLOOM_DEV_API_PORT=8099 npm run dev
```

换端口不隔离数据库，不要让两个 worker 同时操作同一份本地 SQLite 工作区。

### 第一次使用

打开导航中的 **使用教程 / Getting started**，或直接访问 `/guide`。未选择语言时，
中文浏览器默认使用简体中文，其他浏览器使用 English；可随时在 **设置 → 语言** 修改。

1. **认识 Dayloom：** 了解“今日”“助手”和“动态”，以及建议必须审批后才执行的边界。
2. **连接 API：** 选择服务商，前往其控制台创建密钥，再填入 API 基础地址、模型 ID 和密钥。
  示例模型不保证对你的账号可用；聊天产品会员通常不包含 API 额度。
3. **测试连接：** 阅读费用说明并勾选授权，再点击测试。保存成功不代表连接成功；
  失败时可按页面提示检查模型权限、额度、地址和服务器允许的域名。
4. **首次对话：** 编辑一个小任务示例，确认愿意共享的上下文后发送。
5. **确认并开始：** 查看实际回复和具体提案，只批准你希望执行的内容，再进入工作区。
  后台 worker 必须在线才能执行；模型没有提出操作时，也可继续对话或手动创建任务。

可以随时选择“稍后继续”。清除浏览器数据会移除语言和教程进度，但不会删除服务器工作区。
API 密钥只粘贴到连接表单，不要放进对话。测试和聊天可能产生服务商费用，教程不自动充值。
新增服务域名需由服务器管理员审核 `DAYLOOM_MODEL_ALLOWED_ORIGINS`，不能在客户端绕过限制。

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
无效的模型输出不会创建操作。自动化测试使用替身，不调用真实模型服务。

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

**Current source milestone: v0.3 development preview (2026-11-02).**
This adds language selection and guided onboarding to v0.2; it is not a production
binary or an app-store release.

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

### v0.3 development preview updates

- English / Simplified Chinese navigation, primary views, forms, dates and action states without rewriting user content.
- Language selection on the sign-in screen, Settings and guide, remembered in the current browser or device.
- A five-step embedded guide: meet Dayloom, connect an API, verify it, try a conversation, and review proposals.
- Automatic onboarding for a new empty workspace without a model, with continue-later, back and restart controls.
- Editable OpenAI, DeepSeek and Google Gemini examples and key-console links, restricted to server-approved origins.
- Saving never calls the model. Testing and the first conversation require separate explicit consent; failures can be retried and proposals still require approval.
- Workspace-scoped local progress stores only the step and completion flag, never keys or message drafts. Returning to the guide requires another connection test.

**Upgrade notes:** Stop the old API and worker, back up the database and credential
encryption key, then follow the migration procedure for your environment in
[docs/OPERATIONS.md](docs/OPERATIONS.md). Existing records stay in the legacy
local workspace; newly created accounts do not automatically inherit them.

**Local verification:** 5 frontend unit tests and 41 backend tests passed; 1 real
PostgreSQL test was skipped because its service was unavailable. Static checks
and the web production build passed. Integrated-browser checks covered language
persistence, onboarding consent and actual local task approval/execution.
The standalone Playwright suite was not run because Chromium downloads are
restricted on this host; test discovery is not a suite pass. Live integrations,
native compilation/signing and device acceptance remain unverified; purchasing
is not implemented. See [docs/VERIFICATION.md](docs/VERIFICATION.md).

The default has no model connection and never silently falls back to demo mode.
Connect a model through Getting started or Settings. For an explicit offline demo, set
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

### Use Dayloom from scratch

This walkthrough covers download, installation and your first completed task. **Steps 1-5 need no paid API or key.**
If an administrator gave you a Dayloom URL, open it, sign in as instructed, and start at step 5.
This source preview has no verified APK, IPA or EXE release. A GitHub ZIP is not an installer.

#### Step 1: Prepare your computer and terminal

Use a computer with internet access and a browser. Commands go in the terminal; the Dayloom URL goes in your browser.
Linux: open Terminal. macOS: open Applications > Utilities > Terminal.
Windows: follow [Microsoft's WSL2 Ubuntu instructions](https://learn.microsoft.com/en-us/windows/wsl/install).
Run this in administrator PowerShell, restart if prompted, then set an Ubuntu username and password:

```powershell
wsl --install -d Ubuntu
```

Afterward, open **Ubuntu** from the Start menu. Run all remaining Bash commands there, not in PowerShell.
Install Node.js, uv and the project inside Ubuntu; do not mix Windows tools into this setup.
Get approval before installing on a managed computer. Linux has local verification; clean macOS and Windows/WSL2 installations remain unverified.

#### Step 2: Install the tools

Install **Node.js 24 LTS (includes npm)** and **uv (manages Python)**.
On macOS, use the matching installer from the [Node.js website](https://nodejs.org/en/download).
On Linux / WSL Ubuntu, use the [official nvm instructions](https://github.com/nvm-sh/nvm#installing-and-updating):

```bash
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
. "$HOME/.nvm/nvm.sh"
nvm install 24
nvm alias default 24
```

Install uv following its [official guide](https://docs.astral.sh/uv/getting-started/installation/):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

These commands download and execute scripts. Review official sources and your installation policy first.
If curl is missing, install it with your system package manager; never disable certificate checks.
Close and reopen the terminal, then run each command:

```bash
node --version
npm --version
uv --version
uv python install 3.12
```

The first three should print versions. Node.js `v24.x` is recommended, with `22.12` the minimum.
The last command installs Python 3.12 or reports it already installed.
No Docker, separate database or manual virtual-environment creation/activation is needed.

#### Step 3: Download Dayloom

1. Sign in to your authorized GitHub account and open the [Dayloom repository](https://github.com/FankChen/dayloom). The private repository requires owner-granted access.
2. Select a branch containing the required version, click **Code > Download ZIP**, then extract it.
3. Find the folder containing `README.md`, `package.json`, `apps/` and `backend/` together. Name it `dayloom` and place it in your home directory.

This guide uses `~/dayloom`; `~` means your home directory. Replace the `cd` path if you choose another location, quoting paths with spaces.
WSL users can run these in Ubuntu to open its home directory in File Explorer, then put the extracted folder there:

```bash
cd ~
explorer.exe .
```

If Git is installed and authenticated for the private repository, use this **instead of downloading the ZIP**:

```bash
cd ~
git clone https://github.com/FankChen/dayloom.git
```

For a GitHub 404 or `Repository not found`, check the account and permissions. Git HTTPS cannot use your website login password;
follow [GitHub's authentication guide](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github).
Never put tokens in URLs or chat. The embedded guide requires v0.3 source; unpushed local changes are absent from GitHub downloads.

#### Step 4: Install dependencies and start

Run **one line at a time**, waiting for completion before continuing. Stop if a command fails.
Initial dependency downloads may take several minutes:

```bash
cd ~/dayloom
uv sync --locked --python 3.12
npm --prefix apps/web ci
npm run dev
```

These enter the project, install backend dependencies, install web dependencies and start the services.
A fresh download without environment overrides defaults to local single-user mode: **no signup, `.env` copy or API key required**.
The launcher initializes the database and starts the API, worker and web server together.

Wait for startup, then open **http://127.0.0.1:5178** in a browser on the same computer.
Success means the page loads without subsequent startup errors or process exits; a printed URL alone is not readiness.
Keep the terminal open. `200 OK` access logs and Vite updates are normal, not input prompts.
Use another terminal for other commands; use your actual address if you changed ports.

#### Step 5: Complete a task without an API

1. A new empty workspace normally opens Getting started. Choose a language, select **Continue later**, then open **Tasks**.
2. Click **New task** with the plus icon. Enter `Organize today's notes`, set the estimate to `15` minutes, leave other fields at their defaults, and click **Create task**.
3. Confirm the saved task appears. After doing the work, click its left-hand check button to mark it complete.
4. It disappears from the default active list. Select **Completed**, refresh, and confirm the record and status persist.

Manual task management does not call a model or require proposal approval. **Today** shows your daily plan,
**Memories** manages longer-lived information, and **Activity** shows operations. Change language in **Settings > Language**.
An empty workspace is normal; sample records are not inserted automatically.

#### Step 6: Optionally connect real AI

Open **Getting started** or **http://127.0.0.1:5178/guide** and follow the five screens in First-time setup below.
Enter the provider's compatible API base URL, such as `https://api.openai.com/v1`, not a chat website; do not append `/chat/completions`.
The model ID must be available to your API account. An API key is not a login password.

Try: "Create a task to organize the materials for tomorrow's meeting, estimated at 20 minutes."
Review the shared context, consent before sending, inspect the proposal and approve only correct operations, then verify the actual task.
**Saving is not connectivity, a reply is not a created task, and approval is not execution.** The worker must stay online.

Tests and chat may incur charges. Chat subscriptions usually exclude API credit; Dayloom never tops up accounts.
Start with low daily-request/output-token limits and provider budget alerts; application limits are not currency spending caps.
Paste keys only into the connection form, never chat, screenshots or the repository. See Connect a model below for shared context and encryption details.
Explicit `DemoProvider` mode is a rule-based demonstration, not real AI.

#### Step 7: Stop, restart and keep your data

Closing the browser does not stop the backend. Press **Ctrl+C** in the launcher terminal to stop local services.
Background work cannot run while the host is off. Next time, use the **same project folder**:

```bash
cd ~/dayloom
npm run dev
```

No repeat download or dependency installation is needed; do not start duplicate instances.
The default database is `data/dayloom.db`, and the local credential encryption key is `data/credentials.key`.
Stop the API and worker before backing up the **whole `data/` directory** privately and securely.
An externally configured `DAYLOOM_CREDENTIAL_KEY` needs a separate secure backup. Losing the key can make stored credentials unreadable.
Never upload databases or keys to GitHub. Clearing browser data removes language and guide progress, not the server database;
another source directory normally uses another database. Follow [docs/OPERATIONS.md](docs/OPERATIONS.md) before upgrades.

#### Beginner troubleshooting

| Symptom | What to check |
| --- | --- |
| Missing `node` / `npm` / `uv` | Reopen the terminal and check step 2's version commands; WSL tools must be inside Ubuntu. |
| Missing `package.json` / `Missing script: dev` | Enter the project folder containing `apps/`, `backend/` and root `package.json`; do not run inside the ZIP. |
| Download timeout, proxy or certificate error | Check network and required proxy/certificate configuration, then retry without disabling TLS checks. |
| Port occupied or page unavailable | Check for an existing instance, process exits and the correct address/port. Do not stop unrelated services. |
| Login or access-token page | Check for a hosted deployment or environment overrides. Follow administrator instructions, not a guessed password or removal of protection. |
| API test fails | Check quota, model access, base URL, key and allowed origins; never publish the key. |
| Approved but no result | Check action status and worker logs; investigate failed or uncertain outcomes before repeating external operations. |
| Phone cannot open the address | Its `127.0.0.1` points to the phone itself. Use authenticated HTTPS across devices, not exposed development services. |

For alternate ports, first stop the old instance with Ctrl+C, run this from the project root, then open **http://127.0.0.1:5199**:

```bash
DAYLOOM_DEV_WEB_PORT=5199 DAYLOOM_DEV_API_PORT=8099 npm run dev
```

Changing ports does not isolate the database. Do not run two workers against the same local SQLite workspace.

### First-time setup

Open **Getting started** in the navigation or visit `/guide`. Without a saved
choice, Chinese browser locales use Simplified Chinese; other locales use English.
Change this anytime in **Settings → Language**.

1. **Meet Dayloom:** Learn where Today, Inbox and Activity fit, and why suggestions require approval.
2. **Connect your API:** Pick a provider, open its key console and enter the API base URL, model ID and key.
  Example models are not availability guarantees; chat-product subscriptions usually do not include API credit.
3. **Verify connection:** Read the cost notice, give consent and run the test. Saving is not proof of connectivity.
  Troubleshooting covers quota, model access, the base URL and approved domains.
4. **Try a conversation:** Edit the small-task example, review the shared context and explicitly consent before sending.
5. **Review and begin:** Inspect the real response and exact proposals. Approve only what you want done, then enter your workspace.
  The worker must be online to execute. A reply without proposals can be followed by another conversation or a manually created task.

Choose **Continue later** at any point. Clearing browser data removes language
and guide progress, not the server workspace. Paste keys only into the connection
form, never chat. Testing and chatting may incur provider charges; the guide never
tops up an account. New provider domains require administrator review of
`DAYLOOM_MODEL_ALLOWED_ORIGINS`; the client cannot bypass that restriction.

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
Invalid model output does not create actions. Automated tests use doubles, not live model calls.

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
# Android 与 iOS 路线

[简体中文](#android-与-ios-路线) | [English](#android-and-ios-path)

当前客户端是响应式 Web 应用。Capacitor 使用同一份生产构建包和 API。
移动应用只是客户端，不是持续运行的 worker。

本指南涵盖尚未发布的原生集成。账户登录和原生桥已有源码实现，
但原生编译、签名和真机行为尚未验证。更完整的目标架构见
[架构文档](ARCHITECTURE.md)，运维前置条件见[运维文档](OPERATIONS.md)。

## 已实现的源码

- 通过 Capacitor App/Browser 使用系统浏览器进行 OIDC 登录和原生回调。
  短期、一次性票据绑定到应用独立的 PKCE verifier；回调 URL 不携带 bearer 凭据。
- 原生会话使用 Android Keystore AES-GCM 存储，以及仅限本设备的 iOS Keychain 存储。
  退出登录和会话撤销会清除本地存储的会话。
- Android 通知监听权限、明确的来源选择、本地加密采集、来源撤销及清空控件。
  采集默认关闭，最多 100 条，保留不超过 24 小时。会过滤常见认证码模式，
  但无法保证完全识别。不要选中敏感应用。将单条内容上传为任务需要另行明确操作。
- iOS 明确报告不支持跨应用通知采集。
- 发布配置关闭桥接日志、WebView 调试和混合内容；Android 关闭备份和明文流量。

这些是源码层面的属性，不是真机测试结果。取得权限不代表能读取全部短信、聊天历史或任意操作系统数据。

## 构建并同步原生项目

Android 和 iOS 源码项目分别包含在 `apps/web/android` 和 `apps/web/ios` 中。
它们不是已签名或可上架的发布版本。

使用 Node.js 24，在 `apps/web` 中运行：

```bash
npm ci
VITE_API_BASE_URL=https://your-own-server.example npm run build
npx cap sync
```

仅在对应源码项目不存在时运行 `npx cap add android` 或 `npx cap add ios`。
后续 Web 构建后使用 `cap sync`。示例 API 主机名是占位符，不是托管的 Dayloom 服务。
绝不能把模型密钥或服务端访问 token 放入 Vite 环境变量，因为它们会被编译进客户端。
本地 `.env.local` 被版本控制忽略。

除 Web origin 外，服务端允许的 origin 还需包含 iOS 的 `capacitor://localhost` 和
Android 的 `https://localhost`。后端必须通过 HTTPS 提供服务。
生产环境不要启用明文访问或允许任意服务端 origin。

Android 构建需要 Android Studio、SDK，以及所安装 Capacitor 版本要求的 Java 版本。
iOS 构建/签名需要 macOS 和 Xcode，分发还需要 Apple 开发者账户。
Linux 可以开发共享代码，但不能在本地编译/签名 iOS 应用。

原生构建和服务端公共 URL 使用同一个可达的 HTTPS API URL。
手机不能通过 `127.0.0.1` 访问开发电脑。在身份提供方注册准确的服务端 OIDC 回调。
默认原生返回 scheme 为 `app.dayloom.personal://auth/callback`；
修改时保持服务端和两个原生项目一致。经过验证的 universal/app links 仍是后续工作。

## 构建产物

手动触发的 `Native packages` GitHub Actions 工作流接收 HTTPS API URL，
默认构建 Android debug APK 和未签名的 iOS 模拟器应用。
可选 Android release 模式需要所有者提供签名 secrets，生成 APK/AAB 产物。
secret 名称见[运维文档](OPERATIONS.md)。

产物仅限有仓库权限者访问，七天后过期，不会发布为 release。
本地验证没有触发此工作流。iOS 模拟器应用不能安装到普通 iPhone 上；
TestFlight/App Store 分发需要 Apple 团队、provisioning 和签名。

## 原生 Beta 前置条件

- 将暂定应用 ID 改为自己控制的标识符。
- 编译并在真机上测试安全存储、登录/刷新/撤销、抵御回调拦截，以及通知权限/来源变更。
- 通过原生适配器加入日历权限。即使应用自愿只读，iOS 读取也需要完整 EventKit 日历访问权限。
- 加入明确的分享面板采集，再加入带静默时段的可选通知。
- 在设备上测试后台/前台切换、键盘边距、动态文字、权限撤销、离线错误、同步冲突及无障碍。
- 准备隐私披露、账户/数据删除流程和应用商店审核材料。

目前没有实现广泛短信访问、微信历史记录或其他应用的 iOS 通知读取。
后台刷新是尽力而为，任务在服务端运行。原生源码项目不等于已签名发布版本，
浏览器视口测试也不能证明原生 SDK、通知投递或应用商店合规性。

---

# Android and iOS path

The current client is a responsive web app. Capacitor uses the same production
bundle and the same API. The mobile app is a client, not the always-on worker.

This guide covers the unreleased native integration. Account login and native
bridges have source implementations, but native compilation, signing and real
device behavior are not yet verified. The broader target architecture remains in
[ARCHITECTURE.md](ARCHITECTURE.md); operational prerequisites are in
[OPERATIONS.md](OPERATIONS.md).

## Implemented Source

- System-browser OIDC sign-in and native callback through Capacitor App/Browser.
  A short-lived, single-use ticket is bound to the app's separate PKCE verifier;
  bearer credentials are not placed in the callback URL.
- Android Keystore AES-GCM storage and iOS device-only Keychain storage for native
  sessions. Logout and session revocation clear the local stored session.
- Android notification-listener access, explicit source selection, local encrypted
  capture, source revocation and clear controls. Capture defaults off, is capped
  at 100 events and retained for at most 24 hours. Common authentication-code
  patterns are filtered, not guaranteed completely detected. Keep sensitive apps
  unselected. Uploading one item as a task is a separate explicit action.
- iOS explicitly reports cross-app notification capture as unsupported.
- Bridge logging, WebView debugging and mixed content are disabled in release
  configuration. Android backup and cleartext traffic are disabled.

These are source-level properties, not device-test results. Permissions do not
grant access to all SMS, chat history or unrestricted operating-system data.

## Build and sync native shells

Android and iOS source projects are included in `apps/web/android` and
`apps/web/ios`. They are not signed or store-ready releases.

Use Node.js 24 and run these commands inside `apps/web`:

```bash
npm ci
VITE_API_BASE_URL=https://your-own-server.example npm run build
npx cap sync
```

Only run `npx cap add android` or `npx cap add ios` if the corresponding source
project is absent. Use `cap sync` after subsequent web builds. The example API
hostname is a placeholder, not a
hosted Dayloom service. Never put model keys or server access tokens in Vite env
variables: they are compiled into the client. A local `.env.local` is ignored.

Set the server's allowed origins to include `capacitor://localhost` for iOS and
`https://localhost` for Android, in addition to your web origin. Serve the backend
over HTTPS. Do not enable cleartext or arbitrary server origins for production.

Android builds require Android Studio, the SDK and the Java version required by
the installed Capacitor release. iOS builds/signing require macOS, Xcode and an
Apple developer account for distribution. Linux can develop the shared code but
cannot compile/sign the iOS app locally.

Use the same reachable HTTPS API URL for the native build and server public URL.
A phone cannot reach the development machine through `127.0.0.1`. Register the
server's exact OIDC callback with the provider. The default native return scheme
is `app.dayloom.personal://auth/callback`; keep the server and both native projects
in agreement if changing it. Verified universal/app links remain a follow-up.

## Build Artifacts

The manual `Native packages` GitHub Actions workflow accepts the HTTPS API URL.
It builds an Android debug APK by default and an unsigned iOS simulator app.
Optional Android release mode requires owner-provided signing secrets and creates
APK/AAB artifacts. See [OPERATIONS.md](OPERATIONS.md) for the secret names.

Artifacts stay private to repository access, expire after seven days and are not
published as releases. This workflow has not been dispatched as part of local
verification. An iOS simulator app is not installable on an ordinary iPhone;
TestFlight/App Store distribution needs an Apple team, provisioning and signing.

## Before native beta

- Change the provisional app ID to an identifier you control.
- Compile and device-test secure storage, login/refresh/revocation, callback
  interception resistance and notification permission/source changes.
- Add calendar permissions using native adapters. iOS reading needs full EventKit
  calendar access even if the application voluntarily performs read-only operations.
- Add explicit share-sheet capture, then optional notifications with quiet hours.
- Test background/foreground transitions, keyboard insets, dynamic text, revoked
  permissions, offline errors, synchronization conflicts and accessibility on devices.
- Produce privacy disclosures, account/data deletion flows and store review material.

There is no implementation of broad SMS access, WeChat history or other apps'
iOS notifications. Background refresh is best-effort; jobs run on the server.
Native source projects are not signed releases, and browser viewport tests do not establish
native SDK, notification delivery or app-store compliance.
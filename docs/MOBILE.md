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
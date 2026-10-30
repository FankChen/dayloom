# Android and iOS path

The current client is a responsive web app. Capacitor uses the same production
bundle and the same API. The mobile app is a client, not the always-on worker.

## Build and sync native shells

Android and iOS source projects are included in `apps/web/android` and
`apps/web/ios`. They are development shells, not signed or store-ready apps.

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

## Before native beta

- Change the provisional app ID to an identifier you control.
- Replace web sessionStorage tokens with Keychain/Keystore-backed storage and
  scoped/revocable sessions. Current session tokens are suitable only for local preview.
- Add calendar permissions using native adapters. iOS reading needs full EventKit
  calendar access even if the application voluntarily performs read-only operations.
- Add explicit share-sheet capture, then optional notifications with quiet hours.
- Test background/foreground transitions, keyboard insets, dynamic text, revoked
  permissions, offline errors, synchronization conflicts and accessibility on devices.
- Produce privacy disclosures, account/data deletion flows and store review material.

There is no implementation of broad SMS access, WeChat history or other apps'
iOS notifications. Background refresh is best-effort; jobs run on the server.
Native shells are not signed releases, and browser viewport tests do not establish
native SDK, notification delivery or app-store compliance.
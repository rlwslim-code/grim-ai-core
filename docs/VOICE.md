# Voice and platform activation

## Browser

The web client detects browser speech-recognition support and uses speech synthesis when available. Microphone permission, browser support, language availability, a secure origin/localhost, and a suitable installed voice affect behavior. Browser recognition may depend on the browser vendor's remote service. The application does not claim offline speech recognition.

“Hey GRIM” detection is in-app while listening is explicitly active. It is not an always-running background wake-word engine. Voice quality depends on installed browser/system voices; a guaranteed bespoke ominous voice is not bundled. Interrupt speaking using the client controls. Background tabs and mobile browsers may suspend microphone access.

## iOS

This Expo development package does not include a compiled App Intents extension. It cannot register an unrestricted background “Hey GRIM” listener. A practical first integration is an iOS Shortcut that opens the GRIM app; configure the app URL scheme if supported by the mobile app. A more advanced Shortcut can dictate text and send an authenticated JSON request to `POST /api/chat` using a personally configured token. Tokens stored inside Shortcuts remain sensitive; never share a Shortcut containing one.

For production Siri integration, build and review a native App Intents extension that securely obtains the app session and hands off requests. This is remaining native work, not a shipped capability.

## Android and desktop

The web client is available on desktop browsers. The Expo app can speak using supported system speech synthesis. Native continuous recognition/background wake-word detection requires dedicated native modules, OS permissions, foreground-service indicators on Android, battery testing, and platform distribution review. These services are not silently enabled by this release.

See [Expo Speech](https://docs.expo.dev/versions/latest/sdk/speech/) and [Apple App Intents](https://developer.apple.com/documentation/appintents) for native integration.

# Activate device notifications

The frontend and post-deployment sender are implemented, but push remains OFF until the owner configures a provider. No notification has been sent or device delivery tested.

1. Create a OneSignal web app for `https://tktarun03.github.io` using Custom Code setup. Set its default notification URL to `https://tktarun03.github.io/jarvis-ai-news/`. Disable automatic prompts. Use service worker path `/jarvis-ai-news/OneSignalSDKWorker.js` with scope `/jarvis-ai-news/`.
2. Put the public App ID into `assets/push-config.json` (`appId`). This ID is public; never put the REST key in this file.
3. Add its private App REST API key to this repository's GitHub Actions secrets as `ONESIGNAL_REST_API_KEY`. Never paste the key into chat or commit it.
4. Deploy, open News notifications and choose Set up notifications, then Enable notifications. Accept the device permission. On supported iPhones/iPads, first add the site to the Home Screen and launch it there.
5. Send a test to a test subscriber from the provider dashboard, verify receipt while the app is closed, and verify that tapping opens JARVIS. Verify Turn off notifications prevents further delivery.

The pipeline sends only after successful Pages deployment and only when the latest edition's news content differs from the comparison commit. UI, images and generation timestamps do not trigger alerts. Content-derived idempotency keys prevent duplicate requests during provider-supported retry windows. Delivery depends on browser/OS settings. An accepted provider request is not proof of device receipt.

Open pages also check for updates every two minutes and on foregrounding. This is an in-page banner, not background push. Read-aloud uses browser/device speech synthesis; voice quality and background playback vary by device. It starts only on a tap.

Official references:
- https://documentation.onesignal.com/docs/en/web-sdk-reference
- https://documentation.onesignal.com/docs/en/web-push-for-ios
- https://documentation.onesignal.com/reference/create-message

# iOS Universal Links — Setup Guide

Universal Links let the Briefly iOS app open URLs directly instead of falling back to Safari.
The server must serve an Apple App Site Association (AASA) file at a well-known path.

---

## TL;DR — Here's where you put in the AASA appID and you're good to go

Open `.env` (project root) and uncomment + fill in one line:

```
APPLE_TEAM_ID=XXXXXXXXXX
```

Replace `XXXXXXXXXX` with your **10-character Apple Developer Team ID**.

Restart the server. Done. Universal Links will work.

---

## Where to find your Team ID

1. Sign in to [developer.apple.com](https://developer.apple.com/account)
2. Click **Membership** in the left sidebar
3. Your Team ID is the 10-character alphanumeric string next to "Team ID"

It looks like: `A1B2C3D4E5`

---

## What the server serves

Once `APPLE_TEAM_ID` is set, `GET /.well-known/apple-app-site-association` returns:

```json
{
  "applinks": {
    "apps": [],
    "details": [
      {
        "appID": "A1B2C3D4E5.com.briefly.app",
        "paths": ["*"]
      }
    ]
  }
}
```

If `APPLE_TEAM_ID` is **not** set, the endpoint returns `503` with a JSON error — the server
still starts and all other endpoints work normally.

---

## Bundle ID

The bundle ID defaults to `com.briefly.app`. If your Xcode project uses a different bundle ID,
also set:

```
APPLE_BUNDLE_ID=com.yourcompany.briefly
```

---

## Verifying it works

```bash
curl https://your-server.com/.well-known/apple-app-site-association
```

Expected response: `200 OK` with `Content-Type: application/json` and the JSON above.

> **Note:** iOS caches the AASA file aggressively. After a server change, delete and reinstall
> the app on device to force a fresh fetch, or use the
> [AASA Validator](https://branch.io/resources/aasa-validator/) to check the live endpoint.

---

## Xcode side

In Xcode, add the **Associated Domains** capability to your app target:

```
applinks:your-server.com
```

No other Xcode changes are needed — the server handles the rest.

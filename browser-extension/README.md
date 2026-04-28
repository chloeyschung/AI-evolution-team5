# Briefly Browser Extension

A Chrome/Whale browser extension for saving and summarizing web content with AI.

## Features

- **One-Click Save**: Click the extension icon to save the current page
- **Context Menu**: Right-click to save pages or selected text
- **AI Summarization**: Automatic 3-line summaries powered by LLM
- **Metadata Extraction**: Auto-detects title, author, and content type
- **Google OAuth**: Secure login with Google account
- **Dark Mode**: Automatically adapts to system theme

## Prerequisites

- **Node.js** 18+ and npm
- **Chrome/Chromium-based browser** (Chrome, Edge, Brave, Whale)
- **Backend API** running (see below)
- **Google OAuth Client ID** (see Configuration)

## Backend Setup

The extension requires the Briefly backend API to be running:

```bash
# In the Briefly project root
cd /path/to/Briefly

# Start the backend server
uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

The server should be accessible at `http://localhost:8000`.

For full local stack boot (backend + dashboard + extension watcher), use:

```bash
cd /path/to/Briefly
./scripts/run-stack.sh start
```

## Configuration

### 1. Create `.env` file

```bash
cd browser-extension
cp .env.example .env
```

### 2. Get Google OAuth Client ID

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project or select existing one
3. Enable "Google+ API"
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Application type: **Web application**
6. Authorized redirect URIs: Add `<extension-id>.chromium.app/login/login.html`
   - Note: You'll need to build and load the extension first to get the extension ID
7. Copy the **Client ID** to `.env`:

```
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

## Installation

### 1. Install Dependencies

```bash
cd browser-extension
npm install
```

### 2. Build the Extension

```bash
npm run build
```

This creates the `dist/` folder with the built extension.

### 3. Load in Chrome

1. Open `chrome://extensions/`
2. Enable **"Developer mode"** (toggle in top right)
3. Click **"Load unpacked"**
4. Select the `browser-extension/dist` folder
5. The extension icon should appear in your toolbar

### 4. Pin the Extension

Click the puzzle piece icon → find "Briefly" → pin it to keep it visible.

## Development

### Watch Mode

For development, use watch mode to auto-rebuild on changes:

```bash
npm run dev
```

Then in Chrome:
1. Go to `chrome://extensions/`
2. Find Briefly extension
3. Click the refresh icon to reload

### Build Commands

```bash
npm run build      # Build for production
npm run dev        # Build with watch mode
npm run lint       # Run ESLint
npm run typecheck  # Run TypeScript type checking
```

### Verification Commands

Run these before loading/reloading in Chrome:

```bash
cd browser-extension
npx vitest run src/__tests__/web-guidelines-extension.test.ts
npm run test -- --run src/__tests__/extractor.test.ts
npm run typecheck
npm run build
```

## Usage

### Saving Content

1. **Via Extension Icon**:
   - Click the Briefly icon in toolbar
   - Click "Save Current Page" button

2. **Via Context Menu**:
   - Right-click anywhere on a page
   - Select "Save to Briefly"

3. **Via Text Selection** (future):
   - Select text on page
   - Right-click → "Save Selection to Briefly"

### Login Flow

1. Click extension icon
2. Click "Login with Google"
3. Complete Google OAuth in popup
4. Window closes automatically
5. You're now logged in!

### Settings

- **Auto-summarize**: Toggle AI summarization
- **API Base URL**: Hidden by default. Enable only for local debugging with `VITE_SHOW_API_URL_SETTING=true`.
- **Backend URL source**: Uses `VITE_API_BASE_URL` from extension build env.

### Summary Backend

- Extension summary generation is server-side.
- Configure backend with `ANTHROPIC_API_KEY`.
- Optional overrides:
  - `ANTHROPIC_BASE_URL` (default: `https://api.anthropic.com/v1/messages`)
  - `ANTHROPIC_MODEL` (default: `claude-3-5-sonnet-20240620`)

## Architecture

```
browser-extension/
├── manifest.json              # Extension manifest (V3)
├── package.json               # Dependencies & scripts
├── tsconfig.json              # TypeScript config
├── vite.config.ts             # Build config
├── .env.example               # Environment template
├── icons/                     # Extension icons
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
├── dist/                      # Built extension (output)
└── src/
    ├── background/
    │   └── service-worker.ts  # Background service worker
    ├── content/
    │   ├── content-script.ts  # Content script
    │   └── content-script.css # Content script styles
    ├── popup/
    │   ├── popup.html         # Popup UI
    │   ├── popup.ts           # Popup logic
    │   └── popup.css          # Popup styles
    ├── login/
    │   ├── login.html         # OAuth callback page
    │   ├── login.ts           # OAuth handling
    │   └── login.css          # Login page styles
    ├── shared/
    │   ├── types.ts           # TypeScript interfaces
    │   ├── auth.ts            # Authentication manager
    │   ├── api.ts             # API client
    │   └── storage.ts         # Storage manager
    └── utils/
        └── extractor.ts       # Page metadata extraction
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/auth/status` | GET | Check authentication state |
| `/api/v1/auth/google` | POST | Google OAuth login |
| `/api/v1/auth/refresh` | POST | Refresh access token |
| `/api/v1/auth/logout` | POST | Logout and revoke tokens |
| `/api/v1/share` | POST | Save content to Briefly |

## Troubleshooting

### "Cannot read property of undefined" on login

- Make sure `VITE_GOOGLE_CLIENT_ID` is set in `.env`
- Rebuild the extension after changing `.env`

### "Extension couldn't be loaded"

- Check that all icon files exist in `icons/`
- Run `npm run build` to ensure clean build
- Check Chrome extension errors at `chrome://extensions/`

### "Login failed" or "Token exchange failed"

- Verify backend is running at the configured API URL
- Check Google OAuth redirect URI matches extension ID
- Check browser console for detailed error messages

### Icons not showing

- Ensure `icons/` directory has `icon16.png`, `icon48.png`, `icon128.png`
- Rebuild and reload extension

## Testing

### Manual Testing Checklist

- [ ] Extension loads without errors
- [ ] Login with Google works
- [ ] Save current page works
- [ ] Context menu save works
- [ ] Toast notifications appear
- [ ] Token refresh works (wait for token to expire)
- [ ] Logout works
- [ ] Dark mode adapts to system theme

## License

MIT

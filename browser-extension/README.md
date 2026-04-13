# Briefly Browser Extension

A Chrome/Whale browser extension for saving and summarizing web content with AI.

## Features

- **One-Click Save**: Click the extension icon to save the current page
- **Context Menu**: Right-click to save pages or selected text
- **AI Summarization**: Automatic 3-line summaries powered by LLM
- **Metadata Extraction**: Auto-detects title, author, and content type
- **Google OAuth**: Secure login with Google account

## Development

### Prerequisites

- Node.js 18+
- `uv` for running the Briefly backend

### Setup

1. Install dependencies:
   ```bash
   cd browser-extension
   npm install
   ```

2. Start the backend server:
   ```bash
   uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
   ```

3. Build the extension:
   ```bash
   npm run build
   ```

4. Load the extension in Chrome:
   - Open `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select the `browser-extension/dist` folder

### Development Mode

Watch for changes:
```bash
npm run dev
```

### Configuration

Update `VITE_GOOGLE_CLIENT_ID` in `.env` with your Google OAuth Client ID:
```
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

## Building Icons

Icons are required for the extension. Place PNG icons in the `icons/` directory:
- `icon16.png` (16x16)
- `icon48.png` (48x48)
- `icon128.png` (128x128)

You can use any design tool or generate from SVG.

## Testing

Run tests:
```bash
npm test
```

Type check:
```bash
npm run typecheck
```

Lint:
```bash
npm run lint
```

## Architecture

```
browser-extension/
├── manifest.json           # Extension manifest (V3)
├── package.json            # Dependencies & scripts
├── tsconfig.json           # TypeScript config
├── vite.config.ts          # Build config
├── dist/                   # Built extension (output)
└── src/
    ├── background/         # Service worker
    ├── content/            # Content scripts
    ├── popup/              # Extension popup UI
    ├── login/              # OAuth callback page
    ├── shared/             # Shared utilities (API, auth, storage)
    └── utils/              # Helper functions
```

## API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/status` | GET | Check authentication state |
| `/auth/google` | POST | Google OAuth login |
| `/auth/logout` | POST | Logout and revoke tokens |
| `/share` | POST | Save content to Briefly |

## License

MIT

# Briefly Web Dashboard

A web-based dashboard for managing your Briefly Knowledge Library on a larger screen.

## Features

- **Content Library**: View all saved content in grid or list view
- **Inbox & Archive**: Separate views for pending and kept content
- **Analytics**: Track your reading statistics and progress
- **Search & Filter**: Find content by title, author, or platform
- **Google OAuth**: Secure login with your Google account
- **Responsive Design**: Works on desktop and tablet

## Visual Language Contract

- Canonical visual language: `Quiet Momentum`
- Primary product CTA color: `#2D72D2` (blue-led only)
- Deprecated identity colors for product CTAs: `#B98B24`, `#CFA03B`
- Warm accent usage is secondary only; it must not become the default CTA fill.
- Auth screens should keep one dominant signal lane, with 8px+ control separation and full-width primary actions.
- Work surfaces should anchor on one main reading plane per viewport rather than stacked decorative cards.

## Results-Ready Verification

When validating visual polish, run the requested command exactly and report the outcome with the command text and `PASS`/`FAIL` status. If anything fails, include the first failing assertion or typecheck error so the result is actionable.

For the current visual polish pass, use:

```bash
cd web-dashboard && npm run test:e2e -- tests/e2e/quiet-momentum-auth.spec.ts tests/e2e/quiet-momentum-shell.spec.ts tests/e2e/quiet-momentum-worksurfaces.spec.ts
cd web-dashboard && npm run typecheck
```

## Visual Contract Verification

Run from `web-dashboard/`:

```bash
npm run test:e2e -- tests/e2e/quiet-momentum-auth.spec.ts
npm run test:e2e -- tests/e2e/quiet-momentum-shell.spec.ts
npm run test:e2e -- tests/e2e/quiet-momentum-worksurfaces.spec.ts
```

Full matrix (single command):

```bash
npm run test:e2e -- tests/e2e/quiet-momentum-auth.spec.ts tests/e2e/quiet-momentum-shell.spec.ts tests/e2e/quiet-momentum-worksurfaces.spec.ts
```

## Development

### Prerequisites

- Node.js 18+
- `uv` for running the Briefly backend

### Setup

1. Install dependencies:
   ```bash
   cd web-dashboard
   npm install
   ```

2. Create `.env` file:
   ```
   VITE_GOOGLE_CLIENT_ID=your-google-client-id
   VITE_API_BASE_URL=/api
   ```
   `VITE_API_BASE_URL=/api` is recommended for local dev so Vite proxy can forward to backend without CORS issues.

3. Start the backend server:
   ```bash
   # In another terminal
   uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
   ```

4. Start the dev server:
   ```bash
   npm run dev
   ```

5. Open http://localhost:3001 in your browser

### Build for Production

```bash
npm run build
# Output in dist/ directory
```

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
web-dashboard/
├── index.html              # Entry HTML
├── package.json            # Dependencies & scripts
├── vite.config.ts          # Vite configuration
├── tsconfig.json           # TypeScript configuration
├── README.md               # This file
└── src/
    ├── main.ts             # App entry point
    ├── App.vue             # Root component
    ├── router/
    │   └── index.ts        # Vue Router configuration
    ├── stores/
    │   ├── auth.ts         # Authentication state (Pinia)
    │   └── content.ts      # Content state (Pinia)
    ├── components/
    │   ├── layout/         # Layout components (Header, etc.)
    │   └── content/        # Content-related components
    ├── views/              # Page components
    ├── api/                # API client & endpoints
    ├── types/              # TypeScript type definitions
    └── styles/             # Global styles
```

## Technologies

- **Vue 3**: Progressive JavaScript framework
- **TypeScript**: Type-safe JavaScript
- **Pinia**: State management
- **Vue Router**: Client-side routing
- **Vite**: Build tool
- **Axios**: HTTP client

## License

MIT

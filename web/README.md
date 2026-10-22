# GeoMeta web

Next.js (App Router) frontend for GeoMeta — an interactive geographic reasoning coach for GeoGuessr-style practice and study.

## Prerequisites

- **Node.js >= 20.9** (and a matching npm)
- Do **not** run `npm install` / `next build` on older Node (e.g. v14). Current Next.js and `@clerk/nextjs` require 20.9+.
- Local API assumed at `http://localhost:8000/v1` (see `src/lib/api.ts`)

## Install (after Node upgrade)

From this directory:

```bash
node -v   # confirm v20.9+
npm install
cp .env.local.example .env.local   # fill Clerk keys after linking the app
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

| Script | Purpose |
| --- | --- |
| `npm run dev` | Local development server |
| `npm run build` | Production build |
| `npm start` | Serve the production build |
| `npm run lint` | ESLint via `next lint` |

## Auth (Clerk) — blocked until Node 20.9+

`@clerk/nextjs` is listed in `package.json` but **install and init wait for Node 20.9+**. Do not run `clerk init` or commit real secrets.

When ready, link the existing Clerk dashboard app:

```bash
npx clerk init --app app_3Ky95LvncOOFZKnZ3XsJC76uACc
```

Then:

1. Copy publishable / secret keys into `.env.local` (see `.env.local.example` for placeholder names only).
2. Uncomment `<ClerkProvider>` in `src/app/layout.tsx`.
3. Replace stubs in `src/components/AuthControls.tsx` with real imports:

   ```ts
   import { SignInButton, SignUpButton, UserButton, Show } from "@clerk/nextjs";
   ```

## App routes

| Path | Role |
| --- | --- |
| `/` | Brand-first landing + Practice / Study CTAs |
| `/practice` | Practice shell (image, cues, guess form stubs) |
| `/study` | Study library stub |

## Related Python work

Analysis, evaluation harnesses, and annotation tooling live under [`src/`](../src/) at the repo root. This `web/` app is the product UI only.

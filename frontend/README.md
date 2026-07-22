# Shree Lakshmi Astro React Workspaces

This Vite app powers the explicit React workspace routes served by the FastAPI backend:

- `/payment`
- `/astro-community`
- `/admin`

The public website and legacy app flows still live in `../frontend_old`.

## Development

```bash
npm install
npm run dev
```

When `VITE_API_URL` is not set, local development defaults API calls to `http://127.0.0.1:8000`. Production builds default to the current browser origin, which matches the FastAPI-served deployment.

Set these public variables when hosting the React bundle separately from the API:

```bash
VITE_API_URL=https://your-api-origin.example
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-public-anon-key
```

Never expose service-role, Razorpay secret, webhook, or LLM provider keys with a `VITE_` prefix.

## Build

```bash
npm run build
```

FastAPI serves the generated `dist/` bundle for the React workspace routes.

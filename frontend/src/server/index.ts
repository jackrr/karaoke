/**
 * Bun HTTP server — replaces FastAPI for local dev/production.
 *
 * Serves the Svelte frontend (from the SvelteKit pipeline),
 * runs the API routes, and handles WebSocket connections.
 *
 * Start:  bun run dev            (dev server with hot-reload)
 */
const PORT = parseInt(process.env.PORT || '3000', 10);

function log(...args: unknown[]) {
	console.log(`[bun]`, ...args)
}

// ──────────────────────────────────────────────
//   Serve static frontend files (Vite build)
// ──────────────────────────────────────────────
const servePath = '/home/jack/projects/karaoke/frontend'
const distDir = `${servePath}/dist`

function serveFile(url: URL): Response | null {
	// Strip leading / to get path, default to index.html
	const basePath = url.pathname === '/' ? '/index.html' : url.pathname
	const fullPath = `${distDir}${basePath}`

	const file = Bun.file(fullPath)
	if (file.size > 0) {
		// Content-type by extension
		const ext = basePath.split('.').pop()
		const types: Record<string, string> = {
			html: 'text/html',
			css: 'text/css',
			js: 'text/javascript',
			mjs: 'text/javascript',
			ts: 'text/typescript',
			svg: 'image/svg+xml',
			png: 'image/png',
			jpg: 'image/jpeg',
			jpeg: 'image/jpeg',
			gif: 'image/gif',
			webp: 'image/webp',
			ico: 'image/x-icon',
		}
		return new Response(file, {
			headers: { 'Content-Type': types[ext ?? ''] ?? 'application/octet-stream' },
		})
	}
	return null
}

// ──────────────────────────────────────────────
//   HTTP Handler
// ──────────────────────────────────────────────
async function handle(req: Request): Promise<Response> {
	const url = new URL(req.url)
	const pathname = url.pathname.replace(/\/+$/, '') || '/'
	const method = req.method

	// ── API proxy  ───────────────────────
	if (pathname.startsWith('/api') || pathname.startsWith('/ws')) {
		const BACKEND = process.env.BACKEND_URL
			? new URL(process.env.BACKEND_URL)
			: new URL('http://127.0.0.1:8000/api')

		const backendUrl = new URL(pathname, BACKEND.href)
		backendUrl.search = url.search

		const headers = new Headers(req.headers)
		headers.set('host', BACKEND.host)

		try {
			const res = await fetch(backendUrl.href, {
				method,
				headers,
				body: method !== 'GET' && method !== 'HEAD' ? req.body : undefined,
			})
			return new Response(res.body, {
				status: res.status,
				headers: Object.fromEntries(res.headers),
			})
		} catch (err) {
			log('proxy error:', err)
			return new Response('Backend unavailable', { status: 502 })
		}
	}

	// ── Bun-side API (production mode) ───
	// TODO: Wire Bun-side API handlers for production
	if (pathname.startsWith('/api')) {
		return new Response('Bun-side API not implemented yet', { status: 501 })
	}

	// ── Static file serving ──────────────
	const fileResp = serveFile(url)
	if (fileResp) return fileResp

	// Fallback: serve index.html for client-side routing
	return serveFile(new URL('/index.html', `${distDir}/`))
}

// ─--
import { existsSync, readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

const portalRoot = resolve(dirname(fileURLToPath(import.meta.url)))
const metaPath = resolve(portalRoot, 'build-meta.json')
const pkg = JSON.parse(readFileSync(resolve(portalRoot, 'package.json'), 'utf-8'))

function pad2(value: number) {
  return String(value).padStart(2, '0')
}

/** Local build stamp: hhmmssddmmyyyy. */
function localStamp(date: Date) {
  return [
    pad2(date.getHours()),
    pad2(date.getMinutes()),
    pad2(date.getSeconds()),
    pad2(date.getDate()),
    pad2(date.getMonth() + 1),
    date.getFullYear(),
  ].join('')
}

let appVersion = pkg.version || '0.1.2'
let buildNumber = `${appVersion}.${localStamp(new Date())}`
if (existsSync(metaPath)) {
  try {
    const meta = JSON.parse(readFileSync(metaPath, 'utf-8'))
    appVersion = meta.appVersion || appVersion
    buildNumber = meta.buildNumber || buildNumber
  } catch {
    /* ignore */
  }
}

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'masked-icon.svg'],
      manifest: {
        name: 'Planned Education Exam Portal',
        short_name: 'PlannedEd',
        description: 'Secure, offline-capable exam taking portal.',
        theme_color: '#ffffff',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
          },
        ],
      },
      workbox: {
        // Cache API calls (e.g., getting exams) for offline use
        runtimeCaching: [
          {
            urlPattern: /^https?:\/\/.*\/(api|exams|auth)\/.*$/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60 * 24 * 7, // 1 week
              },
              cacheableResponse: {
                statuses: [0, 200],
              },
            },
          },
        ],
      },
    }),
  ],
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(appVersion),
    'import.meta.env.VITE_BUILD_NUMBER': JSON.stringify(buildNumber),
    'import.meta.env.VITE_APP_CHANNEL': JSON.stringify('beta'),
  },
})

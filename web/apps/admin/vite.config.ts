import { existsSync, readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const appRoot = resolve(dirname(fileURLToPath(import.meta.url)))
const metaPath = resolve(appRoot, 'build-meta.json')
const pkg = JSON.parse(readFileSync(resolve(appRoot, 'package.json'), 'utf-8'))

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
  plugins: [react()],
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(appVersion),
    'import.meta.env.VITE_BUILD_NUMBER': JSON.stringify(buildNumber),
    'import.meta.env.VITE_APP_CHANNEL': JSON.stringify('beta'),
  },
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/admin': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})

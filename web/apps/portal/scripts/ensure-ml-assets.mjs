/**
 * Ensure local MediaPipe Face Landmarker assets exist under public/ml/
 * (offline-first, free OSS — no CDN required at runtime).
 */
import { copyFileSync, createWriteStream, existsSync, mkdirSync, readdirSync, statSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { get } from 'node:https'

const portalRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const mlDir = join(portalRoot, 'public', 'ml')
const wasmDir = join(mlDir, 'wasm')
const modelPath = join(mlDir, 'face_landmarker.task')
const wasmSrc = join(portalRoot, 'node_modules', '@mediapipe', 'tasks-vision', 'wasm')
const MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task'

function ensureDir(p) {
  if (!existsSync(p)) mkdirSync(p, { recursive: true })
}

function download(url, dest) {
  return new Promise((resolvePromise, reject) => {
    const out = createWriteStream(dest)
    get(url, (res) => {
      if (res.statusCode && res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        out.close()
        download(res.headers.location, dest).then(resolvePromise).catch(reject)
        return
      }
      if (res.statusCode !== 200) {
        out.close()
        reject(new Error(`HTTP ${res.statusCode} fetching ${url}`))
        return
      }
      res.pipe(out)
      out.on('finish', () => out.close(() => resolvePromise()))
      out.on('error', reject)
    }).on('error', reject)
  })
}

ensureDir(mlDir)
ensureDir(wasmDir)

if (!existsSync(wasmSrc)) {
  console.warn('[ensure-ml-assets] @mediapipe/tasks-vision wasm missing — run npm install')
  process.exit(0)
}

for (const name of readdirSync(wasmSrc)) {
  const src = join(wasmSrc, name)
  if (!statSync(src).isFile()) continue
  copyFileSync(src, join(wasmDir, name))
}
console.log('[ensure-ml-assets] wasm copied to public/ml/wasm')

if (!existsSync(modelPath) || statSync(modelPath).size < 1_000_000) {
  console.log('[ensure-ml-assets] downloading face_landmarker.task …')
  await download(MODEL_URL, modelPath)
  console.log('[ensure-ml-assets] model ready', statSync(modelPath).size, 'bytes')
} else {
  console.log('[ensure-ml-assets] model present', statSync(modelPath).size, 'bytes')
}

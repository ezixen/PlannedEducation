import { readFileSync, writeFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const appRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const packageJsonPath = resolve(appRoot, 'package.json')
const jsonOutputPath = resolve(appRoot, 'build-meta.json')

const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'))
const now = new Date()

function pad2(value) {
  return String(value).padStart(2, '0')
}

/** Local build stamp: hhmmssddmmyyyy. */
function localStamp(date) {
  return [
    pad2(date.getHours()),
    pad2(date.getMinutes()),
    pad2(date.getSeconds()),
    pad2(date.getDate()),
    pad2(date.getMonth() + 1),
    date.getFullYear(),
  ].join('')
}

const buildStamp = localStamp(now)
const appVersion = String(process.env.VITE_APP_VERSION || packageJson.version || '0.1.2').trim()
const buildNumber = String(process.env.BUILD_NUMBER || `${appVersion}.${buildStamp}`).trim()

const buildMeta = {
  appVersion,
  buildNumber,
  channel: 'beta',
  generatedAt: now.toISOString(),
}

writeFileSync(jsonOutputPath, `${JSON.stringify(buildMeta, null, 2)}\n`, 'utf-8')
console.log(`Generated PlannedEducation admin build metadata: beta ${buildNumber}`)

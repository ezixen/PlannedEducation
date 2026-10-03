import { readFileSync, writeFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const portalRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const packageJsonPath = resolve(portalRoot, 'package.json')
const jsonOutputPath = resolve(portalRoot, 'build-meta.json')

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

function localIsoWithOffset(date) {
  const offsetMinutes = -date.getTimezoneOffset()
  const sign = offsetMinutes >= 0 ? '+' : '-'
  const absOffset = Math.abs(offsetMinutes)
  const tzHours = pad2(Math.floor(absOffset / 60))
  const tzMinutes = pad2(absOffset % 60)
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}T${pad2(date.getHours())}:${pad2(date.getMinutes())}:${pad2(date.getSeconds())}.${String(date.getMilliseconds()).padStart(3, '0')}${sign}${tzHours}:${tzMinutes}`
}

const buildStamp = localStamp(now)
const appVersion = String(process.env.VITE_APP_VERSION || packageJson.version || '0.1.2').trim()
const buildNumber = String(process.env.BUILD_NUMBER || `${appVersion}.${buildStamp}`).trim()

const buildMeta = {
  appVersion,
  buildNumber,
  channel: 'beta',
  generatedAt: localIsoWithOffset(now),
  generatedAtUtc: now.toISOString(),
}

writeFileSync(jsonOutputPath, `${JSON.stringify(buildMeta, null, 2)}\n`, 'utf-8')
console.log(`Generated PlannedEducation build metadata: beta ${buildNumber}`)

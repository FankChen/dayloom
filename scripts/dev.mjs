import { spawn, spawnSync } from 'node:child_process'
import { dirname, resolve, delimiter } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const apiPort = process.env.DAYLOOM_DEV_API_PORT ?? '8078'
const webPort = process.env.DAYLOOM_DEV_WEB_PORT ?? '5178'
const origins = new Set(JSON.parse(process.env.DAYLOOM_ALLOWED_ORIGINS ?? '[]'))
origins.add(`http://127.0.0.1:${webPort}`)
origins.add(`http://localhost:${webPort}`)
const environment = {
  ...process.env,
  PATH: `${dirname(process.execPath)}${delimiter}${process.env.PATH ?? ''}`,
  DAYLOOM_ALLOWED_ORIGINS: JSON.stringify([...origins]),
  DAYLOOM_API_TARGET: `http://127.0.0.1:${apiPort}`,
  PYTHONPATH: resolve(root, 'backend'),
}
const initialized = spawnSync('uv', ['run', '--locked', 'python', '-m', 'dayloom.bootstrap'], { cwd: root, env: environment, stdio: 'inherit' })
if (initialized.status !== 0) process.exit(initialized.status ?? 1)
const commands = [
  ['uv', ['run', '--locked', 'uvicorn', 'dayloom.api:create_app', '--factory', '--host', '127.0.0.1', '--port', apiPort, '--no-proxy-headers']],
  ['uv', ['run', '--locked', 'python', '-m', 'dayloom.worker']],
  [process.platform === 'win32' ? 'npm.cmd' : 'npm', ['--prefix', 'apps/web', 'run', 'dev', '--', '--port', webPort, '--strictPort']],
]
let stopping = false
const children = []
function stop(code = 0) {
  if (stopping) return
  stopping = true
  process.exitCode = code
  for (const child of children) child.kill('SIGTERM')
}
for (const [command, arguments_] of commands) {
  const child = spawn(command, arguments_, { cwd: root, env: environment, stdio: 'inherit' })
  children.push(child)
  child.on('error', error => { console.error(`${command}: ${error.message}`); stop(1) })
  child.on('exit', code => { if (!stopping) stop(code ?? 1) })
}
process.on('SIGINT', () => stop())
process.on('SIGTERM', () => stop())
console.log(`Dayloom: http://127.0.0.1:${webPort}`)
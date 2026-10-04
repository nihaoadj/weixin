import { existsSync, readFileSync, realpathSync } from 'node:fs'
import { resolve } from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

// Developer Tools v2 exposes supported automation through wechatide.cmd.
// Do not reconnect the retired App.* WebSocket protocol to the CLI HTTP port.
const root = fileURLToPath(new URL('../../', import.meta.url))
const project = resolve(root, 'dist/dev/mp-weixin')
const deadlineMs = 15_000
const wechatide = process.env.WECHATIDE_CLI_PATH
const client = process.env.WECHATIDE_CLIENT || 'Codex'

function fail(message) {
  throw new Error(message)
}

function quoted(value) {
  if (!value || /[\r\n]/.test(value)) fail('Invalid Developer Tools command value.')
  return `'${value.replaceAll("'", "''")}'`
}

function invoke(args) {
  if (!wechatide || !existsSync(wechatide)) fail('Set WECHATIDE_CLI_PATH to the installed wechatide.cmd command.')
  if (!/^[A-Za-z0-9_-]+$/.test(client)) fail('WECHATIDE_CLIENT contains unsupported characters.')
  const command = `& ${quoted(wechatide)} -c ${quoted(client)} ${args.map(quoted).join(' ')}`
  const result = spawnSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', command], {
    encoding: 'utf8',
    timeout: deadlineMs,
    windowsHide: true,
  })
  if (result.status !== 0) fail('Developer Tools runtime query failed. Open the development project and retry.')
  const start = result.stdout.indexOf('{')
  if (start < 0) fail('Developer Tools returned no runtime result.')
  try {
    return JSON.parse(result.stdout.slice(start))
  } catch {
    fail('Developer Tools returned an invalid runtime result.')
  }
}

export async function diagnose() {
  if (!existsSync(resolve(project, 'app.json'))) fail('Start the Demo dev:mp-weixin watcher and await Build complete.')
  if (realpathSync(project) !== project) fail('Linked project paths are not accepted.')
  const config = JSON.parse(readFileSync(resolve(project, 'project.config.json'), 'utf8'))
  if (config.setting?.urlCheck === false) fail('URL safety checking must remain enabled.')

  const response = invoke(['automation_runtime_info', '--project', project, '--action', 'systemInfo'])
  if (response?.ok !== true) fail('Developer Tools runtime query did not reach the simulator. Refresh and retry.')
  const sdkVersion = response?.result?.systemInfo?.result?.SDKVersion
  if (typeof sdkVersion !== 'string' || !sdkVersion) {
    fail('No SDKVersion: simulator/base library is not ready; compile and open the project first.')
  }
  console.log(JSON.stringify({ project, cliAvailable: true, urlCheck: true, baseLibraryVersion: sdkVersion }))
  console.log('PASS: supported wechatide runtime query only; no page/render acceptance implied.')
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  diagnose().catch((error) => {
    console.error(error instanceof Error ? error.message : 'Developer Tools doctor failed.')
    process.exitCode = 1
  })
}

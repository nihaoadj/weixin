import { existsSync, readFileSync, realpathSync } from 'node:fs'
import { resolve } from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

// No account queries, screenshots, storage changes or IDE setting changes.
const root = fileURLToPath(new URL('../../', import.meta.url))
const cli = process.env.WECHAT_CLI_PATH
const port = Number(process.env.WECHAT_AUTO_PORT || 9420)
const project = resolve(root, 'dist/dev/mp-weixin')
const deadlineMs = 15000

export async function diagnose({ probe = true } = {}) {
  if (!cli || !existsSync(cli)) throw new Error('Set WECHAT_CLI_PATH to the installed Developer Tools CLI.')
  if (/["%\r\n&|<>^!]/.test(cli)) throw new Error('CLI path contains unsupported shell characters.')
  if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('Invalid WECHAT_AUTO_PORT.')
  if (!existsSync(resolve(project, 'app.json')))
    throw new Error('Start the Demo dev:mp-weixin watcher and await Build complete.')
  if (realpathSync(project) !== project) throw new Error('Linked project paths are not accepted.')
  const config = JSON.parse(readFileSync(resolve(project, 'project.config.json'), 'utf8'))
  if (config.setting?.urlCheck === false) throw new Error('URL safety checking must remain enabled.')
  // PowerShell single-quoted literal escaping protects paths with spaces/apostrophes.
  const help =
    process.platform === 'win32'
      ? spawnSync(
          'powershell.exe',
          ['-NoProfile', '-NonInteractive', '-Command', `& '${cli.replaceAll("'", "''")}' auto --help`],
          {
            encoding: 'utf8',
            timeout: deadlineMs,
            windowsHide: true,
          },
        )
      : spawnSync(cli, ['auto', '--help'], { encoding: 'utf8', timeout: deadlineMs })
  if (help.status !== 0) throw new Error('Developer Tools CLI help failed.')
  console.log(JSON.stringify({ project, port, cliAvailable: true, urlCheck: config.setting?.urlCheck !== false }))
  if (!probe) return
  // Probe protocol readiness separately so missing SDKVersion has a useful error.
  const socket = new WebSocket(`ws://127.0.0.1:${port}`)
  try {
    await new Promise((resolveReady, reject) => {
      const timer = setTimeout(() => {
        socket.close()
        reject(new Error('Automation handshake timed out.'))
      }, deadlineMs)
      const finish = (error) => {
        clearTimeout(timer)
        if (error) reject(error)
        else resolveReady()
      }
      socket.onopen = () => socket.send(JSON.stringify({ id: 'doctor-info', method: 'Tool.getInfo', params: {} }))
      socket.onerror = () =>
        finish(new Error('Automation port unavailable. Start CLI auto for the development project.'))
      socket.onmessage = ({ data }) => {
        let response
        try {
          response = JSON.parse(String(data))
        } catch {
          return finish(new Error('Invalid automation protocol response.'))
        }
        if (response.id !== 'doctor-info') return
        if (response.error) return finish(new Error('Developer Tools rejected Tool.getInfo.'))
        const { version, SDKVersion } = response.result || {}
        console.log(JSON.stringify({ toolVersion: version, baseLibraryVersion: SDKVersion || null }))
        if (!SDKVersion)
          return finish(
            new Error(
              'No SDKVersion: simulator/base library is not ready; ordinary compilation and simulator startup required.',
            ),
          )
        finish()
      }
    })
  } finally {
    socket.close()
  }
  console.log('PASS: automation handshake only; no page/render acceptance implied.')
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  diagnose().catch((error) => {
    console.error(error.message)
    process.exitCode = 1
  })
}

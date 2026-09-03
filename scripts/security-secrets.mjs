#!/usr/bin/env node
/**
 * T06 secret scan wrapper.
 *
 * Downloads a pinned Gitleaks release only into the OS temporary directory,
 * verifies its SHA-256 before extraction, and never prints scanner stdout or
 * matched text. Findings are reduced to scope, rule, location and a redacted
 * correlation fingerprint. JSON reports exist only in a per-run temp folder
 * and are removed in finally blocks.
 *
 * Examples:
 *   node scripts/security-secrets.mjs --scope=worktree
 *   node scripts/security-secrets.mjs --scope=history
 *   node scripts/security-secrets.mjs --scope=all --build-dir dist
 *   node scripts/security-secrets.mjs --self-test
 */
import { createHash } from 'node:crypto'
import { spawn } from 'node:child_process'
import { Buffer } from 'node:buffer'
import { access, chmod, copyFile, lstat, mkdir, mkdtemp, readFile, rename, rm, stat, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const VERSION = '8.30.1'
const RELEASE = `https://github.com/gitleaks/gitleaks/releases/download/v${VERSION}`
const ASSETS = {
  'linux-x64': {
    file: `gitleaks_${VERSION}_linux_x64.tar.gz`,
    sha256: '551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb',
    executable: 'gitleaks',
  },
  'linux-arm64': {
    file: `gitleaks_${VERSION}_linux_arm64.tar.gz`,
    sha256: 'e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080',
    executable: 'gitleaks',
  },
  'win32-x64': {
    file: `gitleaks_${VERSION}_windows_x64.zip`,
    sha256: 'd29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e',
    executable: 'gitleaks.exe',
  },
  'win32-arm64': {
    file: `gitleaks_${VERSION}_windows_arm64.zip`,
    sha256: 'b95f5e4f5c425cedca7ee203d9afd29597e692c4924a12ed42f970537c72cc0f',
    executable: 'gitleaks.exe',
  },
}

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const repositoryRoot = path.resolve(scriptDir, '..')
const configPath = path.join(repositoryRoot, 'config', 'gitleaks-security.toml')

function fail(message) {
  process.stderr.write(`security-secrets: ${message}\n`)
  process.exitCode = 2
}

function parseArgs(argv) {
  const options = { scope: 'worktree', buildDir: undefined, selfTest: false }
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]
    if (argument === '--self-test') options.selfTest = true
    else if (argument.startsWith('--scope=')) options.scope = argument.slice('--scope='.length)
    else if (argument === '--scope') options.scope = argv[++index]
    else if (argument.startsWith('--build-dir=')) options.buildDir = argument.slice('--build-dir='.length)
    else if (argument === '--build-dir') options.buildDir = argv[++index]
    else if (argument === '--help' || argument === '-h') options.help = true
    else throw new Error(`unknown argument ${argument}`)
  }
  if (!['worktree', 'history', 'all', 'build'].includes(options.scope)) {
    throw new Error('--scope must be worktree, history, all, or build')
  }
  if (options.scope === 'build' && !options.buildDir) throw new Error('--scope=build requires --build-dir')
  return options
}

function printHelp() {
  process.stdout.write(
    'Usage: node scripts/security-secrets.mjs [--scope worktree|history|all|build] [--build-dir relative/path] [--self-test]\n',
  )
}

function platformAsset() {
  const key = `${process.platform}-${process.arch}`
  const asset = ASSETS[key]
  if (!asset) throw new Error(`unsupported platform ${key}; supported: ${Object.keys(ASSETS).join(', ')}`)
  return asset
}

async function exists(target) {
  try {
    await access(target)
    return true
  } catch {
    return false
  }
}

async function sha256(target) {
  const value = await readFile(target)
  return createHash('sha256').update(value).digest('hex')
}

async function download(url, destination) {
  const response = await globalThis.fetch(url, { redirect: 'follow' })
  if (!response.ok || !response.body) throw new Error(`download failed with HTTP ${response.status}`)
  await writeFile(destination, Buffer.from(await response.arrayBuffer()))
}

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: repositoryRoot,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
      ...options,
    })
    let stdout = ''
    let stderr = ''
    child.stdout?.on('data', (chunk) => {
      if (stdout.length < 8 * 1024 * 1024) stdout += chunk.toString()
    })
    child.stderr?.on('data', (chunk) => {
      if (stderr.length < 64 * 1024) stderr += chunk.toString()
    })
    child.on('error', reject)
    child.on('exit', (code, signal) => resolve({ code: code ?? 2, signal, stdout, stderr }))
  })
}

function ensureInside(parent, target) {
  const root = path.resolve(parent)
  const candidate = path.resolve(target)
  if (candidate !== root && !candidate.startsWith(`${root}${path.sep}`)) throw new Error('unsafe temporary path')
  return candidate
}

async function resolveGitleaks() {
  const asset = platformAsset()
  const tempRoot = path.resolve(os.tmpdir())
  const toolRoot = ensureInside(tempRoot, path.join(tempRoot, 'wxprogrom-security-tools', `gitleaks-${VERSION}`))
  const archive = ensureInside(toolRoot, path.join(toolRoot, asset.file))
  const installDir = ensureInside(toolRoot, path.join(toolRoot, 'bin'))
  const binary = ensureInside(installDir, path.join(installDir, asset.executable))
  await mkdir(toolRoot, { recursive: true })
  let archiveRefreshed = false
  if (!(await exists(archive)) || (await sha256(archive)) !== asset.sha256) {
    await rm(archive, { force: true })
    const partial = ensureInside(toolRoot, path.join(toolRoot, `${asset.file}.partial`))
    await rm(partial, { force: true })
    try {
      await download(`${RELEASE}/${asset.file}`, partial)
      if ((await sha256(partial)) !== asset.sha256) {
        throw new Error('download SHA-256 did not match the pinned official checksum')
      }
      await rename(partial, archive)
      archiveRefreshed = true
    } catch (error) {
      await rm(partial, { force: true })
      throw error
    }
  }
  if (archiveRefreshed || !(await exists(binary))) {
    await rm(installDir, { recursive: true, force: true })
    await mkdir(installDir, { recursive: true })
    const extraction = await (async () => {
      const result =
        process.platform === 'win32'
          ? await run('powershell.exe', [
              '-NoProfile',
              '-NonInteractive',
              '-Command',
              `Expand-Archive -LiteralPath '${archive.replace(/'/g, "''")}' -DestinationPath '${installDir.replace(/'/g, "''")}' -Force`,
            ])
          : await run('tar', ['-xzf', archive, '-C', installDir])
      return result
    })()
    if (extraction.code !== 0) throw new Error('could not extract verified scanner archive')
    if (process.platform !== 'win32') await chmod(binary, 0o755)
  }
  if (!(await exists(binary))) throw new Error('verified scanner binary is missing after extraction')
  return binary
}

function relativeLocation(value) {
  if (typeof value !== 'string') return 'unknown'
  const absolute = path.resolve(repositoryRoot, value)
  const relative = path.relative(repositoryRoot, absolute)
  return relative && !relative.startsWith('..') && !path.isAbsolute(relative)
    ? relative.replaceAll('\\', '/')
    : `[external]/${path.basename(value).replaceAll('\\', '/')}`
}

function sanitize(scope, findings) {
  const unique = new Map()
  for (const finding of findings) {
    const rule = String(finding.RuleID || 'unknown-rule')
    const location = `${relativeLocation(finding.File)}:${Number(finding.StartLine) || 0}`
    const material = `${scope}\0${rule}\0${location}\0${String(finding.Fingerprint || '')}`
    const fingerprint = createHash('sha256').update(material).digest('hex').slice(0, 16)
    unique.set(`${rule}\0${location}\0${fingerprint}`, { scope, rule, location, fingerprint })
  }
  return [...unique.values()].sort((left, right) =>
    `${left.scope}:${left.location}`.localeCompare(`${right.scope}:${right.location}`),
  )
}

async function scan(binary, scope, source, command, config = configPath) {
  const reportDir = await mkdtemp(path.join(os.tmpdir(), 'wxprogrom-secret-report-'))
  const reportPath = path.join(reportDir, 'report.json')
  const commonArgs = [
    '--config',
    config,
    '--report-format',
    'json',
    '--report-path',
    reportPath,
    '--redact',
    '100',
    '--no-banner',
    '--log-level',
    'error',
    '--exit-code',
    '0',
  ]
  const args = command === 'detect' ? [command, ...commonArgs, '--source', source] : [command, ...commonArgs, '.']
  try {
    const result = await run(binary, args, command === 'dir' ? { cwd: source } : undefined)
    if (result.code !== 0 && result.code !== 1) throw new Error(`scanner failed for ${scope} (exit ${result.code})`)
    if (!(await exists(reportPath))) {
      // A history-oriented command can report findings to stdout without creating the
      // requested file on some releases. Re-run only this failure path with a
      // stdout report, keeping the untrusted JSON in memory and sanitizing it
      // before any value can reach the caller.
      const stdoutArgs = [
        '--config',
        config,
        '--report-format',
        'json',
        '--report-path',
        '-',
        '--redact',
        '100',
        '--no-banner',
        '--log-level',
        'error',
        '--exit-code',
        '0',
      ]
      const stdoutResult = await run(
        binary,
        command === 'detect' ? [command, ...stdoutArgs, '--source', source] : [command, ...stdoutArgs, '.'],
        command === 'dir' ? { cwd: source } : undefined,
      )
      const text = stdoutResult.stdout.trim()
      let fallbackFindings
      try {
        fallbackFindings = JSON.parse(text)
      } catch {
        throw new Error(
          `scanner emitted no report for ${scope} (exit ${result.code}; stdout-bytes=${stdoutResult.stdout.length}; stderr-bytes=${stdoutResult.stderr.length})`,
        )
      }
      if (!Array.isArray(fallbackFindings)) throw new Error(`scanner emitted an unexpected report for ${scope}`)
      return sanitize(scope, fallbackFindings)
    }
    const findings = JSON.parse(await readFile(reportPath, 'utf8'))
    if (!Array.isArray(findings)) throw new Error(`scanner emitted an unexpected report for ${scope}`)
    return sanitize(scope, findings)
  } finally {
    await rm(reportDir, { recursive: true, force: true })
  }
}

async function scanManagedWorktree(binary) {
  const listing = await run('git', ['ls-files', '--cached', '--others', '--exclude-standard', '-z'])
  if (listing.code !== 0) throw new Error(`git managed-file listing failed (exit ${listing.code})`)
  const stagingRoot = await mkdtemp(path.join(os.tmpdir(), 'wxprogrom-secret-worktree-'))
  try {
    for (const relative of listing.stdout.split('\0').filter(Boolean)) {
      const source = ensureInside(repositoryRoot, path.resolve(repositoryRoot, relative))
      let metadata
      try {
        metadata = await lstat(source)
      } catch (error) {
        if (error && error.code === 'ENOENT') continue
        throw error
      }
      if (metadata.isSymbolicLink()) throw new Error(`managed source contains a symbolic link: ${relative}`)
      if (!metadata.isFile()) continue
      const destination = ensureInside(stagingRoot, path.resolve(stagingRoot, relative))
      await mkdir(path.dirname(destination), { recursive: true })
      await copyFile(source, destination)
    }
    return await scan(binary, 'worktree', stagingRoot, 'dir')
  } finally {
    await rm(stagingRoot, { recursive: true, force: true })
  }
}

async function validateBuildDirectory(input) {
  const resolved = path.resolve(repositoryRoot, input)
  ensureInside(repositoryRoot, resolved)
  if (!(await exists(resolved)) || !(await stat(resolved)).isDirectory())
    throw new Error(`build directory does not exist: ${input}`)
  return resolved
}

function output(findings) {
  if (!findings.length) {
    process.stdout.write('security-secrets: findings=0\n')
    return
  }
  process.stdout.write(`security-secrets: findings=${findings.length}\n`)
  for (const finding of findings) {
    process.stdout.write(
      `scope=${finding.scope} rule=${finding.rule} location=${finding.location} fingerprint=${finding.fingerprint}\n`,
    )
  }
}

async function selfTest(binary) {
  const directory = await mkdtemp(path.join(repositoryRoot, '.t06-secret-selftest-'))
  try {
    const keyName = ['AI', '_API_', 'KEY'].join('')
    const marker = ['selftest', '6a1bd7a553fe4b73a2f64f76'].join('')
    const synthetic = `${keyName}=${marker}\n`
    await writeFile(path.join(directory, 'synthetic.env'), synthetic)
    await writeFile(path.join(directory, 'placeholder.env'), `${keyName}=not-a-secret\n`)
    const findings = await scan(binary, 'self-test', directory, 'dir')
    if (!findings.some((finding) => finding.rule === 't06-project-secret-assignment')) {
      throw new Error(`synthetic secret was not detected (sanitized findings=${findings.length})`)
    }
    if (findings.some((finding) => finding.location.startsWith('placeholder.env:'))) {
      throw new Error('short placeholder was unexpectedly detected')
    }
    process.stdout.write(`security-secrets: self-test=pass findings=${findings.length}\n`)
  } finally {
    await rm(directory, { recursive: true, force: true })
  }
}

async function main() {
  const options = parseArgs(process.argv.slice(2))
  if (options.help) return printHelp()
  const binary = await resolveGitleaks()
  if (options.selfTest) return selfTest(binary)
  const findings = []
  if (options.scope === 'worktree' || options.scope === 'all') findings.push(...(await scanManagedWorktree(binary)))
  if (options.scope === 'history' || options.scope === 'all')
    findings.push(...(await scan(binary, 'history', repositoryRoot, 'detect')))
  if (options.scope === 'build' || (options.scope === 'all' && options.buildDir)) {
    findings.push(...(await scan(binary, 'build', await validateBuildDirectory(options.buildDir), 'dir')))
  }
  output(findings)
  if (findings.length) process.exitCode = 1
}

main().catch((error) => fail(error instanceof Error ? error.message : 'unexpected failure'))

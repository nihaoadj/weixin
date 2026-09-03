#!/usr/bin/env node
/**
 * Cross-platform T05 evidence entry point.  It creates fresh temporary reports,
 * runs the full suite for the selected side, then invokes the real checker.
 */
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { spawnSync } from 'node:child_process'

const root = path.resolve(import.meta.dirname, '..')
const runtime = globalThis
const python = runtime.process.env.PYTHON ?? 'python'

function run(command, args, cwd = root) {
  const result = spawnSync(command, args, { cwd, stdio: 'inherit', shell: false })
  if (result.error) throw result.error
  if (result.status !== 0) throw new Error(`${command} exited with ${result.status ?? 1}`)
}

function verifyFrontend(reportDirectory) {
  run(runtime.process.execPath, [
    'node_modules/vitest/vitest.mjs',
    'run',
    '--coverage',
    '--coverage.reporter=json',
    '--coverage.reporter=text',
    `--coverage.reportsDirectory=${reportDirectory}`,
  ])
  run(runtime.process.execPath, [
    'scripts/critical-coverage.mjs',
    '--frontend',
    path.join(reportDirectory, 'coverage-final.json'),
  ])
}

function verifyBackend(reportPath) {
  run(
    python,
    ['-m', 'pytest', '--cov=app', '--cov-branch', `--cov-report=json:${reportPath}`, '-q'],
    path.join(root, 'backend'),
  )
  run(runtime.process.execPath, ['scripts/critical-coverage.mjs', '--backend', reportPath])
}

const mode = runtime.process.argv[2]
if (!['--frontend', '--backend', '--all'].includes(mode)) {
  throw new Error('use --frontend, --backend, or --all')
}
const artifactRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'wx-t05-verify-'))
try {
  if (mode === '--frontend' || mode === '--all') verifyFrontend(path.join(artifactRoot, 'frontend'))
  if (mode === '--backend' || mode === '--all') verifyBackend(path.join(artifactRoot, 'backend.json'))
} catch (error) {
  runtime.console.error(error instanceof Error ? error.message : String(error))
  runtime.process.exitCode = 1
} finally {
  runtime.console.log(`T05 verification reports: ${artifactRoot}`)
}

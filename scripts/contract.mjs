import { mkdtemp, mkdir, readdir, readFile, rm } from 'node:fs/promises'
import { dirname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'
import console from 'node:console'
import { tmpdir } from 'node:os'
import process from 'node:process'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const artifacts = [
  'docs/openapi.json',
  'src/data/contracts/openapi.generated.ts',
  'src/test/fixtures/case-draft.json',
  'src/features/content/infrastructure/pathologyCatalog.generated.json',
]

function parseOutputDirectory(args) {
  if (args.length === 0) return projectRoot
  if (args.length === 2 && args[0] === '--output-dir') return resolve(projectRoot, args[1])
  throw new Error('Usage: node scripts/contract.mjs generate [--output-dir <directory>]')
}

function parseSnapshotDirectory(args) {
  if (args.length === 0) return projectRoot
  if (args.length === 2 && args[0] === '--snapshot-dir') return resolve(projectRoot, args[1])
  throw new Error('Usage: node scripts/contract.mjs check [--snapshot-dir <directory>]')
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: projectRoot,
    env: scrubbedEnvironment(options.env),
    stdio: 'inherit',
  })
  if (result.error) throw result.error
  if (result.status !== 0) throw new Error(`${command} exited with ${result.status}`)
}

function scrubbedEnvironment(overrides = {}) {
  const environment = { ...process.env }
  for (const name of Object.keys(environment)) {
    const normalizedName = name.toUpperCase()
    if (
      normalizedName === 'DATABASE_URL' ||
      normalizedName.startsWith('AI_') ||
      normalizedName.startsWith('PBL_') ||
      normalizedName.startsWith('COZE_') ||
      normalizedName.startsWith('JWT_') ||
      normalizedName.startsWith('OPENAI_') ||
      normalizedName.startsWith('WECHAT_') ||
      normalizedName.endsWith('_KEY') ||
      normalizedName.endsWith('_SECRET') ||
      normalizedName.endsWith('_TOKEN')
    ) {
      delete environment[name]
    }
  }
  return { ...environment, ...overrides }
}

function contractExportEnvironment() {
  return {
    APP_ENV: 'contract-export',
    DATABASE_URL: 'sqlite:///:memory:',
    JWT_SECRET: 'contract-export',
    SEED_SHOWCASE_CASE: 'false',
    AI_ENABLED: 'false',
    AI_BASE_URL: '',
    AI_API_KEY: '',
    AI_MODEL: '',
    ENABLE_DEMO_AUTH: 'false',
    WECHAT_APP_ID: '',
    WECHAT_APP_SECRET: '',
    WECHAT_API_BASE_URL: '',
    WECHAT_TEACHER_OPENIDS: '',
  }
}

function artifactPath(outputDirectory, artifact) {
  return resolve(outputDirectory, artifact)
}

async function generate(outputDirectory) {
  const outputPaths = artifacts.map((artifact) => artifactPath(outputDirectory, artifact))
  await Promise.all(outputPaths.map((outputPath) => mkdir(dirname(outputPath), { recursive: true })))

  run(process.env.PYTHON ?? 'python', ['backend/scripts/export_openapi.py', outputPaths[0]], {
    env: contractExportEnvironment(),
  })
  run(process.execPath, [
    join(projectRoot, 'node_modules/openapi-typescript/bin/cli.js'),
    outputPaths[0],
    '--empty-objects-unknown',
    '--output',
    outputPaths[1],
  ])
  run(process.env.PYTHON ?? 'python', ['backend/scripts/export_contract_fixtures.py', '--output', outputPaths[2]], {
    env: contractExportEnvironment(),
  })
  run(process.env.PYTHON ?? 'python', ['backend/scripts/export_pathology_catalog.py', '--output', outputPaths[3]], {
    env: contractExportEnvironment(),
  })
  run(process.execPath, [
    join(projectRoot, 'node_modules/prettier/bin/prettier.cjs'),
    '--config',
    join(projectRoot, '.prettierrc.json'),
    '--write',
    ...outputPaths,
  ])
}

function normalizeLineEndings(contents) {
  return contents.toString('utf8').replace(/\r\n?/g, '\n')
}

async function fileList(directory, rootDirectory = directory) {
  const entries = await readdir(directory, { withFileTypes: true })
  const result = []
  for (const entry of entries) {
    const absolutePath = join(directory, entry.name)
    if (entry.isDirectory()) {
      result.push(...(await fileList(absolutePath, rootDirectory)))
    } else if (entry.isFile()) {
      result.push(relative(rootDirectory, absolutePath).replaceAll('\\', '/'))
    }
  }
  return result
}

async function check(snapshotDirectory) {
  const temporaryDirectory = await mkdtemp(join(tmpdir(), 'medical-qa-contract-'))
  try {
    await generate(temporaryDirectory)
    const expected = new Set(artifacts)
    const generated = await fileList(temporaryDirectory)
    const extras = generated.filter((path) => !expected.has(path))
    if (extras.length > 0) throw new Error(`Unexpected generated contract artifacts: ${extras.join(', ')}`)

    const differences = []
    for (const artifact of artifacts) {
      const source = artifactPath(snapshotDirectory, artifact)
      const generatedPath = artifactPath(temporaryDirectory, artifact)
      try {
        const [sourceContents, generatedContents] = await Promise.all([readFile(source), readFile(generatedPath)])
        if (normalizeLineEndings(sourceContents) !== normalizeLineEndings(generatedContents)) differences.push(artifact)
      } catch (error) {
        if (error && error.code === 'ENOENT') differences.push(`${artifact} (missing)`)
        else throw error
      }
    }
    if (differences.length > 0) throw new Error(`Contract artifacts are out of date: ${differences.join(', ')}`)
  } finally {
    await rm(temporaryDirectory, { recursive: true, force: true })
  }
}

const [operation, ...args] = process.argv.slice(2)
try {
  if (operation === 'generate') await generate(parseOutputDirectory(args))
  else if (operation === 'check') await check(parseSnapshotDirectory(args))
  else throw new Error('Usage: node scripts/contract.mjs <generate|check> [--output-dir <directory>]')
} catch (error) {
  console.error(error instanceof Error ? error.message : error)
  process.exitCode = 1
}

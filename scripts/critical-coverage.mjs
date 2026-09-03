#!/usr/bin/env node
/** Validate current Vitest/coverage.py JSON against T05 global responsibility groups. */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..')
const runtime = globalThis

function fail(message) {
  throw new Error(`critical coverage: ${message}`)
}

function normal(value) {
  if (typeof value !== 'string' || !value) fail('coverage path must be a non-empty string')
  return path.resolve(root, value.replaceAll('\\', '/')).replaceAll('\\', '/')
}

function count(value, label) {
  if (!Number.isSafeInteger(value) || value < 0) fail(`${label} must be a non-negative integer`)
  return value
}

function metric(covered, total, label) {
  count(covered, `${label}.covered`)
  count(total, `${label}.total`)
  if (covered > total) fail(`${label}.covered cannot exceed ${label}.total`)
  return { covered, total }
}

function limit(value, label) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 100) {
    fail(`${label} must be a finite percentage from 0 to 100`)
  }
  return value
}

function percentage(value, label) {
  if (value.total === 0) return null
  const result = (value.covered / value.total) * 100
  if (!Number.isFinite(result) || result < 0 || result > 100) fail(`${label} computed percentage is invalid`)
  return result
}

function expand(pattern) {
  const normalized = pattern.replaceAll('\\', '/')
  if (!normalized.includes('*')) return [normal(normalized)]
  const parts = normalized.split('/')
  const index = parts.findIndex((part) => part.includes('*'))
  const start = path.resolve(root, ...parts.slice(0, index))
  const regex = new RegExp(
    `^${normalized
      .replace(/[.+^${}()|[\]\\]/g, '\\$&')
      .replaceAll('**/', '(.*/)?')
      .replaceAll('**', '.*')
      .replaceAll('*', '[^/]*')}$`,
  )
  const found = []
  function walk(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const item = path.join(directory, entry.name)
      if (entry.isDirectory()) walk(item)
      else if (regex.test(path.relative(root, item).replaceAll('\\', '/'))) found.push(normal(item))
    }
  }
  if (fs.existsSync(start)) walk(start)
  return found
}

function vitestMetric(entry, name, file) {
  const key = name === 'lines' ? 's' : name === 'functions' ? 'f' : 'b'
  if (
    !entry ||
    typeof entry !== 'object' ||
    !Object.hasOwn(entry, key) ||
    !entry[key] ||
    typeof entry[key] !== 'object'
  ) {
    fail(`${file} has no ${name} coverage data`)
  }
  const values = Object.values(entry[key])
  if (name === 'branches') {
    if (!values.every(Array.isArray)) fail(`${file} has malformed branch coverage data`)
    const valuesFlat = values.flat()
    return metric(
      valuesFlat.filter((value) => count(value, `${file}.${name}`) > 0).length,
      valuesFlat.length,
      `${file}.${name}`,
    )
  }
  return metric(values.filter((value) => count(value, `${file}.${name}`) > 0).length, values.length, `${file}.${name}`)
}

function load(kind, reportPath) {
  let raw
  try {
    raw = JSON.parse(fs.readFileSync(reportPath, 'utf8'))
  } catch (error) {
    fail(`cannot read coverage JSON ${reportPath}: ${error instanceof Error ? error.message : String(error)}`)
  }
  if (!raw || typeof raw !== 'object') fail('coverage JSON root must be an object')
  const entries = new Map()
  if (kind === 'frontend') {
    for (const [file, entry] of Object.entries(raw)) {
      entries.set(
        normal(file),
        Object.fromEntries(['lines', 'branches', 'functions'].map((name) => [name, vitestMetric(entry, name, file)])),
      )
    }
  } else {
    if (!raw.files || typeof raw.files !== 'object') fail('backend coverage JSON has no files object')
    for (const [file, entry] of Object.entries(raw.files)) {
      const summary = entry?.summary
      if (!summary || typeof summary !== 'object') fail(`${file} has no coverage summary`)
      entries.set(normal(path.isAbsolute(file) ? file : path.join('backend', file)), {
        lines: metric(summary.covered_lines, summary.num_statements, `${file}.lines`),
        branches: metric(summary.covered_branches, summary.num_branches, `${file}.branches`),
      })
    }
  }
  return entries
}

function metrics(config, kind) {
  if (!config || typeof config !== 'object' || !config.thresholds || typeof config.thresholds !== 'object') {
    fail(`${kind} has no thresholds`)
  }
  const names = Object.keys(config.thresholds)
  if (!names.length) fail(`${kind} has no threshold metrics`)
  for (const name of names) limit(config.thresholds[name], `${kind}.${name} threshold`)
  return names
}

function checkGroup(kind, group, report, names, thresholds) {
  if (!group || typeof group.name !== 'string' || !group.name || !Array.isArray(group.files) || !group.files.length) {
    fail(`${kind} group has no name or file list`)
  }
  const files = [...new Set(group.files.flatMap(expand))]
  if (!files.length) fail(`${group.name} matches no source files`)
  const totals = Object.fromEntries(names.map((name) => [name, { covered: 0, total: 0 }]))
  for (const file of files) {
    if (!fs.existsSync(file)) fail(`${group.name} source file is missing: ${path.relative(root, file)}`)
    const entry = report.get(file)
    if (!entry) fail(`${group.name} is absent from coverage: ${path.relative(root, file)}`)
    for (const name of names) {
      if (!Object.hasOwn(entry, name)) fail(`${group.name} has no ${name} coverage data: ${path.relative(root, file)}`)
      const value = metric(entry[name].covered, entry[name].total, `${group.name}.${name}`)
      totals[name].covered += value.covered
      totals[name].total += value.total
    }
  }
  return names.map((name) => {
    const result = percentage(totals[name], `${group.name}.${name}`)
    if (name === 'lines' && result === null) fail(`${group.name} has no executable line coverage data`)
    // A group with no syntactic branches is applicable, but has no ratio to compare.
    if (result === null) return `${name}=N/A`
    if (result < thresholds[name]) fail(`${group.name} ${name} ${result.toFixed(2)}% is below ${thresholds[name]}%`)
    return `${name}=${result.toFixed(2)}%`
  })
}

function checkOverall(kind, report, names, thresholds) {
  const totals = Object.fromEntries(names.map((name) => [name, { covered: 0, total: 0 }]))
  if (!report.size) fail(`${kind} coverage report has no files`)
  for (const [file, entry] of report) {
    for (const name of names) {
      if (!Object.hasOwn(entry, name)) fail(`${kind} report has no ${name} coverage data: ${path.relative(root, file)}`)
      const value = metric(entry[name].covered, entry[name].total, `${kind}.all.${name}`)
      totals[name].covered += value.covered
      totals[name].total += value.total
    }
  }
  return names.map((name) => {
    const result = percentage(totals[name], `${kind}.all.${name}`)
    if (name === 'lines' && result === null) fail(`${kind} all has no executable line coverage data`)
    if (result === null) return `${name}=N/A`
    if (result < thresholds[name]) fail(`${kind} all ${name} ${result.toFixed(2)}% is below ${thresholds[name]}%`)
    return `${name}=${result.toFixed(2)}%`
  })
}

export function check(kind, configPath, reportPath) {
  if (kind !== 'frontend' && kind !== 'backend') fail(`unknown report kind ${kind}`)
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'))?.[kind]
  const names = metrics(config, kind)
  if (!Array.isArray(config.groups) || !config.groups.length) fail(`${kind} has no critical groups`)
  const report = load(kind, reportPath)
  const overallThresholds = config.overallThresholds
  if (!overallThresholds || typeof overallThresholds !== 'object') fail(`${kind} has no overall thresholds`)
  for (const name of names) limit(overallThresholds[name], `${kind}.overall.${name} threshold`)
  runtime.console.log(`${kind}:all ${checkOverall(kind, report, names, overallThresholds).join(' ')}`)
  for (const group of config.groups) {
    runtime.console.log(`${kind}:${group.name} ${checkGroup(kind, group, report, names, config.thresholds).join(' ')}`)
  }
}

function fixture(kind, dir, report, config) {
  const reportPath = path.join(dir, `${kind}.coverage.json`)
  const configPath = path.join(dir, `${kind}.config.json`)
  fs.writeFileSync(reportPath, JSON.stringify(report))
  fs.writeFileSync(configPath, JSON.stringify({ [kind]: config }))
  return () => check(kind, configPath, reportPath)
}

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

function selfTest() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'critical-coverage-'))
  try {
    const source = path.join(dir, 'one.ts')
    fs.writeFileSync(source, 'export const one = 1\n')
    const report = { [source]: { s: { 0: 1 }, f: { 0: 1 }, b: { 0: [1, 1] } } }
    const config = {
      overallThresholds: { lines: 100, branches: 100, functions: 100 },
      thresholds: { lines: 100, branches: 100, functions: 100 },
      groups: [{ name: 'one', files: [source] }],
    }
    assert.doesNotThrow(fixture('frontend', dir, report, config), 'exact threshold uses real check')
    const below = clone(report)
    below[source].s[0] = 0
    assert.throws(fixture('frontend', dir, below, config), /below/)
    assert.throws(
      fixture('frontend', dir, { [path.join(dir, 'other.ts')]: report[source] }, config),
      /absent from coverage/,
    )
    assert.throws(fixture('frontend', dir, report, { ...config, groups: [] }), /no critical groups/)
    assert.throws(fixture('frontend', dir, report, { ...config, thresholds: { lines: Number.NaN } }), /threshold/)
    assert.throws(
      fixture('frontend', dir, report, {
        ...config,
        groups: [{ name: 'missing', files: [path.join(dir, 'missing.ts')] }],
      }),
      /source file is missing/,
    )
    const zeroBranches = clone(report)
    zeroBranches[source].b = {}
    assert.doesNotThrow(fixture('frontend', dir, zeroBranches, config), 'zero applicable branch path uses real check')
    const emptyCounts = clone(report)
    emptyCounts[source] = { s: {}, f: {}, b: {} }
    assert.throws(fixture('frontend', dir, emptyCounts, config), /no executable line coverage data/)
    const malformed = clone(report)
    delete malformed[source].s
    assert.throws(fixture('frontend', dir, malformed, config), /no lines coverage data/)

    const relative = path.relative(path.join(root, 'backend'), source).replaceAll('\\', '/')
    const backendReport = {
      files: { [relative]: { summary: { covered_lines: 1, num_statements: 1, covered_branches: 1, num_branches: 1 } } },
    }
    const backend = {
      overallThresholds: { lines: 100, branches: 100 },
      thresholds: { lines: 100, branches: 100 },
      groups: [{ name: 'one', files: [source] }],
    }
    assert.doesNotThrow(fixture('backend', dir, backendReport, backend), 'backend exact threshold uses real check')
    const missingCovered = clone(backendReport)
    delete missingCovered.files[relative].summary.covered_lines
    assert.throws(fixture('backend', dir, missingCovered, backend), /covered must be a non-negative integer/)
    const impossible = clone(backendReport)
    impossible.files[relative].summary.covered_branches = 2
    assert.throws(fixture('backend', dir, impossible, backend), /cannot exceed/)
    runtime.console.log('critical coverage self-test passed')
  } finally {
    fs.rmSync(dir, { recursive: true, force: true })
  }
}

const [mode, reportPath] = runtime.process.argv.slice(2)
if (mode === '--self-test') selfTest()
else if (mode === '--frontend' || mode === '--backend') {
  if (!reportPath) fail('coverage JSON path is required')
  check(mode.slice(2), path.join(root, 'config/critical-coverage.json'), path.resolve(root, reportPath))
} else fail('use --self-test, --frontend <coverage.json>, or --backend <coverage.json>')

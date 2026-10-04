#!/usr/bin/env node
/* global console */
import fs from 'node:fs'
import { createRequire } from 'node:module'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'
import * as typescriptModule from 'typescript'

const ts = typescriptModule.default || typescriptModule
const requireModule = createRequire(import.meta.url)
const vueCompilerSfc = (() => {
  try {
    return requireModule('@vue/compiler-sfc')
  } catch {
    return undefined
  }
})()
const parseSfc = vueCompilerSfc?.parse
const root = process.cwd()
const configFile = path.join(root, 'config', 'frontend-boundaries.json')
const config = JSON.parse(fs.readFileSync(configFile, 'utf8'))
const implementationExtensions = config.implementationExtensions || ['.ts', '.vue']
const platformIoMembers = new Set(
  config.platformIoMembers || [
    'request',
    'getStorageSync',
    'setStorageSync',
    'removeStorageSync',
    'clearStorageSync',
    'getStorageInfoSync',
  ],
)
const frameworkModules = config.frameworkModules || ['vue', '@dcloudio/uni-app']
const browserNetworkGlobals = new Set(config.browserNetworkGlobals || ['fetch', 'XMLHttpRequest'])
const browserGlobalObjects = new Set(config.browserGlobalObjects || ['window', 'globalThis', 'self'])
const platformIoRoots = config.platformIoRoots || ['src/platform']
const browserNetworkRoots = config.browserNetworkRoots || ['src/platform/http']

const slash = (value) => value.replaceAll('\\', '/')
const relativePath = (file) => slash(path.relative(root, file))
const normalizedPath = (file) => slash(path.resolve(file))

function isImplementationFile(file) {
  const relative = relativePath(file)
  if (file.endsWith('.d.ts')) return false
  if (!implementationExtensions.some((extension) => file.endsWith(extension))) return false
  if (!relative.startsWith(`${config.sourceRoot}/`)) return false
  return (
    !config.testFileMarkers.some((marker) => path.basename(file).includes(marker)) && !relative.startsWith('src/test/')
  )
}

function isJsonResourceFile(file) {
  const relative = relativePath(file)
  return relative.startsWith(`${config.sourceRoot}/`) && file.endsWith('.json')
}

function listFiles(directory) {
  if (!fs.existsSync(directory)) return []
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const file = path.join(directory, entry.name)
    return entry.isDirectory() ? listFiles(file) : isImplementationFile(file) || isJsonResourceFile(file) ? [file] : []
  })
}

function candidateFiles(candidate) {
  return [
    candidate,
    ...implementationExtensions.map((extension) => `${candidate}${extension}`),
    ...implementationExtensions.map((extension) => path.join(candidate, `index${extension}`)),
    `${candidate}.json`,
  ]
}

function resolveImport(specifier, importer, entries) {
  let candidate
  const aliases = Object.entries(config.aliases || { '@/': 'src/' }).sort(
    (left, right) => right[0].length - left[0].length,
  )
  const alias = aliases.find(([prefix]) => specifier === prefix.slice(0, -1) || specifier.startsWith(prefix))
  if (alias) {
    const [prefix, targetRoot] = alias
    const suffix = specifier === prefix.slice(0, -1) ? '' : specifier.slice(prefix.length)
    candidate = path.join(root, targetRoot, suffix)
  } else if (specifier.startsWith('.')) {
    candidate = path.resolve(path.dirname(importer), specifier)
  } else {
    return undefined
  }

  const wanted = new Set(candidateFiles(candidate).map(normalizedPath))
  return entries.find((entry) => wanted.has(normalizedPath(entry.file)))
}

function classify(relative) {
  const normalized = slash(relative)
  if (config.generatedPaths.includes(normalized)) {
    const featureOwner = normalized.match(/^src\/features\/([^/]+)\//)?.[1]
    return { kind: 'generated', path: normalized, featureOwner }
  }
  if (normalized.endsWith('.json')) return { kind: 'resource', path: normalized }
  if (config.presentationRoots.some((rootPath) => normalized === rootPath || normalized.startsWith(`${rootPath}/`))) {
    return { kind: 'presentation', path: normalized }
  }
  if (config.legacyRoots.some((rootPath) => normalized === rootPath || normalized.startsWith(`${rootPath}/`))) {
    return { kind: 'legacy', path: normalized }
  }
  if (config.sharedRoots.some((rootPath) => normalized === rootPath || normalized.startsWith(`${rootPath}/`))) {
    return { kind: 'shared', path: normalized }
  }
  if (normalized.startsWith('src/platform/')) return { kind: 'platform', path: normalized }
  if (normalized.startsWith('src/bootstrap/')) return { kind: 'bootstrap', path: normalized }
  if (normalized.startsWith('src/shared/')) return { kind: 'shared', path: normalized }
  const feature = normalized.match(/^src\/features\/([^/]+)\/(.*)$/)
  if (feature) {
    const [featureName, rest] = feature.slice(1)
    const first = rest.split('/')[0]
    const layer = config.featureLayers.includes(first) ? first : rest === 'public.ts' ? 'public' : 'unknown'
    return { kind: 'feature', feature: featureName, layer, path: normalized }
  }
  return { kind: 'other', path: normalized }
}

function isPresentationContext(sourceInfo) {
  return sourceInfo.kind === 'presentation' || (sourceInfo.kind === 'feature' && sourceInfo.layer === 'presentation')
}

function startsWithPath(candidate, prefix) {
  return candidate === prefix || candidate.startsWith(`${prefix}/`)
}

function sourceUnits(entry) {
  if (!entry.relative.endsWith('.vue')) return [{ source: entry.source, offset: 0 }]
  if (typeof parseSfc !== 'function') {
    return [
      {
        source: '',
        offset: 0,
        sfcErrors: ['@vue/compiler-sfc is unavailable; SFC scripts cannot be analyzed safely'],
      },
    ]
  }

  const parsed = parseSfc(entry.source, { filename: entry.file })
  const units = [parsed.descriptor.script, parsed.descriptor.scriptSetup].filter(Boolean).map((block) => ({
    source: block.src ? '' : block.content,
    offset: block.loc.start.offset,
    externalSrc: block.src,
  }))
  if (parsed.errors.length) units.push({ source: '', offset: 0, sfcErrors: parsed.errors })
  return units.length ? units : [{ source: '', offset: 0 }]
}

function lineFor(entry, unit, sourceFile, node) {
  const position =
    node && typeof node.getStart === 'function'
      ? node.getStart(sourceFile)
      : Number.isInteger(node?.start)
        ? node.start
        : 0
  const line = sourceFile.getLineAndCharacterOfPosition(position).line
  return entry.source.slice(0, unit.offset).split('\n').length + line
}

function unwrapExpression(node) {
  let current = node
  while (
    current &&
    (ts.isParenthesizedExpression(current) ||
      ts.isAsExpression(current) ||
      ts.isTypeAssertionExpression(current) ||
      ts.isNonNullExpression(current) ||
      (ts.isSatisfiesExpression && ts.isSatisfiesExpression(current)))
  ) {
    current = current.expression
  }
  return current
}

function identifierText(node) {
  const unwrapped = unwrapExpression(node)
  return unwrapped && ts.isIdentifier(unwrapped) ? unwrapped.text : undefined
}

function propertyText(node) {
  if (ts.isIdentifier(node) || ts.isStringLiteralLike(node)) return node.text
  if (ts.isPropertyAccessExpression(node)) return node.name.text
  if (
    ts.isElementAccessExpression(node) &&
    node.argumentExpression &&
    ts.isStringLiteralLike(node.argumentExpression)
  ) {
    return node.argumentExpression.text
  }
  return undefined
}

function importTypeSpecifier(node) {
  const argument = node.argument
  if (ts.isLiteralTypeNode(argument) && ts.isStringLiteralLike(argument.literal)) return argument.literal.text
  if (ts.isStringLiteralLike(argument)) return argument.text
  return undefined
}

function isFrameworkModule(specifier) {
  return frameworkModules.some((moduleName) => specifier === moduleName || specifier.startsWith(`${moduleName}/`))
}

function addViolation(violations, entry, unit, sourceFile, node, specifier, target, message) {
  violations.push({
    file: entry.relative,
    line: lineFor(entry, unit, sourceFile, node),
    import: specifier,
    target: target?.path || 'external',
    message,
  })
}

function collectPlatformAliases(sourceFile) {
  const platformObjects = new Set(['uni'])
  const ioAliases = new Map()
  const browserObjects = new Set(browserGlobalObjects)
  const browserIoAliases = new Map([...browserNetworkGlobals].map((name) => [name, name]))
  const declarations = []

  function collect(node) {
    if (ts.isVariableDeclaration(node)) declarations.push(node)
    ts.forEachChild(node, collect)
  }
  collect(sourceFile)

  let changed = true
  while (changed) {
    changed = false
    for (const declaration of declarations) {
      const initializer = declaration.initializer && unwrapExpression(declaration.initializer)
      if (!initializer) continue
      if (ts.isIdentifier(declaration.name)) {
        const initializerName = identifierText(initializer)
        if (initializerName && platformObjects.has(initializerName) && !platformObjects.has(declaration.name.text)) {
          platformObjects.add(declaration.name.text)
          changed = true
        }
        if (initializerName && browserObjects.has(initializerName) && !browserObjects.has(declaration.name.text)) {
          browserObjects.add(declaration.name.text)
          changed = true
        }
        const member =
          ts.isPropertyAccessExpression(initializer) || ts.isElementAccessExpression(initializer)
            ? propertyText(initializer)
            : undefined
        const base = member ? identifierText(initializer.expression) : undefined
        if (
          member &&
          base &&
          platformObjects.has(base) &&
          platformIoMembers.has(member) &&
          !ioAliases.has(declaration.name.text)
        ) {
          ioAliases.set(declaration.name.text, member)
          changed = true
        }
        if (
          member &&
          base &&
          browserObjects.has(base) &&
          browserNetworkGlobals.has(member) &&
          !browserIoAliases.has(declaration.name.text)
        ) {
          browserIoAliases.set(declaration.name.text, member)
          changed = true
        }
        const alias = identifierText(initializer)
        if (alias && ioAliases.has(alias) && !ioAliases.has(declaration.name.text)) {
          ioAliases.set(declaration.name.text, ioAliases.get(alias))
          changed = true
        }
        if (alias && browserIoAliases.has(alias) && !browserIoAliases.has(declaration.name.text)) {
          browserIoAliases.set(declaration.name.text, browserIoAliases.get(alias))
          changed = true
        }
      } else if (ts.isObjectBindingPattern(declaration.name)) {
        const initializerName = identifierText(initializer)
        if (!initializerName) continue
        if (platformObjects.has(initializerName)) {
          for (const element of declaration.name.elements) {
            if (!ts.isBindingElement(element)) continue
            const member = element.propertyName ? propertyText(element.propertyName) : identifierText(element.name)
            const binding = identifierText(element.name)
            if (binding && member && platformIoMembers.has(member) && !ioAliases.has(binding)) {
              ioAliases.set(binding, member)
              changed = true
            }
          }
        }
        if (browserObjects.has(initializerName)) {
          for (const element of declaration.name.elements) {
            if (!ts.isBindingElement(element)) continue
            const member = element.propertyName ? propertyText(element.propertyName) : identifierText(element.name)
            const binding = identifierText(element.name)
            if (binding && member && browserNetworkGlobals.has(member) && !browserIoAliases.has(binding)) {
              browserIoAliases.set(binding, member)
              changed = true
            }
          }
        }
      }
    }
  }
  return { platformObjects, ioAliases, browserObjects, browserIoAliases }
}

function platformMember(node, platformObjects) {
  if (!ts.isPropertyAccessExpression(node) && !ts.isElementAccessExpression(node)) return undefined
  const base = identifierText(node.expression)
  if (!base || !platformObjects.has(base)) return undefined
  return { member: propertyText(node), opaque: ts.isElementAccessExpression(node) && !propertyText(node) }
}

function browserMember(node, browserObjects) {
  if (!ts.isPropertyAccessExpression(node) && !ts.isElementAccessExpression(node)) return undefined
  const base = identifierText(node.expression)
  if (!base || !browserObjects.has(base)) return undefined
  return { member: propertyText(node), opaque: ts.isElementAccessExpression(node) && !propertyText(node) }
}

function parseEntry(entry, sourceInfo, violations, graphNode) {
  if (sourceInfo.kind === 'generated' || sourceInfo.kind === 'resource') return

  for (const unit of sourceUnits(entry)) {
    const sourceFile = ts.createSourceFile(entry.file, unit.source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS)
    if (sourceFile.parseDiagnostics.length) {
      const diagnostic = sourceFile.parseDiagnostics[0]
      addViolation(
        violations,
        entry,
        unit,
        sourceFile,
        diagnostic,
        'TypeScript parser',
        sourceInfo,
        'implementation script could not be parsed by TypeScript',
      )
      continue
    }
    if (unit.sfcErrors?.length) {
      addViolation(
        violations,
        entry,
        unit,
        sourceFile,
        undefined,
        'Vue SFC parser',
        sourceInfo,
        'SFC script block could not be parsed by @vue/compiler-sfc',
      )
      continue
    }
    const { platformObjects, ioAliases, browserObjects, browserIoAliases } = collectPlatformAliases(sourceFile)
    const reportedIo = new Set()

    function reportPlatformIo(node, importName, message = 'platform HTTP/Storage I/O must stay behind src/platform') {
      if (platformIoRoots.some((rootPath) => startsWithPath(sourceInfo.path, rootPath))) return
      const position = node.getStart(sourceFile)
      if (reportedIo.has(position)) return
      reportedIo.add(position)
      addViolation(violations, entry, unit, sourceFile, node, importName, sourceInfo, message)
    }

    function reportBrowserNetworkIo(
      node,
      importName,
      message = 'browser network I/O must stay behind src/platform/http',
    ) {
      if (browserNetworkRoots.some((rootPath) => startsWithPath(sourceInfo.path, rootPath))) return
      const position = node.getStart(sourceFile)
      if (reportedIo.has(position)) return
      reportedIo.add(position)
      addViolation(violations, entry, unit, sourceFile, node, importName, sourceInfo, message)
    }

    function addDependency(specifier, node, type) {
      const targetEntry = resolveImport(specifier, entry.file, graphNode.entries)
      const edge = {
        specifier,
        source: entry,
        target: targetEntry,
        line: lineFor(entry, unit, sourceFile, node),
        type,
        unit,
        sourceFile,
        node,
      }
      graphNode.edges.push(edge)
      if (!targetEntry) {
        const localImport = type === 'sfc-script' || specifier.startsWith('@/') || specifier.startsWith('.')
        const assetImport = /\.(?:css|scss|less|svg|png|jpe?g|gif|webp)$/iu.test(specifier)
        if (localImport && !assetImport) {
          addViolation(
            violations,
            entry,
            unit,
            sourceFile,
            node,
            specifier,
            undefined,
            'unresolved local import must be reviewed before merge',
          )
        } else if (isFrameworkModule(specifier) && !isPresentationContext(sourceInfo) && sourceInfo.kind !== 'other') {
          addViolation(
            violations,
            entry,
            unit,
            sourceFile,
            node,
            specifier,
            undefined,
            'external framework dependency may not enter core layers',
          )
        }
        return
      }

      const target = classify(targetEntry.relative)
      if (target.kind === 'generated' && target.featureOwner) {
        const canReadFeatureGenerated =
          sourceInfo.kind === 'bootstrap' ||
          (sourceInfo.kind === 'feature' &&
            sourceInfo.feature === target.featureOwner &&
            ['public', 'infrastructure'].includes(sourceInfo.layer))
        if (!canReadFeatureGenerated)
          addViolation(
            violations,
            entry,
            unit,
            sourceFile,
            node,
            specifier,
            target,
            'feature-owned generated artifacts may be read only by their public/infrastructure layer or bootstrap',
          )
      }

      if (isFrameworkModule(specifier) && !isPresentationContext(sourceInfo) && sourceInfo.kind !== 'other') {
        addViolation(
          violations,
          entry,
          unit,
          sourceFile,
          node,
          specifier,
          target,
          'external framework dependency may not enter core layers',
        )
      }

      if (sourceInfo.kind === 'presentation') {
        if (target.kind === 'legacy')
          addViolation(
            violations,
            entry,
            unit,
            sourceFile,
            node,
            specifier,
            target,
            'pages/components may not import legacy services/data/config',
          )
        if (target.kind === 'feature' && !['public', 'presentation'].includes(target.layer))
          addViolation(
            violations,
            entry,
            unit,
            sourceFile,
            node,
            specifier,
            target,
            'pages/components may import only feature public APIs or presentation views',
          )
        if (
          target.kind === 'platform' &&
          !config.presentationPlatformRoots.some((rootPath) => startsWithPath(target.path, rootPath))
        )
          addViolation(
            violations,
            entry,
            unit,
            sourceFile,
            node,
            specifier,
            target,
            'pages/components may use only navigation/log platform ports',
          )
        if (target.kind === 'bootstrap')
          addViolation(
            violations,
            entry,
            unit,
            sourceFile,
            node,
            specifier,
            target,
            'pages/components may not import the composition root',
          )
      }

      if (sourceInfo.kind === 'feature') {
        if (sourceInfo.layer === 'domain') {
          if (['platform', 'bootstrap', 'legacy', 'presentation'].includes(target.kind))
            addViolation(
              violations,
              entry,
              unit,
              sourceFile,
              node,
              specifier,
              target,
              'domain may not depend on platform, bootstrap, legacy, or presentation code',
            )
          if (target.kind === 'feature' && (target.feature !== sourceInfo.feature || target.layer !== 'domain'))
            addViolation(
              violations,
              entry,
              unit,
              sourceFile,
              node,
              specifier,
              target,
              'domain may depend only on its own domain types/ports',
            )
        }
        if (sourceInfo.layer === 'application') {
          if (target.kind === 'platform')
            addViolation(
              violations,
              entry,
              unit,
              sourceFile,
              node,
              specifier,
              target,
              'application may not depend on concrete platform adapters',
            )
          if (target.kind === 'bootstrap' || target.kind === 'legacy')
            addViolation(
              violations,
              entry,
              unit,
              sourceFile,
              node,
              specifier,
              target,
              'application may not depend on bootstrap or legacy code',
            )
          if (
            target.kind === 'feature' &&
            (target.feature !== sourceInfo.feature || ['infrastructure', 'presentation'].includes(target.layer))
          )
            addViolation(
              violations,
              entry,
              unit,
              sourceFile,
              node,
              specifier,
              target,
              'application may depend on domain ports, not another feature or concrete adapters',
            )
        }
        if (sourceInfo.layer === 'presentation') {
          if (target.kind === 'feature' && !['public', 'presentation'].includes(target.layer))
            addViolation(
              violations,
              entry,
              unit,
              sourceFile,
              node,
              specifier,
              target,
              'feature presentation may depend only on public APIs or presentation views, not business layers',
            )
          if (target.kind === 'bootstrap' || target.kind === 'legacy')
            addViolation(
              violations,
              entry,
              unit,
              sourceFile,
              node,
              specifier,
              target,
              'feature presentation may not depend on bootstrap or legacy code',
            )
        }
        if (sourceInfo.layer === 'infrastructure') {
          if (target.kind === 'bootstrap' || target.kind === 'legacy')
            addViolation(
              violations,
              entry,
              unit,
              sourceFile,
              node,
              specifier,
              target,
              'infrastructure may not depend on bootstrap or legacy code',
            )
          if (target.kind === 'feature' && target.feature !== sourceInfo.feature && target.layer !== 'domain')
            addViolation(
              violations,
              entry,
              unit,
              sourceFile,
              node,
              specifier,
              target,
              'cross-feature infrastructure must use a port/public API',
            )
        }
      }

      if (sourceInfo.kind === 'platform' && target.kind === 'feature')
        addViolation(
          violations,
          entry,
          unit,
          sourceFile,
          node,
          specifier,
          target,
          'platform may not depend on feature code',
        )
      if (sourceInfo.kind === 'shared' && ['feature', 'platform', 'bootstrap', 'legacy'].includes(target.kind))
        addViolation(
          violations,
          entry,
          unit,
          sourceFile,
          node,
          specifier,
          target,
          'shared must remain pure and dependency-light',
        )
    }

    if (unit.externalSrc) {
      addDependency(unit.externalSrc, undefined, 'sfc-script')
      continue
    }

    function visit(node) {
      if (ts.isImportDeclaration(node) && ts.isStringLiteralLike(node.moduleSpecifier)) {
        addDependency(
          node.moduleSpecifier.text,
          node.moduleSpecifier,
          node.importClause?.isTypeOnly ? 'type-import' : 'import',
        )
      } else if (ts.isExportDeclaration(node) && node.moduleSpecifier && ts.isStringLiteralLike(node.moduleSpecifier)) {
        addDependency(node.moduleSpecifier.text, node.moduleSpecifier, node.isTypeOnly ? 'type-export' : 'export')
      } else if (ts.isImportTypeNode(node)) {
        const specifier = importTypeSpecifier(node)
        if (specifier) addDependency(specifier, node, 'import-type')
        else
          addViolation(
            violations,
            entry,
            unit,
            sourceFile,
            node,
            'opaque import type',
            sourceInfo,
            'opaque import types must use a literal module path',
          )
      } else if (ts.isImportEqualsDeclaration(node)) {
        const reference = node.moduleReference
        if (
          ts.isExternalModuleReference(reference) &&
          reference.expression &&
          ts.isStringLiteralLike(reference.expression)
        )
          addDependency(reference.expression.text, reference.expression, 'import-equals')
        else if (ts.isExternalModuleReference(reference))
          addViolation(
            violations,
            entry,
            unit,
            sourceFile,
            node,
            'opaque import-equals',
            sourceInfo,
            'opaque module loading must use a literal local module',
          )
      } else if (ts.isCallExpression(node)) {
        if (node.expression.kind === ts.SyntaxKind.ImportKeyword) {
          const argument = node.arguments.length === 1 ? node.arguments[0] : undefined
          if (argument && ts.isStringLiteralLike(argument)) addDependency(argument.text, argument, 'dynamic-import')
          else
            addViolation(
              violations,
              entry,
              unit,
              sourceFile,
              node,
              'opaque dynamic import',
              sourceInfo,
              'dynamic imports must use a literal module path',
            )
        } else if (ts.isIdentifier(node.expression) && node.expression.text === 'require') {
          const argument = node.arguments.length === 1 ? node.arguments[0] : undefined
          if (argument && ts.isStringLiteralLike(argument)) addDependency(argument.text, argument, 'require')
          else
            addViolation(
              violations,
              entry,
              unit,
              sourceFile,
              node,
              'opaque require',
              sourceInfo,
              'opaque module loading must use a literal local module',
            )
        } else if (ts.isIdentifier(node.expression) && ioAliases.has(node.expression.text)) {
          reportPlatformIo(node, `uni.${ioAliases.get(node.expression.text)}`)
        } else if (ts.isIdentifier(node.expression) && browserIoAliases.has(node.expression.text)) {
          reportBrowserNetworkIo(node, `browser.${browserIoAliases.get(node.expression.text)}`)
        }
      } else if (ts.isNewExpression(node)) {
        const constructorName = identifierText(node.expression)
        if (constructorName && browserIoAliases.has(constructorName))
          reportBrowserNetworkIo(node, `browser.${browserIoAliases.get(constructorName)}`)
      }

      if (ts.isPropertyAccessExpression(node) || ts.isElementAccessExpression(node)) {
        const access = platformMember(node, platformObjects)
        if (access?.opaque)
          reportPlatformIo(
            node,
            'opaque uni platform API access',
            'opaque platform API access must stay behind src/platform',
          )
        else if (access?.member && platformIoMembers.has(access.member)) reportPlatformIo(node, `uni.${access.member}`)
        const browserAccess = browserMember(node, browserObjects)
        if (browserAccess?.opaque)
          reportBrowserNetworkIo(
            node,
            'opaque browser network API access',
            'opaque browser network API access must stay behind src/platform/http',
          )
        else if (browserAccess?.member && browserNetworkGlobals.has(browserAccess.member))
          reportBrowserNetworkIo(node, `browser.${browserAccess.member}`)
      }
      ts.forEachChild(node, visit)
    }
    visit(sourceFile)
  }
}

function detectCycles(entries, graph, violations) {
  let nextIndex = 0
  const stack = []
  const onStack = new Set()
  const indexes = new Map()
  const lowLinks = new Map()

  function strongConnect(key) {
    indexes.set(key, nextIndex)
    lowLinks.set(key, nextIndex)
    nextIndex += 1
    stack.push(key)
    onStack.add(key)

    for (const edge of graph.get(key).edges) {
      if (!edge.target) continue
      const targetKey = normalizedPath(edge.target.file)
      if (!indexes.has(targetKey)) {
        strongConnect(targetKey)
        lowLinks.set(key, Math.min(lowLinks.get(key), lowLinks.get(targetKey)))
      } else if (onStack.has(targetKey)) {
        lowLinks.set(key, Math.min(lowLinks.get(key), indexes.get(targetKey)))
      }
    }

    if (lowLinks.get(key) !== indexes.get(key)) return
    const component = []
    let member
    do {
      member = stack.pop()
      onStack.delete(member)
      component.push(member)
    } while (member !== key)
    const componentSet = new Set(component)
    const cycleEdges = component.flatMap((memberKey) =>
      graph.get(memberKey).edges.filter((edge) => edge.target && componentSet.has(normalizedPath(edge.target.file))),
    )
    if (
      component.length > 1 ||
      cycleEdges.some((edge) => normalizedPath(edge.source.file) === normalizedPath(edge.target.file))
    ) {
      const members = component.map((memberKey) => graph.get(memberKey).entry.relative).sort()
      for (const edge of cycleEdges)
        addViolation(
          violations,
          edge.source,
          edge.unit,
          edge.sourceFile,
          edge.node,
          edge.specifier,
          classify(edge.target.relative),
          `dependency cycle detected across ${members.join(' -> ')}`,
        )
    }
  }

  for (const entry of entries) {
    const key = normalizedPath(entry.file)
    if (!indexes.has(key)) strongConnect(key)
  }
}

export function analyze(entries) {
  const violations = []
  const graph = new Map(entries.map((entry) => [normalizedPath(entry.file), { entry, edges: [], entries }]))
  for (const entry of entries) {
    const sourceInfo = classify(entry.relative)
    const graphNode = graph.get(normalizedPath(entry.file))
    if (sourceInfo.kind === 'other' && !config.allowedOtherPaths.includes(entry.relative)) {
      violations.push({
        file: entry.relative,
        line: 1,
        import: 'unclassified source file',
        target: entry.relative,
        message: 'every implementation file must belong to a declared layer or framework entry',
      })
    }
    parseEntry(entry, sourceInfo, violations, graphNode)
  }
  detectCycles(entries, graph, violations)
  return violations
}

export function virtualEntries(files) {
  return Object.entries(files).map(([relative, source]) => ({
    relative: slash(relative),
    file: path.join(root, relative),
    source,
  }))
}

function printViolations(violations) {
  for (const violation of violations)
    console.error(`${violation.file}:${violation.line} -> ${violation.import}: ${violation.message}`)
}

function assertCase(name, violations, predicate) {
  if (!violations.some(predicate)) {
    printViolations(violations)
    throw new Error(`frontend boundary self-test failed: ${name}`)
  }
  return violations.filter(predicate).length
}

export function runSelfTest() {
  const legal = virtualEntries({
    'src/pages/ok.vue': `<script setup lang="ts">
import {
  getApplicationServices,
} from '@/features/qa/public'
import type { Conversation } from '@/types/records'
await import('@/features/qa/public')
void getApplicationServices
void (null as Conversation | null)
</script>`,
    'src/pages/external-ok.vue': `<script lang="ts" src="../features/qa/public.ts"></script>`,
    'src/pages/composition.vue': `<script setup lang="ts">
import QaPanel from '@/features/qa/presentation/QaPanel.vue'
import { runUseCase } from '@/features/qa/public'
void QaPanel
void runUseCase
</script>`,
    'src/features/qa/presentation/QaPanel.vue': `<script setup lang="ts">
import { computed } from 'vue'
import { runUseCase } from '@/features/qa/public'
import MedState from '@/components/ui/MedState.vue'
void computed
void runUseCase
void MedState
</script>`,
    'src/components/ui/MedState.vue': '<template><view /></template>',
    'src/features/qa/public.ts': `export { runUseCase } from './application/useCase'
export type { QaPort } from './domain/ports'`,
    'src/features/qa/application/useCase.ts': `import type { QaPort } from '../domain/ports'
export const runUseCase = (port: QaPort) => port.run()`,
    'src/features/qa/domain/ports.ts': `import type { Conversation } from '@/types/records'
export interface QaPort { run(): Promise<Conversation[]> }`,
    'src/features/qa/infrastructure/adapter.ts': `import { z } from 'zod'
import { apiRequest } from '@/platform/http/apiClient'
export const adapter = { z, apiRequest }`,
    'src/features/content/infrastructure/pathologyCatalog.generated.json':
      '{ generated catalog content is intentionally not parsed',
    'src/features/content/infrastructure/catalogReader.ts': `import catalog from './pathologyCatalog.generated.json'
export const readCatalog = () => catalog`,
    'src/features/content/public.ts': `import catalog from './infrastructure/pathologyCatalog.generated.json'
export const contentCatalog = catalog`,
    'src/bootstrap/catalogReader.ts': `import catalog from '@/features/content/infrastructure/pathologyCatalog.generated.json'
export const readCatalog = () => catalog`,
    'src/types/records.ts': 'export interface Conversation { id: string }',
    'src/platform/http/apiClient.ts': 'export const apiRequest = () => undefined',
    'src/platform/http/browserIo.ts': `fetch('/api')
new XMLHttpRequest()`,
  })
  const positive = analyze(legal)
  if (positive.length) {
    printViolations(positive)
    throw new Error(`frontend boundary self-test failed: legal fixture produced ${positive.length} violation(s)`)
  }

  const cases = [
    {
      name: 'pages and components cannot import feature business layers',
      files: {
        'src/pages/bad-domain.vue': `<script setup lang="ts">
import type { QaPort } from '@/features/qa/domain/ports'
void (null as QaPort | null)
</script>`,
        'src/components/bad-infrastructure.vue': `<script setup lang="ts">
import { adapter } from '@/features/qa/infrastructure/adapter'
void adapter
</script>`,
        'src/features/qa/domain/ports.ts': 'export interface QaPort { run(): void }',
        'src/features/qa/infrastructure/adapter.ts': 'export const adapter = true',
      },
      predicate: (violation) =>
        violation.message.includes('pages/components may import only feature public APIs or presentation views'),
      count: 2,
    },
    {
      name: 'feature presentation cannot import business layers',
      files: {
        'src/features/qa/presentation/bad.vue': `<script setup lang="ts">
import { runUseCase } from '../application/useCase'
import type { QaPort } from '../domain/ports'
import { adapter } from '../infrastructure/adapter'
void runUseCase
void (null as QaPort | null)
void adapter
</script>`,
        'src/features/qa/application/useCase.ts': 'export const runUseCase = () => undefined',
        'src/features/qa/domain/ports.ts': 'export interface QaPort { run(): void }',
        'src/features/qa/infrastructure/adapter.ts': 'export const adapter = true',
      },
      predicate: (violation) =>
        violation.message.includes('feature presentation may depend only on public APIs or presentation views'),
      count: 3,
    },
    {
      name: 'cross-feature generated JSON import',
      files: {
        'src/features/learning/infrastructure/catalogReader.ts': `import catalog from '@/features/content/infrastructure/pathologyCatalog.generated.json'
export const readCatalog = () => catalog`,
        'src/features/content/infrastructure/pathologyCatalog.generated.json': '{ not parsed generated content',
      },
      predicate: (violation) =>
        violation.message.includes(
          'feature-owned generated artifacts may be read only by their public/infrastructure layer or bootstrap',
        ),
      count: 1,
    },
    {
      name: 'own generated JSON is unavailable to UI and core layers',
      files: {
        'src/features/content/infrastructure/pathologyCatalog.generated.json': '{ generated content is not parsed',
        'src/pages/own-generated.vue': `<script setup lang="ts">
import catalog from '@/features/content/infrastructure/pathologyCatalog.generated.json'
void catalog
</script>`,
        'src/features/content/presentation/OwnGenerated.vue': `<script setup lang="ts">
import catalog from '../infrastructure/pathologyCatalog.generated.json'
void catalog
</script>`,
        'src/features/content/domain/catalog.ts': `import catalog from '../infrastructure/pathologyCatalog.generated.json'
export const domainCatalog = catalog`,
        'src/features/content/application/catalog.ts': `import catalog from '../infrastructure/pathologyCatalog.generated.json'
export const applicationCatalog = catalog`,
      },
      predicate: (violation) =>
        violation.message.includes(
          'feature-owned generated artifacts may be read only by their public/infrastructure layer or bootstrap',
        ),
      count: 4,
    },
    {
      name: 'missing relative JSON resource',
      files: {
        'src/features/qa/infrastructure/missingResource.ts': `import resource from './missing.json'
export const read = () => resource`,
      },
      predicate: (violation) =>
        violation.message.includes('unresolved local import') && violation.import === './missing.json',
      count: 1,
    },
    {
      name: 'framework import in domain',
      files: {
        'src/features/qa/domain/rules.ts': `import { ref } from 'vue'
export const rules = ref([])`,
      },
      predicate: (violation) =>
        violation.message.includes('external framework dependency') && violation.import === 'vue',
      count: 1,
    },
    {
      name: 'framework import type in domain',
      files: {
        'src/features/qa/domain/types.ts': `export type Bad = import('vue').Ref<string>`,
      },
      predicate: (violation) =>
        violation.message.includes('external framework dependency') && violation.import === 'vue',
      count: 1,
    },
    {
      name: 'opaque dynamic import',
      files: {
        'src/pages/bad-dynamic.vue': `<script setup lang="ts">
const targetPath = '@/features/qa/public'
await import(targetPath)
</script>`,
      },
      predicate: (violation) =>
        violation.message.includes('dynamic imports') && violation.import === 'opaque dynamic import',
      count: 1,
    },
    {
      name: 'async and sync storage aliases',
      files: {
        'src/pages/bad-storage.vue': `<script setup lang="ts">
const {
  getStorage: read,
  setStorage: write,
  removeStorage: remove,
  clearStorage: clear,
  getStorageInfo: info,
  getStorageSync: readSync,
  setStorageSync: writeSync,
  removeStorageSync: removeSync,
  clearStorageSync: clearSync,
  getStorageInfoSync: infoSync,
} = uni
read({ key: 'user' })
write({ key: 'user', data: 'x' })
remove({ key: 'user' })
clear()
info()
readSync('user')
writeSync('user', 'x')
removeSync('user')
clearSync()
infoSync()
</script>`,
      },
      predicate: (violation) =>
        violation.message.includes('platform HTTP/Storage I/O') && violation.import.startsWith('uni.'),
      count: 10,
    },
    {
      name: 'computed platform request and destructured alias',
      files: {
        'src/pages/bad-io.vue': `<script setup lang="ts">
const { request: send } = uni
send({
  url: '/x',
})
uni[
  'request'
]({ url: '/x' })
</script>`,
      },
      predicate: (violation) => violation.message.includes('platform HTTP/Storage I/O'),
      count: 2,
    },
    {
      name: 'browser network I/O and aliases',
      files: {
        'src/shared/bad-network.ts': `const send = fetch
send('/api')
fetch('/api')
const { fetch: sendFromWindow } = window
sendFromWindow('/api')
new XMLHttpRequest()
window.fetch('/api')`,
      },
      predicate: (violation) => violation.message.includes('browser network I/O'),
      count: 5,
    },
    {
      name: 'domain importing presentation',
      files: {
        'src/features/qa/domain/rules.ts': `import type { Page } from '@/pages/shell.vue'
export type RulesPage = Page`,
        'src/pages/shell.vue': '<template><view /></template>',
      },
      predicate: (violation) =>
        violation.message.includes('domain may not depend') && violation.target === 'src/pages/shell.vue',
      count: 1,
    },
    {
      name: 'external SFC script dependency',
      files: {
        'src/pages/external-src.vue': `<script lang="ts" src="../features/qa/infrastructure/probe.ts"></script>`,
        'src/features/qa/infrastructure/probe.ts': 'export const probe = true',
      },
      predicate: (violation) =>
        violation.message.includes('pages/components may import only feature public APIs or presentation views') &&
        violation.target === 'src/features/qa/infrastructure/probe.ts',
      count: 1,
    },
    {
      name: 're-export cycle',
      files: {
        'src/shared/a.ts': `export { valueB } from './b'
export const valueA = 'a'`,
        'src/shared/b.ts': `export { valueA } from './a'
export const valueB = 'b'`,
      },
      predicate: (violation) => violation.message.includes('dependency cycle'),
      count: 2,
    },
    {
      name: 'import type dependency cycle',
      files: {
        'src/shared/type-a.ts': `export type A = import('./type-b').B`,
        'src/shared/type-b.ts': `export type B = import('./type-a').A`,
      },
      predicate: (violation) => violation.message.includes('dependency cycle'),
      count: 2,
    },
  ]
  let negativeCount = 0
  for (const testCase of cases) {
    const violations = analyze(virtualEntries(testCase.files))
    const matched = assertCase(testCase.name, violations, testCase.predicate)
    if (testCase.count !== undefined && matched !== testCase.count) {
      printViolations(violations)
      throw new Error(`frontend boundary self-test failed: ${testCase.name} expected ${testCase.count}, got ${matched}`)
    }
    negativeCount += matched
  }
  console.log(`frontend-boundaries self-test PASS (positive=0, targeted-negative=${negativeCount})`)
}

function runCli() {
  if (process.argv.includes('--self-test')) {
    runSelfTest()
    return
  }
  const files = listFiles(path.join(root, config.sourceRoot)).map((file) => ({
    file,
    relative: relativePath(file),
    source: fs.readFileSync(file, 'utf8'),
  }))
  const violations = analyze(files)
  if (violations.length) {
    printViolations(violations)
    process.exitCode = 1
  } else {
    const implementationCount = files.filter((entry) => isImplementationFile(entry.file)).length
    const resourceCount = files.length - implementationCount
    console.log(
      `frontend-boundaries PASS (${implementationCount} implementation files and ${resourceCount} JSON resources checked)`,
    )
  }
}

const invokedFile = process.argv[1] ? path.resolve(process.argv[1]) : ''
if (
  invokedFile &&
  path.normalize(invokedFile).toLowerCase() === path.normalize(fileURLToPath(import.meta.url)).toLowerCase()
)
  runCli()

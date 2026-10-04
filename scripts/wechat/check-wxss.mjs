import { existsSync, readdirSync } from 'node:fs'
import { dirname, join, relative, resolve } from 'node:path'
import { spawnSync } from 'node:child_process'

const args = process.argv.slice(2)
const option = (name) => args[args.indexOf(name) + 1]
const project = resolve(args.includes('--project') ? option('--project') : 'dist/dev/mp-weixin')
const compiler = args.includes('--compiler')
  ? resolve(option('--compiler'))
  : process.env.WECHATIDE_CLI_PATH
    ? join(dirname(process.env.WECHATIDE_CLI_PATH), 'resources/app.asar.unpacked/node_modules/wcc-exec/wcsc.exe')
    : undefined

function styles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name)
    return entry.isDirectory()
      ? styles(path)
      : entry.name.endsWith('.wxss')
        ? [relative(project, path).replaceAll('\\', '/')]
        : []
  })
}

try {
  if (!compiler || !existsSync(compiler))
    throw new Error('Set WECHATIDE_CLI_PATH or pass --compiler with the installed native wcsc compiler path.')
  if (!existsSync(join(project, 'app.wxss'))) throw new Error('Build the Mini Program first; app.wxss is missing.')
  const files = styles(project).sort()
  const result = spawnSync(compiler, ['-lc', ...files], {
    cwd: project,
    encoding: 'utf8',
    windowsHide: true,
    timeout: 30_000,
    maxBuffer: 20 * 1024 * 1024,
  })
  if (result.error) throw result.error
  if (result.status !== 0) {
    // Native wcsc reports the source path/line that the IDE's generic 10041 hides.
    console.error(result.stderr?.trim() || result.stdout?.slice(0, 4000) || 'Native WXSS compilation failed.')
    process.exitCode = result.status || 1
  } else {
    console.log(`PASS: native WXSS compilation (${files.length} files). Project: ${project}`)
    console.log('Syntax check only; continue with ordinary IDE compile, real interaction and screenshot inspection.')
  }
} catch (error) {
  console.error(error instanceof Error ? error.message : 'Native WXSS check failed.')
  process.exitCode = 1
}

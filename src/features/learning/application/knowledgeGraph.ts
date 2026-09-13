import type {
  KnowledgeGraph,
  KnowledgeGraphEdge,
  KnowledgeGraphIssue,
  KnowledgeGraphModule,
  KnowledgeGraphNode,
  KnowledgeMapPoint,
} from '@/types/knowledge'

const ROOT_ID = 'pathology'

function recommendationRank(point: KnowledgeMapPoint, pointsByCode: Map<string, KnowledgeMapPoint>): number {
  if (point.status === 'weak') return 0
  if (point.status === 'due') return 1
  if (point.status === 'learning') return 2
  if (point.status === 'not_started') {
    const prerequisites = point.prerequisiteCodes || []
    const ready = prerequisites.every((code) => pointsByCode.get(code)?.status === 'stable')
    return ready ? 3 : 4
  }
  return 5
}

export function buildKnowledgeGraph(input: KnowledgeMapPoint[]): KnowledgeGraph {
  const issues: KnowledgeGraphIssue[] = []
  const points: KnowledgeMapPoint[] = []
  const pointsByCode = new Map<string, KnowledgeMapPoint>()

  for (const point of input) {
    if (pointsByCode.has(point.code)) {
      issues.push({ type: 'duplicate_point', pointCode: point.code })
      continue
    }
    points.push(point)
    pointsByCode.set(point.code, point)
  }

  const modules: KnowledgeGraphModule[] = []
  const modulesByCode = new Map<string, KnowledgeGraphModule>()
  for (const point of points) {
    let module = modulesByCode.get(point.systemCode)
    if (!module) {
      module = {
        code: point.systemCode,
        title: point.systemLabel,
        order: modules.length,
        pointCodes: [],
        stableCount: 0,
        attentionCount: 0,
      }
      modules.push(module)
      modulesByCode.set(module.code, module)
    }
    module.pointCodes.push(point.code)
    if (point.status === 'stable') module.stableCount += 1
    if (point.status === 'weak' || point.status === 'due') module.attentionCount += 1
  }

  const validPrerequisites = new Map<string, string[]>()
  const dependents = new Map<string, string[]>()
  const indegree = new Map(points.map((point) => [point.code, 0]))

  for (const point of points) {
    const unique = [...new Set(point.prerequisiteCodes || [])]
    const valid: string[] = []
    for (const code of unique) {
      if (!pointsByCode.has(code)) {
        issues.push({ type: 'missing_prerequisite', pointCode: point.code, relatedCode: code })
        continue
      }
      valid.push(code)
      dependents.set(code, [...(dependents.get(code) || []), point.code])
    }
    validPrerequisites.set(point.code, valid)
    indegree.set(point.code, valid.length)
  }

  const orderByCode = new Map(points.map((point, index) => [point.code, index]))
  const queue = points.filter((point) => indegree.get(point.code) === 0).map((point) => point.code)
  const depths = new Map(points.map((point) => [point.code, 0]))
  const processed = new Set<string>()

  while (queue.length) {
    queue.sort((a, b) => (orderByCode.get(a) || 0) - (orderByCode.get(b) || 0))
    const code = queue.shift()!
    processed.add(code)
    for (const dependent of dependents.get(code) || []) {
      depths.set(dependent, Math.max(depths.get(dependent) || 0, (depths.get(code) || 0) + 1))
      const next = (indegree.get(dependent) || 0) - 1
      indegree.set(dependent, next)
      if (next === 0) queue.push(dependent)
    }
  }

  const maxDepth = Math.max(0, ...depths.values())
  for (const point of points) {
    if (processed.has(point.code)) continue
    depths.set(point.code, maxDepth + 1)
    issues.push({ type: 'cyclic_prerequisite', pointCode: point.code })
  }

  const nodes: KnowledgeGraphNode[] = [
    { id: ROOT_ID, kind: 'root', title: '病理学总论', order: 0, depth: -2 },
    ...modules.map((module) => ({
      id: module.code,
      kind: 'module' as const,
      title: module.title,
      order: module.order,
      depth: -1,
      moduleCode: module.code,
    })),
    ...points.map((point, order) => ({
      id: point.code,
      kind: 'point' as const,
      title: point.title,
      order,
      depth: depths.get(point.code) || 0,
      moduleCode: point.systemCode,
      point,
    })),
  ]

  const edges: KnowledgeGraphEdge[] = modules.map((module) => ({
    id: `${ROOT_ID}->${module.code}`,
    from: ROOT_ID,
    to: module.code,
    kind: 'contains',
    crossModule: false,
  }))

  for (const point of points) {
    const prerequisites = validPrerequisites.get(point.code) || []
    const hasSameModulePrerequisite = prerequisites.some(
      (code) => pointsByCode.get(code)?.systemCode === point.systemCode,
    )
    if (!hasSameModulePrerequisite) {
      edges.push({
        id: `${point.systemCode}->${point.code}`,
        from: point.systemCode,
        to: point.code,
        kind: 'contains',
        crossModule: false,
      })
    }
    for (const prerequisite of prerequisites) {
      edges.push({
        id: `${prerequisite}->${point.code}`,
        from: prerequisite,
        to: point.code,
        kind: 'prerequisite',
        crossModule: pointsByCode.get(prerequisite)?.systemCode !== point.systemCode,
      })
    }
  }

  const recommended = [...points]
    .map((point, order) => ({ point, order, rank: recommendationRank(point, pointsByCode) }))
    .sort((a, b) => a.rank - b.rank || a.order - b.order)[0]?.point

  return {
    rootId: ROOT_ID,
    nodes,
    edges,
    modules,
    issues,
    recommendedPointCode: recommended?.code,
    recommendedModuleCode: recommended?.systemCode,
  }
}

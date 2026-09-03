import type { CaseAssessment, CaseAttempt, CaseDraftGenerateResult } from '@/types/case'

const normalizeAnswerText = (value: string) => value.toLocaleLowerCase().replace(/\s+/g, '')

function answerTexts(attempt: CaseAttempt, stageIds: string[]): string[] {
  const values: string[] = []
  for (const message of attempt.messages) {
    if (message.role === 'user') values.push(message.content)
  }
  for (const submission of attempt.submissions) {
    if (!stageIds.includes(submission.stageId)) continue
    const collect = (value: unknown) => {
      if (typeof value === 'string' && value.trim()) values.push(value)
      else if (Array.isArray(value)) value.forEach(collect)
      else if (value && typeof value === 'object') Object.values(value).forEach(collect)
    }
    collect(submission.answer)
  }
  return values
}

function evidenceForKeyword(texts: string[], keyword: string): string | undefined {
  const normalizedKeyword = normalizeAnswerText(keyword)
  const candidates = texts.flatMap((text) =>
    text
      .split(/[。！？；\n]/u)
      .map((part) => part.trim())
      .filter((part) => normalizeAnswerText(part).includes(normalizedKeyword)),
  )
  return candidates.sort((left, right) => left.length - right.length)[0]?.slice(0, 160)
}

export function scoreDemoCase(attempt: CaseAttempt, draft: CaseDraftGenerateResult): CaseAssessment['dimensions'] {
  return draft.rubric.dimensions.map((dimension) => {
    const texts = answerTexts(attempt, dimension.stageIds)
    const normalized = texts.map(normalizeAnswerText).join('|')
    const hit = dimension.criteria.filter((criterion) =>
      criterion.keywords.some((keyword) => normalized.includes(normalizeAnswerText(keyword))),
    )
    const missing = dimension.criteria.filter((criterion) => !hit.includes(criterion))
    let score = Math.round((hit.length / dimension.criteria.length) * 1000) / 10
    if (missing.some((criterion) => criterion.critical)) score = Math.min(score, 69)
    const evidence = hit
      .flatMap((criterion) => criterion.keywords.map((keyword) => evidenceForKeyword(texts, keyword)))
      .filter((value, index, all): value is string => Boolean(value) && all.indexOf(value) === index)
      .slice(0, 3)
    return {
      dimensionId: dimension.id,
      label: dimension.label,
      score,
      weightedScore: Math.round((score * dimension.weight) / 1000) / 10,
      evidence: evidence.length ? evidence : ['尚未发现对应的学生原文证据'],
      feedback: missing.length ? missing[0].feedback : '已覆盖该维度的关键评价点。',
      nextStep: missing.length ? missing[0].feedback : '继续保持并补充更明确的原文依据。',
    }
  })
}

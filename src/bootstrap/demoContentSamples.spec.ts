import { afterEach, describe, expect, it, vi } from 'vitest'
import type { SessionUser } from '@/types/records'
import type { Problem } from '@/types/records'
import type { CaseDraftGenerateResult } from '@/types/case'
import pathologyCatalog from '@/features/content/infrastructure/pathologyCatalog.generated.json'
import { storageKeys } from '@/platform/storage/storage'

const demoTeacher: SessionUser = {
  openid: 'demo_teacher',
  role: 'teacher',
  nickName: '演示教师',
  avatarUrl: '',
  createdAt: new Date(0).toISOString(),
}

const caseSampleIds = [
  'pathology.cell-injury-showcase',
  'pathology.inflammation-showcase',
  'pathology.circulatory-showcase',
  'pathology.repair-showcase',
  'pathology.neoplasm-showcase',
]
const earlyCaseTitles: Record<string, string> = {
  'pathology.cell-injury-showcase': '细胞损伤与适应',
  'pathology.inflammation-showcase': '炎症',
  'pathology.circulatory-showcase': '循环障碍',
  'pathology.repair-showcase': '修复',
  'pathology.neoplasm-showcase': '肿瘤',
}
const earlyCaseDescription = 'Demo 合成教学病例，用于教师病例库查看与编辑。'

type StoredCaseFixture = {
  deletedAt?: string
  problem: Problem
  draft: CaseDraftGenerateResult
  authorOpenid: string
  reviews: unknown[]
}

afterEach(() => {
  vi.unstubAllEnvs()
  vi.resetModules()
})

describe('Demo teacher content samples', () => {
  it('initializes complete owned cases and single-choice bank items once and preserves later edits and deletions', async () => {
    vi.resetModules()
    vi.stubEnv('VITE_APP_MODE', 'demo')
    const { getApplicationServices } = await import('./wiring')
    const services = getApplicationServices()
    expect(services.session.getSession()).toBeNull()
    services.ensureDemoData()
    await services.session.saveSession(demoTeacher)

    const initialCases = (await services.content.getGuidedCasesAsync()).filter((item) =>
      caseSampleIds.includes(item.id),
    )
    expect(initialCases.map((item) => item.id).sort()).toEqual([...caseSampleIds].sort())
    expect(
      [...initialCases].sort((left, right) => right.time.localeCompare(left.time)).map((item) => item.title),
    ).toEqual(['细胞损伤与适应', '炎症的病理变化', '血液循环障碍', '组织修复', '肿瘤的形态特征'])
    expect(initialCases.every((item) => item.contentType === 'guided_case')).toBe(true)
    expect(
      initialCases.every((item) => item.allowedActions?.includes('edit') && item.allowedActions.includes('delete')),
    ).toBe(true)
    expect(initialCases.map((item) => item.knowledgePointCodes?.length)).toEqual([3, 3, 3, 3, 3])
    for (const item of initialCases) {
      const draft = await services.content.getCaseAuthoringAsync(item.id)
      expect(draft?.caseDefinition.facts.length).toBeGreaterThan(0)
      expect(draft?.rubric.dimensions.length).toBeGreaterThan(0)
      expect(draft?.description).toContain('Demo 合成：')
    }

    const initialBank = await services.content.listTeacherQuestionBank({ limit: 20 })
    expect(initialBank.total).toBe(3)
    expect(initialBank.items.map((item) => item.id).sort((left, right) => left - right)).toEqual([
      640001, 640002, 640003,
    ])
    expect(initialBank.items.every((item) => item.status === 'active')).toBe(true)
    expect(
      initialBank.items.every(
        (item) =>
          item.options.length === 4 &&
          Number.isInteger(item.answer.correct_option) &&
          Number(item.answer.correct_option) >= 0 &&
          Number(item.answer.correct_option) < item.options.length &&
          item.explanation.length > 0 &&
          item.pointCodes.length === 1 &&
          item.title.startsWith('Demo 样例：') &&
          !('sourceType' in item) &&
          !('sourceId' in item),
      ),
    ).toBe(true)
    expect(initialBank.items.flatMap((item) => item.pointCodes).sort()).toEqual([
      'pathology.cell-injury.reversible',
      'pathology.circulatory.congestion',
      'pathology.inflammation.vascular',
    ])

    const editedCase = initialCases[0]
    const caseDraft = await services.content.getCaseAuthoringAsync(editedCase.id)
    expect(caseDraft).toBeDefined()
    await services.content.saveGuidedCaseAsync({ ...caseDraft!, title: '已编辑的 Demo 病例' }, editedCase.id)
    await services.content.deleteGuidedCaseAsync(initialCases[1].id)

    const editedBank = initialBank.items.find((item) => item.id === 640001)!
    const bankUpdate = await services.content.updateTeacherQuestionBankItem(editedBank.id, editedBank.version, {
      taskType: editedBank.taskType,
      title: '已编辑的 Demo 单选题',
      prompt: editedBank.prompt,
      options: editedBank.options,
      answer: editedBank.answer,
      explanation: editedBank.explanation,
      pointCodes: editedBank.pointCodes,
      dimensionIds: editedBank.dimensionIds,
    })
    const deletedBank = initialBank.items.find((item) => item.id === 640003)!
    await services.content.deleteTeacherQuestionBankItem(deletedBank.id, deletedBank.version, 'demo-sample-delete')

    services.ensureDemoData()
    const repeatedCases = await services.content.getGuidedCasesAsync()
    const repeatedBank = await services.content.listTeacherQuestionBank({ limit: 20 })
    expect(repeatedCases.find((item) => item.id === editedCase.id)?.title).toBe('已编辑的 Demo 病例')
    expect(repeatedCases.some((item) => item.id === initialCases[1].id)).toBe(false)
    expect(repeatedCases.filter((item) => caseSampleIds.includes(item.id))).toHaveLength(4)
    expect(repeatedBank.items.find((item) => item.id === editedBank.id)).toMatchObject({
      title: '已编辑的 Demo 单选题',
      version: bankUpdate.version,
    })
    expect(repeatedBank.items.some((item) => item.id === deletedBank.id)).toBe(false)
    expect(repeatedBank.total).toBe(2)

    await services.session.saveSession({ ...demoTeacher, openid: 'demo_other_teacher' })
    const otherTeacherCases = await services.content.getGuidedCasesAsync()
    expect(otherTeacherCases.find((item) => item.id === editedCase.id)?.allowedActions).toEqual([])
    expect(await services.content.getCaseAuthoringAsync(editedCase.id)).toBeUndefined()
    await expect(
      services.content.saveGuidedCaseAsync({ ...caseDraft!, title: '未经授权的修改' }, editedCase.id),
    ).rejects.toMatchObject({ code: 'FORBIDDEN', statusCode: 403 })
    await expect(services.content.deleteGuidedCaseAsync(editedCase.id)).rejects.toMatchObject({
      code: 'FORBIDDEN',
      statusCode: 403,
    })
    expect(await services.content.listTeacherQuestionBank()).toMatchObject({ items: [], total: 0 })
    await expect(
      services.content.updateTeacherQuestionBankItem(editedBank.id, bankUpdate.version, bankUpdate),
    ).rejects.toMatchObject({ code: 'RESOURCE_NOT_FOUND', statusCode: 404 })

    vi.resetModules()
    vi.stubEnv('VITE_APP_MODE', 'demo')
    const { getApplicationServices: getReloadedServices } = await import('./wiring')
    const reloaded = getReloadedServices()
    await reloaded.session.saveSession(demoTeacher)
    reloaded.ensureDemoData()
    const reloadedCases = await reloaded.content.getGuidedCasesAsync()
    const reloadedBank = await reloaded.content.listTeacherQuestionBank({ limit: 20 })
    expect(reloadedCases.find((item) => item.id === editedCase.id)?.title).toBe('已编辑的 Demo 病例')
    expect(reloadedCases.some((item) => item.id === initialCases[1].id)).toBe(false)
    expect(reloadedBank.items.find((item) => item.id === editedBank.id)).toMatchObject({
      title: '已编辑的 Demo 单选题',
      version: bankUpdate.version,
    })
    expect(reloadedBank.items.some((item) => item.id === deletedBank.id)).toBe(false)
  })

  it('does not initialize or persist Demo samples in API mode', async () => {
    vi.resetModules()
    vi.stubEnv('VITE_APP_MODE', 'api')
    const [{ getApplicationServices }, { storage, storageKeys }] = await Promise.all([
      import('./wiring'),
      import('@/platform/storage/storage'),
    ])
    const services = getApplicationServices()

    expect(services.mode).toBe('api')
    services.ensureDemoData()

    expect(storage.readRaw(storageKeys.guidedDrafts)).toBeUndefined()
    expect(storage.readRaw('content:t64-question-bank')).toBeUndefined()
    expect(uni.request).not.toHaveBeenCalled()
    expect(uni.setStorageSync).not.toHaveBeenCalled()
  })

  it('upgrades only exact early Demo fixtures and preserves edited or deleted samples', async () => {
    vi.resetModules()
    vi.stubEnv('VITE_APP_MODE', 'demo')
    const { getApplicationServices } = await import('./wiring')
    const initial = getApplicationServices()
    expect(initial.session.getSession()).toBeNull()
    initial.ensureDemoData()
    await initial.session.saveSession(demoTeacher)

    const earlyCases = uni.getStorageSync(storageKeys.guidedDrafts) as StoredCaseFixture[]
    uni.setStorageSync(
      storageKeys.guidedDrafts,
      earlyCases.map((record) => {
        const id = record.problem.id
        const legacyTitle = earlyCaseTitles[id]
        if (!legacyTitle) return record
        const allCodes = pathologyCatalog.filter((point) => point.case_slug === id).map((point) => point.code)
        const edited = id === 'pathology.inflammation-showcase'
        const deleted = id === 'pathology.repair-showcase'
        const title = edited ? '教师已编辑的炎症病例' : legacyTitle
        return {
          ...record,
          deletedAt: deleted ? '2026-10-03T09:00:00.000Z' : record.deletedAt,
          problem: {
            ...record.problem,
            title,
            description: earlyCaseDescription,
            knowledgePointCodes: allCodes,
          },
          draft: { ...record.draft, title, description: earlyCaseDescription },
        }
      }),
    )

    type StoredBankSnapshot = {
      items: Array<{
        id: number
        version: number
        status: 'active' | 'archived'
        title: string
        pointCodes: string[]
        updatedAt: string
        [key: string]: unknown
      }>
      [key: string]: unknown
    }
    const earlyBank = uni.getStorageSync('content:t64-question-bank') as StoredBankSnapshot
    const oldBankTimestamp = '2026-10-02T08:30:00.000Z'
    uni.setStorageSync('content:t64-question-bank', {
      ...earlyBank,
      items: earlyBank.items.map((item) => {
        if (item.id === 640001)
          return {
            ...item,
            pointCodes: ['pathology.cell-injury.adaptation'],
            updatedAt: oldBankTimestamp,
          }
        if (item.id === 640002)
          return {
            ...item,
            title: '教师已编辑的 Demo 炎症题',
            pointCodes: ['pathology.cell-injury.adaptation'],
          }
        return item
      }),
    })

    initial.session.clearSession()
    vi.resetModules()
    vi.stubEnv('VITE_APP_MODE', 'demo')
    const { getApplicationServices: getReloadedServices } = await import('./wiring')
    const reloaded = getReloadedServices()
    expect(reloaded.session.getSession()).toBeNull()
    reloaded.ensureDemoData()
    await reloaded.session.saveSession(demoTeacher)

    const migratedCases = uni.getStorageSync(storageKeys.guidedDrafts) as StoredCaseFixture[]
    const migratedById = new Map(migratedCases.map((record) => [record.problem.id, record]))
    for (const id of [caseSampleIds[0], caseSampleIds[2], caseSampleIds[4]]) {
      const record = migratedById.get(id)!
      expect(record.problem.title).toBe(
        id === caseSampleIds[0] ? '细胞损伤与适应' : id === caseSampleIds[2] ? '血液循环障碍' : '肿瘤的形态特征',
      )
      expect(record.problem.description).toContain('Demo 合成：')
      expect(record.problem.knowledgePointCodes).toHaveLength(3)
      expect(record.draft.title).toBe(record.problem.title)
      expect(record.draft.description).toBe(record.problem.description)
    }
    expect(migratedById.get(caseSampleIds[1])?.problem.title).toBe('教师已编辑的炎症病例')
    expect(migratedById.get(caseSampleIds[1])?.problem.description).toBe(earlyCaseDescription)
    expect(migratedById.get(caseSampleIds[1])?.problem.knowledgePointCodes).toEqual(
      pathologyCatalog.filter((point) => point.case_slug === caseSampleIds[1]).map((point) => point.code),
    )
    expect(migratedById.get(caseSampleIds[3])).toMatchObject({
      deletedAt: '2026-10-03T09:00:00.000Z',
      problem: { title: '修复', description: earlyCaseDescription },
    })

    const migratedBank = uni.getStorageSync('content:t64-question-bank') as StoredBankSnapshot
    expect(migratedBank.items.find((item) => item.id === 640001)).toMatchObject({
      version: 1,
      status: 'active',
      pointCodes: ['pathology.cell-injury.reversible'],
      updatedAt: oldBankTimestamp,
    })
    expect(migratedBank.items.find((item) => item.id === 640002)).toMatchObject({
      title: '教师已编辑的 Demo 炎症题',
      pointCodes: ['pathology.cell-injury.adaptation'],
    })
  })
})

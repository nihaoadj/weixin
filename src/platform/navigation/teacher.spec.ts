import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ROUTES } from '@/platform/navigation'
import {
  backFromTeacherDetail,
  parseTeacherWorkspaceTarget,
  relaunchToTeacherWorkspace,
  redirectLegacyTeacherInsightsDetail,
  switchTeacherWorkspace,
  teacherContentReturnParams,
} from './teacher'

describe('teacher workspace navigation', () => {
  it.each(['questions', 'knowledge-cards'])(
    'normalizes retired %s resource links without stale filters',
    (resource) => {
      expect(parseTeacherWorkspaceTarget({ tab: 'content', resource, keyword: '旧题', status: 'disabled' })).toEqual({
        workspace: 'content',
        resource: 'cases',
      })
    },
  )
  it('routes legacy PBL test queue targets to the independent queue and preserves filters', () => {
    relaunchToTeacherWorkspace({
      workspace: 'pbl',
      section: 'diagnostics',
      classId: 3,
      sessionId: 9,
      reviewKind: 'needs_changes',
    })
    expect(uni.reLaunch).toHaveBeenCalledWith(
      expect.objectContaining({
        url: `${ROUTES.teacherTestQueue}?section=diagnostics&reviewKind=needs_changes&classId=3&sessionId=9`,
      }),
    )
    vi.clearAllMocks()
    backFromTeacherDetail({ workspace: 'pbl', section: 'diagnostics', classId: 3, reviewKind: 'generation_failed' })
    expect(uni.reLaunch).toHaveBeenCalledWith(
      expect.objectContaining({
        url: `${ROUTES.teacherTestQueue}?section=diagnostics&reviewKind=generation_failed&classId=3`,
      }),
    )
  })
  it('preserves supported resource return filters while constraining the owner', () => {
    expect(
      teacherContentReturnParams(
        { resource: 'cases', keyword: ' 炎症 ', status: 'pending', returnUrl: '/foreign' },
        'cases',
      ),
    ).toEqual({ resource: 'cases', keyword: '炎症' })
    expect(teacherContentReturnParams({ status: 'arbitrary' }, 'cases')).toEqual({ resource: 'cases' })
  })
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getCurrentPages).mockReturnValue([])
    vi.mocked(uni.reLaunch).mockImplementation((options) => {
      options?.complete?.({ errMsg: 'reLaunch:ok' })
    })
    vi.mocked(uni.navigateBack).mockImplementation((options) => {
      options?.complete?.({ errMsg: 'navigateBack:ok' })
    })
    vi.mocked(uni.redirectTo).mockImplementation((options) => {
      options?.complete?.({ errMsg: 'redirectTo:ok' })
    })
  })

  it('replaces old student details with validated Insights context and strips arbitrary return targets', () => {
    redirectLegacyTeacherInsightsDetail('student', {
      studentId: '12',
      classId: '7',
      panel: 'knowledge',
      dateFrom: '2026-09-01',
      dateTo: '2026-09-30',
      returnUrl: '/foreign',
      returnTab: 'pbl',
    })
    const url = vi.mocked(uni.redirectTo).mock.calls[0][0].url
    expect(url).toContain(`${ROUTES.teacherInsightsStudentDetail}?`)
    expect(url).toContain('studentId=12')
    expect(url).toContain('classId=7')
    expect(url).toContain('dateFrom=2026-09-01')
    expect(url).not.toContain('returnUrl')
    expect(url).not.toContain('returnTab')
    expect(uni.reLaunch).not.toHaveBeenCalled()
  })

  it('replaces old result details and routes invalid identifiers to the readonly root', () => {
    redirectLegacyTeacherInsightsDetail('result', { resultId: '46e8274d-f99c-41d2-9681-680a0106874a', classId: '7' })
    expect(vi.mocked(uni.redirectTo).mock.calls[0][0].url).toContain(`${ROUTES.teacherInsightsResult}?`)
    vi.clearAllMocks()
    redirectLegacyTeacherInsightsDetail('result', { resultId: 'foreign/path', classId: '7' })
    redirectLegacyTeacherInsightsDetail('student', { studentId: '-1', classId: '7' })
    expect(uni.redirectTo).not.toHaveBeenCalled()
    expect(uni.reLaunch).toHaveBeenCalled()
    expect(vi.mocked(uni.reLaunch).mock.calls[0][0].url).toContain(ROUTES.teacherInsights)
  })

  it('moves legacy reports and problems links to their owning workspaces', () => {
    expect(
      parseTeacherWorkspaceTarget({ tab: 'reports', section: 'analytics', panel: 'mastery', classId: '12' }),
    ).toEqual({ workspace: 'insights', panel: 'knowledge', classId: 12 })
    expect(parseTeacherWorkspaceTarget({ tab: 'problems' })).toEqual({ workspace: 'content', resource: 'cases' })
    expect(parseTeacherWorkspaceTarget({ tab: 'problems', section: 'question-bank' })).toEqual({
      workspace: 'content',
      resource: 'question-bank',
    })
  })

  it('moves work-item and result aliases to PBL review and read-only insights', () => {
    expect(
      parseTeacherWorkspaceTarget({ tab: 'pbl', section: 'diagnostics', reviewKind: 'generation_failed' }),
    ).toEqual({ workspace: 'pbl', section: 'diagnostics', reviewKind: 'generation_failed' })
    expect(parseTeacherWorkspaceTarget({ tab: 'pbl', reviewKind: 'released' })).toEqual({
      workspace: 'pbl',
      section: 'classrooms',
    })
    expect(parseTeacherWorkspaceTarget({ tab: 'work-items', classId: '7', sessionId: 'demo-pbl-1' })).toEqual({
      workspace: 'pbl',
      section: 'diagnostics',
      classId: 7,
      sessionId: 'demo-pbl-1',
    })
    expect(
      parseTeacherWorkspaceTarget({ tab: 'problems', section: 'pbl-diagnostics', workStatus: 'responded' }),
    ).toEqual({
      workspace: 'pbl',
      section: 'diagnostics',
      workStatus: 'responded',
    })
    expect(parseTeacherWorkspaceTarget({ tab: 'pbl', section: 'results', classId: '8', sessionId: 'demo-14' })).toEqual(
      {
        workspace: 'insights',
        panel: 'progress',
        classId: 8,
        sessionId: 'demo-14',
      },
    )
  })

  it('drops invalid numeric identifiers and unapproved query values', () => {
    expect(
      parseTeacherWorkspaceTarget({
        tab: 'pbl',
        section: 'work-items',
        classId: '9007199254740992',
        sessionId: 'demo-pbl-0',
        snapshotId: '1.5',
        workStatus: 'all',
        returnUrl: '/pages/anything/else',
      }),
    ).toEqual({ workspace: 'pbl', section: 'diagnostics' })

    expect(parseTeacherWorkspaceTarget({ tab: 'reports', dateFrom: '2026-10-02', dateTo: '2026-10-01' })).toEqual({
      workspace: 'insights',
    })
  })

  it('uses root relaunch for main navigation and retains only typed context', () => {
    switchTeacherWorkspace('pbl')
    expect(uni.reLaunch).toHaveBeenCalledWith(expect.objectContaining({ url: ROUTES.teacherPbl }))
    expect(uni.navigateTo).not.toHaveBeenCalled()

    relaunchToTeacherWorkspace({
      workspace: 'content',
      resource: 'question-bank',
      keyword: ' 肺炎 ',
      status: 'archived',
      classId: -2,
    })
    expect(uni.reLaunch).toHaveBeenLastCalledWith(
      expect.objectContaining({
        url: `${ROUTES.teacherContent}?resource=question-bank&keyword=%E8%82%BA%E7%82%8E`,
      }),
    )
    expect(uni.navigateTo).not.toHaveBeenCalled()
  })

  it('falls back to the detail owner root with its valid context when no history exists', () => {
    backFromTeacherDetail({ workspace: 'insights', panel: 'students', classId: 17, sessionId: 3 }, 2)
    expect(uni.navigateBack).not.toHaveBeenCalled()
    expect(uni.reLaunch).toHaveBeenCalledWith(
      expect.objectContaining({ url: `${ROUTES.teacherInsights}?panel=students&classId=17&sessionId=3` }),
    )
  })

  it('returns through the current detail stack before using its fallback', () => {
    vi.mocked(getCurrentPages).mockReturnValue([{}, {}] as never)
    backFromTeacherDetail({ workspace: 'pbl', section: 'diagnostics', classId: 7, snapshotId: 41 })

    expect(uni.navigateBack).toHaveBeenCalledWith(expect.objectContaining({ delta: 1 }))
    expect(uni.reLaunch).not.toHaveBeenCalled()
  })

  it('relaunches to the typed owner root if native back fails', () => {
    vi.mocked(getCurrentPages).mockReturnValue([{}, {}] as never)
    vi.mocked(uni.navigateBack).mockImplementation((options) => {
      options?.fail?.({ errMsg: 'navigateBack:fail' })
    })

    backFromTeacherDetail({ workspace: 'pbl', section: 'classrooms', classId: 4, sessionId: 'demo-pbl-2' })

    expect(uni.reLaunch).toHaveBeenCalledWith(
      expect.objectContaining({ url: `${ROUTES.teacherPbl}?section=classrooms&classId=4&sessionId=demo-pbl-2` }),
    )
  })
})

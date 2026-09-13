import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiLearningRepository as learning } from '@/features/learning/infrastructure/apiLearningRepository'
import { apiClassroomRepository } from '@/features/classroom/infrastructure/apiClassroomRepository'
import { apiAnalyticsRepository } from '@/features/analytics/infrastructure/apiAnalyticsRepository'
import {
  configureDemoTeacherFeedback,
  demoLearningRepository as demoLearning,
} from '@/features/learning/infrastructure/demoLearningRepository'
import { demoClassroomRepository } from '@/features/classroom/infrastructure/demoClassroomRepository'
import { demoAnalyticsRepository } from '@/features/analytics/infrastructure/demoAnalyticsRepository'
import { clearApiCache } from '@/platform/http/apiClient'
import { mockHttp, now, respond } from '@/test/http'
import { saveSession } from '@/features/identity/public'

const teacher = { ...apiClassroomRepository, ...apiAnalyticsRepository }
const demoTeacher = { ...demoClassroomRepository, ...demoAnalyticsRepository }

const task = {
  id: 1,
  position: 0,
  task_type: 'micro_drill',
  dimension_id: 'test_selection',
  status: 'pending',
  public_definition: { answer_schema: 'short_text', instruction: '练习', display_hints: ['提示'] },
}
const plan = {
  id: 1,
  status: 'active',
  source_assessment_id: 1,
  source_type: 'case_assessment',
  source_id: 1,
  target_dimension_ids: ['test_selection'],
  due_at: now,
  generation_mode: 'fallback',
  model_name: 'fallback',
  prompt_version: 'v1',
  fallback_used: true,
  created_at: now,
  tasks: [task],
}
const attempt = { id: 1, task_id: 1, status: 'in_progress', created_at: now, public_definition: task.public_definition }
const dimension = { dimension_id: 'test_selection', label: '检查', average_score: 80 }
const progress = {
  eligible_pairs: 1,
  started_pairs: 1,
  completed_pairs: 1,
  completion_rate: 1,
  current_average_score: 80,
  average_improvement: 5,
  dimensions: [dimension],
}
const classDto = { id: 1, name: '一班', code: 'class_1', status: 'active', teacher_id: 2, created_at: now }

beforeEach(() => {
  vi.stubEnv('VITE_APP_MODE', 'api')
  vi.stubEnv('VITE_API_BASE_URL', 'https://example.test')
  clearApiCache()
})
afterEach(() => {
  vi.unstubAllEnvs()
  clearApiCache()
})

describe('learning adapter boundaries', () => {
  it('maps plan, task, attempt, notification and profile fields explicitly', async () => {
    mockHttp((path) =>
      path === '/learning/profile'
        ? {
            formal_dimensions: [],
            recent_assessments: [],
            practice_mastery: { test_selection: { average_score: 80, attempt_count: 2 } },
            active_plan: plan,
            unread_count: 1,
          }
        : path.endsWith('/start')
          ? { mode: 'micro_drill', task, attempt }
          : path.startsWith('/learning-task-attempts')
            ? {
                ...attempt,
                status: path.endsWith('/submit') ? 'assessed' : 'in_progress',
                score: 80,
                next_step: '复习',
              }
            : path === '/notifications'
              ? {
                  items: [
                    {
                      id: 1,
                      type: 'learning_plan_ready',
                      entity_type: 'learning_plan',
                      entity_id: 1,
                      title: '新计划',
                      body: '学习',
                      created_at: now,
                    },
                  ],
                  unread_count: 1,
                }
              : path === '/notifications/read-all'
                ? { marked: 1 }
                : plan,
    )
    expect((await learning.getLearningProfile()).practiceMastery.test_selection).toEqual({
      averageScore: 80,
      attemptCount: 2,
    })
    expect((await learning.createLearningPlan('1')).targetDimensionIds).toEqual(['test_selection'])
    expect((await learning.getCurrentLearningPlan())?.tasks[0].publicDefinition.answerSchema).toBe('short_text')
    expect((await learning.getLearningPlan(1)).sourceAssessmentId).toBe(1)
    expect((await learning.startLearningTask(1)).mode).toBe('micro_drill')
    expect((await learning.getLearningTaskAttempt(1)).nextStep).toBe('复习')
    expect((await learning.submitLearningTaskAttempt(1, { text: '回答' })).status).toBe('assessed')
    expect((await learning.completeLearningPlan(1)).id).toBe(1)
    expect((await learning.getLearningNotifications()).items[0].entityId).toBe(1)
    await learning.markLearningNotificationsRead()
    expect(uni.setStorageSync).not.toHaveBeenCalled()
  })
  it('accepts a PBL-session teacher-feedback notification without treating it as a learning plan', async () => {
    mockHttp((path) =>
      path === '/notifications'
        ? {
            items: [
              {
                id: 22,
                type: 'pbl_teacher_feedback',
                entity_type: 'pbl_session',
                entity_id: 8,
                title: '教师已回应',
                body: '请补充证据。',
                created_at: now,
              },
            ],
            unread_count: 1,
          }
        : plan,
    )
    await expect(learning.getLearningNotifications()).resolves.toMatchObject({
      items: [{ entityType: 'pbl_session', entityId: 8, type: 'pbl_teacher_feedback' }],
    })
  })
  it('distinguishes missing current plans, denied access and invalid nested data', async () => {
    vi.mocked(uni.request).mockImplementation((options) => {
      respond(options, { detail: 'missing' }, 404)
      return undefined as never
    })
    await expect(learning.getCurrentLearningPlan()).resolves.toBeUndefined()
    vi.mocked(uni.request).mockImplementation((options) => {
      respond(options, { detail: 'denied' }, 403)
      return undefined as never
    })
    await expect(learning.getCurrentLearningPlan()).rejects.toMatchObject({ code: 'FORBIDDEN' })
    mockHttp(() => ({ ...plan, tasks: [{ ...task, status: '未知状态' }] }))
    await expect(learning.getLearningPlan(1)).rejects.toMatchObject({ code: 'CONTRACT_ERROR' })
  })
})

describe('teacher adapter boundaries', () => {
  it('maps class mutations and all analytics without per-record requests', async () => {
    mockHttp((path, options) =>
      path === '/classes'
        ? options.method === 'GET'
          ? [classDto]
          : classDto
        : path.endsWith('/students')
          ? [{ id: 1, nickname: '学生', external_id: 'student', joined_at: now }]
          : path.startsWith('/classes/')
            ? classDto
            : path === '/analytics/overview'
              ? {
                  ...progress,
                  scope: { class_id: 1, class_name: '一班', date_from: now, date_to: now },
                  student_count: 1,
                  published_case_count: 1,
                  weak_dimensions: [dimension],
                  cases: [{ problem_id: 1, title: '病例', completed: 1, assigned: 1, average_score: 80 }],
                  students: [{ student_id: 1, nickname: '学生', completed: 1, assigned: 1, average_score: 80 }],
                }
              : path.includes('/analytics/cases')
                ? {
                    ...progress,
                    problem: { id: 1, title: '病例', version: 1 },
                    average_duration_minutes: 5,
                    distribution: { high: 1 },
                    students: [
                      {
                        student_id: 1,
                        nickname: '学生',
                        status: 'assessed',
                        baseline: 75,
                        current: 80,
                        delta: 5,
                        focus_stage: 'tests',
                        last_assessed_at: now,
                      },
                    ],
                  }
                : {
                    ...progress,
                    student: { id: 1, nickname: '学生' },
                    assigned: 1,
                    started: 1,
                    completed: 1,
                    cases: [
                      {
                        problem_id: 1,
                        title: '病例',
                        version: 1,
                        first_score: 75,
                        latest_score: 80,
                        delta: 5,
                        attempt_count: 2,
                        focus_stage: 'tests',
                        last_assessed_at: now,
                      },
                    ],
                    timeline: [{ attempt_id: 1, problem_id: 1, score: 80, assessed_at: now }],
                    learning_plan: { id: 1, status: 'active', target_dimension_ids: ['test_selection'], due_at: now },
                    practice_mastery: { test_selection: { average_score: 80, attempt_count: 1 } },
                  },
    )
    expect((await teacher.getTeacherClasses())[0].teacherId).toBe(2)
    await teacher.createTeacherClass('一班', 'class_1')
    await teacher.updateTeacherClass(1, { status: 'archived' })
    expect((await teacher.getClassStudents(1))[0].externalId).toBe('student')
    await teacher.addStudentToClass(1, 'student')
    await teacher.removeStudentFromClass(1, 1)
    expect((await teacher.getAnalyticsOverview(1, now, now)).weakDimensions[0].averageScore).toBe(80)
    expect((await teacher.getAnalyticsCase(1)).students[0].lastAssessedAt).toBe(now)
    expect((await teacher.getAnalyticsStudent(1)).timeline[0].attemptId).toBe(1)
    expect(uni.request).toHaveBeenCalledTimes(9)
  })
})

describe('Demo adapter capability boundary', () => {
  it('keeps the synthetic classroom readable and rejects unavailable writes without HTTP', async () => {
    expect(await demoLearning.getLearningProfile()).toMatchObject({ unreadCount: 0 })
    expect(await demoLearning.getCurrentLearningPlan()).toBeUndefined()
    expect(await demoLearning.getLearningNotifications()).toEqual({ items: [], unreadCount: 0 })
    await demoLearning.markLearningNotificationsRead()
    const unsupported = [
      () => demoLearning.createLearningPlan('1'),
      () => demoLearning.getLearningPlan(1),
      () => demoLearning.startLearningTask(1),
      () => demoLearning.getLearningTaskAttempt(1),
      () => demoLearning.submitLearningTaskAttempt(1, {}),
      () => demoLearning.completeLearningPlan(1),
      () => demoTeacher.createTeacherClass('一班', 'one'),
      () => demoTeacher.updateTeacherClass(1, { name: '二班' }),
      () => demoTeacher.addStudentToClass(1, 'student'),
      () => demoTeacher.removeStudentFromClass(1, 2),
    ]
    for (const action of unsupported) await expect(action()).rejects.toMatchObject({ code: 'UNSUPPORTED_OPERATION' })
    expect(await demoTeacher.getTeacherClasses()).toMatchObject([{ id: 1, code: 'demo_class_1' }])
    expect(await demoTeacher.getClassStudents(1)).toHaveLength(2)
    expect(await demoTeacher.getAnalyticsOverview()).toMatchObject({ studentCount: 0, completionRate: null })
    expect(await demoTeacher.getAnalyticsOverview(1, now, now)).toMatchObject({ scope: { classId: 1 } })
    expect(await demoTeacher.getAnalyticsCase(1)).toMatchObject({ completedPairs: 0 })
    expect(await demoTeacher.getAnalyticsStudent(1)).toMatchObject({ completed: 0 })
    expect(uni.request).not.toHaveBeenCalled()
  })

  it("maps only the signed-in student's PBL feedback to a precise readable notification", async () => {
    saveSession({
      role: 'student',
      openid: 'demo-notification-student',
      nickName: '演示学生',
      avatarUrl: '',
      createdAt: now,
      classIds: ['demo_class_1'],
    })
    configureDemoTeacherFeedback({
      async teacherFeedbackNotifications() {
        return [
          {
            id: 24,
            sessionId: 'demo-dialogue-feedback-24',
            actionType: 'feedback_only',
            body: '请补充形态证据。',
            createdAt: now,
          },
        ]
      },
    })
    await expect(demoLearning.getLearningNotifications(true)).resolves.toEqual({
      items: [
        expect.objectContaining({
          type: 'pbl_teacher_feedback',
          entityType: 'pbl_session',
          entityId: 'demo-dialogue-feedback-24',
        }),
      ],
      unreadCount: 1,
    })
    await demoLearning.markLearningNotificationsRead()
    await expect(demoLearning.getLearningNotifications(true)).resolves.toEqual({ items: [], unreadCount: 0 })
  })
})

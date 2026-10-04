import { expect, it } from 'vitest'
import { saveSession } from '@/features/identity/public'
import { ensureDemoData } from '@/features/qa/public'
import { DemoContentRepository } from '@/features/content/infrastructure/demoContentRepository'
import { DemoPblRepository } from './demoPblRepository'

it('keeps mixed turn styles and rejects reuse of an ID with another style', async () => {
  ensureDemoData()
  saveSession({
    role: 'student',
    openid: 'demo_student',
    nickName: 'Demo',
    avatarUrl: '',
    createdAt: new Date(0).toISOString(),
    classIds: ['demo_class_1'],
  })
  const repository = new DemoPblRepository(new DemoContentRepository())
  const created = await repository.createDialogue({
    clientSessionId: 't31-mixed',
    interactionStyle: 'guided',
    goalPointCodes: ['pathology.inflammation.vascular'],
  })
  const id = created.session.id
  const first = await repository.message(id, '合成问题', 't31-first', 'direct')
  expect(first.interactionStyle).toBe('direct')
  expect(first.diagnostic?.assistantReply).toMatch(/^回应\n[\s\S]*\n\n关键要点\n[\s\S]*\n\n下一步\n/)
  expect(await repository.message(id, '合成问题', 't31-first', 'direct')).toEqual(first)
  await expect(repository.message(id, '合成问题', 't31-first', 'guided')).rejects.toMatchObject({
    code: 'STATE_CONFLICT',
  })
  const second = await repository.message(id, '合成解释', 't31-second', 'guided')
  expect(second.interactionStyle).toBe('guided')
  expect(second.messages.map((message) => message.interactionStyle)).toEqual(['direct', 'direct', 'guided', 'guided'])
})

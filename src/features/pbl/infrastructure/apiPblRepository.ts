import { z } from 'zod'
import { apiRequest } from '@/platform/http/apiClient'
import type { PblDiagnostic, PblRepository, PblSession, PblSuggestion } from '../domain/ports'
const session = z.object({ id: z.number(), class_id: z.number(), topic_code: z.string(), status: z.string() })
const suggestion = z.object({
  id: z.number(),
  title: z.string(),
  prompt: z.string(),
  linked_findings: z.array(z.string()),
  status: z.string(),
  version: z.number(),
  problem_id: z.number().nullable().optional(),
})
const diagnostic = z.object({
  diagnostic_status: z.string(),
  assistant_reply: z.string(),
  follow_up_question: z.string().nullable().optional(),
  knowledge_gaps: z.array(z.unknown()),
  reasoning_issues: z.array(z.unknown()),
  recommended_questions: z.array(suggestion).optional(),
})
const toSession = (v: z.infer<typeof session>): PblSession => ({
  id: String(v.id),
  classId: String(v.class_id),
  topicCode: v.topic_code,
  status: v.status,
})
const toSuggestion = (v: z.infer<typeof suggestion>): PblSuggestion => ({
  id: String(v.id),
  title: v.title,
  prompt: v.prompt,
  linkedFindings: v.linked_findings,
  status: v.status,
  version: v.version,
  problemId: v.problem_id == null ? undefined : String(v.problem_id),
})
const toDiagnostic = (v: z.infer<typeof diagnostic>): PblDiagnostic => ({
  diagnosticStatus: v.diagnostic_status,
  assistantReply: v.assistant_reply,
  followUpQuestion: v.follow_up_question || undefined,
  knowledgeGaps: v.knowledge_gaps,
  reasoningIssues: v.reasoning_issues,
  recommendedQuestions: v.recommended_questions?.map(toSuggestion),
})
export class ApiPblRepository implements PblRepository {
  async active() {
    return (await apiRequest({ path: '/student/pbl-sessions', schema: z.array(session) })).map(toSession)
  }
  async participation(id: string) {
    const value = await apiRequest({
      path: `/student/pbl-sessions/${id}/participation`,
      schema: z.object({
        messages: z.array(z.object({ role: z.string(), content: z.string() })),
        diagnostic: diagnostic.nullable(),
      }),
    })
    return { messages: value.messages, diagnostic: value.diagnostic ? toDiagnostic(value.diagnostic) : undefined }
  }
  async message(id: string, content: string, clientMessageId: string) {
    const value = await apiRequest({
      path: `/student/pbl-sessions/${id}/messages`,
      method: 'POST',
      body: { content, client_message_id: clientMessageId },
      schema: z.object({ diagnostic }),
    })
    return toDiagnostic(value.diagnostic)
  }
  async diagnostics() {
    return (await apiRequest({ path: '/teacher/pbl-diagnostics', schema: z.array(diagnostic) })).map(toDiagnostic)
  }
  async editSuggestion(item: PblSuggestion, reject = false) {
    return toSuggestion(
      await apiRequest({
        path: `/teacher/pbl-question-suggestions/${item.id}`,
        method: 'PATCH',
        body: { version: item.version, title: item.title, prompt: item.prompt, reject },
        schema: suggestion,
      }),
    )
  }
  async adopt(id: string) {
    return toSuggestion(
      await apiRequest({
        path: `/teacher/pbl-question-suggestions/${id}/adopt-and-publish`,
        method: 'POST',
        schema: suggestion,
      }),
    )
  }
}

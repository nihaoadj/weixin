import { z } from 'zod'

export const teacherQuestionBankTaskTypeSchema = z.enum(['retest', 'knowledge_review', 'discussion', 'micro_drill'])
export const teacherQuestionBankContentSchema = z.object({
  task_type: teacherQuestionBankTaskTypeSchema,
  title: z.string().min(1).max(200),
  prompt: z.string().min(1).max(2000),
  options: z.array(z.string()).max(6),
  answer: z.record(z.string(), z.unknown()),
  explanation: z.string().max(2000),
  point_codes: z.array(z.string().min(1)).min(1).max(3),
  dimension_ids: z.array(z.string()).max(6),
})
export const teacherQuestionBankSourceSchema = teacherQuestionBankContentSchema
  .extend({
    source_type: z.literal('route_test_question'),
    source_id: z.string().uuid(),
    source_digest: z.string().regex(/^[0-9a-f]{64}$/),
  })
  .strict()
export const teacherQuestionBankItemSchema = teacherQuestionBankContentSchema.extend({
  id: z.number().int().positive(),
  version: z.number().int().positive(),
  status: z.enum(['active', 'archived']),
  medical_review_status: z.string().nullable(),
  updated_at: z.string().min(1),
})
export const teacherQuestionBankPageSchema = z.object({
  items: z.array(teacherQuestionBankItemSchema),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
})

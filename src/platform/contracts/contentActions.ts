import { z } from 'zod'

const count = z.number().int().nonnegative()
export const teacherContentActionSummarySchema = z
  .object({
    cases_draft: count,
    cases_rejected: count,
    cases_approved: count,
    questions_draft: count,
    questions_rejected: count,
    cards_draft: count,
    cards_rejected: count,
    medical_cases_pending: count.nullable(),
    medical_cards_pending: count.nullable(),
    as_of: z.string().datetime({ offset: true }),
  })
  .strict()

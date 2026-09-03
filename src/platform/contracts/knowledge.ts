import { z } from 'zod'

const timestamp = z.string().min(1)

export const apiKnowledgeCardContributionSchema = z.object({
  id: z.number().int(),
  point_code: z.string().min(1),
  class_code: z.string().nullable().optional(),
  version: z.number().int().positive(),
  card_type: z.enum(['single_choice', 'recall']),
  prompt: z.string().min(1),
  options: z.array(z.string()),
  correct_option: z.number().int().nullable().optional(),
  explanation: z.string(),
  reference: z.string(),
  status: z.enum(['draft', 'pending', 'approved', 'rejected', 'disabled']),
  reviewer_id: z.number().int().nullable().optional(),
  review_comment: z.string(),
  reviewed_at: timestamp.nullable().optional(),
  created_at: timestamp,
  updated_at: timestamp,
})

export const apiKnowledgeCardContributionListSchema = z.array(apiKnowledgeCardContributionSchema)

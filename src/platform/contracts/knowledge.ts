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
  ai_title: z.string().nullable().optional(),
  source_type: z.enum(['pbl_ai']).nullable().optional(),
  source_snapshot_id: z.number().int().nullable().optional(),
  source_position: z.number().int().nullable().optional(),
  source_finding_ids: z.array(z.string()).default([]),
  origin_student_id: z.number().int().nullable().optional(),
  origin_student_name: z.string().nullable().optional(),
  target_student_ids: z.array(z.number().int()).default([]),
})

export const apiKnowledgeCardContributionListSchema = z.array(apiKnowledgeCardContributionSchema)

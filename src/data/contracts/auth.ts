import { z } from 'zod'
import type { components } from './openapi.generated'

export type ApiLoginResponse = components['schemas']['LoginResponse']

const apiUserSchema = z.object({
  id: z.number().int(),
  role: z.enum(['student', 'teacher']),
  nickname: z.string(),
  avatar_url: z.string().optional().default(''),
  class_ids: z.array(z.string()).optional().default([]),
  permissions: z.array(z.string()).optional().default([]),
  created_at: z.string().min(1),
})

export const apiLoginResponseSchema = z.object({
  access_token: z.string().min(1),
  token_type: z.string().optional().default('bearer'),
  user: apiUserSchema,
})

export type ValidatedLoginResponse = z.infer<typeof apiLoginResponseSchema>

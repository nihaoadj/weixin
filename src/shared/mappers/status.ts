export const reportLabels = { draft: '草稿', pending_review: '待批阅', reviewed: '已批阅' } as const
export const problemLabels = { draft: '待审核', published: '已发布', rejected: '已拒绝' } as const
export type ReportState = keyof typeof reportLabels
export type ProblemState = keyof typeof problemLabels

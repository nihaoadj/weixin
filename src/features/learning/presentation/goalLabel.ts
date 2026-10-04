import type { KnowledgePoint } from '@/types/knowledge'

export function learningGoalLabel(code: string, catalog: KnowledgePoint[]): string {
  return catalog.find((point) => point.code === code)?.title || '相关知识点'
}

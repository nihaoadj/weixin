import type { PblDiagnostic, PblRepository, PblSession, PblSuggestion } from '../domain/ports'
const analysis: PblDiagnostic = {
  diagnosticStatus: 'probing',
  assistantReply: '请先说明你如何把组织损伤、炎症反应与临床线索联系起来。',
  followUpQuestion: '你预期哪些细胞或介质参与早期炎症？',
  knowledgeGaps: [],
  reasoningIssues: [],
}
export class DemoPblRepository implements PblRepository {
  async active(): Promise<PblSession[]> {
    return [{ id: 'demo-pbl-1', classId: '1', topicCode: 'pathology.inflammation', status: 'active' }]
  }
  async participation() {
    return { messages: [], diagnostic: undefined }
  }
  async message() {
    return analysis
  }
  async diagnostics() {
    return []
  }
  async editSuggestion(item: PblSuggestion) {
    return item
  }
  async adopt(id: string) {
    return {
      id,
      title: 'PBL 讨论题',
      prompt: '请说明炎症过程的关键证据。',
      linkedFindings: ['pathology.inflammation'],
      status: 'published',
      version: 1,
      problemId: 'demo-problem',
    }
  }
}

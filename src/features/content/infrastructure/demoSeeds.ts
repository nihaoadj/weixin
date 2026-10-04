import type { CaseDraftGenerateResult, CaseStageId } from '@/types/case'
import catalog from './pathologyCatalog.generated.json'

const stages: Record<CaseStageId, string> = {
  history: '收集病理背景与形态观察',
  problem_representation: '概括病理问题',
  differential: '比较至少两个机制假设',
  tests: '选择验证证据',
  management: '总结机制与解释边界',
}
const dimensions: Array<[string, string, number, CaseStageId]> = [
  ['information_gathering', '病理信息采集', 20, 'history'],
  ['problem_representation', '问题表征', 15, 'problem_representation'],
  ['differential_diagnosis', '假设比较', 20, 'differential'],
  ['evidence_reasoning', '形态证据推理', 15, 'differential'],
  ['test_selection', '验证方法', 15, 'tests'],
  ['management_safety', '解释边界', 15, 'management'],
]
function draft(topic: string): CaseDraftGenerateResult {
  const points = catalog.filter((p) => p.system_code === topic),
    first = points[0]
  return {
    title: `${first.system_label}：病理证据讨论`,
    description: 'Demo 合成病理学案例，供界面操作演示。',
    specialty: '病理学',
    difficulty: 'basic',
    estimatedMinutes: 15,
    generationMode: 'fallback',
    safetyNotice: '开发合成样例，未经过真实医学专家审核。',
    caseDefinition: {
      schemaVersion: 2,
      opening: {
        setting: '病理学 PBL 讨论课',
        patientIntro: `比较${points[0].title}与${points[1].title}的形态和机制。`,
        chiefComplaint: '如何使用观察证据支持病理解释？',
      },
      stageInstructions: stages,
      facts: [
        {
          id: 'morphology',
          category: 'exam',
          label: '形态观察',
          value: first.description,
          triggers: ['形态', '观察', '切片'],
          revealStage: 'history',
        },
      ],
      referenceReasoning: {
        problemRepresentation: first.description,
        differentials: points.slice(0, 2).map((p, i) => ({
          diagnosis: p.title,
          supportingFactIds: ['morphology'],
          opposingFactIds: [],
          priority: i + 1,
        })),
        tests: [{ name: '形态对照', purpose: '寻找区别证据', priority: 'necessary', resultFactId: 'morphology' }],
        management: [{ action: '请教师复核', rationale: '仅供教学', priority: 1, safetyCritical: true }],
      },
      practiceBlueprints: dimensions.map(([id, , , stage]) => ({
        id: `${topic}.${id}`,
        dimensionId: id,
        stageId: stage,
        learnerLevel: 'undergraduate',
        publicInstruction: stages[stage],
        allowedVariants: [],
        fixedFacts: [first.description],
        fallbackPrompt: stages[stage],
        answerSchema: 'short_text',
        criteria: [
          { id: 'evidence', weight: 100, keywords: ['证据'], feedback: '补充可核对的形态证据', critical: false },
        ],
      })),
    },
    rubric: {
      dimensions: dimensions.map(([id, label, weight, stage]) => ({
        id,
        label,
        weight,
        stageIds: [stage],
        criteria: [
          { id: 'evidence', label: '形态依据', keywords: ['证据'], feedback: '补充观察依据', critical: false },
        ],
      })),
    },
  }
}
export const showcaseDraft = draft('pathology.cell-injury')
export const additionalShowcaseDrafts: Record<string, CaseDraftGenerateResult> = Object.fromEntries(
  [...new Set(catalog.map((p) => p.system_code))].slice(1).map((topic) => [`${topic}-showcase`, draft(topic)]),
)

import type { ChatMessage, ProblemType, StudentQuestion } from '@/types/domain'

const MAX_PROMPT_LENGTH = 4000

export interface MedicalChatRequest {
  prompt: string
  history: ChatMessage[]
  question?: StudentQuestion
  mode?: ProblemType | '自由问答'
  topicCodes?: string[]
}

export interface MedicalAssistantPort {
  request(request: MedicalChatRequest): Promise<string>
}

const emergencyPatterns = [
  /胸(口)?(持续|突然|剧烈|压榨|闷)?.{0,8}(痛|疼)/,
  /呼吸(困难|急促)|喘不上气|不能呼吸/,
  /意识(不清|丧失)|昏迷|抽搐/,
  /大出血|止不住血/,
  /偏瘫|口角歪斜|言语不清/,
  /自杀|轻生|不想活/,
]

export function detectEmergency(content: string): boolean {
  return emergencyPatterns.some((pattern) => pattern.test(content))
}

export function emergencyResponse(): string {
  return '⚠️ 你描述的情况可能包含紧急危险信号。请立即停止线上问答并联系当地急救服务（中国大陆拨打 120），不要自行驾车就医；如身边有人，请让其陪同并保持电话畅通。本提示仅用于安全分流，不能替代急诊评估。'
}

export function normalizeMedicalChatRequest(request: MedicalChatRequest): MedicalChatRequest {
  const prompt = request.prompt.trim().slice(0, MAX_PROMPT_LENGTH)
  if (!prompt) throw new Error('问题不能为空')
  return { ...request, prompt }
}

export function createMedicalAssistant(
  mode: 'demo' | 'api',
  adapters: { demo: MedicalAssistantPort; api: MedicalAssistantPort },
): MedicalAssistantPort {
  return {
    async request(request: MedicalChatRequest): Promise<string> {
      const normalized = normalizeMedicalChatRequest(request)
      if (detectEmergency(normalized.prompt) || detectEmergency(normalized.question?.title || '')) {
        return emergencyResponse()
      }
      return adapters[mode].request(normalized)
    },
  }
}

export function createDemoResponse(request: MedicalChatRequest): string {
  if (request.mode === '模拟诊疗') {
    return '演示反馈：在排除急症后，请继续询问起病时间、诱因、伴随症状、既往史和用药史，并说明你的鉴别诊断依据。'
  }
  if (request.mode === '病例分析') {
    return '演示反馈：建议按“主要问题—支持证据—鉴别诊断—检查计划—处理原则”组织答案，并说明每一步的依据。'
  }
  return `演示反馈：你提出了“${request.prompt.slice(0, 32)}${request.prompt.length > 32 ? '…' : ''}”。建议从定义、常见表现、鉴别要点和处理原则四部分梳理。医学内容仅用于教学，不能替代医生诊断。`
}

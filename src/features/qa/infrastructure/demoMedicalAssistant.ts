import {
  createDemoResponse,
  type MedicalAssistantPort,
  type MedicalChatRequest,
} from '@/features/qa/application/medicalAssistant'

export const demoMedicalAssistant: MedicalAssistantPort = {
  async request(request: MedicalChatRequest): Promise<string> {
    await new Promise((resolve) => setTimeout(resolve, 450))
    return createDemoResponse(request)
  },
}

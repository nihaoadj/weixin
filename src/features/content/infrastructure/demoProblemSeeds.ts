import type { Problem } from '@/types/domain'

export function createDemoProblems(): Problem[] {
  const today = new Date().toISOString().slice(0, 10)
  return [
    {
      id: 'prob_001',
      type: '医学常识',
      title: '抗菌药物合理使用的基本原则有哪些？',
      description: '请从适应证、病原学依据、疗程和不良反应监测等方面说明。',
      target: 'all',
      status: '待审核',
      time: today,
    },
    {
      id: 'prob_002',
      type: '病例分析',
      title: '高血压病例分析',
      description: '患者男性，55岁，血压160/100mmHg，并有头痛、头晕症状。请分析诊断和治疗思路。',
      target: 'all',
      status: '待审核',
      time: today,
    },
    {
      id: 'prob_003',
      type: '模拟诊疗',
      title: '发热咳嗽病例模拟诊疗',
      description: '患者发热3天，体温持续在38℃以上，咳嗽时胸痛并伴黄色痰。',
      target: 'all',
      status: '待审核',
      time: today,
    },
  ]
}

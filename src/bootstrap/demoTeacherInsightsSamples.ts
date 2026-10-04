// Synthetic classroom fixtures, installed only by the Demo App bootstrap.
const subjects = [
  {
    key: 'vascular',
    name: '炎症血管反应',
    facts: [
      '小动脉扩张使局部血流增加，产生红和热。',
      '微血管通透性升高使富含蛋白的液体渗出。',
      '渗出液进入组织间隙可形成炎性水肿。',
    ],
  },
  {
    key: 'leukocytes',
    name: '白细胞募集',
    facts: [
      '白细胞募集包括边集、滚动、黏附和穿出。',
      '选择素参与白细胞滚动，整合素参与牢固黏附。',
      '白细胞沿趋化因子浓度梯度向炎症灶移动。',
    ],
  },
  {
    key: 'mediators',
    name: '炎症介质',
    facts: [
      '组胺可引起小血管扩张和通透性升高。',
      '前列腺素参与炎症疼痛和发热。',
      '趋化因子可引导白细胞向炎症部位募集。',
    ],
  },
  {
    key: 'acute',
    name: '急性炎症形态',
    facts: [
      '急性炎症以血管反应、渗出和中性粒细胞浸润为主要特点。',
      '浆液性炎症以浆液渗出为主。',
      '化脓性炎症以大量中性粒细胞浸润和组织液化坏死为特点。',
    ],
  },
  {
    key: 'chronic',
    name: '慢性炎症',
    facts: [
      '慢性炎症常见淋巴细胞、浆细胞和巨噬细胞浸润。',
      '慢性炎症中组织损伤与修复可同时存在。',
      '持续的修复反应可引起纤维组织增生。',
    ],
  },
]
const names = [
  '韩同学',
  '郑同学',
  '许同学',
  '何同学',
  '刘同学',
  '黄同学',
  '杨同学',
  '徐同学',
  '朱同学',
  '马同学',
  '胡同学',
  '郭同学',
]
const subjectIndexes = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 2, 3]
export const demoTeacherInsightsSamples = names.map((name, index) => {
  const subjectIndex = subjectIndexes[index]!
  const subject = subjects[subjectIndex]!
  const studentId = 5601 + index
  return {
    index,
    name,
    studentId,
    openid: `demo_insights_student_${index + 1}`,
    routeId: `56000000-0000-4000-8000-${String(studentId).padStart(12, '0')}`,
    sessionId: `demo-insights-${subject.key}`,
    sessionNumber: 5601 + subjectIndex,
    pointCode: `pathology.inflammation.${subject.key}`,
    topicName: subject.name,
    facts: subject.facts,
    objectiveCorrect: [1, 2, 2, 3, 0, 1, 3, 4, 3, 4, 2, 4][index]!,
    shortCorrect: [1, 1, 2, 3, 0, 1, 2, 3, 2, 3, 1, 3][index]!,
  }
})

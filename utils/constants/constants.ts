// 常量定义

// DeepSeek API配置
export const DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions';
export const DEEPSEEK_API_KEY = 'YOUR_DEEPSEEK_API_KEY'; // 替换为实际的API密钥
export const DEEPSEEK_MODEL = 'deepseek-chat';

// 百川智能Baichuan-M3 Plus医疗大模型API配置（免费）
export const BAICHUAN_API_URL = 'https://api.baichuan-ai.com/v1/chat/completions';
export const BAICHUAN_API_KEY = 'YOUR_BAICHUAN_API_KEY'; // 替换为实际的API密钥
export const BAICHUAN_MODEL = 'Baichuan-M3-Plus-Medical';

// 微信云开发环境ID
export const CLOUD_ENV_ID = 'cloud1-0gfg31k2f428b96b'; // 替换为实际的云开发环境ID

// 存储键名
export const STORAGE_KEYS = {
  USER_INFO: 'userInfo',
  ROLE: 'role',
  OPENID: 'openid',
  CONVERSATION_HISTORY: 'conversationHistory',
  REPORTS: 'reports'
};

// 用户角色
export const USER_ROLES = {
  STUDENT: 'student',
  TEACHER: 'teacher'
};

// 报告状态
export const REPORT_STATUS = {
  PENDING: '待批阅',
  REVIEWED: '已批阅'
};

// 消息角色
export const MESSAGE_ROLES = {
  USER: 'user',
  ASSISTANT: 'assistant'
};

// 评分范围
export const SCORE_RANGE = {
  MIN: 0,
  MAX: 100
};

// 对话历史记录最大数量
export const MAX_HISTORY_COUNT = 10;
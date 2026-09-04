# 验证与回退

## 验收矩阵

| 范围       | 证据                                                               |
| ---------- | ------------------------------------------------------------------ |
| 学生课堂   | 固定导航、课堂状态、关闭课堂、加载/错误状态、键盘与 320–1440 宽度  |
| 学习任务   | 下一项提示、提交中/失败/完成/待核验状态，原有幂等提交仍可用        |
| 教师工作区 | PBL 默认、四个 tab 同页切换、深链接初始 tab、重复点击无多余刷新    |
| 边界       | API/Demo 模式分离、页面不直接访问 storage 或 HTTP、无 API 合同变化 |

## 检查命令

```bash
npx prettier --check <T12-files>
npm run lint
npm run type-check
npm run test
node scripts/frontend-boundaries.mjs
npm run build:h5
npm run build:mp-weixin
npm run test:e2e
npm run test:e2e:demo
```

## 回退

本轮无数据写入或迁移。若体验回归，回退 T12 的页面、组件、导航编排和测试文件即可；不需要数据库恢复，也不影响 T11 PBL 记录、任务或教师发布结果。

## 外部阻塞

微信真机手势与生产发布不在本地构建验收范围。真实 AI 不属于本轮前端优化测试，避免额外 API 成本。

# 初始版本功能与安全对比

审计日期：2026-08-29  
对比基线：远程仓库 `2a9ad32`（version-0.0.1）及其后远程主线 `253c544`（version-0.02）  
对比对象：当前工作树的 uni-app + FastAPI 重构

## 结论

远程初始版本 `2a9ad32` 中所有可达的核心业务闭环均已保留：学生问答、历史回看、报告生成与提交、教师报告列表和批阅。重构用 FastAPI、SQLite/Alembic、JWT 和 repository adapter 替换了微信云函数与客户端直连模型接口，并未删除这些能力。

2026-08-29 已按初始版本同步主路径：入口只保留“学生”和“教师”；学生登录或恢复会话后进入自由问答，教师进入学生报告列表；学生提交报告后回到自由问答。医学审核仍是拥有 `medical_review` 权限的教师能力，不再显示为第三种身份。

“全部保留”需要附带三个部署条件：旧云环境中的数据不会自动进入新数据库；微信 AppID 必须确认是否仍使用原项目；真实微信登录、真实 AI 和生产域名需要配置部署环境。离线 Demo 可以直接运行，但不能代替生产账号和真实数据迁移。

## 功能映射

| 初始版本能力             | 初始实现                                                | 当前实现                                                                | 审计结论               |
| ------------------------ | ------------------------------------------------------- | ----------------------------------------------------------------------- | ---------------------- |
| 首页会话分流             | `index.ts`：学生→chat，教师→teacher/list，未登录→login  | `src/pages/index/index.vue` 使用相同三分流                              | 已同步并保留           |
| 两种身份入口             | `login.ts`：学生、教师                                  | `src/pages/login/login.vue`：学生、教师；审核改为教师权限               | 已同步并保留           |
| 学生自由医学问答         | `student/chat`                                          | `src/pages/student/chat/chat.vue` → `repositoryAsync` → `/medical-chat` | 已保留，密钥移出客户端 |
| 对话保存和历史续聊       | `conversationHistory`，history→chat 带 `conversationId` | `repository`/`repositoryAsync`、`student/history`→chat                  | 已保留                 |
| 报告生成和报告详情       | chat→report，显示分数、总结、错误建议、对话预览         | `student/chat`→`report`，保留相同信息并新增优点/通用建议                | 已保留并增强           |
| 学生提交报告后的返回     | report 提交后回到 student/chat                          | `src/pages/report/report.vue` 提交成功后回到 student/chat               | 已同步并保留           |
| 教师报告列表             | `teacher/list`：待批报告→detail                         | `src/pages/teacher/list/list.vue`：报告→detail                          | 已恢复旧入口和闭环     |
| 教师评分与反馈           | `teacher/detail`，提交后返回列表                        | `src/pages/teacher/detail/detail.vue`、`/reports/{id}/review`           | 已保留并增加权限校验   |
| 云函数数据模型与登录     | `init`、`login`、`getReport`、`submitReport`            | Alembic、`/auth`、`/conversations`、`/reports`                          | 已替换，不再依赖云函数 |
| 日志页                   | 存在源码但未列入初始 `app.json`                         | `src/pages/logs/logs.vue` 已注册                                        | 保留并变为可访问       |
| 题目、病例、班级、个性化 | 初始版本没有                                            | `problems`、病例训练、审核、班级分析、学习计划                          | 纯新增，不取代旧主流程 |

## 演示数据与真实旧数据

- 默认 `VITE_APP_MODE=demo`：应用启动时会在本地写入一份示例学生对话、待批报告和问题数据；学生与教师两种入口都可以立即看到对应内容。
- `VITE_APP_MODE=api`：开发库 `backend/data/dev.db` 已有可重复导入的测试数据，执行 `python backend/scripts/seed_test_data.py` 可恢复。
- 初始项目的 CloudBase 云数据库真实记录不在 Git 仓库内，也没有随代码提交；未取得原云环境授权与数据导出前，不能也没有自动导入这些真实记录。这是数据迁移事项，不是功能代码缺失。

## 关键差异与补齐状态

- 学生端病例接口只返回公开题面；隐藏事实、参考推理、rubric、fixed facts、digest 和内部审计字段由服务端保留。
- guided case 不能通过普通 `PUT` 直接改成 published；必须作者提交、审核专家审批、作者按当前 digest 发布。已发布版本不可原地编辑，需 clone version。
- 病例作者、审核专家、班级教师和学生分别按服务端身份/资源范围隔离；不能依赖客户端传入 role、openid 或 class id 获得权限。
- 旧 `class_ids` 与新的 `class_members` 在迁移和读取时兼容合并；0005/0006/0007 均为新增迁移，未修改 0001–0004。
- 教师学情支持总览、病例下钻、学生档案、班级筛选和日期范围；统计基于结构化 `CaseAssessment`，不把自由问答分数混入病例统计。
- 新增 CAP、急性胸痛、右下腹痛三套合成教学病例；后两套使用独立事实、参考路径、rubric blueprint 和版本摘要，不复用 CAP 的隐藏答案。

## 泄露审计

在远程历史的旧聊天页 TypeScript/JavaScript 中发现疑似真实模型 API key。当前工作树和 API 构建产物不再包含该值，但 Git 历史仍可读取，因此按已泄露处理：立即撤销/轮换、核查账单和调用日志，必要时评估历史重写及协作者影响。本文、日志和交付说明均不重复该密钥。

旧项目的 AppID、云环境 ID 属于项目标识，不等同于 AppSecret；仍需核对对应云资源权限。当前 AppSecret 与 AI key 只从后端环境变量读取，不进入 `src` 或微信构建包。

## 可复核证据

```text
git ls-tree -r --name-only 2a9ad32
git ls-tree -r --name-only 253c544
npm run check
npm run backend:check
npm run test:e2e
python -m pytest tests/test_migrations.py -q
```

当前 DevTools 应打开 `dist/dev/mp-weixin/`，而不是仓库根目录；根目录没有 `app.json` 是 uni-app 源码结构的正常现象，构建输出才包含小程序 `app.json`。

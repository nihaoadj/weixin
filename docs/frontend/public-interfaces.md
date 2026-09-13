# 前端模块公开接口

本文件是 T03 的页面调用合同。页面和共享组件只从下表的 `public.ts` 引入业务能力；`domain`、`application` 和 `infrastructure` 是模块内部实现，不能作为页面依赖。公开函数返回稳定的页面 view 或稳定领域 record，不暴露 OpenAPI DTO、Zod schema、StorageGateway 或 adapter 实例。

## 公开入口

| 模块      | 入口                               | 公开能力                                                                                                                                         |
| --------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| identity  | `src/features/identity/public.ts`  | `getSession`、`getRole`、`saveSession`、`clearSession`、`requireRole`、`logout`、`isApiRuntime`、`isDemoRuntime`、微信/Demo 登录同步             |
| qa        | `src/features/qa/public.ts`        | 对话列表/摘要/详情/保存、学生题目和作答线程、医学助手、Demo 数据初始化                                                                           |
| reports   | `src/features/reports/public.ts`   | 报告详情/摘要、草稿保存、提交批阅和教师评分                                                                                                      |
| content   | `src/features/content/public.ts`   | 题目 CRUD、发布/拒绝、病例 authoring、clone、医学审核和保存                                                                                      |
| training  | `src/features/training/public.ts`  | 五阶段病例 attempt、患者消息、阶段提交和 assessment                                                                                              |
| learning  | `src/features/learning/public.ts`  | 画像、计划、任务、微训练 attempt、通知、复盘、知识图、知识点学习路径与个人未审核练习                                                             |
| classroom | `src/features/classroom/public.ts` | 教师班级、学生列表、加退班和班级更新                                                                                                             |
| analytics | `src/features/analytics/public.ts` | 总览、病例下钻和学生下钻                                                                                                                         |
| pbl       | `src/features/pbl/public.ts`       | 学生个人阶段/消息、私有研讨提交预览与提交、教师工作项/反馈/课堂看板/跟进、教师建议发布、两轮任务、只读自动结果、课堂汇总及本人 PBL 学情总览/详情 |

所有入口内部通过 `src/bootstrap/wiring.ts` 取得已装配的 port。调用者不选择 API/Demo、不拼接 URL、不读写 storage；API 失败会保留明确错误，不会切换到 Demo。

## 页面导航合同

- 学生一级导航只包含 `pbl | learning | insights | chat`，分别显示为课堂、学习、学情、答疑；`StudentPrimaryRoute` 只接受这四个根路由。
- `ROUTES.studentCases` 保留公开兼容路径，但属于学习的二级资源页；用 `view=cases|knowledge|questions` 选择病例、知识或练习，非法值回退到病例。
- `ROUTES.studentKnowledgeNode` 为知识点学习页，必须携带已编码的 `topicCode`；非法或不存在编码显示可恢复错误并返回 `studentCases?view=knowledge`。知识图纯函数只消费 `getKnowledgeMap()` 的公开视图，不改变 `LearningRepository` 合同。
- 一级页面切换经 `goPrimary`/`reLaunch`，一级到详情经 `goDetail`/`navigateTo`，连续训练替换经 `replaceDetail`/`redirectTo`。二级页返回失败时必须回到其逻辑父页面。
- 教师 workspace 公开 key 仍为 `overview | reports | problems | pbl`，显示为待办、学情、内容、PBL。内容 section 为 `pbl-diagnostics | resources`，默认诊断建议；学情 section 为 `pbl-follow-ups | analytics | records`，默认 PBL 跟进；PBL 无 section 时直接显示课堂。
- 旧 `tab=pbl&section=work-items|diagnostics` 规范化到内容诊断，`follow-ups|results` 规范化到学情跟进，`classrooms|sessions` 继续进入 PBL 课堂。旧 `ROUTES.teacherAnalytics` 只保留为教师身份校验后的兼容重定向入口。
- 页面组件只使用导航平台公开函数，不直接拼接页面 URL 或调用散落的 `uni.navigate*`。

## 数据与身份边界

- API DTO 只在 `src/platform/contracts` 和所属 infrastructure mapper 中出现。生成类型的唯一现有输出仍是 `src/data/contracts/openapi.generated.ts`，由 `npm run contract:generate` 管理，禁止手改。
- `src/types/records.ts` 使用稳定英文状态，`src/types/domain.ts` 是旧页面中文 view；公开入口在边界完成 `shared/mappers/presentation.ts` 转换。
- 问题/题目 `type` 是后端可扩展的非空展示标签；公开接口保留已知标签的类型提示，不因历史或新增题型（例如“病例单选”）拒绝整批内容。
- Demo 业务集合由所属 feature 的 infrastructure store 读取，私有对话、问答线程、病例 attempt 和 assessment 使用既有 user-scoped key；API 业务响应只进入内存 cache。
- 会话保存、退出、token 清理和 401 失效由 identity port 与 `platform/http` 协作；页面不直接操作 `apiAccessToken` 或身份 key。
- 学生公开病例只通过 content/training 的公开结果获取；隐藏事实、参考推理、rubric、审核 digest 和内部字段不进入学生公开 DTO。
- PBL 页面只消费个人阶段、阶段缺失要素、任务 cycle/variant 和阈值结果；不暴露正确答案、私有 rubric、完整模型提示或隐藏病例事实。教师工作区没有阶段切换和结果重判公开函数。
- 知识节点只从 learning 公开接口读取材料、路径和个人练习；未完成四阶段时只显示研讨入口。个人 AI 练习读取时没有参考答案和解析，作答后才显示“按 AI 参考答案”的反馈；它不复用正式成绩或知识点状态接口。
- 学情页面通过 `getPblLearningReports`/`getPblLearningReport` 读取确定性报告；报告可以显示任务公开题面、本人得分与反馈，但不显示原始答案、正确选项、其他学生薄弱点、教师 ID 或 provider failure。
- 教师端 PBL 能力通过 `getTeacherPblWorkItems`、`getTeacherPblSessions`、`getTeacherPblFollowUps` 和反馈公开函数读取数据；其展示容器分属内容、PBL 课堂与学情，但不改变 `features/pbl` 的领域所有权。学生 PBL 页只读取本人提交快照的反馈摘要与下一行动，不能传入 student、class、snapshot 或 session 以扩大数据范围。

## 兼容入口与仓内证据

旧 `src/services/*` facade、旧 `src/data/*` aggregate/mapper/repository 已确认没有仓库内消费者：测试先迁移到真实 feature/platform 模块，再删除这些运行时文件。当前不以“仓库外消费者”作为保留理由，也不假设外部调用者永久依赖旧路径；若未来确有外部调用者，须由统筹提出带具体调用方、版本窗口和移除日期的单独兼容变更。

唯一保留的 `src/data/contracts/openapi.generated.ts` 是既有 OpenAPI 生成输出，不是业务 facade；它由 `npm run contract:generate` 管理，禁止手改。仓内证据可用以下检查复验：

```bash
rg "@/services|@/data" src e2e --glob '!src/data/contracts/openapi.generated.ts'
rg --files src/services src/data
```

预期分别是无旧运行时引用（平台契约对生成物的引用除外）以及仅列出生成 OpenAPI 类型文件。

## 变更规则

新增页面能力时先在所属 feature 的 domain port 定义最小合同，再由 API/Demo adapter 实现，最后在 `public.ts` 暴露稳定函数。跨模块流程上移到 application 或 bootstrap 注入 port；不得通过 `shared` 大包、循环导入或兼容 facade 隐藏未迁移实现。每次变更运行：

```bash
node scripts/frontend-boundaries.mjs --self-test
node scripts/frontend-boundaries.mjs
npm run type-check
npm test
```

上述边界脚本是当前事实，但尚未作为 `frontend:boundaries` 写入 `package.json`；S3 结构调整应直接调用它们。完整发布门禁、远程 CI 和目标 Node 22 环境仍由统筹与平台另行验收。

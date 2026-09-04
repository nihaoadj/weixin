# T03 前端业务分包与分层重构任务书

状态：阶段任务书。原始计划状态为“待执行”；实际仓库侧证据见 [T03 交付记录](deliveries/T03.md)。优先级：P1。执行角色：熟悉 uni-app、Vue 3、TypeScript 和可测试架构的前端工程师。

## 1. 目标与非目标

把当前分散在 services、data、types、页面中的业务职责归入明确模块，形成展示、应用、领域、基础设施的边界。必须迁移实际逻辑和调用关系，不能只把旧目录改名，不能同时保留两套业务实现。

保持微信小程序/H5 路由、UI 行为、API 合同、Demo 能力范围和本地存储兼容。保留 uni-app 的 App.vue、main.ts、pages.json、manifest.json 和页面入口约束，不引入新的状态管理框架、微前端或大规模视觉设计。

## 2. 前置资料与依赖

必读：[架构](../../architecture.md)、[数据层规范](../../data-layer.md)、[ADR 0001](../../adr/0001-data-layer-contracts.md)、[总计划](../01-07-engineering-governance/README.md)、[T05](../05-critical-tests-coverage/README.md)。

源码起点：[repositoryAsync.ts](../../src/services/repositoryAsync.ts)、[apiClient.ts](../../src/services/apiClient.ts)、[storage.ts](../../src/data/storage.ts)、[core port](../../src/data/repositories/core.ts)、[报告用例](../../src/data/usecases/reportDraft.ts)、[teacherInsights.ts](../../src/services/teacherInsights.ts)、[remoteAuth.ts](../../src/services/remoteAuth.ts)。

可先做 T03-01 设计盘点；行为重构前需 T01 安全测试基础设施、T02 基础门禁和 T05-01/02 行为基线完成。重构期间与 T04 保持 API 合同冻结；服务端漏洞修复如改变行为，须单独记录，不让纯目录移动掩盖它。

## 3. 目标结构及模块职责

建议在 `src/features/` 下按业务分包；`src/platform/` 承担运行平台与外部 IO；`src/bootstrap/` 负责启动装配；`src/shared/` 只保留有明确复用者的纯类型、纯工具和 UI。这些路径是本任务目标，当前不一定存在。

| 模块      | 自己拥有的职责                          | 不应拥有的职责                  |
| --------- | --------------------------------------- | ------------------------------- |
| identity  | 登录、会话、角色展示、身份失效编排      | 教师后台全部业务、HTTP 实现细节 |
| qa        | 会话、消息、问答、普通题目的作答线程    | 病例 authoring、报告批阅规则    |
| reports   | 报告草稿、提交、批阅及展示模型          | 会话持久化实现、任意用户查询    |
| content   | 题目/病例内容、版本、医学审核、发布操作 | 学生训练过程、班级成员管理      |
| training  | 病例阶段、学生答案、评估与训练报告      | 病例编辑和模型供应商 HTTP       |
| learning  | 画像、计划、微训练、通知、复盘          | 直接操作完整病例训练的内部仓储  |
| classroom | 教师班级和成员管理                      | 审核权限授予、计算所有学情统计  |
| analytics | 学情筛选、聚合结果展示和下钻            | 在页面重新计算服务端评分口径    |

学生/教师页面属于不同入口，不复制业务模块。医学审核先归 content 子职责，只有发现可独立交付且有清晰边界时才另立模块；应通过 ADR 解释，而不是因文件数量多随意拆包。

模块内部按实际需要设置：

| 层/入口         | 责任与依赖                                                                   |
| --------------- | ---------------------------------------------------------------------------- |
| public.ts       | 只暴露公开应用接口、稳定输入输出和必要展示入口；不是 export * 全部内部代码   |
| presentation/   | Vue 组件、composable、页面状态、标签映射；调用本模块应用接口                 |
| application/    | 用例编排、输入输出、窄 port；只依赖领域及注入的 port，不直接导入具体 adapter |
| domain/         | 业务对象、状态、纯规则；不依赖 Vue、uni、HTTP、storage、生成 DTO             |
| infrastructure/ | API/Demo adapter、DTO/Zod 校验、mapper、模块持久化 schema；实现应用 port     |
| wiring.ts       | 仅启动装配可导入的工厂，连接具体 adapter 与用例；不能被页面当作普通服务调用  |

简单模块可以只创建实际用到的层；但复杂职责不能继续塞进 public.ts。不得创建空层、无意义工厂、通用万能 Repository 或大量只转发一行且没有边界价值的类。

## 4. 依赖合同

1. `pages` 作为框架路由入口，只组合模块公开 UI/应用接口和共享 UI。模块专用组件应回到所属模块；通用 MedState、图标等保留统一公共位置。
2. 展示层调用应用层；应用层依赖领域和 port；基础设施实现 port 并依赖领域，不控制业务步骤。用例不能反向从 adapter 被调用来决定业务流程。
3. 启动装配连接实现；通过显式注入/受控上下文把已装配的接口提供给展示层。应用/领域层不能反向导入 bootstrap 获取全局服务。
4. 模块之间仅导入 public 接口。跨模块编排属于上层用例，例如 reports 通过会话 port 保存消息，不导入 qa 的 API adapter。
5. `platform/http` 负责网络、错误、缓存、去重；身份失效通过注入回调/事件通知身份编排，不直接导入页面路由并执行弹窗跳转。平台层不依赖 features。
6. `platform/storage` 管理底层存取和隔离；业务集合的 schema/迁移归模块，认证凭据的存储策略归 identity 与受控平台接口。必须保留现有 key、版本和损坏数据保护，拆包本身不升级存储版本。
7. API/Demo 仅在组合根根据 runtime mode 选择一次；调用失败不能切换实现。AI 的服务端安全 fallback 与客户端切换 Demo 数据源是不同机制。
8. shared 不反向导入业务模块；跨域 ID、分页等真正公共类型可以共享，具体病例、报告、审核结构归所属模块。

## 5. 分步实施

### T03-01 建立全量映射与架构决策

扫描全部 src 自有代码，列出“旧文件/导出/调用方 → 新模块/层/公开接口”；明确保留的框架入口、静态资源、生成产物、测试和兼容门面。审查 module graph，避免 learning/training 和 reports/qa 相互依赖形成循环。

为生成 DTO 选择唯一目标位置，默认 `src/platform/contracts/openapi.generated.ts`；模块只在 infrastructure 中引用。Zod 校验及 conformance 按模块保留，类型检查必须覆盖它们。与 T02 冻结生成工具输出参数及文件清单，与 T04 确定模块术语。

产出：ADR、模块字典、导入矩阵和迁移映射。完成标准：所有自有源文件有明确归属，纯粹“其他/待定”不是最终分类。

### T03-02 收敛平台能力与启动装配

先抽取请求、缓存、底层存储、平台登录、导航能力，保留旧导出转发以缩小单次变更。拆开 apiClient 当前同时承担的 transport、token 操作和 401 UI 导航，不能改变会话清理语义。

把 core、teacher、learning、case 多处 API/Demo 选择收敛到统一组合根。避免容器递归导入公开门面；通过 fake port 验证每个用例无需初始化 uni 或真实 HTTP 即可执行。

保留请求缓存 TTL、用户作用域、并发去重、128 项上限及旧请求失效保护。页面不能直接获取 adapter，登录失败不得留下新 token 与旧 session 的错配状态。

产出：平台接口、组合根、旧入口兼容表及平台行为测试。

### T03-03 以报告链路完成首个纵向迁移

迁移报告领域模型、port、DTO mapper、API/Demo adapter、草稿保存/提交/批阅用例及页面状态。将“先保存会话再保存报告”的编排上移到应用层；adapter 只实现原子的网络/存储步骤。

先调用会话 port、再保存草稿，不能用 Promise.all 改变顺序。现有两次 HTTP 写入不能被前端包装宣称为数据库原子事务；明确第一步成功第二步失败时的错误与重试行为，保留服务端幂等标识。不在本任务偷偷添加新的后端聚合端点。

报告 ID 与 conversation client ID 映射、跨学生隔离、undefined/null 兼容语义、标签映射保持。旧 facade 仅转发到新实现，不能保留一个可独立写数据的旧版本。

产出：完整样板模块及迁移后行为证据。报告链路通过后再推广分包模式，避免先批量移动所有文件再调试。

### T03-04 迁移剩余业务模块与页面职责

按 identity → qa/content → training → learning → classroom/analytics 的可用依赖顺序实施，每迁移一组都运行相关测试和类型检查。

将 repository.ts 中认证、Demo 集合、领域规则分离；将 teacherInsights 中班级、审核和统计按模块拆分；caseRepository 中本地训练规则归 training，不把 Demo 当作不需维护的旁路。

对聊天页、病例编辑页、训练页提取有业务含义的 composable/子组件，页面保留加载/空态/异常态、交互和生命周期。不要按任意行数机械拆函数，不能为了小文件增加跨组件隐式状态。

Demo 不支持的班级写入、学习计划写入继续返回明确 UNSUPPORTED_OPERATION；不假装成功，不扩大产品范围。确认两端条件编译行为，不能用 happy-dom 测试通过替代微信构建。

### T03-05 同步合同、工具与测试路径

同步 Vite/Vitest/tsconfig aliases、coverage include、测试 fixtures、生成路径、文档和 IDE 引用。所有手写实现进入覆盖率统计；不能因移到 features 后旧 include 未匹配而让覆盖率虚增。

生成 DTO 由工具生成，禁止手改；搬迁后的 Zod 输出仍与 DTO 做编译期一致性检查。删除已无调用者的旧门面；若对仓库外存在调用者，记录具体消费者、兼容期和迁移方案，不用“可能有人用”永久保留。

### T03-06 实现导入边界门禁

扩展 ESLint/依赖图检查，提供 `frontend:boundaries`。规则需识别 alias、相对导入、re-export、type-only 导入和静态可解析的动态 import，禁止通过 ../../ 绕过模块限制；对无法解析的跨业务动态路径明确拒绝或列出审核点。

禁止页面/业务 UI 调用 uni.request、直接操作 storage，禁止 domain/application 导入 Vue/uni/具体 adapter，禁止其他模块穿透 infrastructure 和平台层反向依赖业务层。类型依赖也要避免循环。

用独立 fixture 验证合法依赖通过、违规依赖失败；不能为测试方便在真实代码长期加入坏 import。旧兼容路径若过渡允许，必须精确枚举，最终移除。

### T03-07 完成双端和双模式回归

运行前端全检查、契约检查、API/Demo E2E、微信与 H5 构建；由 T05 执行目标模块场景，T06 检查日志/缓存敏感信息，T07 更新真实文档。交付中明确未完成的真机认证事项。

## 6. 关键验收矩阵

| ID    | 场景                                           | 必须达到的结果                                |
| ----- | ---------------------------------------------- | --------------------------------------------- |
| FE-01 | pages、features、platform、shared 全量依赖检查 | 无禁止依赖和业务循环；全部实现文件有归属      |
| FE-02 | 用 fake port 执行报告/训练核心用例             | 无真实 HTTP/storage；业务先后顺序和错误可验证 |
| FE-03 | API 断网/401/异常 DTO                          | 明确失败，绝不切 Demo；无非法响应进入领域层   |
| FE-04 | 用户切换、退出、写入后延迟 GET 返回            | 缓存清理且旧响应不能污染当前身份/新数据       |
| FE-05 | 旧版存储、损坏数据、重复迁移、跨用户读取       | 保持版本兼容、原值保护和用户隔离              |
| FE-06 | 报告先保存会话后保存草稿，第二步失败           | 顺序固定，错误不吞掉；重试无意外重复数据      |
| FE-07 | 学生/教师主要入口，API/Demo                    | 功能与权限保持；明确不支持的操作仍拒绝        |
| FE-08 | H5/微信构建、页面入口与条件编译                | 无路由丢失、平台 API 误用和只在 H5 生效的实现 |
| FE-09 | 把实现移动到 features 后运行 coverage          | 所有迁移实现仍被统计；关键门槛由 T05 验证     |
| FE-10 | 从旧目录搜索导入及重复实现                     | 清理完成，或仅有具体批准的外部兼容入口        |

## 7. 验证命令

在 T01 安全基础设施就绪后执行；新命令由本任务/T05 落地后可用：

```bash
npm run frontend:boundaries
npm run type-check
npm run test:coverage
npm run test:critical
npm run contract:check
npm run build:mp-weixin
npm run build:h5
npm run test:e2e
npm run test:e2e:demo
```

T02 接入后再用 `npm run check:all` 综合验收。测试选择不能一直停留在首个样板模块，最终覆盖全部迁移模块。

## 8. 完成标准及交付物

- [ ] FE-01～FE-10 全部满足；验收记录关联具体命令和用例。
- [ ] 交付的是实际分层逻辑，非目录树或批量重命名；旧 facade 无重复业务实现。
- [ ] 页面只通过公开能力访问业务；平台层没有页面跳转、病例规则等反向依赖。
- [ ] 单一模式装配、领域模型和 DTO 隔离、API/Demo 行为一致性可验证。
- [ ] 所有源码/测试/生成器/coverage 路径同步，无“代码移走检查也消失”。
- [ ] 交付 ADR、新旧映射、公开接口说明、边界规则与自测、回归证据及 `deliveries/T03.md`。

## 9. 回退与风险处理

按模块提交，每步保留可构建版本；回退某模块时同步回退调用方、生成路径及配置，不能只还原文件位置。结构重构不主动删除已有本地数据；若必须更改存储格式，另立兼容迁移步骤并交 T01/T05 验证。遇到跨模块依赖环先调整职责或上移编排，不靠 shared 大包、循环容器或禁用 Lint 解围。

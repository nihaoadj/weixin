# T66 代码与文件组织规范复核及修复

状态：S0–S3文件组织修复与验证完成；S4保护核对完成，临时清理受工具策略阻塞。已有函数覆盖率门槛未达标，迁移前后对比见交付。日期：2026-10-04。

## 当前事实与范围

用户要求再次复核[代码与目录组织规范](../../code-organization-standard.md)，依据该规范检查和修复项目文件组织。规范中的可选布局不自动转化为迁移要求；项目现行规则用于保持行为和合同兼容。

起始工作区有 1,556 条 Git 状态记录。已保存 1,875 个现存受跟踪/未跟踪文件的路径、大小、SHA-256，以及完整状态和暂存区条目基线到受忽略的 `.contract-tmp/t66-filesystem-baseline/`。不提交、不推送、不修改暂存区；迁移保留工作区文件的当前内容。

初始前端边界检查退出码 0（211 个实现文件）；后端边界检查退出码 0（9 个模块）。这些结果只说明现有检查通过，不证明目录归属已经合理。

已确认的差距：规范“原则”证据等级与部分条文不一致；uni-app 来源链接需要更新；Python 编辑器缩进缺少覆盖；仓库根保留 7 份独立 pelican HTML 示例；全局组件区包含业务专属实现，需进一步按实际依赖划分。现存后端旧路径有兼容壳，生成快照和 `output/` 中有必要消费者与证据，不按名称直接清理。

## 目标与不变的业务合同

- 修正规范的证据等级、引用与迁移验收表达，保存可离线查阅的来源热度记录。
- 根据代码归属迁移明确的业务专属文件与独立示例，更新全部活动引用、测试及工具扫描范围。
- 保持路由、界面、权限、API/Demo 行为、数据库结构和迁移版本关系。业务访问仍经现行功能合同；功能视图可以由页面/应用壳组合。
- 补齐文件分类和必要自动检查，在 CI 中执行实际采用的目录/边界规则。
- 按基线与迁移映射核对已有内容与暂存区，记录命令、退出码和适用的未验项。

本次不因目录规范更换技术栈，不升级依赖，不删除历史证据，不重写生成快照内容，也不恢复既往已收尾阶段的验收。Vite peer 版本差距单独记录，目录整理不以忽略它作为兼容性通过证据。

## 迁移映射与决策

| 对象                                  | 处理                                    | 理由与影响                                          |
| ------------------------------------- | --------------------------------------- | --------------------------------------------------- |
| `.editorconfig`                       | 加 Python 四空格覆盖                    | 与现有 Python 源码和工具规则一致                    |
| 根目录 7 个 `pelican-*.html`          | 移至 `docs/examples/pelican/`，字节保持 | 独立示例不承担运行入口；先查引用再移动              |
| 明确的功能专属组件/帮助函数及邻近测试 | 按盘点结果补充逐文件映射后迁移          | 统一业务归属；更新 import、mock、源码读取与构建范围 |
| 跨功能教师工作区与通用 UI             | 保留明确的组合/共享职责                 | 不把应用组合错误归入一个业务模块                    |
| 后端兼容壳、共享合同与生成物          | 依据调用者决定，默认保留必要路径        | 不制造重复实现，不机械改变有效消费位置              |
| 运行输出与证据                        | 明确分类与新增本地输出位置              | 保留既有截图/记录，新增可重建输出不入库             |

## 实施节点

1. S0：复核规范、只读文件与依赖盘点、确定映射；格式/链接/空白和技能结构检查通过后再改运行路径。
2. S1：规范与文件分类规则、纯配置与独立示例整理。
3. S2：按确定映射迁移源码与邻近测试，同步边界检查、覆盖范围、CI 和当前架构说明。
4. S3：执行目录检查、前后端相关边界、类型/Lint、契约和必要行为/构建回归；涉及微信产物路径时按最小范围验收。
5. S4：基线保护核对、交付记录、清理本次临时文件；未受影响的历史验收不重开。

## 验证与回退

先验证静态组织和引用，再跑受影响行为与最终集成。生成器/数据库资源未修改时不运行数据库迁移；契约检查使用脚本自己的隔离环境。应用构建只在受影响模式运行。

修订边界检查时保留旧负例并增加合法功能 UI 与越界导入的自检，确保允许新归属不放宽核心层隔离。文件组织检查需要覆盖路径大小写、未解析的本地源码引用、运行代码反向引用工具/测试以及既定文件分类。

源文件移动的回退依据逐文件映射逆向进行，禁止用 `git reset` / `git checkout` 覆盖起始用户内容。配置/脚本修改保留本次修改前字节副本；回退只作用于本次范围。收尾比较暂存区原始条目哈希并核对未纳入本次修改清单的基线文件。

交付记录：[implementation.md](deliveries/implementation.md)。

S0 的计划格式、本地链接、空白与技能结构/自检均退出 0 后实施。S1–S2 已完成规范分级、逐文件归属迁移、Demo知识目录注入、失效豁免删除及门禁接入。S3 的目录/边界、自检、Lint、类型、格式、契约、620项行为测试及API/Demo构建均通过；覆盖率命令因已有函数覆盖率不足退出 1，基线77.12%、当前77.20%，阈值仍为80%。S4 暂存区与未纳入修复的文件、HTML字节和T64归档已核对；本次临时副本清理动作被工具策略拒绝，保留受忽略的T66目录与脚本，未宣称清理成功。

按文档入口仅留最近两轮完整计划的要求，T64两份原文已字节保持地[归档](../../archive/update-plan-t64-20261004.md)，保留T65/T66，既有人工待验状态未改变。

## 已确认逐文件迁移

以下映射在改源码前确定；实现及邻近测试保留现有内容，只更新必要引用。

| 原路径                                                                       | 新路径                                                                         |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `src/components/student/PathologyKnowledgeMap.vue`                           | `src/features/learning/presentation/PathologyKnowledgeMap.vue`                 |
| `src/components/student/PathologyKnowledgeMap.spec.ts`                       | `src/features/learning/presentation/PathologyKnowledgeMap.spec.ts`             |
| `src/components/teacher/TeacherFinalTestReviewQueue.vue`                     | `src/features/learning/presentation/TeacherFinalTestReviewQueue.vue`           |
| `src/components/teacher/TeacherFinalTestReviewQueue.spec.ts`                 | `src/features/learning/presentation/TeacherFinalTestReviewQueue.spec.ts`       |
| `src/components/student/PblConversationBoundary.vue`                         | `src/features/pbl/presentation/PblConversationBoundary.vue`                    |
| `src/components/student/PblConversationBoundary.spec.ts`                     | `src/features/pbl/presentation/PblConversationBoundary.spec.ts`                |
| `src/components/student/PblResponseStylePicker.vue`                          | `src/features/pbl/presentation/PblResponseStylePicker.vue`                     |
| `src/components/student/PblResponseStylePicker.spec.ts`                      | `src/features/pbl/presentation/PblResponseStylePicker.spec.ts`                 |
| `src/components/student/PblTargetComparison.vue`                             | `src/features/pbl/presentation/PblTargetComparison.vue`                        |
| `src/components/student/PblPhaseTrack.vue`                                   | `src/features/pbl/presentation/PblPhaseTrack.vue`                              |
| `src/components/student/LearningDialogueReview.vue`                          | `src/features/pbl/presentation/LearningDialogueReview.vue`                     |
| `src/components/student/learningDialogueTurns.ts`                            | `src/features/pbl/presentation/learningDialogueTurns.ts`                       |
| `src/components/student/learningDialogueTurns.spec.ts`                       | `src/features/pbl/presentation/learningDialogueTurns.spec.ts`                  |
| `src/components/student/pbl-report.behavior.spec.ts`                         | `src/features/pbl/presentation/pbl-report.behavior.spec.ts`                    |
| `src/components/teacher/TeacherPblWorkItemDetail.vue`                        | `src/features/pbl/presentation/TeacherPblWorkItemDetail.vue`                   |
| `src/components/teacher/teacherPresentation.ts`                              | `src/features/pbl/presentation/teacherPresentation.ts`                         |
| `src/components/teacher/TeacherPblScreen.vue`                                | `src/features/pbl/presentation/TeacherPblScreen.vue`                           |
| `src/components/teacher/TeacherPblClassrooms.vue`                            | `src/features/pbl/presentation/TeacherPblClassrooms.vue`                       |
| `src/components/teacher/teacher-pbl-reference.behavior.spec.ts`              | `src/features/pbl/presentation/teacher-pbl-reference.behavior.spec.ts`         |
| `src/components/teacher/teacher-pbl-diagnostic-detail.behavior.spec.ts`      | `src/features/pbl/presentation/teacher-pbl-diagnostic-detail.behavior.spec.ts` |
| `src/components/teacher/teacher-pbl-alignment.behavior.spec.ts`              | `src/features/pbl/presentation/teacher-pbl-alignment.behavior.spec.ts`         |
| `src/components/teacher/CaseSetupForm.vue`                                   | `src/features/content/presentation/CaseSetupForm.vue`                          |
| `src/components/teacher/case-setup-form.behavior.spec.ts`                    | `src/features/content/presentation/case-setup-form.behavior.spec.ts`           |
| `src/components/teacher/TeacherContentScreen.vue`                            | `src/features/content/presentation/TeacherContentScreen.vue`                   |
| `src/components/teacher/TeacherContentResources.vue`                         | `src/features/content/presentation/TeacherContentResources.vue`                |
| `src/components/teacher/TeacherContentResources.behavior.spec.ts`            | `src/features/content/presentation/TeacherContentResources.behavior.spec.ts`   |
| `src/components/teacher/TeacherInsightsScreen.vue`                           | `src/features/analytics/presentation/TeacherInsightsScreen.vue`                |
| `src/components/teacher/TeacherInsightsReadWorkspace.vue`                    | `src/features/analytics/presentation/TeacherInsightsReadWorkspace.vue`         |
| `src/components/teacher/TeacherInsightsReadWorkspace.spec.ts`                | `src/features/analytics/presentation/TeacherInsightsReadWorkspace.spec.ts`     |
| `src/components/teacher/TeacherInsightsKnowledgeTable.vue`                   | `src/features/analytics/presentation/TeacherInsightsKnowledgeTable.vue`        |
| `src/components/teacher/TeacherInsightsStudentRow.vue`                       | `src/features/analytics/presentation/TeacherInsightsStudentRow.vue`            |
| `src/components/teacher/studentRecordLayout.ts`                              | `src/features/analytics/presentation/studentRecordLayout.ts`                   |
| `src/components/teacher/studentRecordLayout.spec.ts`                         | `src/features/analytics/presentation/studentRecordLayout.spec.ts`              |
| `src/shared/mappers/mappers.spec.ts`                                         | `src/test/integration/mappers.spec.ts`                                         |
| `pelican-bicycle-animation.html`                                             | `docs/examples/pelican/pelican-bicycle-animation.html`                         |
| `pelican-bike-svg.html`                                                      | `docs/examples/pelican/pelican-bike-svg.html`                                  |
| `pelican-bike.html`                                                          | `docs/examples/pelican/pelican-bike.html`                                      |
| `pelican-coastal-ride.html`                                                  | `docs/examples/pelican/pelican-coastal-ride.html`                              |
| `pelican-cycling-animation.html`                                             | `docs/examples/pelican/pelican-cycling-animation.html`                         |
| `pelican-cyclist.html`                                                       | `docs/examples/pelican/pelican-cyclist.html`                                   |
| `pelican-seaside-animation.html`                                             | `docs/examples/pelican/pelican-seaside-animation.html`                         |
| `src/features/learning/infrastructure/demoLearningRepository.compat.spec.ts` | `src/test/integration/demoLearningRepository.compat.spec.ts`                   |

Demo 知识目录的字段映射移入内容模块，装配根注入读取函数；学习模块仅依赖共享知识点合同。集成测试跨模块装配依赖，因此移入集成测试区。

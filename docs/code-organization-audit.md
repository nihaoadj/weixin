# 代码与文件组织修复审计

本审计记录 T66 按[代码与目录组织规范](code-organization-standard.md)实施的文件分类与边界修复。规范引用、原则等级和 GitHub 元数据来源已在规范及[离线来源快照](references/code-organization-sources-20261004.json)中修订；本页复述项目适用结论，不重新评估外部来源。

状态：本轮文件组织修复完成，共迁移42个文件；命令与实际结果见[实施记录](update_plan/66-code-organization/deliveries/implementation.md)。目录/边界、Lint、类型、格式与契约检查通过，620项行为测试通过。全局函数覆盖率77.20%仍低于80%门槛，迁移前基线为77.12%，未降低阈值或缩小覆盖范围。

## 分类结论

| 范围               | 修复结论                                                                                                                                                  | 可核对位置                                                                                                                                                                                                          |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 规则与来源         | 将证据等级调整为与来源数量和覆盖范围一致；使用 uni-app 当前官方工程页；保存 GitHub API 当日字段快照，明确热度不是行业共识。                               | [规范](code-organization-standard.md)、[来源快照](references/code-organization-sources-20261004.json)                                                                                                               |
| 前端业务展示       | 只属于单一业务的组件、帮助函数及邻近测试归入 `src/features/<feature>/presentation/`；跨业务教师工作区与全局 UI 保留在共享/应用组合位置。                  | 例如 [PBL 展示](../src/features/pbl/presentation/TeacherPblScreen.vue)、[内容展示](../src/features/content/presentation/TeacherContentScreen.vue)、[教师工作区](../src/components/teacher/TeacherWorkspaceDeck.vue) |
| 前端集成测试与合同 | mapper 与适配集成测试移入 `src/test/integration/`；共享公开合同继续保留在 `src/platform/contracts/`，不强行归属到某个业务。                               | [mapper 集成测试](../src/test/integration/mappers.spec.ts)、[兼容测试](../src/test/integration/demoLearningRepository.compat.spec.ts)、[学习合同](../src/platform/contracts/learning.ts)                            |
| 学习 Demo 数据边界 | `learning` 基础设施不直接读取 `content` 内部 JSON。`content` 侧适配生成快照，应用 bootstrap 将读取函数注入学习 Demo；生成 JSON 继续归 `content` 所有。    | [bootstrap 装配](../src/bootstrap/wiring.ts)、[内容侧目录适配](../src/features/content/infrastructure/demoKnowledgeCatalog.ts)、[生成快照](../src/features/content/infrastructure/pathologyCatalog.generated.json)  |
| 后端兼容与测试数据 | 删除 3 条指向已删除源文件的后端 import allowlist；维护脚本通过 `app.bootstrap.test_seed` 获取测试种子。仍有测试或适配消费者的兼容壳予以保留。             | [后端边界配置](../config/backend-boundaries.json)、[测试种子脚本](../backend/scripts/seed_test_data.py)、[E2E 服务脚本](../backend/scripts/run_e2e_server.py)、[兼容入口](../backend/app/services/test_seed.py)     |
| 独立 HTML 示例     | 7 个根目录 pelican 页面移至 `docs/examples/pelican/`，作为文档示例保存，迁移不改文件字节。                                                                | [示例索引](examples/pelican/README.md)                                                                                                                                                                              |
| 文本与本地产物配置 | Python 缩进设为 4 空格；全局忽略 `__pycache__`；将 ZIP 标成二进制；本地产物、`output/local/`、根级 `tmp/` 与 `data/` 使用明确忽略规则。                   | [EditorConfig](../.editorconfig)、[Git 属性](../.gitattributes)、[忽略规则](../.gitignore)、[output 分类](../output/README.md)                                                                                      |
| 结构检查接入       | 新结构检查器核对路径大小写、根目录独立 HTML、后端 allowlist 路径和运行时代码对脚本/测试的反向依赖；`structure:check` 与 `structure:self-test` 已接入 CI。 | [检查器](../scripts/check-code-organization.py)、[检查规则](../config/code-organization.json)、[CI 工作流](../.github/workflows/ci.yml)                                                                             |

空目录不是 Git 可追踪的结构实体，不以创建占位文件作为组织修复。已有兼容壳依据测试和适配调用保留，不因旧目录名或文件名批量删除。

### 后端兼容入口的退出条件

| 入口              | 已确认消费者/用途                                                                                  | 迁移目标与删除条件                                                                                                                        |
| ----------------- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `app.api.reports` | `backend/tests/test_data_layer.py`沿用旧模块的注入接缝；该文件用`sys.modules`指向真实实现          | 迁到`app.modules.reports.api.reports`并验证monkeypatch仍作用于真实实现后删除别名                                                          |
| `app.models`      | `backend/tests/conftest.py`及数据/性能等测试使用全局ORM注册入口                                    | 逐步使用`app.bootstrap.model_registry`或所属模块ORM；迁移与测试消费者全部更新、metadata注册结果相同后删除兼容导出                         |
| `app.schemas`     | `test_case_ai.py`的`PatientReplyModel`、`test_medical_ai.py`的`MedicalChatRequest`仍从旧入口导入   | 迁到对应模块API schema；确认无旧消费者与公开兼容要求后删除重导出                                                                          |
| `app.services`    | `conftest.py`/`test_characterization.py`的病例种子及AI、授权、analytics、test_seed测试仍使用旧入口 | 测试种子迁bootstrap，业务调用迁所属模块public/用例；逐文件确认调用者已迁移、旧适配的Actor/事务/响应行为已覆盖后删除，不默认整目录长期保留 |

这些路径不是第二套业务目录的扩展点。新增调用采用现行模块入口；本次维护脚本已迁移，兼容删除需要单独验证实际消费者。

## 保持原路径的内容

uni-app `static/` 资源位置继续遵循框架复制规则。契约脚本仍生成并检查以下四个原路径：`docs/openapi.json`、`src/data/contracts/openapi.generated.ts`、`src/test/fixtures/case-draft.json`、`src/features/content/infrastructure/pathologyCatalog.generated.json`。它们有不同的文档、构建、测试和运行时消费者，不为目录整齐集中迁移；见[契约生成器](../scripts/contract.mjs)。

既有验收证据按其用途保留，具体入口见 [output 目录说明](../output/README.md)。新增可重建的本地产物写入被忽略的 `output/local/`，不据此宣称历史 `output/` 已清理。

## 单独记录的依赖风险

锁文件中的 Vite 为 `7.3.6`，`@dcloudio/vite-plugin-uni` 声明的 Vite peer 版本为精确值 `5.2.8`。本次没有改变依赖版本。此项需要单独评估和验证，不属于目录违规，也不能据此评价整个技术栈“不规范”。证据见 [package.json](../package.json) 与 [package-lock.json](../package-lock.json)。

## 最终验收

最终结果见[实施记录](update_plan/66-code-organization/deliveries/implementation.md)。API/Demo生产构建、Demo开发编译和原生WXSS语法检查通过；微信普通刷新成功，doctor确认SDK3.17.2与URL校验开启。目录迁移没有视觉设计变化，未新增截图或重开历史点击验收；真实API、远程CI、真机与干净环境安装未作为本次通过项。

本次临时基线、隔离副本与迁移脚本的删除被执行工具策略拒绝，仍在受忽略的`.contract-tmp/`内；未将该清理标记为完成。

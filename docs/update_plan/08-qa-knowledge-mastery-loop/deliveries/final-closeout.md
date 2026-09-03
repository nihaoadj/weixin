# T08 最终交付记录

# T08 实施交付记录

状态：已完成；核心学生闭环、教师批阅复习标记、班级知识聚合、24 个主题目录、合同同步、独立后端功能开关及 `recall` 受控揭晓/自评 API 均已完成仓库内验收。

## 当前事实

- 已创建只读、版本化的内科学基础目录（6 个系统、24 个主题、每主题至少 1 张 `single_choice` 卡），并提供 `GET /knowledge/tree` 与主题校验；Demo 目录和卡片同步覆盖全部主题。
- 问答对话新增最多 3 个稳定知识点代码的学习上下文；上下文属于学生对话，服务端拒绝目录外代码。
- 同时提供 `GET/PUT /conversations/{id}/learning-context`：只能读取或更新本人对话，更新上下文不会覆盖既有消息；`GET /conversations/summaries?knowledge_point_code=...` 保持分页筛选。
- 新增结束小测、错题复习项、SM-2 风格个人调度、客观题提交后揭晓答案/解析、主动收藏回答进入复习队列，以及对应 API/Demo 前端实现。
- 聊天页、知识巩固页和“学习”首页已连通；API 失败保持当前运行模式，不降级为另一数据源。
- 教师批阅报告时可从目录选择最多 3 个建议复习知识点；服务端拒绝未知代码并以报告 ID 为幂等来源创建学生复习项。
- 教师可查本人具体班级的复习参与人数、到期积压和客观正确率；少于 5 名参与学生时，薄弱知识点排名自动隐藏。
- `T08_LEARNING_CONTEXT_ENABLED`、`T08_EXIT_QUIZ_ENABLED` 与 `T08_REVIEW_CAPTURE_ENABLED` 默认开启；关闭后保留已存对话/复习记录的读取，拒绝新增主题上下文、小测或复习证据写入。
- 已批准且在学生班级范围内的 `recall` 补充卡可通过受控 reveal 接口获取解析，随后以 `again/hard/good/easy` 自评更新个人调度。自评尝试的 `selected_option` 保持 `null`，不进入教师客观正确率。
- 教师可修订本人未停用的补充卡；修订会递增版本、清除审核人/意见并重置为草稿，必须重新提交医学审核。
- 知识地图由 `GET /learning/knowledge-map` 返回。它仅按个人已记录的复习项和调度状态显示“未开始、薄弱、学习中、待复习、相对稳定”，浏览目录和模型候选不会改变状态。
- 历史问答保留原有分页，并可按已确认的主题筛选；筛选在 API/Demo 仓储层执行，历史卡片显示主题标签。

## 本次核验范围

- 已批准且在学生范围内的教师 `single_choice` 补充卡会被学习 API 纳入结束小测、到期队列和服务端判分；答案与解析仍在提交前隐藏，错题以稳定 `teacher-choice:{id}` 卡代码进入个人复习证据。
- 教师 `recall` 补充卡在学生学习页使用独立的“先回忆 → 揭晓教学要点 → 四档自评”交互；不会复用客观题选项组件或把自评写入客观正确率。
- 未执行生产迁移、历史回填、远程发布或真实模型调用。

## 数据、权限与回退

- 新增迁移：`20260831_0010`（对话学习上下文）、`0011`（复习项、状态、尝试）、`0012`（教师补充卡）、`0013`（题目/病例知识绑定）与 `0014`（报告复习知识点）。迁移仅面向受管测试库验证过，且 `0014` 兼容 ORM 已建表的 E2E 启动路径。
- 复习接口均要求学生角色；只在提交客观题后返回正确性与解析。答案不出现在小测题目 DTO 中。
- 回退时先关闭入口并停止产生新证据；`0014` downgrade 只移除报告知识点关联，既有对话、报告、病例和学习计划不被改写。生产数据回退前须备份新增复习数据。

## 验证证据

| 命令 | 退出码 | 结果 |
| --- | ---: | --- |
| `npm run backend:test:safety`（最终） | 0 | 14 passed（既有 SQLite FK 循环 warning） |
| `npm run backend:test:migrations`（最终） | 0 | 2 passed（同一既有 warning） |
| `cd backend; python -m pytest tests/test_t08_knowledge_review.py -q`（最终） | 0 | 12 passed：目录覆盖、答案保密、错题入队、学生权限、主题上下文、主题筛选分页、知识地图证据、补充卡审批、题目绑定、报告批阅复习项、班级权限与回忆自评 |
| `python backend/scripts/check_boundaries.py` | 0 | backend boundaries PASS |
| `node scripts/frontend-boundaries.mjs` | 0 | frontend boundaries PASS |
| `npm run contract:generate` / `npm run contract:check` | 0 | OpenAPI、生成类型和 fixture 已同步，临时快照校验一致 |
| `npm run type-check`（最终） | 0 | Vue/Node TypeScript 严格检查通过；题目编辑测试的空值 guard 已修复 |
| `npm run lint`（最终） | 0 | ESLint 无 warning |
| `npm run build:h5` | 0 | H5 构建完成；仅有 Zod 依赖的既有 Rollup 注释 warning |
| `npm run build:mp-weixin`（最终） | 0 | 微信小程序构建完成；同一既有依赖 warning |
| `npm run test:e2e:demo` | 0 | 5 passed：Demo 主报告流程、学习页和教师工作台 |
| `npm run test:e2e:demo`（主动回忆 UI 后） | 0 | 5 passed：无补充卡的 Demo 学习页保持可用，新增区块不影响现有工作流 |
| `npm run test:e2e` | 0 | 8 passed：API 数据层、空状态、学生/教师主流程、病例和视觉回归；E2E 受管临时库成功升级至 `0014` |
| `npm run test:e2e`（最终） | 0 | 8 passed：受管临时库升级至 `0014`，API 数据层、分页、学生/教师主流程、病例和视觉回归通过 |
| `npm run test:e2e:demo`（最终） | 0 | 5 passed：Demo 主报告流程、学习页、教师工作台和视觉检查通过 |
| `git diff --check` | 0 | 无空白错误 |
| `python .agents/skills/wx-engineering-standards/scripts/self_check.py` | 0 | 工程规范结构、链接与状态标签检查通过 |

## 未执行项与回退

- 未执行生产迁移、历史回填、远程发布、真实模型调用、真实微信调用或生产数据删除；这些均不属于本次授权范围。
- 运行过的迁移只存在于受管测试/E2E 临时数据库。回退时关闭三个 T08 功能开关以停止新增证据，保留对话、报告和复习数据；迁移 downgrade 只影响本轮新增表/索引，不修改既有对话、病例、报告或学习计划。

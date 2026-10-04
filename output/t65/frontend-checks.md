# T65 前端验收

验收覆盖本批变更文件和完整前端 Vitest。首轮全并行测试出现两处超时和一处 storage spy 断言失败；串行复验两文件 4/4 通过，随后将全量 worker 限为 2 后 619/619 通过。没有修改其他代理的测试或模块。

| 检查             | 命令                                                                                                                                         | 结果                                                                                                                                                                                                                                          |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 首轮全量 Vitest  | `npm test`                                                                                                                                   | exit 1；112 files 中 110 passed、2 failed；619 tests 中 616 passed、3 failed。`demoContentSamples.spec.ts` 首用例超时，API-mode 用例的 `uni.setStorageSync` spy 收到 3 次教师 session 调用；`demoTeacherInsightsSamples.spec.ts` 首用例超时。 |
| 失败文件串行复验 | `npm test -- --maxWorkers=1 --no-file-parallelism src/bootstrap/demoContentSamples.spec.ts src/bootstrap/demoTeacherInsightsSamples.spec.ts` | exit 0；2 files、4 tests passed。                                                                                                                                                                                                             |
| 全量 Vitest 复验 | `npm test -- --maxWorkers=2`                                                                                                                 | exit 0；112 files、619 tests passed。首轮现象与并行资源争用或共享 spy 串扰一致；这是基于串行及限 worker 复验的判断，没有改测试来掩盖首轮失败。                                                                                                |
| 类型检查         | `npm run type-check`                                                                                                                         | exit 0（复验）。                                                                                                                                                                                                                              |
| 前端边界         | `node scripts/frontend-boundaries.mjs`                                                                                                       | exit 0；211 implementation files checked。                                                                                                                                                                                                    |
| ESLint           | `npx eslint --max-warnings=0`，范围为本批 14 个现存源码/spec 文件                                                                            | exit 0。                                                                                                                                                                                                                                      |
| Prettier         | `npx prettier --check`，同上 14 个文件                                                                                                       | exit 0。首次检查发现 5 个由本批删改引起的格式差异，执行 `npx prettier --write` 仅整理这 5 个文件后复验通过。                                                                                                                                  |

ESLint 与 Prettier 的 14 文件范围：

```text
src/features/content/domain/ports.ts
src/features/content/infrastructure/apiContentRepository.ts
src/features/content/infrastructure/demoContentRepository.ts
src/features/content/public.ts
src/features/content/public.spec.ts
src/features/content/infrastructure/demoContentRepository.retirement.spec.ts
src/features/content/infrastructure/t53-question-bank-source.spec.ts
src/features/content/infrastructure/teacherActionSummary.spec.ts
src/features/learning/domain/ports.ts
src/features/learning/infrastructure/apiLearningRepository.ts
src/features/learning/infrastructure/demoLearningRepository.ts
src/features/learning/public.ts
src/features/learning/infrastructure/demoLearningRepository.caseReview.spec.ts
src/types/knowledge.ts
```

证据日志：[`frontend-vitest.log`](frontend-vitest.log)、[`frontend-bootstrap-retry.log`](frontend-bootstrap-retry.log)、[`frontend-vitest-retry.log`](frontend-vitest-retry.log)、[`frontend-type-check-final.log`](frontend-type-check-final.log)、[`frontend-boundaries.log`](frontend-boundaries.log)、[`frontend-eslint-final.log`](frontend-eslint-final.log)、[`frontend-prettier-final.log`](frontend-prettier-final.log)。

## 相邻旧 API 的消费者分类

此次验收只读检查了 QA 的 `QuestionRepository` 和 Content 的旧问题/发布/复核/归档方法，没有扩大清理范围。

| 合同或方法                                                                                                                                                        | 源码消费者证据                                                                                                                                                                                                                                                                                                                                                                                                                      | 分类                                                                       |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| QA `QuestionRepository`：`getStudentQuestions`、`findStudentQuestion`、`getQuestionThread`、`saveQuestionThread`                                                  | 接口见 [`ports.ts`](../../src/features/qa/domain/ports.ts#L10)，公开转发见 [`public.ts`](../../src/features/qa/public.ts#L24)。排除 spec 后，仓库内仅这些 public 转发和 API/Demo adapter 实现命中；页面/组件/装配没有调用。旧 question 与 question-detail 行为 spec 仍 mock 这些调用并断言不触发；QA core spec 保留 adapter 行为/退役边界测试。                                                                                     | 无当前生产调用；保留兼容 facade 和防复活/adapter 测试。本批未删除。        |
| Content 旧 Problem 写方法：`saveProblemsAsync`、`upsertProblemAsync`、`publishProblemAsync`、`rejectProblemAsync`、`resetProblemsAsync`                           | public 导出见 [`content/public.ts`](../../src/features/content/public.ts#L14)。排除 spec 后，这些 public 名称没有页面或组件调用；`qa/core-behavior.spec.ts` 对 publish/reject/reset 保留 `RETIRED_FLOW` 防复活断言。`getProblemsAsync` 仍被学生 question 页调用，`findProblemAsync` 仍被教师 problem-detail 页调用，不能把读取合同整体归为 dead。bootstrap 使用的 `demoProblemStore.resetProblems()` 是另一条 Demo 初始化内部函数。 | 写方法无生产调用，保留兼容边界；读取仍被使用。本批未删。                   |
| Content case publish/clone/review：`cloneCaseVersionAsync`、`publishGuidedCaseAsync`、`submitGuidedCaseForReviewAsync`、Medical Review queue/view/decision 及别名 | public facade 在 [`content/public.ts`](../../src/features/content/public.ts#L26)；排除 spec 后，页面/组件没有这些调用。`content/public.spec.ts`、`training/infrastructure/repository.behavior.spec.ts`、`demoContentRepository.retirement.spec.ts` 留有 retired/auth/state 边界测试。当前 case-edit 仍使用 `getCaseAuthoringAsync`、`getGuidedCasesAsync`、`saveGuidedCaseAsync`，这些是活跃编辑合同。                              | 旧写入/复核 facade 无当前页面调用；保留测试合同与兼容页边界。本批未删。    |
| Content 题库 `archiveTeacherQuestionBankItem`                                                                                                                     | public 及 repository 有实现；排除 spec 后没有生产调用。教师资源和个人题库页面使用 `deleteTeacherQuestionBankItem`，不是 archive facade。API/Demo question-bank spec 覆盖 archive 行为。                                                                                                                                                                                                                                             | archive 方法目前只有 adapter/spec 消费；删除题目是当前生产路径。本批未删。 |

源码消费者查询以 `rg` 排除 `*.spec.*` 和 `*.test.*`，并分别检查 `src/pages`、`src/components`、`src/bootstrap`、`src/platform`。相关身份/退役边界测试仍保留，不据此宣称上述合同已完成清理。

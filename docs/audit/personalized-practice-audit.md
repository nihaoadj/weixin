# V3 个性化训练与第二阶段审计留证

审计日期：2026-08-28  
规格来源：`docs/update/README.md` v3.0

## 当前结论

V3 的病例审核、班级学情和个性化训练链路已在当前工作树实现并通过本地质量门禁。Demo 和 API 是两个显式运行模式：Demo 使用确定性本地数据，API 只访问 FastAPI，不因网络错误混入本地数据。

仍属于发布前外部事项的内容：真实微信 AppID/AppSecret、教师 openid 白名单、HTTPS 合法域名、生产数据库/AI 网关、旧云数据库导入验数和仓库外医学专家签署。Demo 中的 `approved` 只是演示状态，不能作为医学审核签署。

## V3 审计矩阵

| ID         | 严重度 | 证据                                                                  | 状态              | 验证                                                                 |
| ---------- | ------ | --------------------------------------------------------------------- | ----------------- | -------------------------------------------------------------------- |
| V3-AUD-001 | P0     | `src/pages/student/case`、`backend/app/api/case_attempts.py`          | verified          | `npm run test:e2e`、后端病例测试                                     |
| V3-AUD-002 | P0     | `backend/app/services/case_training.py`、`case_ai.py`                 | verified          | `pytest tests/test_case_training.py tests/test_case_ai.py`           |
| V3-AUD-003 | P0     | `backend/app/api/medical_review.py`、`problems.py`                    | verified          | `tests/test_case_hardening.py`、`tests/test_second_phase.py`         |
| V3-AUD-004 | P0     | `case-edit.vue`、`review-list.vue`、`review-detail.vue`               | verified          | `npm run type-check`、前端测试                                       |
| V3-AUD-005 | P0     | `caseRepository.ts` Demo 状态机、`caseRepositoryAsync.ts` API adapter | verified          | `caseRepository.flow.spec.ts`、adapter spec                          |
| V3-AUD-006 | P0     | `backend/app/api/classes.py`、`services/access_control.py`            | verified          | `tests/test_second_phase.py`                                         |
| V3-AUD-007 | P0     | `backend/app/services/analytics.py`、教师分析页面                     | verified          | `tests/test_second_phase.py`、`test_analytics_performance.py`        |
| V3-AUD-008 | P0     | `20260823_0005`、`0006`、`0007`                                       | verified          | `tests/test_migrations.py`、`alembic upgrade head`                   |
| V3-AUD-009 | P1     | `backend/app/services/personalized.py`、学习计划页面                  | verified          | `tests/test_personalized.py`                                         |
| V3-AUD-010 | P1     | `backend/app/services/case_ai.py`、`medical_ai.py`                    | verified          | AI 重试、schema 校验、fallback 测试                                  |
| V3-AUD-011 | P1     | `backend/app/api/problems.py` 学生序列化                              | verified          | 病例隐私/定向发布测试，API 构建扫描                                  |
| V3-AUD-012 | P1     | CAP、急性胸痛、右下腹痛三套 seed                                      | verified          | `test_showcase_cases_have_distinct_target_facts_and_reference_paths` |
| V3-AUD-013 | P1     | repository、认证、报告、教师题目链路                                  | verified          | `npm run test:coverage`、后端全量测试                                |
| V3-AUD-014 | P1     | `docs/audit/initial-version-comparison.md`                            | verified          | 远程 commit tree 与功能逐项映射                                      |
| V3-AUD-015 | P1     | `src/pages/teacher/analytics/*`                                       | verified          | 总览/病例/学生下钻、日期和维度字段联调                               |
| V3-AUD-016 | P0     | 远程旧聊天页历史                                                      | accepted_external | 密钥撤销、账单/日志核查和历史清理需平台/仓库权限                     |

## 实际验证命令

```text
npm run check
npm run backend:check
npm run test:e2e
cd backend && python -m pytest tests/test_migrations.py -q
git diff --check
```

质量阈值：前端 branches ≥ 80%；后端 total ≥ 90%，关键模块由独立 API/服务测试覆盖。最终数值以本次命令输出为准，不能沿用历史审计数字。

## 安全边界

- 学生不接收 hidden facts、reference reasoning、private rubric、fixed facts、blueprint digest、作者/定向 ID 或能力标签。
- guided case 的发布必须经过作者提交、审核专家审批和当前 digest 校验；审核后内容变化会阻止发布。
- authoring、审核详情、班级和分析均按服务端身份及 owner 范围隔离；审核专家不自动获得班级数据。
- AI 凭据只从后端环境变量读取；客户端仅持有 API token，不包含模型 key 或 AppSecret。
- 旧远程历史发现硬编码模型 key，当前源码/构建产物已清除其使用路径，但历史仍属于泄露面，必须轮换而不是只删除文件。

# T06 安全、隐私与发布边界最终仓库侧交付

日期：2026-08-31。阶段：S3 仓库侧收尾。结论：**SEC-02～SEC-08 的本地可验证部分已复核；T06 及生产发布仍被 SEC-01、SEC-03 政策和 SEC-09 外部证据阻断。** 本文绝不代表凭据撤销、远程历史处理、生产发布、真实微信/AI 调用或医学审核已完成。

## 范围、基线与已有改动保护

- 起始 HEAD／目标 hash：`b96bab910dc5ee43410fa55c5b856cc4d3f3415d`（`chore: complete data layer and dependency hardening`）。本工作树开工时已存在大量前后端、契约、页面、迁移、计划文档的修改和未跟踪文件，且 `docs/update/README.md` 已删除；全部保留，未 reset、clean、恢复、提交、推送、合并或部署。
- 开工前 preimage SHA-256：`backend/app/core/config.py` `258ADF40BF8FA7F4BF73469BE8FE5D34ADEF6AA8EC75D7DFEF0ABC6D1575CDD8`；`backend/app/main.py` `F83FB52EEC93F9D9E446B4DE6D346AFE01115BFFD7498C535089C7287307EC90`；`scripts/security-secrets.mjs` `143922358C4C43FA3C1A06B9A3AB33455C0D563C766E008095E434F67AE429CB`；本交付和 `backend/tests/test_t06_security.py` 当时不存在。
- 本轮仅改动 T06 范围：生产环境归一化判定与 seed 防护、T06 秘密扫描器自测、T06 专属安全测试、本交付。未编辑 `package.json`、锁文件、CI、业务分层、迁移、OpenAPI 或权威 security/deployment/database/data-layer 文档。
- 公开 HTTP 合同、API/Demo 数据契约、报告可见范围、数据库 schema 和 Alembic 链均未改变；没有运行迁移、seed、真实 AI/微信或任何生产/共享数据库操作。

## 当前事实：仓库内安全矩阵

| 验收                     | 已核实的当前事实与仓库证据                                                                                                                                                                                                                                                                                                    | 状态                                                                                                                                              |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| SEC-01 历史凭据          | `--scope=history` 仍返回 3 条历史 `generic-api-key` 脱敏发现并退出 1；位置与既有 T06 记录一致，未读取匹配值。                                                                                                                                                                                                                 | **P0 阻断**：撤销/轮换及调用审计未知。                                                                                                            |
| SEC-02 秘密扫描          | 固定 Gitleaks v8.30.1、上游默认规则和精确项目赋值规则；没有路径/规则/历史 allowlist。自测同时验证合成泄露命中和短占位符不误报；工作树为 0。                                                                                                                                                                                   | 仓库侧通过；历史发现按 SEC-01 保留。                                                                                                              |
| SEC-03 角色、owner、范围 | 学生自有会话/报告与病例数据使用 actor/owner 查询；内容、班级、分析及审核入口有教师 owner/reviewer 边界。受管测试覆盖内容 owner、班级/分析 owner、跨学生报告和学生 DTO。                                                                                                                                                       | 部分通过；报告教师范围当前明确为 `submitted_global`，并非本人班级限制。产品负责人尚未决定收紧或批准共享审阅队列，故不能宣称跨教师报告隔离已满足。 |
| SEC-04 登录来源与角色    | 微信角色仅由服务端帐号/教师 openid allowlist 决定；请求 `requested_role` 不能把非白名单帐号变成教师。Demo 只在非生产且 `ENABLE_DEMO_AUTH=true` 时可用。                                                                                                                                                                       | 仓库侧通过；真实微信账号与平台证据见 SEC-09。                                                                                                     |
| SEC-05 DTO、缓存、日志   | 学生病例公开视图不返回 definition/facts/rubric，训练用例覆盖隐藏字段；API 缓存以身份 epoch 隔离、401/登出清空；业务 API 响应不写持久存储。AI audit 表仅有关联 ID、模型/版本、耗时、fallback/失败类别，无 prompt、学生答案或请求/响应列。浏览器 `console` 仅静态复核为错误处理调用，仍须由发布方核查浏览器/代理/遥测保留策略。 | 本地代码与负例通过；外部日志留存边界待 SEC-09。                                                                                                   |
| SEC-06 AI 与审核         | 外发调用不记录 prompt/response；失败分类、两次有界尝试和 deterministic fallback 已有用例；固定评分/evidence 限制、审核 digest 与内容变更失效由病例强化用例覆盖。AI 在本轮受管测试中禁用，未调用外部服务。                                                                                                                     | 仓库侧通过；供应商数据处理及医学签署待 SEC-09。                                                                                                   |
| SEC-07 生产配置与 seed   | 新增 `Settings.is_production` 的空白/大小写归一化，并让弱 JWT 检查和生命周期 seed 共用它；生产环境因此稳定禁用 demo 与 showcase seed。T06 负例覆盖 `" Production "`。CORS、HTTPS、受管数据库和运行时环境变量仍必须由发布环境验证。                                                                                            | 仓库侧通过；平台配置待 SEC-09。                                                                                                                   |
| SEC-08 依赖与构建物      | npm 生产/全量审计均无 high/critical；Python audit 无已知漏洞。H5 与 mp-weixin 实际构建目录均用扫描器复核为 0。                                                                                                                                                                                                                | 本地通过；low/moderate 依赖风险按既有升级批次跟踪，不以 allowlist 隐藏。                                                                          |
| SEC-09 平台/医学事项     | 未访问外部平台、真实账号、生产数据库、模型或微信；未取得合法域名、HTTPS/CORS、备份恢复、AI 数据处理或医学审核签署证据。                                                                                                                                                                                                       | **P0 发布阻断**。                                                                                                                                 |

## 本轮加固与测试

1. `backend/app/core/config.py` 统一定义归一化生产态；`backend/app/main.py` 用它验证 JWT 和决定是否 seed，消除 `APP_ENV` 大小写/空白可让生产态错误 seed 的配置边界。
2. `backend/tests/test_t06_security.py` 新增 SEC-07 生产 Demo/seed 负例，以及 SEC-05/06 AI 审计列白名单断言。
3. `scripts/security-secrets.mjs --self-test` 现在同时证明合成秘密被命中、短占位符未命中；扫描输出仍限于规则、脱敏位置/指纹、计数和退出码。

| 命令                                                                                                                                                                   | 结果                                                                                                             |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `python .agents/skills/wx-engineering-standards/scripts/self_check.py`                                                                                                 | 0；项目规范结构/链接/状态标签通过。                                                                              |
| `node --check scripts/security-secrets.mjs`                                                                                                                            | 0。                                                                                                              |
| `node scripts/security-secrets.mjs --self-test`                                                                                                                        | 0；`findings=1`（合成样本，未输出值）。                                                                          |
| `node scripts/security-secrets.mjs --scope=worktree`                                                                                                                   | 0；`findings=0`。                                                                                                |
| `node scripts/security-secrets.mjs --scope=history`                                                                                                                    | **1**；3 条历史脱敏发现，未伪造绿色。                                                                            |
| `npm run build:mp-weixin`、`npm run build:h5` 后的 `--scope=build`                                                                                                     | H5、mp-weixin 各 0；`findings=0`。构建过程有第三方 Zod 纯注释转换提示，未影响产物扫描。                          |
| `python -m pytest ...test_t06_security/test_auth/test_case_training/test_case_hardening/test_data_layer/test_content_draft_generation/test_case_ai/test_medical_ai -q` | 0；32 passed。                                                                                                   |
| `python -m pytest backend/tests/test_second_phase.py backend/tests/test_access_control.py -q`                                                                          | 0；7 passed。                                                                                                    |
| `python -m ruff check backend/app/core/config.py backend/app/main.py backend/tests/test_t06_security.py`                                                               | 0。                                                                                                              |
| `npm run backend:test:safety`                                                                                                                                          | 0；14 passed，在 T01 受管随机临时 SQLite 中运行，未接触开发/共享数据库；仅见既有 SQLite 外键 drop 排序 warning。 |
| `npm run audit:prod` / `npm run audit:all`                                                                                                                             | 各 0；分别 18 / 22 项 low/moderate，high/critical 均为 0，无 advisory allowlist。                                |
| `npm run backend:audit`                                                                                                                                                | 0；`No known vulnerabilities found`。本机 pip-audit 缓存写入失败只影响性能，不影响结果。                         |

所有后端 pytest 仍报告既有 SQLite 循环外键 drop 排序 warning；没有吞错、关闭权限、放宽门槛或修改测试隔离。`npm ci --legacy-peer-deps` 仅按已有锁文件安装本地构建依赖，未改动依赖清单或锁文件。

## R1-05 文档返修与统筹复验边界

- 本节是 2026-08-31 的限定文档返修：只格式化并补足交付证据边界，未修改本轮 T06 的四个代码/测试/扫描器文件，也没有重新运行数据库、E2E、构建、网络扫描或依赖审计。
- 统筹在主工作区的只读审核报告为 `D:/CODE/weixin/wxprogrom7.15/docs/update_plan/deliveries/S3-review-01.md`。该报告独立记录：29 项 T06 安全相关测试、扫描自测、工作树扫描及两个**现存** H5/微信构建目录扫描均退出 0；它明确说明本次没有重新构建、没有重新运行 history 扫描或依赖审计。
- 上述统筹结果是外部复验证据，不是本候选工作树本轮执行的命令，也不替代前表中本候选先前已执行的检查。它不构成生产发布批准，且不改变 SEC-01、SEC-03 与 SEC-09 的阻断状态。
- 本轮最终文档检查在最后一次内容修改后执行：`npx prettier --check docs/update_plan/deliveries/T06-final.md`、相对链接/路径核对和 `git diff --check -- docs/update_plan/deliveries/T06-final.md`。各退出码与最终 SHA-256 记录在本轮系统临时 manifest 中，避免把格式检查替换为 `git diff --check`。

## 外部移交与解除条件

| 阻断/负责人                  | 需要的脱敏证据与解除条件                                                                                                                                                         |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SEC-01 凭据平台管理员        | 依据既有三条脱敏位置/指纹定位历史凭据，撤销/轮换、检查调用账单及访问日志；仅返回工单号、时间、状态和脱敏关联信息。不能提供即保持阻断。                                           |
| SEC-03 产品负责人 + T04/T05  | 明确教师报告是本人班级范围还是批准的全局提交审阅队列；若收紧，实施服务端范围过滤并用两教师列表/摘要/详情/by-conversation/review 负例复验。当前 `submitted_global` 不作自行修改。 |
| SEC-09 发布/平台管理员       | 在批准环境核验强 JWT、Demo off、seed off、HTTPS/CORS、微信合法域名、受管数据库及备份恢复；返回脱敏状态和证据链接。不得在此工作树直接执行迁移或 seed。                            |
| SEC-06/09 供应商与医学负责人 | 提供 AI 数据处理/保留边界和医学内容审核签署证据；真实微信/AI 集成仅用批准测试帐号和环境单独验证。                                                                                |
| T02                          | 将扫描自测、工作树/历史扫描和双端构建物扫描接入 CI；历史非零不得被忽略或上传原始扫描 JSON。                                                                                      |

## 回退

回退前先核对上述 HEAD 和 preimage。由于三个既有文件在本轮开始前已含 S2 未提交改动，只能精确反转本轮 hunks：移除 `Settings.is_production`，恢复其两个调用点的原内联表达式，移除 `should_seed_showcase`，以及移除扫描自测的 `placeholder.env` 和对应断言；确认未被后续任务接管后删除 `backend/tests/test_t06_security.py` 与本交付。不得整文件恢复、reset、clean、目录覆盖、恢复 `docs/update/README.md`、迁移 downgrade 或恢复任何历史凭据。安全回退不得重新允许生产 Demo、seed 或弱 JWT；若无法保持这些边界，应暂停受影响发布。

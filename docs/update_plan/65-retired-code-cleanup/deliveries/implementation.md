# T65 审计与交付

2026-10-03实施，2026-10-04收尾。S0–S3工程收尾，已核实的旧业务实现与无引用文件已清理；一处备份临时目录删除受命令策略阻塞。仅处理本轮增量，不改暂存区，不提交或推送。

## 清理判断与实际结果

| 范围         | 处理与依据                                                                                                                                                                                                                                                                   |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 页面与路径   | 47个注册页面全部存在，源页面全部已注册，没有孤儿页面。旧知识卡、审核及历史报告等页面承担授权检查/兼容跳转，保留注册及防复活测试。删除9个零调用教师路由常量，注册测试仍严格验证活动路径与9个显式兼容路径的并集。                                                              |
| UI组件       | 删除5个无生产引用组件：PageContextBar、ChatWelcome、PblStatusDistribution、PblReportSectionHeading、PblRecurringTargets。只删除混合spec中的对应用例，保留仍使用的组件验证；剩余组件未发现无名称引用者。                                                                      |
| 微信工具     | 删除23个旧automator/历史取证脚本、13个已停用npm入口、停用提示器和旧automator开发依赖。保留doctor、check-wxss与官方wechatide CLI。锁文件减少33个依赖条目，未升级现存包；ws仍被当前uni/happy-dom使用，保留其覆盖版本。                                                         |
| 静态资源     | 删除18份无引用的旧工具、导航、审核插画和hospital图片。核对MedIcon动态name联合类型后保留当前图标；活动静态资源引用均存在。                                                                                                                                                    |
| 前端业务     | 移除知识卡贡献与独立复习/ExitQuiz的public、private port、API/Demo实现和专属DTO，删除2个仅覆盖旧复习API的spec，混合spec保留题库来源、操作摘要、独立病例与兼容跳转检查。API知识图谱状态映射保留；Demo旧复习数组原本为空且无持久化读写，图谱继续返回not_started并校验学生身份。 |
| 后端内容     | 移除不可达的病例克隆/发布/拒绝/旧审核写入仓储、教师卡CRUD/列表/审核仓储、配套port及无人调用的校验helper。保留历史审核读取、教师操作计数、病例回答计数、知识目录读取和历史知识卡所有权检查。旧发布成功测试改为验证409 RETIRED_FLOW及历史状态不变。                            |
| 后端独立复习 | KnowledgeReviewApplication只保留当前knowledge_map。删除组题、判题、评分、到期排程、证据写入等死实现及专属DTO/转换器；仓储仅保留历史state/item读取，图谱历史状态与模型/表不变。旧成功路径用例删除，图谱weak状态测试直接种隔离历史fixture，不再调用已退役capture。             |
| 后端讨论     | 删除SqlAlchemyQuestionRepository文件、QuestionRepository port及QuestionsApplication无用repo/uow注入，同步factory与4处直接调用。兼容HTTP仍执行学生授权并空读/404/409；现有对话、AI助手、历史模型与回答计数不变。                                                              |

合计删除49个源码/脚本/资源/测试文件（首批46个、2个旧spec、1个旧讨论仓储），另精简前后端混合文件中的死实现。完整清单见[删除与快照审计](../../../../output/t65/cleanup-audit.json)、[路径审计](../../../../output/t65/path-audit.json)、[依赖锁差异](../../../../output/t65/lockfile-diff.json)。

有意保留的部分：旧页面及HTTP兼容拒绝边界、前端QA/病例生命周期兼容facade及防复活测试；题库DELETE内部复用archive存储操作，历史归档读取与API仍有消费者，不能整体删除。相关前端零页面调用facade未在本批扩删，具体分类见[消费者记录](../../../../output/t65/frontend-checks.md)。本次结论限于已核实的清理范围，不宣称仓库完全没有兼容代码。

## 验证

| 命令或范围                         | 结果与证据                                                                                                                                                                                                                                                                       |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 首批4个组件/导航spec               | exit 0，29 tests；[日志](../../../../output/t65/root-targeted-tests.log)                                                                                                                                                                                                         |
| 前端6个受影响spec、类型            | exit 0，21 tests；后续完整集成覆盖该范围                                                                                                                                                                                                                                         |
| `npm test`                         | 首次exit 1：616/619通过，2个超时及后续存储spy失败；[原日志](../../../../output/t65/frontend-vitest.log)保留。失败两文件单worker复查4项通过，未修改测试；全量`npm test -- --maxWorkers=2` exit 0，112 files / 619 tests；[复验](../../../../output/t65/frontend-vitest-retry.log) |
| 首批后端定向pytest                 | exit 0，37 tests；准确命令、Ruff及边界见[记录](../../../../output/t65/backend-checks.md)                                                                                                                                                                                         |
| 后端复习/图谱/证据定向pytest       | exit 0，30 tests；同上第二批记录。历史图谱状态、退役拒绝和当前证据消费通过；测试fixture teardown保留既有FK循环排序警告                                                                                                                                                           |
| 后端讨论及相邻API/历史数据pytest   | exit 0，28 tests；[QA检查](../../../../output/t65/qa-checks.md)、[日志](../../../../output/t65/qa-pytest.log)。Ruff及9模块后端边界通过                                                                                                                                           |
| `npm run contract:check`           | exit 0；[日志](../../../../output/t65/contract-check.log)。隔离临时库导出并比对，现有OpenAPI、生成类型、病例fixture与知识目录一致，未写源码合同                                                                                                                                  |
| 显式Demo `npm run build:mp-weixin` | exit 0；[日志](../../../../output/t65/demo-build.log)。产物目录文件合计2,651,159 bytes（2.528 MiB），不是微信服务端上传包计费量                                                                                                                                                  |
| 原生WXSS/WXML                      | exit 0，生产70份WXSS、80份WXML；[样式](../../../../output/t65/native-wxss.log)、[模板](../../../../output/t65/native-wxml.log)                                                                                                                                                   |

首批运行检查没有降低测试超时或断言标准；低并发复验通过支持首次失败来自资源争用/超时后异步串扰的判断，但不能仅凭此日志确定唯一根因。本轮无页面布局与交互行为调整，复用T64 S7当前手机布局及S6已确认入口证据，未重新宣称全部真实点击或API联调通过。前端类型、边界与本批Lint/格式通过，准确命令见[前端记录](../../../../output/t65/frontend-checks.md)。后端三组分别37、30、28项通过，存在重叠用例，不相加声称95个独立测试或全量后端通过；完整后端未重跑。最终文档格式、引用和增量空白检查见[收尾检查](../../../../output/t65/final-checks.md)。

## 工作保护、归档与未验项

修改前记录[git状态](../../../../output/t65/initial-status.txt)，以当前工作树原文创建[首批ZIP](../../../../output/t65/cleanup-before.zip)、[前端API ZIP](../../../../output/t65/frontend-api-before.zip)、[后端内容ZIP](../../../../output/t65/backend-content-before.zip)、[后端复习ZIP](../../../../output/t65/backend-learning-before.zip)、[QA ZIP](../../../../output/t65/qa-retirement-before.zip)，逐文件字节数和SHA256已核验。回退按单文件增量恢复，不用HEAD覆盖此前未提交修改；完整待删列表及修改前版本由manifest定位。

T63已归档至[索引](../../../archive/update-plan-t63-20261003.md)及ZIP，3份原文逐文件hash核验；现行只保留T64、T65。人工待验仍在[台账](../../../manual-acceptance.md)，归档不免除历史待验。

没有迁移、seed或清理真实数据库，没有删除历史模型/迁移，没有手改生成合同。真实API/AI、生产、真机和旧人工待验不属于本轮新增通过证据。

临时快照staging目录`output/t65/.frontend-api-before-stage`的删除被命令策略拦截，暂保留；已完成核验的ZIP/manifest足以定位原文，该目录不进入小程序产物。收尾需在允许文件删除的环境清理它。

# 数据库、迁移与恢复

开发与受管测试使用SQLite，PostgreSQL尚未完成生产兼容验证。迁移head以Alembic revision为准；执行前查询目标库版本，代码head不证明已apply。

## 所有权与安全

`backend/data/dev.db`是忽略入库的开发数据。pytest须在应用导入前绑定launcher-owned随机临时SQLite，清表前验证规范路径、marker、token、文件及链接边界；不能绕过fixture对未知engine执行create_all/drop_all。测试隔离、迁移和启动脚本变化按[开发](development.md#按改动选择验证)先检查。

实际迁移、seed、回填或清理须确认受管非生产目标、关联清单、新备份和可执行恢复步骤。共享/生产库不作试验；迁移与业务清理分开。模型/表字段以canonical ORM和Alembic为准。

## 数据保留与降级限制

迁移中拒绝downgrade是数据保护，不能先清表绕过。以下列出重要不可逆条件，完整逻辑仍须阅读目标revision：

| Revision后缀 | 必须保留的限制                                                                                                  |
| ------------ | --------------------------------------------------------------------------------------------------------------- |
| 0018/0019    | schema v3快照、第二轮数据或评价记录存在时拒绝对应降级                                                           |
| 0020         | 自主会话或非默认回应方式存在时拒绝                                                                              |
| 0023/0024    | 已有反馈或报告class_id时拒绝                                                                                    |
| 0025         | 任意学习证据事件/指标存在时拒绝，不得删除证据换取downgrade                                                      |
| 0026         | 消息/快照方式混合或与参与记录不一致时拒绝                                                                       |
| 0027         | upgrade无法证明完成边界时失败；私人消息/结果及完成定位存在时拒绝downgrade                                       |
| 0028         | 仅原始、未修改/审核的v4目录可降级；缺失/多个active、悬空、无来源或循环图显式失败                                |
| 0029         | 正式计划持久化至少两个学习目标，不能靠旧静态目标恢复                                                            |
| 0030         | 任意带source_type的AI知识卡存在时拒绝降级                                                                       |
| 0031/0032    | 任务包/教师题库来源外键及唯一状态约束不能丢失；软排除保留RESTRICT来源外键，存在included=false项目时0032拒绝降级 |
| 0035         | 已进入总结反思的病例或已写入反思阶段决策时拒绝降级；不删除会话、消息或阶段决策换取降级                          |
| 0036         | 已有混合题测试、待判分答卷或结果导学对话时拒绝降级；不能删除学生答案或消息换取降级                              |

新路线、步骤、病例会话、测试、答卷、结果及命令receipt使用内部整数主键与外部UUID。0033冻结12张路线业务表的SQLite/PostgreSQL DDL，增加通知UUID定位及题库来源脱钩字段；冻结DDL不等同于PostgreSQL已验收。0034在旧闭包清空且cutover记录匹配后删除12张退役表及旧候选任务列，线上PBL约束收窄为schema v8。有新路线/结果时降级拒绝，不删除新数据换取降级。

运行时metadata不应重建退役表；0001固定历史pilot表集合，后续PBL及新路线表由对应revision创建。新源码head与实际目标库版本分别核验，不在未知开发库自动apply。

seed与迁移不赋予专家审核状态，审核合同见[安全](security.md#ai与医学审核)。

## 回填与转换

脚本默认dry-run；apply前必须阅读脚本参数及对应计划，不把seed当测试隔离。`seed_test_data.py`会先应用迁移，仅受管非生产使用。T44切换步骤见[迁移与数据清理](archive/update-plans-t44-t61-20261003.md#file-d14615b9eadb4d05)。

`backfill_report_class_scope.py`只接纳可唯一证明的班级归属：已有class_id/草稿跳过，教师拥有班级及唯一成员证据不足时不猜测。`backfill_learning_evidence.py`仅回填正式合格证据，不纳入自主/私人内容或退役问答报告分数。旧PBL评价回填不再执行。

`transition_pbl_t14.py`、`backfill_pbl_evaluations.py`和`rebuild_t43_reports.py`只返回RETIRED_FLOW，不打开数据库。`cleanup_t44_learning.py`默认dry-run，受管目标、marker/token、当前版本、闭包manifest及新备份匹配后才允许apply；中途失败整笔回滚。先0033解除题库旧外键，再清理固定旧闭包，再0034删除旧表；账号、班级、知识目录、独立病例和题库内容/版本完整保留。清理脚本是本次证据删除例外，不开放运行时append-only DELETE。

知识库转换及恢复演练使用副本和精确seed编码，不按关键词误删独立资源。

清理前核对来源外键和保留资源清单，不能误删独立资源；具体清理范围、顺序和验证按对应计划执行。

## T64 独立病例训练快照

`20261003_0037`为case_attempts增加nullable problem_snapshot JSON，仅内部训练使用，不进入学生DTO。新attempt创建时冻结definition/rubric及必要病例元数据；既有attempt在教师首次编辑/删除资源前补冻结，不改problem_id或历史答案。病例deleted与题库archived为内部删除标记，活动读取隐藏，历史引用保留。downgrade检测到非空快照时在DDL前拒绝，保留快照、列和迁移版本；SQL NULL及JSON null均视为空。受管fixture验证迁移往返和快照保护；未在本轮迁移真实API数据库，部署前按实际目标备份、版本和迁移检查执行。

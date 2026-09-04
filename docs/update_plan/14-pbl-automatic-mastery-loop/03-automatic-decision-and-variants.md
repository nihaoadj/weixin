# 自动判定与变式策略

## 判定政策

政策版本固定记录为 `pbl-mastery-v1`，采用逐项达标：

- 正式讨论任务必须完成，但不参与分数判定。
- 每个知识薄弱点的再测必须有成绩且得分为 100。
- 每个推理微训练必须有成绩且得分至少 70。
- 若有病例重练，每个目标推理维度必须有成绩且至少 70；总分高不能覆盖目标维度失败。
- 任一必需成绩、提交证据或目标映射缺失时失败关闭，不得判定 improved。

判定结果和逐项目标依据写入 `decision_basis`，只记录计划 ID、政策版本、轮次、结果、阈值和失败目标编码；不得记录答案、rubric、完整学生回答或模型提示。

## 两轮策略

- 采用发布时在同一事务预创建 cycle 1 与 cycle 2 任务；cycle 2 初始为 inactive。
- cycle 1 全部达标：计划完成，`verification_status=improved`。
- cycle 1 未达标：`current_cycle=2`，只激活失败目标的 cycle 2 任务；无关任务标记 skipped。
- cycle 2 全部达标：计划完成并标记 improved。
- cycle 2 仍失败或证据缺失：计划完成，标记 `needs_reinforcement` 和 `automation_exhausted=true`，提示线下支持。
- 重复提交、病例回调或通知请求不得重复激活任务、重复评估或重复通知。

## 目录与变式

目录升级为 `pathology-general-v3`：

- 既有 practice/retest 编码保留为 cycle 1 兼容资源。
- 每个知识点增加 `.practice.v2` 与 `.retest.v2` 等价变式。
- 每个病例推理维度增加明确的 cycle 2 微训练提示和 variant code。
- cycle 2 不得复用 cycle 1 的卡片或微训练 variant code。
- 教师采用发布前校验所有相关目标的两轮资源均已审核；缺失时整个事务失败。

第二轮只改变表面材料、提问顺序或病例线索表达，不改变知识目标、评分阈值和安全边界。

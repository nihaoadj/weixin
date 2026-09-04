# API 与数据设计

## 数据库 0018

`pbl_participations` 增加 `current_phase`、`phase_started_revision`、`phase_status`、`phase_completed_at`。

`pbl_inference_snapshots` 增加 `phase`、`phase_decision`、`phase_evidence_message_ids`、`phase_evidence_summary`、`phase_missing_elements`。

`learning_plans` 增加 `current_cycle`、`max_cycles`、`automation_exhausted`、`decision_policy_version`、`decision_basis`、`evaluated_at`。保留历史 `verification_status`、`verified_by`、`verified_at`；新记录的结果只由系统写入。

`learning_tasks` 增加 `cycle_number`、`target_type`、`target_code`、`variant_code`，状态增加 inactive/skipped。

## AI schema v3

请求包含 participation 当前阶段和阶段开始 revision。响应增加：

```json
{
  "schema_version": 3,
  "phase_assessment": {
    "phase": "problem_framing",
    "decision": "continue",
    "evidence_message_ids": ["message-id"],
    "evidence_summary": "学生已表达主要问题，但缺少关键背景。",
    "missing_elements": ["补充病例背景"]
  }
}
```

Coze Bot、Workflow、开发专用 OpenAI-compatible 和 Demo Mock 必须共享该运行时 schema；provider 不允许自动 fallback。

## API 合同

- 学生课堂及消息响应增加个人阶段、阶段状态、缺失要素和完成锁定信息。
- 教师课堂响应增加各阶段人数分布。
- 学习计划响应增加轮次、政策版本、自动判定依据、耗尽状态和任务变式信息。
- 学生 DTO 只暴露阈值结果和目标编码，不暴露答案、rubric、隐藏病例事实或教师内部字段。
- 教师结果查询保留为只读。
- 原课堂阶段 PATCH 与教师 verify POST 标记 deprecated，固定返回 `STATE_CONFLICT`，不得改变数据。

## 历史转换

提供独立脚本，默认 dry-run：

- 已有 ready v2 participation 转换为 synthesis/completed；其他历史 participation 从 problem_framing 重新开始，证据窗口从当前 revision 起算。
- 已有人工 improved/needs_reinforcement 原样保留，在 decision basis 标记 legacy teacher。
- pending_teacher 使用同一政策重算；失败时在 apply 模式补建并激活第二轮变式任务。

脚本不得自动指向未知、共享或生产数据库。0018 downgrade 只有不存在 schema v3 阶段记录和 cycle 2 任务时才允许；否则明确拒绝并要求从已验证备份恢复。

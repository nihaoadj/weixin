# 产品状态机

## 参与级阶段

每个学生参与记录独立维护：

`problem_framing → hypothesis → evidence → synthesis → completed`

阶段目标固定如下：

| 阶段            | 目标                               | 允许结果            |
| --------------- | ---------------------------------- | ------------------- |
| problem_framing | 形成清晰的问题表征                 | continue / advance  |
| hypothesis      | 至少提出一个机制假设并说明不确定性 | continue / advance  |
| evidence        | 用病例证据支持或反驳假设并指出限制 | continue / advance  |
| synthesis       | 整合机制、证据与剩余疑问           | continue / complete |
| completed       | 锁定的完成态                       | 返回既有结果        |

## 推进约束

- AI 返回当前阶段、决策、证据消息 ID、证据摘要和缺失要素；服务端是最终状态机裁决者。
- `advance` 只能从前三阶段推进一个相邻阶段；`complete` 只能从 synthesis 进入 completed。
- 阶段证据必须是当前 participation、当前阶段开始 revision 之后的学生消息；旧阶段或教师/AI 消息不得复用。
- AI 输出无效、越级、无证据或提供方不可用时统一标记 `unavailable`，不推进阶段、不生成诊断。
- `ready` 只能与 synthesis 的合法 complete 同时出现；此前只能继续追问。
- completed 后禁止创建新消息；使用相同 message ID 的重试返回既有结果，不产生新快照或推进。

## 展示规则

- 学生只看到自己的阶段、状态、缺失要素与阶段进度。
- 教师课堂列表展示各阶段人数分布，不提供阶段写入口。
- 课堂级历史 `phase` 字段仅为兼容，不再驱动新流程。

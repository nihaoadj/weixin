# 验证与回退

## 仓库内验收

- `python backend/scripts/check_boundaries.py --self-test` 和正式边界检查均退出 0。
- Coze Bot/Workflow SDK 边界 fixture 覆盖成功、conversation 续用、完成、interrupt、超时、限流、异常、空内容、坏 JSON 和 schema 错误；普通 API 覆盖成功与所有受控失败；三 adapter 等价。
- PBL 用例覆盖 probing/ready、学生字段隔离、跨班/跨教师/退班/关闭课堂、重复 `client_message_id`、revision 竞争、suggestion supersede、编辑保护和采用幂等。
- 0015/0016 在 T01 临时库完成 upgrade/downgrade、JSON 历史 backfill、消息唯一约束、索引和数据保留验证；不得对开发或生产库试跑。
- 运行契约生成/只读检查、前后端格式/Lint/类型/边界、完整后端测试、相关前端测试、微信/H5 构建及本地 Mock E2E，并记录退出码。

本地 Mock E2E 固定流程：教师创建课堂 → 学生进入并发送重复 client ID → probing → 后续 ready → 双方看到同一薄弱分析 → 学生响应不含建议题 → 教师编辑并采用 → 重复采用返回同一 `problem_id` → 目标班级学生看到正式题。

## 完成声明

以上仓库检查全部通过后，只能标记“仓库内完成、真实 Coze 外部联调未验证”。真实 Coze 需要受管资源、最小权限 token、数据处理审批和独立联调证据。

## 回退

以 `PBL_AI_ENABLED=false` 停止新推理，不切换普通 API。已生成诊断保持只读，已发布题由 content 继续管理。数据 downgrade 前导出新增记录并确认 `problem_origins` 和正式题来源影响。

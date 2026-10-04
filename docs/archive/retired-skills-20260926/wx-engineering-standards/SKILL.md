---
name: wx-engineering-standards
description: Route code or engineering-rule changes in this repository to the applicable contracts and checks.
---

# WX Engineering Standards

Locate the relevant heading/keyword; read only that section and reuse unchanged context. Do not follow every link.

- Classify changes under [development](../../../docs/development.md#更新分流): functional changes require a plan before code; ordinary maintenance does not. Select checks under [verification](../../../docs/development.md#按改动选择验证).
- Read [product](../../../docs/product.md) for business changes; [plans/evidence](../../../docs/update_plan/README.md) when resuming work. Distinguish 当前事实 from 计划目标.
- Module/data changes use [architecture](../../../docs/architecture.md); R05 boundaries are checked by `node scripts/frontend-boundaries.mjs` and `python backend/scripts/check_boundaries.py`.
- Database changes use [database](../../../docs/database.md); authorization, AI or sensitive data use [security](../../../docs/security.md).
- Demo-visible runtime changes require [WeChat validation](../../../docs/wechat.md), including direct maintenance. UI methods use [wx-frontend-ui](../wx-frontend-ui/SKILL.md).

For substantial deliveries, use [the template](references/delivery-template.md). Project skill maintenance runs `python .agents/skills/wx-engineering-standards/scripts/self_check.py` and the same command with `--self-test`; these do not validate runtime behavior.

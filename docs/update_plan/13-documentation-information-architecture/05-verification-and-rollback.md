# 验证与回退

## 验收矩阵

| 范围       | 验收证据                                                                                     |
| ---------- | -------------------------------------------------------------------------------------------- |
| 文档分组   | 根入口、各二级入口和计划索引均能说明当前与阶段资料                                           |
| 计划一致性 | T01–T07 与 T08–T13 均使用独立目录，任务书与交付证据同目录保存                                |
| 链接       | 当前与阶段资料中的相对 Markdown 文档链接目标存在；旧路径搜索无遗漏的活跃引用                 |
| 格式       | T13 与受影响 Markdown 通过 Prettier、无尾随空白、`git diff --check` 通过                     |
| 工程规则   | `wx-engineering-standards` self-check 通过；不运行与纯文档无关的数据库、构建、E2E 或 AI 检查 |

## 检查命令

```bash
python .agents/skills/wx-engineering-standards/scripts/self_check.py
npx prettier --check <affected-markdown-files>
<relative-markdown-link-check>
rg -n "[ \t]+$" <affected-markdown-files>
git diff --check
```

## 回退

本轮没有数据或运行时代码变更。回退时使用 `git mv` 将所有移动文件回到本轮前位置，并恢复 `docs/README.md`、`docs/update_plan/README.md`、`AGENTS.md`、ADR 与 Markdown 链接；不得使用 `git reset`、`git clean` 或覆盖既有工作区改动。

## 外部阻塞

仓库外书签、已发布文档站点和第三方链接不在本地扫描范围。阶段交付里当时的源码快照、构建截图或临时证据链接可能已不再存在，保留原文但不纳入当前导航验证。若后续发现外部引用旧路径，应以独立兼容通知处理，不以仓内链接通过代替外部验证。

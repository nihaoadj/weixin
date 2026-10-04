# T65 收尾检查

2026-10-04。前端完整回归、后端三组定向、契约与构建检查见各自日志；本文件记录最终文档与增量一致性检查。

| 检查               | 命令/范围                                                                                                    | 退出码与证据                                                               |
| ------------------ | ------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------- |
| 文档引用与计划保留 | 本轮文档相对链接存在性扫描，检查计划目录                                                                     | 0；172个本地链接无缺失，仅64/65两份计划目录，[结果](final-link-check.json) |
| 增量空白           | `git diff --check -- <cleanup-audit.json中的路径及本轮文档>`，另加`--cached`检查索引范围                     | 均0；[结果](final-diff-check.json)                                         |
| 格式               | `npx prettier --check`：本轮root修改的5份源码/spec、package/lock及文档；代理14份源码检查见frontend-checks.md | 修正QA交付md表格格式后0；[日志](final-prettier.log)                        |
| root源码Lint       | `npx eslint`：UI/chat/PBL混合spec及导航index/spec，`--max-warnings=0`                                        | 0；[日志](root-lint.log)                                                   |
| 对外合同           | `npm run contract:check`                                                                                     | 0；[日志](contract-check.log)，隔离临时导出/比对，不改生成源码             |
| 归档与快照         | 逐文件字节数和SHA256核对各manifest；QA归档34项，清理汇总88个原文记录                                         | 0；[清理汇总](cleanup-audit.json)、[QA核验](qa-checks.md)                  |

前端619/619通过；后端三个定向批次37/30/28项通过，含重叠，未宣称全量后端通过。首次前端超时、QA文档格式失败及修正记录保留。既有SQLite fixture清理警告不作为真实数据库缺陷结论。未提交或推送。

命令策略拒绝删除`output/t65/.frontend-api-before-stage`，该冗余备份临时目录仍存在，不进入小程序产物；ZIP/manifest核验与源码清理已完成。未绕过该限制。

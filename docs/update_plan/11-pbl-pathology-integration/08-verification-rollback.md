# 验收与回退

## 待实现验收矩阵

| ID  | 必须验证                                                                        |
| --- | ------------------------------------------------------------------------------- |
| K01 | 5 主题/30 点/60 客观题/30 recall/5 病例；编码唯一、前置无环、资源绑定、目录漂移 |
| K02 | 旧编码不能新增；未提交客观题答案保密；recall 自评不计客观正确率                 |
| D01 | 空库、0007、0016 升级与 downgrade；受管副本备份恢复和转换幂等                   |
| D02 | 账号/班级/PBL/非示例原文保护；旧成绩不映射；Demo/API 隔离                       |
| P01 | 建课必须审核病例与正确知识点；阶段版本冲突；关闭历史只读                        |
| P02 | 多轮 probing/ready、证据归属、无效输出、稳定请求结果、并发 CAS                  |
| P03 | 跨教师/班级/学生拒绝；分页筛选、最新诊断、旧 revision 可追溯                    |
| P04 | 未保存文案采用生效；重复采用/提交不重复题目/任务/调度                           |
| L01 | 定向任务、复习、微训练、再测、教师核验及课堂统计                                |
| A01 | 真实 DeepSeek 合成联调；Coze 只 Mock；超时/限流/鉴权/坏合同显式失败             |
| S01 | .env 忽略且未跟踪；密钥/敏感字段负向扫描；自动化不读本地凭据                    |
| U01 | 新首页/旧路由兼容；空/失败/冲突/键盘；320/768/1024/1440；H5/微信构建            |

## 命令路由

计划门禁：prettier --check 本目录、相对链接/尾随空白检查、python .agents/skills/wx-engineering-standards/scripts/self_check.py。

修改测试启动或迁移后先 npm run backend:test:safety 和 npm run backend:test:migrations。实施按风险执行 npm run type-check、npm run lint、npm run test、npm run backend:check、node scripts/frontend-boundaries.mjs、python backend/scripts/check_boundaries.py。合同更新执行 npm run contract:generate 与 npm run contract:check。最终 npm run build:h5、npm run build:mp-weixin、npm run test:e2e、npm run test:e2e:demo；相关 coverage 门禁不降低。

## 外部阻塞与回退

真实 Coze、生产、微信真机、医学专家审核不计入仓库内完成。DeepSeek 结果单独记录，不用 Mock 冒充。失败时停止新增推理、发布和任务；应用/schema 回退仅针对本轮；删除数据使用已验证备份恢复。已有未提交改动不 reset/clean/restore。

# 依赖安全基线

## 病例训练数据隔离

学生病例接口使用显式响应结构：隐藏事实、参考推理、评分 criteria 和 `revealed_fact_ids` 均不会返回。attempt、提交和 assessment 始终按 `student_id` 查询；教师 authoring 接口要求教师角色。AI 审计日志只记录调用元数据，不记录密钥、完整 prompt 或学生完整回答。

## 当前策略

CI 使用 `audit-ci` 阻止新出现的高危和严重生产依赖漏洞。`audit-ci.json` 中的条目是当前 DCloud/uni-app 构建链无法单独升级消除的临时例外，不代表漏洞已被忽略。

当前客户端不处理真实患者身份数据，不加载不受信任的 ZIP/JPEG 文件，也不向用户暴露 Vite 开发服务器。生产部署只发布构建后的静态资源与微信小程序包。

## 凭据泄露处置

远程仓库初始提交 `2a9ad32` 的旧版聊天页曾把一个看似真实的模型 API key 写入客户端源码（TypeScript 和生成的 JavaScript 各一处）。重构后的工作树已不再包含该值，但 Git 历史仍可读取，因此该 key 必须按已泄露处理：立即在对应模型平台撤销/轮换，并检查调用账单和访问日志。历史清理需要另行评估远程仓库协作者影响，不能仅靠删除当前文件视为完成。

旧版同时暴露了 AppID 和云环境 ID；这些是项目标识，不等同于 AppSecret，但仍应核对云数据库权限和合法域名。当前实现不再把模型密钥放在小程序端，微信 AppSecret 仅由后端环境变量读取。

## 临时例外

- 例外仅限 `audit-ci.json` 中列出的 advisory。
- 每次升级整组 DCloud 依赖后重新运行 `npm audit --omit=dev` 并删除已修复条目。
- 下次强制复查日期：2026-09-20。
- 如任一例外进入实际运行时攻击面，必须停止发布，不能继续依赖白名单。

# 第二阶段安全边界

- permissions 由服务端 seed/allowlist 决定，LoginRequest 不接受客户端权限；`demo_reviewer` 才有 `medical_review`。
- 班级、审核和分析接口按教师 owner 隔离，跨范围统一 404；审核专家不会自动获得班级分析数据。
- 学生响应仍不包含 hidden facts/reference/rubric；分析只读取结构化 CaseAssessment，不读取自由问答 Report.ai_score。
- 发布前校验审核状态；审核记录保存病例版本和 SHA-256 digest，便于发现审核后内容变化。
- 微信登录的角色由服务端已有账号或 `WECHAT_TEACHER_OPENIDS` 白名单决定，客户端不能通过请求字段提升为教师。
- 生产启动会拒绝默认或过短的 `JWT_SECRET`；密钥缺失时不允许带着可预测签名密钥运行。

# V3 安全边界补充

- 学生接口只返回公开病例 metadata、public definition、学生自己的答案/反馈；`private_rubric`、`fixed_facts`、reference reasoning、blueprint digest 和模型 prompt 不出现在学生 DTO。
- 学生题目响应不返回定向发布的学生/班级 ID、作者 ID、能力标签或审核内部字段。
- 微训练输入只使用维度、阶段、审核蓝图公开字段和去标识化薄弱反馈；不发送 nickname、external ID、班级或无关历史。
- 动态题面经过 Pydantic、答案 schema、长度、注入、剂量/处方和隐藏 ID 校验；失败重试一次后使用固定 fallback。
- 服务端固定 criteria 决定总分，AI 只能改写反馈；evidence 必须逐字来自学生答案并限制为最多三条、每条 160 字。
- 站内通知只读写当前学生记录，不建设后台定时器或微信消息服务。

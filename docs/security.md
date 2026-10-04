# 授权、AI与敏感数据

## 服务端授权

所有受保护接口认证Bearer token，用例再次校验角色、owner和成员范围，不信任客户端角色、studentId/classId或Demo状态。教师只能查询本人拥有班级的正式可见证据，医学reviewer身份不自动扩大教师学情权限；不可见对象返回统一404，不泄露存在性。

微信code2Session由服务端调用，角色由已有账号或服务端白名单决定。生产设置`APP_ENV=production`、强JWT secret和`ENABLE_DEMO_AUTH=false`，拒绝默认/过短secret；客户端不得保存微信AppSecret、Coze/AI key或JWT secret。

学生DTO不暴露隐藏事实、参考推理、rubric criteria、未提交测试的固定答案、内部审核/审计字段或他人材料；最终提交后的答案解析仅本人可见；以最小view投影过滤，不能只靠页面隐藏。私人续问的内容、摘要、计数、时间和provider结果不对教师开放，自主与非正式证据不进入正式统计。教师题库副本不携带学生私人内容。

## AI与医学审核

生产PBL仅使用后端Coze gateway/adapter，显式设置`PBL_AI_PROVIDER=coze`及`COZE_INVOCATION_MODE=bot|workflow`；开发openai_compatible不用于生产，不自动切换provider或mode，配置切换后重启并验证。PBL在线入口只接受schema v8，三个学习任务按task_kind/request_id/版本及来源白名单校验，失败不切换提供方、不制造已诊断证据。紧急医学安全分流不调用AI。

外发内容去标识化、按场景限量；问答历史最多20条。动态训练AI反馈只能引用原作答允许的证据片段（最多3条、每条160字符），不得覆盖确定性评分或evidence。日志/截图/交付仅记录必要状态、耗时、错误码与定位，不记录token、prompt、完整学生回答、隐藏病例、原始请求/响应或真实敏感数据。

历史医学审核绑定内容版本和SHA-256摘要，审核记录不更新/删除；T64教师个人病例改由教师核对完整内容后保存、直接用于教学，不再要求独立医学审核或发布，不伪造专家签署。`source_supported`仅是来源支持，`pending_expert_review`仍待专家签署；Demo合成或教师教学审阅不代替独立医学审核。路线资料与合成病例按本次授权直接用于个体学习；课堂最终测试仍按冻结版本经教师教学审阅；知识图谱来源与专家审核要求不变，不由教师个人资源保存或Demo合成状态替代。

## 凭据与发布检查

秘密只在受管环境；本地.env忽略入库，前端VITE变量都视为公开。依赖/secret门禁见[开发](development.md#依赖维护)。审计使用脱敏指纹，不把泄露值再次写入报告；发现已泄露凭据须由责任人轮换并核查访问记录，删代码不等于失效。

历史凭据及3项secret指纹的未关闭处置见[T43归档](archive/t43-completed-20260926.zip)，原审计见[历史包](archive/history-20260926.zip)。

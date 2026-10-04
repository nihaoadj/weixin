# 临床思维学习助手

微信小程序病理学PBL教学项目，前端uni-app / Vue 3 / TypeScript，后端FastAPI / SQLAlchemy / Alembic。学生进行结构化研讨与训练，教师审阅课堂最终测试、查看学习结果并维护病例与个人题库；API与Demo模式显式分离。

开发与运行见[开发文档](docs/development.md)，确定性演示及实际页面验证见[微信验收](docs/wechat.md)。API失败不会自动回退本地数据；真实身份、AI及医学审核不能由Demo证明。

[文档入口](docs/README.md)按任务指向现行主题；[计划索引](docs/update_plan/README.md)记录实施与证据。当前完整计划仅保留T63、T64，其余见[阶段概述与归档](docs/update_plan/summary.md)。AI单轮路线与最终测试已实现，T64接续简化教师内容：病例库/个人题库采用直接维护与删除，不再分审核/发布/归档状态，旧讨论题、补充卡与独立复习退出活动流程。未完成的微信补验见[人工台账](docs/manual-acceptance.md)；历史报告写入/教师批阅已退役。

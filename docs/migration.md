# 迁移路线

## 当前目标

项目已从“前端本地 Demo + 微信云函数预留”迁移为：

```text
uni-app 前端 + FastAPI 后端 + SQLite 开发库
```

## 已完成

- 新增 `backend/` FastAPI 工程。
- 后端目录已标准化为 `api/`、`core/`、`models/`、`schemas/`、`services/`、`tests/`。
- 新增 SQLite 数据库模型。
- 新增 Demo 登录、AI、对话、报告、题目、题目作答线程 API。
- 前端新增 `apiClient.ts` 统一请求层。
- 前端新增 `repositoryAsync.ts` 统一远程/本地仓储入口。
- H5/演示环境可使用 FastAPI demo-login；微信小程序 API 模式使用服务端 `code2Session` 登录。
- 前端 AI 请求可携带 FastAPI token 访问 `/v1/medical-chat`。
- 前端对话、历史、报告、教师批阅、题目管理、学生题目作答已切到异步 adapter。
- API 模式已补回服务端微信 `code2Session` 登录；微信 AppSecret 只存在后端环境变量，教师角色由服务端白名单控制。
- 新增 `20260828_0007` 迁移，保存形成性报告的结构化错误、优点和建议。
- 新增 `20260823_0005` 兼容迁移：为旧班级字段回填 `class_members`，补 author FK 和分析索引；`0006` 的 down_revision 已接在 `0005` 之后。
- 文档已收敛为少量主文档。
- 旧 `cloudfunctions/` 已移除，后端统一收敛到 `backend/`。

## 当前仍保留

`src/services/repository.ts` 仍保留本地 Demo fallback。它不是主迁移方向，但保留它有两个作用：

- 未启动 FastAPI 时仍可体验小程序。
- 作为开发阶段的离线演示模式。

本地 Demo fallback 是显式离线演示模式，不是生产数据源；API 模式不会因网络错误静默切换到 Demo。旧云函数和云数据库数据不自动迁移，正式切换前需按外部数据迁移方案导入并验数。

## 后续生产化事项

1. 将微信 openid 白名单替换为正式账号/组织身份系统，并完成教师授权管理。
2. 将 SQLite 切换为 PostgreSQL，并在生产环境执行 Alembic 迁移。
3. 配置真实 AI 网关、模型凭据、合法域名和生产监控；服务端调用、急症拦截和审计边界已具备。
4. 完成隐私合规、医学专家签署和真实微信账号联调。
5. 如不再需要离线演示，再删除本地 Demo fallback，让页面全部强依赖 FastAPI。

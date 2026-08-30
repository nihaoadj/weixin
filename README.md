# 临床思维学习助手

这是一个基于 **uni-app + Vue 3 + TypeScript + FastAPI** 的医学教学助手，可构建为微信小程序和 H5。试点版包含学生问答、形成性报告、教师批阅、练习题管理和显式 Demo/API 双运行模式。

## 快速运行

```bash
npm ci --legacy-peer-deps
npm run backend:install
npm run backend:migrate
python backend/scripts/seed_test_data.py
npm run backend:dev
npm run dev:mp-weixin
```

微信开发者工具打开：

```text
dist/dev/mp-weixin/
```

H5 本地预览：

```bash
npm run dev:h5
```

## 运行模式

复制 `.env.example` 为 `.env`：

```text
# 无需后端的确定性演示
VITE_APP_MODE=demo

# 真实 FastAPI 链路
VITE_APP_MODE=api
VITE_API_BASE_URL=http://127.0.0.1:8000
```

API 模式不会静默回退到本地数据，登录或请求失败会明确提示，避免本地与远端数据分裂。

## 常用命令

```bash
npm run type-check
npm run lint
npm run test
npm run test:e2e
npm run backend:check
npm run contract:check
npm run build:mp-weixin
npm run build:h5
```

## 项目结构

```text
.
├── src/             # uni-app 前端源码
├── backend/         # Python FastAPI 后端源码
├── docs/            # 架构、接口、数据库、部署、功能和迁移文档
└── dist/            # 本地构建产物，忽略入库
```

完整技术文档入口见 [docs/README.md](./docs/README.md)，目录边界说明见 [docs/architecture.md](./docs/architecture.md)。

## 当前功能

- 学生端：医学问答、历史记录、练习题、多轮回答、学习报告、提交批阅，以及五阶段结构化病例训练、六维报告和针对性重练。
- 教师端：报告批阅、评分反馈、题目新建/编辑/审核/发布、班级成员管理、病例与学生学情下钻；病例草稿可由确定性 AI 兜底生成。
- 工程侧：OpenAPI 契约生成、API/Demo Repository adapter、运行时数据校验、内存请求缓存、AI 服务边界和 uni-app 双端构建。

运行前先执行 `npm run backend:migrate` 应用 Alembic 数据库迁移。当前试点身份入口可通过 `ENABLE_DEMO_AUTH=false` 关闭；生产环境默认不应启用 Demo 登录。API 模式下微信小程序通过服务端 `code2Session` 登录，H5 开发仍可使用 Demo 登录。接入真实用户和医学数据前，仍需完成账号授权、隐私合规和医学安全审核。

## 结构化病例训练

内置“社区获得性肺炎”合成教学病例。后端在非生产环境且 `SEED_SHOWCASE_CASE=true` 时幂等初始化；`AI_ENABLED=false`（默认）时医学问答、病例草稿、虚拟患者回复和报告评价均使用确定性兜底。API 学生响应只返回病例开场信息，不返回隐藏事实、参考路径、量表 criteria 或事实审计字段。

## 开发测试数据

在 `backend/` 目录执行 `python scripts/seed_test_data.py` 可向当前非生产数据库幂等导入测试数据。脚本会先应用 Alembic 最新迁移，不删除已有记录；生产环境会主动拒绝执行。数据包括 `demo_student`、`demo_student_b`、`demo_teacher`、`demo_reviewer` 四个演示账号、待审核病例、题目问答、待批报告、病例评估和个性化训练计划。

# 当前更新状态

本仓库已按 `docs/update/README.md` v3.0 接入结构化病例审核、班级学情和个性化跨病例训练。当前迁移包含 `20260828_0007`；学生端包含学习画像、三项计划、动态微训练、站内通知和复盘，教师端包含病例/学生下钻。

本地验证入口见 `docs/audit/initial-version-comparison.md` 和 `docs/audit/personalized-practice-audit.md`。真实 AI 凭据、微信教师白名单、微信合法域名、生产部署和仓库外医学专家签署仍是外部事项；不要将 Demo 审核视为医学专家签署。

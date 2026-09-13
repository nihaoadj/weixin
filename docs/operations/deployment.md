# 运行与部署

微信小程序是唯一产品目标。用户已授权 T25 直接退役 H5 命令及浏览器回归；缺少的小程序验证保留为待验收，不由历史浏览器证据替代。前端交付遵循 [微信验收规范](wechat-validation.md)；本次用户要求暂不执行真机，不能据开发者工具结果声明生产/真机验证通过。

## 前端运行

```bash
npm ci --legacy-peer-deps
npm run dev:mp-weixin
```

微信开发者工具打开：

```text
dist/dev/mp-weixin
```

## 后端运行

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --require-hashes -r requirements-dev.txt
# 仅确认 DATABASE_URL 是受管的开发/测试库后：
python -m alembic upgrade head
# seed_test_data.py 会迁移数据库；只可用于受管非生产库。
python -m uvicorn app.main:app --reload
```

后端地址：

```text
http://127.0.0.1:8000
```

API 文档：

```text
http://127.0.0.1:8000/docs
```

## 前端连接后端

复制根目录 `.env.example` 为 `.env`，设置前端连接参数：

```text
VITE_APP_MODE=api
VITE_API_BASE_URL=http://127.0.0.1:8000
```

API 模式接入真实微信登录时，在 `backend/.env` 配置以下服务端变量；`WECHAT_APP_SECRET` 只能放在后端，不能写入 `src` 或小程序构建产物：

```text
WECHAT_APP_ID=微信小程序 AppID
WECHAT_APP_SECRET=微信小程序 AppSecret
WECHAT_TEACHER_OPENIDS=教师 openid，多个值用逗号分隔
```

AI、JWT、数据库和微信配置可参考 `backend/.env.example`；其中 `AI_API_KEY`、`JWT_SECRET` 和 `WECHAT_APP_SECRET` 只能存在于后端环境。

未配置微信凭据时，API 模式的小程序登录会明确返回配置错误，不会退回固定 Demo 身份。

离线演示需明确设置 `VITE_APP_MODE=demo`。生产后端必须设置 `APP_ENV=production`、高强度 `JWT_SECRET` 和 `ENABLE_DEMO_AUTH=false`。

## 构建

```bash
npm run build:mp-weixin
```

## 质量检查

```bash
npm run check
npm run backend:test:safety
npm run backend:test:migrations
npm run backend:check
npm run contract:check
```

结构调整还应直接运行 `node scripts/frontend-boundaries.mjs` 与 `python backend/scripts/check_boundaries.py`；这些脚本尚未拥有 `package.json` 的别名。测试与 E2E 使用受管随机临时 SQLite，不能连接开发、共享或生产数据库。

## 生产部署建议

开发阶段使用 SQLite；本地或测试环境可直接运行 Uvicorn。以下生产拓扑只是目标建议，尚无受管生产配置、PostgreSQL 兼容、远程 CI/分支保护、微信真机/域名、真实 AI 或医学审核的验收证据：

```text
Nginx / 云负载均衡
        ↓
Uvicorn / Gunicorn
        ↓
FastAPI
        ↓
PostgreSQL
```

微信小程序上线时，需要在微信公众平台配置后端 HTTPS 合法请求域名。

# T09：`PBL_AI_ENABLED=true` 时必须显式配置 provider。生产只允许 Coze 且需要 token、mode 和相应资源 ID；切换 provider/mode 需重启，禁止自动 fallback。

# 运行与部署

## 前端运行

```bash
npm install
npm run dev:h5
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
python -m pip install --require-hashes -r requirements.txt
python -m alembic upgrade head
python scripts/seed_test_data.py  # 仅开发/测试库，需要测试数据时执行
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

未配置微信凭据时，API 模式的小程序登录会明确返回配置错误，不会退回固定 Demo 身份。H5 开发仍可使用 Demo 登录。

离线演示需明确设置 `VITE_APP_MODE=demo`。生产后端必须设置 `APP_ENV=production`、高强度 `JWT_SECRET` 和 `ENABLE_DEMO_AUTH=false`。

## 构建

```bash
npm run build:mp-weixin
npm run build:h5
```

## 质量检查

```bash
npm run check
cd backend
python -m pytest
```

## 生产部署建议

开发阶段可以用 SQLite。本地或测试环境可直接运行 Uvicorn。生产阶段建议：

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

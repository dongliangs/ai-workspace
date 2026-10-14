# AI WorkSpace

一个基于 Vue 3 + FastAPI 的 AI 智能工作台，支持普通对话与 Agent 模式（ReAct 工具调用循环），可上传 Excel 文件进行数据分析与可视化图表生成。

## 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| **前端** | Vue 3.5 + Vite 8 + TypeScript | SPA 单页应用 |
| UI 框架 | Element Plus + Tailwind CSS 4 | 组件库 + 原子化 CSS |
| 状态管理 | Pinia | auth / chat 双 store |
| 图表 | ECharts 6 | Agent 工具生成的 echarts_option 前端渲染 |
| HTTP | Axios + Fetch SSE | 普通接口走 Axios，流式对话走 Fetch ReadableStream |
| **后端** | FastAPI + Uvicorn | Python 3.10+，异步 ASGI |
| ORM | SQLAlchemy 2.0（async） | 异步引擎 + AsyncSession |
| 数据库 | MySQL 8（aiomysql 驱动） | 启动时 `create_all` 自动建表 |
| LLM | DeepSeek（OpenAI 兼容协议） | Chat Completions + tool_calls |
| 认证 | JWT + RSA 加密 + Argon2 哈希 | 前端公钥加密密码，后端私钥解密 |

## 项目结构

```
ai-workSpace/
├── frontend/ai-workspace/     # 前端
│   ├── src/
│   │   ├── api/               # 接口封装：auth / conversation / file
│   │   ├── components/
│   │   │   ├── chat/          # AgentMessageBubble / ToolCard / ChartRenderer / AgentSteps / MarkdownContent
│   │   │   ├── layout/        # AppSidebar / AppHeader
│   │   │   └── common/        # FileUploader
│   │   ├── layouts/           # AppLayout（主框架）/ AuthLayout（登录页）
│   │   ├── views/             # auth / home / workspace / chat（chat & agent 共用）
│   │   ├── stores/            # auth.ts / chat.ts
│   │   ├── utils/             # request.ts（Axios+Fetch SSE）/ rsa.ts
│   │   └── router/            # 路由守卫（未登录跳 /auth）
│   ├── vite.config.ts         # dev 代理 /api → 127.0.0.1:8000
│   └── .env                   # VITE_APP_API_BASE_URL / VITE_GLOB_API_URL
│
├── backend/                   # 后端
│   ├── main.py                # FastAPI 入口，lifespan 建表 + 注册工具
│   ├── core/
│   │   ├── config.py          # Pydantic Settings（读 .env）
│   │   └── security.py        # JWT / RSA / 密码哈希 / get_current_user
│   ├── api/                   # 路由层
│   │   ├── auth.py            # 注册 / 登录 / 获取公钥 / 获取当前用户
│   │   ├── conversation.py    # 会话 CRUD + 普通聊天流式
│   │   ├── file.py            # 文件上传
│   │   └── agent.py           # Agent SSE 流式入口
│   ├── services/              # 业务层
│   │   ├── auth_service.py    # 注册 / 登录逻辑
│   │   ├── llm_service.py    # DeepSeek 客户端（chat_with_tools / stream）
│   │   ├── file_service.py    # 文件校验 / 存储 / 归属校验
│   │   └── agent_service.py  # Agent SSE 编排 + 最终消息持久化
│   ├── agent/                 # Agent 模块（ReAct Runtime）
│   │   ├── runtime.py         # AgentContext + AgentRuntime（ReAct 循环）
│   │   ├── executor.py        # 工具执行器（始终返回 ToolResult）
│   │   ├── registry.py        # 工具注册表（Schema + handler 绑定）
│   │   ├── schema.py          # ToolDefinition / ToolResult 数据结构
│   │   ├── prompts.py         # Agent 系统提示词
│   │   ├── bootstrap.py       # 启动时注册所有工具
│   │   └── tools/             # 具体工具实现
│   │       ├── calculator.py
│   │       ├── analyze_excel.py
│   │       └── generate_chart.py
│   ├── models/                # SQLAlchemy 模型
│   │   ├── base.py            # DeclarativeBase
│   │   ├── user.py            # 用户表
│   │   ├── conversation.py    # 会话表（chat / agent / knowledge）
│   │   ├── message.py         # 消息表（含 tool_results JSON）
│   │   └── file.py            # 文件表
│   ├── schemas/               # Pydantic 响应模型
│   ├── db/session.py          # 异步 Engine + AsyncSessionLocal
│   ├── uploads/               # 用户上传文件（git 忽略，运行时创建）
│   ├── requirements.txt
│   └── .env                   # 环境变量（git 忽略）
│
└── .gitignore
```

## 核心架构

### 请求流转

- **普通聊天**：前端 `sendMessageStream()` → `POST /api/conversations/{id}/messages` → SSE 流式返回 LLM 增量文本
- **Agent 模式**：前端 `sendAgentMessageStream()` → `POST /api/agent/{id}/messages` → SSE 推送 `agent_start → text → tool_start → tool_result → done` 事件序列
- **文件上传**：前端 `upload()` → `POST /api/files/upload` → 存储到 `uploads/{user_id}/` → 返回 file_id → 发送消息时携带 `file_ids`

### Agent ReAct 循环

后端 `AgentRuntime.run()` 实现 Thought → Action → Observation 循环：

1. **Thought**：携带 context + tools 调用 DeepSeek，LLM 返回文本或 tool_calls
2. **Final**：无 tool_calls → 最终回答，结束循环
3. **Action**：Executor 从 Registry 查找 handler 执行工具
4. **Observation**：工具结果追加到 context，回到步骤 1
5. 最大循环 10 次，防止死循环

### 认证流程

1. 前端 `GET /api/auth/public-key` 获取 RSA 公钥
2. 前端用公钥加密密码 → `POST /api/auth/register` 或 `/login`
3. 后端私钥解密 → Argon2 哈希校验/存储 → 签发 JWT
4. 前端 localStorage 持久化 token，请求拦截器自动注入 `Authorization: Bearer`

> RSA 密钥对在服务启动时内存生成，重启后失效。**生产部署必须单进程**，不能用多 worker。

## 数据模型

| 表 | 关键字段 | 说明 |
|---|---|---|
| `users` | id, email, password_hash, nickname, is_active | 用户 |
| `conversation` | id, user_id, title, type | 会话（chat/agent/knowledge） |
| `message` | id, conversation_id, role, content, tool_results | 消息（tool_results 为 JSON 数组） |
| `file` | id, user_id, conversation_id, message_id, storage_path | 上传文件元数据 |

## 本地开发

### 后端

```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 配置 .env（参考下方环境变量）
# 确保 MySQL 已启动且 ai_workspace 库已创建

uvicorn main:app --reload --port 8000
```

### 前端

```bash
cd frontend/ai-workspace
pnpm install
pnpm dev  # http://localhost:5173
```

### 环境变量

**后端 `backend/.env`**：

```env
DATABASE_URL=mysql+aiomysql://root:password@localhost:3306/ai_workspace
JWT_SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=60
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
```

**前端 `frontend/ai-workspace/.env`**：

```env
VITE_GLOB_API_URL=/api
VITE_APP_API_BASE_URL=http://127.0.0.1:8000
```

## Agent 工具扩展

在 `agent/tools/` 下创建新工具文件，定义 `ToolDefinition` + `handler`，然后在 `agent/bootstrap.py` 中注册：

```python
# agent/tools/my_tool.py
from agent.schema import ToolDefinition, ToolResult

my_tool_definition = ToolDefinition(
    name="my_tool",
    description="...",
    parameters={...}  # JSON Schema
)

async def my_tool_handler(**kwargs):
    # 业务逻辑
    return {"result": "..."}
```

```python
# agent/bootstrap.py
from agent.tools.my_tool import my_tool_definition, my_tool_handler

def register_all_tools():
    registry.register(my_tool_definition, my_tool_handler)
    # ...
```

## 生产部署

- **数据库**：MySQL 8，建独立账号，配置 `DATABASE_URL`
- **后端**：`uvicorn main:app --host 127.0.0.1 --port 8000`，systemd 托管，**单进程**
- **前端**：`pnpm build` → `dist/` 静态文件交给 Nginx
- **Nginx**：同域反代 `/api/` 到后端，SSE 场景需 `proxy_buffering off`
- **uploads/**：运行时用户数据，需备份，Docker 部署挂卷

  

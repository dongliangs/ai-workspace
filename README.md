# AI WorkSpace

一个基于 Vue 3 + FastAPI 的 AI 智能工作台：

- **普通对话**：DeepSeek 流式聊天，多会话历史
- **Agent 模式**：自研 ReAct 工具调用循环（计算器 / Excel 分析 / 图表生成 / 知识库检索）
- **知识库问答（V0.3）**：上传 PDF / DOCX / TXT 文档自动构建向量索引（本地 Embedding + Milvus-lite），固定 RAG 管线生成带来源引用的回答；Agent 会话也可绑定知识库按需检索

## 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| **前端** | Vue 3.5 + Vite 8 + TypeScript | SPA 单页应用 |
| UI 框架 | Element Plus + Tailwind CSS 4 | 组件库 + 原子化 CSS |
| 状态管理 | Pinia | auth / chat / knowledgeBase |
| 图表 | ECharts 6 | Agent 工具生成的 echarts_option 前端渲染 |
| HTTP | Axios + Fetch SSE | 普通接口走 Axios，流式对话走 Fetch ReadableStream |
| **后端** | FastAPI + Uvicorn | Python 3.12，异步 ASGI，单进程部署 |
| ORM | SQLAlchemy 2.0（async） | 异步引擎 + AsyncSession |
| 数据库 | MySQL 8（aiomysql 驱动） | 启动时 `create_all` 自动建表 |
| RAG | LangChain v1.x 适配层 | loaders/chunker/embedding/vector_store 薄适配，保留自研 Agent Loop |
| 向量检索 | bge-small-zh-v1.5 + Milvus-lite | 本地 512 维 Embedding（离线加载）+ 单文件向量库，metadata 租户隔离 |
| LLM | DeepSeek（OpenAI 兼容协议） | Chat Completions + tool_calls |
| 认证 | JWT + RSA 加密 + Argon2 哈希 | 前端公钥加密密码，后端私钥解密 |

## 项目结构

```
ai-workSpace/
├── frontend/ai-workspace/     # 前端
│   ├── src/
│   │   ├── api/               # 接口封装：auth / conversation / file / knowledgeBase
│   │   ├── components/
│   │   │   ├── chat/          # ChatWorkspace / AgentMessageBubble / ToolCard / ChartRenderer / MarkdownContent
│   │   │   ├── layout/        # AppSidebar / AppHeader
│   │   │   └── common/        # FileUploader
│   │   ├── layouts/           # AppLayout（主框架）/ AuthLayout（登录页）
│   │   ├── views/             # auth / home / workspace / chat（chat & agent & knowledge 共用）
│   │   │   └── knowledge-base/ # 知识库列表 / 详情（el-table 文档管理）
│   │   ├── stores/            # auth.ts / chat.ts / knowledgeBase.ts
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
│   │   ├── conversation.py    # 会话 CRUD（recent 支持 type 过滤）+ 普通聊天流式
│   │   ├── file.py            # 文件上传
│   │   ├── agent.py           # Agent SSE 流式入口（可选 kb_id 绑定知识库）
│   │   ├── knowledge_base.py  # 知识库 CRUD（doc_count / chunk_count 统计）
│   │   ├── document.py        # 文档上传 / 列表 / 删除 / 失败重试
│   │   └── knowledge_chat.py  # 知识库问答入口（会话持久化绑定）
│   ├── services/              # 业务层
│   │   ├── auth_service.py    # 注册 / 登录逻辑
│   │   ├── llm_service.py     # DeepSeek 客户端（chat_with_tools / stream）
│   │   ├── file_service.py    # 文件校验 / 存储 / 归属校验
│   │   ├── agent_service.py   # Agent SSE 编排 + 最终消息持久化
│   │   ├── knowledge_service.py # 知识库 CRUD / 统计 / 会话绑定
│   │   ├── document_service.py # 文档索引生命周期（上传 / 重试 / 删除）
│   │   └── rag_service.py     # 知识库问答编排（固定 RAG 管线，不走 Agent Loop）
│   ├── agent/                 # Agent 模块（自研 ReAct Runtime）
│   │   ├── runtime.py         # AgentContext + AgentRuntime（ReAct 循环）
│   │   ├── executor.py        # 工具执行器（统一包装 ToolResult + 上下文注入）
│   │   ├── registry.py        # 工具注册表（Schema + handler 绑定）
│   │   ├── schema.py          # ToolDefinition / ToolResult 数据结构
│   │   ├── prompts.py         # Agent 系统提示词
│   │   ├── bootstrap.py       # 启动时注册所有工具
│   │   └── tools/             # 具体工具实现
│   │       ├── calculator.py
│   │       ├── analyze_excel.py
│   │       ├── generate_chart.py
│   │       └── knowledge_search.py  # 知识库检索（服务端注入 user_id/kb_id）
│   ├── knowledge/             # 知识库模块（LangChain v1.x 适配层）
│   │   ├── loaders.py         # 文档解析：PDF / DOCX / TXT
│   │   ├── chunker.py         # 语义分块（tiktoken 计量，带 overlap）
│   │   ├── embedding.py       # bge-small-zh-v1.5 本地推理（HF_HUB_OFFLINE 离线加载）
│   │   ├── vector_store.py    # Milvus-lite 封装（metadata: user_id/kb_id/document_id）
│   │   ├── retrieval.py       # Top-K 检索 + 得分阈值过滤（问答与 Agent 工具共用）
│   │   └── prompts.py         # RAG 系统提示词（带来源引用规范）
│   ├── models/                # SQLAlchemy 模型
│   │   ├── base.py            # DeclarativeBase
│   │   ├── user.py            # 用户表
│   │   ├── conversation.py    # 会话表（chat / agent / knowledge）
│   │   ├── message.py         # 消息表（含 tool_results JSON，RAG 来源引用也存于此）
│   │   ├── file.py            # 文件表
│   │   ├── knowledge_base.py  # 知识库表（conversation_id 绑定问答会话）
│   │   └── document.py        # 知识库文档表（状态机 + chunk_count）
│   ├── schemas/               # Pydantic 响应模型
│   ├── design/                # 架构设计文档（backend_architecture.md）
│   ├── db/session.py          # 异步 Engine + AsyncSessionLocal
│   ├── uploads/               # 用户上传文件（git 忽略，运行时创建）
│   ├── milvus_data.db         # Milvus-lite 向量库单文件（git 忽略，运行时创建）
│   ├── requirements.txt
│   └── .env                   # 环境变量（git 忽略）
│
└── .gitignore
```

## 核心架构

### 请求流转

- **普通聊天**：前端 `sendMessageStream()` → `POST /api/conversations/{id}/messages` → SSE 流式返回 LLM 增量文本
- **Agent 模式**：前端 `sendAgentMessageStream()` → `POST /api/agent/{id}/messages`（可选携带 `kb_id` 绑定知识库） → SSE 推送 `agent_start → text → tool_start → tool_result → done` 事件序列
- **知识库问答**：前端 `sendKnowledgeMessageStream()` → `POST /api/knowledge-bases/{kb_id}/chat` → 服务端解析/绑定会话（`kb.conversation_id` 持久化，重进自动续接历史） → SSE 推送 `start → retrieval_start → retrieval_result → text → done`，回答带来源引用
- **文件上传**：前端 `upload()` → `POST /api/files/upload` → 存储到 `uploads/{user_id}/` → 返回 file_id → 发送消息时携带 `file_ids`
- **文档索引**：`POST /api/knowledge-bases/{kb_id}/documents` → 解析 → 分块 → 向量化（同步执行） → 状态 `indexed/failed`；失败可通过 `POST .../documents/{doc_id}/retry` 重试

### Agent ReAct 循环

后端 `AgentRuntime.run()` 实现 Thought → Action → Observation 循环：

1. **Thought**：携带 context + tools 调用 DeepSeek，LLM 返回文本或 tool_calls
2. **Final**：无 tool_calls → 最终回答，结束循环
3. **Action**：Executor 从 Registry 查找 handler 执行工具；`AgentContext` 携带的 `user_id/kb_id` 由服务端注入（LLM 不可见、不可伪造）
4. **Observation**：工具结果追加到 context，回到步骤 1
5. 最大循环 10 次，防止死循环

> 知识库问答**不走 Agent Loop**：它是 rag_service 的固定 RAG 管线（每轮必检索再生成）；
> Agent 会话则通过 `knowledge_search` 工具按需检索。两条链路在 `knowledge/retrieval.py` 汇合。

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
| `message` | id, conversation_id, role, content, tool_results | 消息（tool_results 为 JSON 数组，RAG 来源引用也存于此） |
| `file` | id, user_id, conversation_id, message_id, storage_path | 上传文件元数据 |
| `knowledge_base` | id, user_id, name, doc_count, chunk_count(聚合), conversation_id | 知识库（conversation_id 服务端绑定问答会话） |
| `knowledge_document` | id, knowledge_base_id, file_id, status, chunk_count, error_message | 知识库文档（status: processing / indexed / failed） |

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

# 知识库/RAG（可选，以下为默认值）
# MILVUS_DB_PATH=milvus_data.db
# CHUNK_SIZE=600
# CHUNK_OVERLAP=100
# RETRIEVAL_TOP_K=5
# RETRIEVAL_SCORE_THRESHOLD=0.3
```

> Embedding 模型 `bge-small-zh-v1.5`（约 95MB）首次使用时从 hf-mirror.com 下载并缓存到
> `~/.cache/huggingface`；缓存后代码内 `HF_HUB_OFFLINE=1` 离线加载，不再联网校验。

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
- **后端**：`uvicorn main:app --host 127.0.0.1 --port 8000`，systemd 托管，**单进程**（Python 3.12）
- **前端**：`pnpm build` → `dist/` 静态文件交给 Nginx
- **Nginx**：同域反代 `/api/` 到后端（不剥离前缀，后端路由自带 `/api`），SSE 场景需 `proxy_buffering off`
- **uploads/**：运行时用户数据，需备份，Docker 部署挂卷
- **milvus_data.db**：向量库单文件，与 uploads 同级挂卷持久化
- **HF 模型缓存**：服务器需预下载 bge-small-zh-v1.5（配置 hf-mirror.com 镜像），或打包 `~/.cache/huggingface` 挂载进容器

详细架构设计见 [backend/design/backend_architecture.md](backend/design/backend_architecture.md)。

  

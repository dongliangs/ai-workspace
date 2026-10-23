# 后端架构设计总览（V0.3）

> 更新时间：2026-10-22 ｜ 覆盖范围：FastAPI 后端整体架构、三种会话模式、Agent 运行时、知识库（RAG）模块、数据模型

---

## 1. 总体分层架构

```mermaid
graph TB
    subgraph Client["前端 SPA（Vue3 + Element Plus）"]
        FE["工作台 / 普通对话 / Agent 对话 / 知识库管理 / 知识库问答"]
    end

    subgraph API["API 层（api/ · FastAPI Router，统一 /api 前缀）"]
        AUTH["auth.py<br/>注册/登录"]
        CONV["conversation.py<br/>普通对话 + 会话/消息记录<br/>（recent 支持 type 过滤）"]
        AGENT["agent.py<br/>Agent 会话消息入口<br/>（kb_id 归属校验）"]
        KBCHAT["knowledge_chat.py<br/>知识库问答入口<br/>（会话持久化绑定）"]
        KB["knowledge_base.py<br/>知识库 CRUD"]
        DOC["document.py<br/>文档上传/列表/删除/重试"]
        FILE["file.py<br/>统一文件上传"]
    end

    subgraph SVC["服务层（services/ · 业务协调）"]
        LLM["llm_service<br/>DeepSeek 封装<br/>chat_with_llm_stream / chat_with_tools"]
        AGENTSVC["agent_service<br/>SSE 序列化 + 最终消息落库"]
        RAG["rag_service<br/>知识库问答编排<br/>（固定 RAG 管线，不走 Agent Loop）"]
        KBSVC["knowledge_service<br/>知识库 CRUD / 统计 / 会话绑定"]
        DOCSVC["document_service<br/>文档索引生命周期"]
        FILESVC["file_service<br/>文件保存 / 消息关联"]
    end

    subgraph RUNTIME["Agent 运行时（agent/ · V0.2 自研 ReAct）"]
        RT["runtime.py<br/>AgentRuntime<br/>ReAct 循环 + AgentContext"]
        EXE["executor.py<br/>execute_tool<br/>ToolResult 统一包装<br/>+ 会话上下文注入"]
        REG["registry.py<br/>工具注册中心"]
        TOOLS["tools/<br/>calculator / analyze_excel<br/>generate_chart / knowledge_search"]
        BOOT["bootstrap.py<br/>register_all_tools"]
    end

    subgraph KNOWLEDGE["知识库模块（knowledge/ · LangChain v1.x 适配层）"]
        LOADERS["loaders.py<br/>PDF/TXT/MD 解析"]
        CHUNKER["chunker.py<br/>文本分块"]
        EMB["embedding.py<br/>bge-small-zh-v1.5<br/>本地 Embedding（512 维）"]
        VSTORE["vector_store.py<br/>Milvus-lite 向量库"]
        RETRIEVE["retrieval.py<br/>相似度检索 + 阈值过滤"]
        KPROMPT["prompts.py<br/>RAG 提示词"]
    end

    subgraph DATA["数据层"]
        MYSQL[("MySQL<br/>SQLAlchemy async")]
        MILVUS[("Milvus-lite<br/>milvus_data.db")]
        FS[("本地磁盘<br/>uploads/")]
    end

    EXT["DeepSeek LLM API（外部）"]

    Client --> API
    AUTH --> MYSQL
    CONV --> LLM
    CONV --> MYSQL
    AGENT --> AGENTSVC --> RT
    KBCHAT --> RAG
    RAG --> RETRIEVE
    RAG --> LLM
    KB --> KBSVC --> MYSQL
    DOC --> DOCSVC
    FILE --> FILESVC --> FS
    DOCSVC --> LOADERS
    DOCSVC --> CHUNKER
    DOCSVC --> EMB
    DOCSVC --> VSTORE
    RT --> EXE --> REG --> TOOLS
    TOOLS --> RETRIEVE
    EXE --> MYSQL
    LLM --> EXT
    EMB -.本地推理.-> EMB
    RETRIEVE --> MILVUS
```

**目录结构对应：**

```text
backend/
├── main.py              # 应用入口：lifespan 建表 + 注册工具 + 初始化向量库
├── core/                # 横切：config（Settings）+ security（RSA/JWT 认证）
├── db/                  # async engine + AsyncSessionLocal + get_db
├── models/              # ORM：User / Conversation / Message / File / KnowledgeBase / KnowledgeDocument
├── schemas/             # Pydantic 请求/响应契约（ApiResponse 统一包装）
├── api/                 # 路由层（见上图）
├── services/            # 业务编排层（见上图）
├── agent/               # 自研 Agent 运行时（见第 3 节）
├── knowledge/           # RAG 基础设施（见第 4 节）
└── design/              # 设计文档
```

---

## 2. 三种会话模式（核心业务视角）

`Conversation.type` 区分三种模式，共用同一张 `conversation` / `message` 表和统一会话记录接口（`GET /conversations/recent?type=chat|agent|knowledge`）。

```mermaid
flowchart LR
    subgraph Chat["① 普通对话 chat"]
        C1["POST /conversations/:id/messages"] --> C2["llm_service<br/>chat_with_llm_stream"]
        C2 --> C3["SSE 逐 token 推送<br/>+ 消息落库"]
    end

    subgraph AgentMode["② Agent 会话 agent（自研 ReAct Loop）"]
        A1["POST /agent/:id/messages<br/>{content, file_ids?, tools?, kb_id?}"] --> A2["AgentContext<br/>system prompt + 历史<br/>+ user_id/kb_id 会话身份"]
        A2 --> A3["AgentRuntime.run()<br/>Thought→Action→Observation<br/>最多 10 轮"]
        A3 --> A4["executor 执行工具<br/>（calculator / analyze_excel<br/>/ generate_chart / knowledge_search）"]
        A4 --> A5["SSE: agent_start / text<br/>/ tool_start / tool_result / done"]
    end

    subgraph Knowledge["③ 知识库问答 knowledge（固定 RAG 管线）"]
        K1["POST /knowledge-bases/:kb_id/chat"] --> K0["resolve_knowledge_conversation<br/>请求指定 → 复用 kb 绑定 → 新建并绑定<br/>（kb.conversation_id 持久化）"]
        K0 --> K2["rag_service<br/>rag_chat_stream"]
        K2 --> K3["retrieval.retrieve()<br/>向量检索 Top-K"]
        K3 --> K4["build_rag_context<br/>组装上下文 + 来源"]
        K4 --> K5["chat_with_llm_stream<br/>生成带来源的回答"]
        K5 --> K6["SSE: start / retrieval_start<br/>/ retrieval_result / text / done"]
    end
```

**关键设计说明：**

| 对比项 | 普通对话 | Agent 会话 | 知识库问答 |
|---|---|---|---|
| 入口路由 | `/conversations/:id/messages` | `/agent/:id/messages` | `/knowledge-bases/:kb_id/chat` |
| 编排方式 | 直接调 LLM | 自研 ReAct Loop（LLM 自主决策用工具） | 固定管线（必检索，再生成） |
| 检索 | 无 | 按需（LLM 决定是否调 knowledge_search） | 每轮必检索 |
| 上下文 | 历史消息 | 历史消息 + 工具观察结果 | 检索片段注入 prompt |
| 会话身份注入 | 无 | `AgentContext(user_id, kb_id?)` → executor → 工具 | 路由参数直接携带 kb_id |
| 会话持久化 | 前端传会话 id | 前端传会话 id | 服务端绑定 `kb.conversation_id`，重进自动续接 |

> ⚠️ **澄清**：知识库问答**不经过 Agent Loop**。它是 rag_service 里的固定 RAG 管线；Agent 会话则通过
> `knowledge_search` 工具间接复用同一套检索层。两条链路在 `knowledge/retrieval.py` 汇合。
>
> **Agent 绑定知识库**：请求可选携带 `kb_id`，服务端校验归属后写入 `AgentContext`，由 executor
> 注入工具（服务端值优先，LLM 无法伪造）；未绑定时 knowledge_search 如实返回提示。
> 前端 `AgentStreamParams.kbId` 已接线（Agent 对话页选择知识库的 UI 入口尚未做）。

---

## 3. Agent 运行时（V0.2 自研，非 LangChain Agent）

```mermaid
sequenceDiagram
    participant FE as 前端
    participant API as api/agent.py
    participant SVC as agent_service
    participant RT as AgentRuntime
    participant LLM as DeepSeek
    participant EXE as execute_tool
    participant H as 工具 handler

    FE->>API: POST /agent/:id/messages {content, file_ids?, tools?, kb_id?}
    API->>API: 校验会话归属 + type=agent<br/>校验 kb_id 归属（可选）<br/>保存用户消息/关联文件
    API->>RT: AgentContext(system_prompt, user_id, kb_id)<br/>+ 历史 + 文件元数据
    RT->>SVC: run() 异步生成事件流

    loop 最多 10 轮（MAX_ITERATIONS）
        RT->>LLM: chat_with_tools(messages, tool_defs)
        LLM-->>RT: 文本回答 或 tool_calls
        RT-->>FE: SSE text（推理内容）
        alt 返回 tool_calls
            RT-->>FE: SSE tool_start {tool, arguments}
            RT->>EXE: execute_tool(name, arguments,<br/>context={user_id, kb_id})
            Note over EXE: 按签名智能合并注入：<br/>只传 handler 声明的键，<br/>服务端值优先（防 LLM 伪造）
            EXE->>H: handler(**merged)
            Note over H: 契约：返回原始数据 dict，<br/>异常直接抛出
            H-->>EXE: data / raise
            EXE-->>RT: ToolResult(success/error)，不抛异常
            RT-->>FE: SSE tool_result {tool, status, result}
            RT->>RT: Observation 加入上下文
        else 纯文本（最终回答）
            RT-->>FE: SSE text + done
        end
    end
    SVC->>SVC: 最终回答落库（含 tool_results）
```

**核心契约：**

1. **工具注册**：`registry.register(ToolDefinition, handler)`，启动时 `register_all_tools()` 一次性注册；
   Runtime 不感知具体工具，新增工具零侵入
2. **ToolResult 统一包装**：handler 只返回原始数据；executor 负责包装成功/失败，Runtime
   无需 try/except，只读 `result.status`
3. **上下文注入**：`AgentContext` 携带 `user_id/kb_id`（kb_id 来自请求绑定，服务端校验归属）
   → `execute_tool(context=...)` → 按签名过滤注入 → 工具内不暴露给 LLM、不可被 LLM 参数覆盖
4. **无工具退化**：LLM 不返回 tool_calls 时退化为普通对话

---

## 4. 知识库模块（RAG 双链路）

### 4.1 索引链路（文档上传，同步执行）

```mermaid
flowchart TD
    U["POST /knowledge-bases/:kb_id/documents<br/>（前端超时放宽至 5 分钟）"] --> SAVE["file_service.save_upload_file<br/>存磁盘 + File 记录"]
    SAVE --> CI["document_service.create_and_index"]
    CI --> REC["创建 KnowledgeDocument<br/>status=PROCESSING"]
    REC --> PARSE["loaders.parse<br/>PDF/DOCX/TXT → 文本 + 页码"]
    PARSE --> SPLIT["chunker.split<br/>语义分块"]
    SPLIT --> EMB2["embedding.embed_documents<br/>bge-small-zh-v1.5（本地，离线模式）"]
    EMB2 --> ADD["vector_store.add_documents<br/>metadata: user_id/kb_id/document_id"]
    ADD --> OK["status=INDEXED<br/>chunk_count=分块数"]
    OK --> CNT["_refresh_doc_count<br/>按 indexed 实时重算 KB.doc_count"]
    PARSE -.失败.-> FAIL["status=FAILED<br/>error_message 落库<br/>（不计入 doc_count）"]
    FAIL -.->|"POST /knowledge-bases/:kb_id/documents/:doc_id/retry"| RETRY["document_service.retry_index<br/>清残留向量 → 重建 → 计数重算<br/>（仅 failed 可重试）"]
    RETRY --> OK
```

### 4.2 检索链路（两处消费方共用）

```mermaid
flowchart LR
    subgraph 消费方A["知识库问答（每轮必检索）"]
        R1["rag_service"] --> RET
    end
    subgraph 消费方B["Agent 会话（LLM 按需调用）"]
        R2["knowledge_search 工具"] --> RET["retrieval.retrieve<br/>(question, user_id, kb_id)"]
    end
    RET --> SS["vector_store.similarity_search<br/>Top-K（metadata 过滤 user/kb）"]
    SS --> TH["得分阈值过滤<br/>retrieval_score_threshold"]
    TH --> OUT["片段列表<br/>content/document_id/page_number/score"]
```

**向量库设计**：Milvus-lite 单文件（`milvus_data.db`），bge-small-zh-v1.5 本地推理（512 维，
`HF_HUB_OFFLINE=1` 离线加载，模型缓存后不联网校验）；metadata 带 `user_id/kb_id` 实现
租户隔离检索。

---

## 5. 数据模型

```mermaid
erDiagram
    User ||--o{ Conversation : "1:N"
    User ||--o{ File : "上传"
    User ||--o{ KnowledgeBase : "1:N"
    Conversation ||--o{ Message : "1:N"
    Message ||--o{ File : "message_id 关联附件"
    KnowledgeBase ||--o{ KnowledgeDocument : "1:N"
    File ||--o| KnowledgeDocument : "file_id 复用存储"

    Conversation {
        int id PK
        int user_id FK
        string title
        enum type "chat / agent / knowledge"
        datetime created_at
        datetime updated_at
    }
    Message {
        int id PK
        int conversation_id FK
        enum role "user / assistant"
        text content
        json tool_results "Agent 工具结果（刷新恢复图表）"
        datetime created_at
    }
    File {
        int id PK
        int user_id FK
        int message_id "nullable 消息附件"
        string storage_path "uploads/"
        string original_filename
        string file_type
        int file_size
    }
    KnowledgeBase {
        int id PK
        int user_id FK
        string name
        text description
        enum status "active"
        int doc_count "仅统计 indexed（实时重算）"
        int conversation_id "nullable 服务端绑定的问答会话"
    }
    KnowledgeDocument {
        int id PK
        int knowledge_base_id FK
        int user_id FK
        int file_id FK
        string filename
        string file_type
        enum status "pending/processing/indexed/failed"
        int chunk_count
        text error_message
    }
```

**统计口径**：`doc_count` 与 `KB.chunk_count`（接口实时 SUM 聚合，仅 indexed）均不冗余存储
计数器易漂移的教训——`doc_count` 已改为上传成功/删除时按状态重算自愈。

---

## 6. 横切关注点与部署约束

| 关注点 | 设计 |
|---|---|
| 认证 | RSA 密钥启动时内存随机生成 + JWT；**必须单进程部署**（多 worker 密钥不一致导致认证失败） |
| 统一响应 | `ApiResponse{code, data, message}` + 全局异常处理器（404/422/500） |
| SSE | 所有流式接口关闭代理缓冲（`X-Accel-Buffering: no`），Nginx 需同步配置；生产环境 `/api` 转发不剥离前缀 |
| 启动初始化 | lifespan：`create_all` 建表 → `register_all_tools()` → `init_collection()` 向量库 |
| CORS | 开发环境放行 `http://localhost:5173` |
| Embedding | hf-mirror 首次下载，本地缓存后 `HF_HUB_OFFLINE=1` 离线加载，避免网络波动 |
| 部署 | Ubuntu 24.04 + Docker Compose，**单进程 uvicorn**（RSA + Milvus-lite 文件锁均要求） |

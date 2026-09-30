# AI WorkSpace

> 基于 Vue 3 + TypeScript + Vite 构建的 AI 对话工作台前端，支持会话管理、流式输出、文件上传等能力。

## 项目简介

AI WorkSpace 是一个面向 AI 对话场景的前端工作台，核心业务围绕 **"会话-消息"** 模型展开：

- **工作台（Workspace）**：登录后落地页，提供快捷入口、模板、最近会话，输入提示词即可一键发起 AI 对话。
- **AI Chat**：对话主页面，支持流式打字机输出、停止生成、复制、重新生成、附件上传、对话记录切换。
- **认证体系**：邮箱密码登录/注册，JWT 鉴权，路由守卫保护需登录页面，登录态 localStorage 持久化。

核心业务流程：

```
/workspace 输入提示词
  → 截取前 30 字作 title 创建会话（POST /conversations/create）
  → 跳转 /chat
  → 发送消息（POST /conversations/{id}/messages，流式 SSE/NDJSON）
  → LLM 逐块返回 → 前端增量渲染打字机
  → 用户可中断、复制、重新生成
```

## 技术栈

| 分类 | 选型 | 说明 |
| --- | --- | --- |
| 框架 | Vue 3.5 + `<script setup>` + TypeScript | Composition API，单文件组件 |
| 构建工具 | Vite 8 + `@vitejs/plugin-vue` / `plugin-vue-jsx` | 支持 JSX/TSX，dev 热更新 |
| 状态管理 | Pinia 4 | `auth`（登录态）、`chat`（会话列表/当前会话） |
| 路由 | Vue Router 5 | `createWebHistory`，`beforeEach` 路由守卫鉴权 |
| UI 组件库 | Element Plus 2 | `ElMessage` 等全局组件 |
| 图标 | lucide-vue-next | 按需引入，tree-shaking 友好 |
| CSS 方案 | Tailwind CSS 4 + CSS Variables | 原子类 + 设计 token（`--aws-*`）双轨 |
| HTTP | axios（普通接口）+ fetch（流式） | 自研 `request.ts` 统一封装 |
| 代码规范 | ESLint + oxlint + Prettier | 双 lint 链路，prettier 格式化 |
| 单元测试 | Vitest 4 + @vue/test-utils | jsdom 环境 |
| Node 要求 | `^22.18.0 \|\| >=24.12.0` | 见 `package.json` engines |

## 目录结构

```
ai-workspace/
├── .env                          # 环境变量（VITE_APP_API_BASE_URL / VITE_GLOB_API_URL）
├── .gitignore
├── vite.config.ts                # Vite 配置（@ → src 别名）
├── package.json
└── src/
    ├── main.ts                   # 入口：挂载 Pinia / Router / ElementPlus
    ├── App.vue
    ├── assets/
    │   ├── base.css              # Tailwind 入口 + 设计 token（--aws-*）
    │   └── main.css
    ├── router/
    │   └── index.ts              # 路由表 + beforeEach 鉴权守卫
    ├── layouts/
    │   ├── AppLayout.vue         # 已登录布局（Sidebar + Header + stage）
    │   ├── AuthLayout.vue        # 登录/注册布局
    │   └── GuestLayout.vue
    ├── components/
    │   └── layout/
    │       ├── AppSidebar.vue    # 左侧导航 + 对话记录（chat 页专属）
    │       └── AppHeader.vue     # 顶部栏
    ├── views/
    │   ├── home/index.vue        # 未登录落地页
    │   ├── auth/index.vue        # 登录/注册
    │   ├── workspace/index.vue   # 工作台（快捷入口 + 最近会话）
    │   └── chat/index.vue        # AI 对话主页面
    ├── stores/
    │   ├── auth.ts               # 登录态 + localStorage 持久化
    │   └── chat.ts               # 会话列表 / currentId
    ├── api/
    │   ├── auth.ts               # 登录/注册/获取当前用户
    │   └── conversation.ts       # 会话 CRUD + 发送消息（流式）
    └── utils/
        └── request.ts            # axios 实例 + stream() 流式封装
```

## 核心设计

### 1. 请求层封装（`src/utils/request.ts`）

统一封装 axios 实例，提供多类方法：

| 方法 | 用途 | 备注 |
| --- | --- | --- |
| `get / post / put / delete` | 普通 JSON 接口 | 自动注入 `Authorization: Bearer <token>` |
| `download` | 文件下载 | `responseType=blob`，自动提取文件名并触发保存 |
| `upload` | 文件上传 | `FormData` + `onUploadProgress` 进度回调 |
| `stream` | LLM 流式响应 | `fetch + ReadableStream`，返回 `AsyncGenerator`，支持 SSE/NDJSON |

**响应信封拆包**：后端返回 `{ code, data, message }`，拦截器对 `code===0` 自动剥离外层，业务层直接拿 `data`；`code!==0` 统一 `ElMessage.error` 并 reject；401 触发登出跳登录页。

**流式实现要点**：浏览器中 axios 基于 XHR 无法边收边吐，故 `stream()` 改用 `fetch + ReadableStream + TextDecoder`，按 SSE（`\n\n` 分隔）或 NDJSON（`\n` 分隔）切分缓冲区，逐块 `yield`。调用方 `for await...of` 消费，可直接增量写入 Vue 响应式变量实现打字机效果。

### 2. 状态管理

**`auth.ts`**
- `token` / `user`：响应式登录态，刷新时从 localStorage 恢复
- `login / register / logout`：登录/注册/登出，JWT 持久化
- `authCurrentUser`：进入 AppLayout 时拉取最新用户信息
- `rememberedEmail`：登录页"记住我"自动回填

**`chat.ts`**
- `sessions`：会话列表
- `currentId`：当前选中会话（`null` = 新对话欢迎态）
- `createSession(title)` / `fetchRecent()` / `selectSession(id)`

### 3. 路由与鉴权

```
/             → Home（未登录落地页）
/auth         → AuthLayout → 登录/注册
/workspace    → AppLayout → 工作台（需登录）
/chat         → AppLayout → AI 对话（需登录）
```

`router.beforeEach` 规则：
- `/workspace` 未登录 → 跳 `/auth?redirect=...`
- `/auth` 已登录 → 跳 `/workspace`
- `/` 已登录 → 跳 `/workspace`

### 4. 布局架构

`AppLayout.vue` 采用三段式 flex 布局：

```
┌─────────────┬───────────────────────────┐
│             │ AppHeader（固定）          │
│ AppSidebar  ├───────────────────────────┤
│ 220px 固定  │ app-stage（overflow-y:auto）│
│             │   <RouterView />           │
│             │                            │
└─────────────┴───────────────────────────┘
```

`AppSidebar` 在 `/chat` 页面会额外渲染"对话记录"区域，列表超出可滚动，导航菜单与用户信息固定。

### 5. 设计系统

CSS 变量集中在 `src/assets/base.css`，以 `--aws-*` 前缀统一管理：

- 表面：`--aws-background` / `--aws-card` / `--aws-sidebar` / `--aws-header`
- 品牌色：`--aws-primary` (#3b82f6) / `--aws-primary-hover` / `--aws-success` (#10b981)
- 文本：`--aws-foreground` / `--aws-muted` / `--aws-placeholder`
- 圆角：`--aws-radius-sm` (4) / `md` (8) / `lg` (12) / `xl` (16)
- 字号：`--aws-text-xs` (12) ~ `2xl` (24)

## 接口一览

会话相关接口定义在 [src/api/conversation.ts](src/api/conversation.ts)：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/conversations/create` | 创建会话，body `{ title, type: 'chat' }` |
| `GET`  | `/conversations/recent` | 获取当前用户最近会话列表 |
| `GET`  | `/conversations/{id}` | 查询会话基本信息 |
| `GET`  | `/conversations/{id}/messages` | 查询历史消息（ASC） |
| `POST` | `/conversations/{id}/messages` | 发送消息，流式返回 assistant 内容 |

认证接口定义在 [src/api/auth.ts](src/api/auth.ts)（登录、注册、获取当前用户）。

## 环境配置

`.env` 文件：

```env
VITE_GLOB_API_URL=/api
VITE_APP_API_BASE_URL=http://127.0.0.1:8000
```

- `VITE_APP_API_BASE_URL`：后端域名（开发环境 `127.0.0.1:8000`）
- `VITE_GLOB_API_URL`：接口前缀（`/api`）

## Project Setup

```sh
pnpm install
```

### Compile and Hot-Reload for Development

```sh
pnpm dev
```

### Type-Check, Compile and Minify for Production

```sh
pnpm build
```

### Run Unit Tests with [Vitest](https://vitest.dev/)

```sh
pnpm test:unit
```

### Lint with [ESLint](https://eslint.org/) + [oxlint](https://oxc.rs/docs/cli/usage/linter.html)

```sh
pnpm lint
```

### Format with [Prettier](https://prettier.io/)

```sh
pnpm format
```

## Recommended IDE Setup

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Type Support for `.vue` Imports in TS

TypeScript cannot handle type information for `.vue` imports by default, so we replace the `tsc` CLI with `vue-tsc` for type checking. In editors, we need [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) to make the TypeScript language service aware of `.vue` types.

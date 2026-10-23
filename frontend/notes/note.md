# V0.3 知识库模块 · 开发思路（列表页）

> 对应设计稿：`design/knowledge-base-list.html`（已评审通过）
> 对应需求：《AI_WorkSpace_V0.3_知识库问答检索需求设计文档》§ 知识库列表页

## 一、需求理解与本期范围

V0.3 新增"知识库"模块：用户创建知识库 → 上传文档 → 系统解析/分块/向量化 → 基于知识库问答（引用溯源）。

本期只做**列表页**（用户评审后再继续详情页），包括：

- 知识库卡片网格：名称、描述、文档数、片段数、更新时间、悬浮操作（重命名/删除）
- 空状态：引导创建第一个知识库
- 创建 / 重命名弹窗（同一个弹窗两种模式）
- 删除二次确认
- 点击卡片跳转详情页（详情页下期开发，当前为占位页，保证跳转交互闭环不 404）

## 二、分层架构（对齐项目现状）

```
views/knowledge-base/index.vue   ← 页面：渲染三态 + 交互编排，不直接碰 API
        │
stores/knowledgeBase.ts          ← Pinia store：列表状态 + CRUD action（setup 风格，对齐 chat store）
        │
api/knowledgeBase.ts             ← API 层：类型定义 + get/post/put/del 封装（对齐 conversation.ts）
        │
utils/request.ts                 ← 现有 axios 封装：拦截器统一弹错误 toast
```

分层原则（沿用 V0.2 chat 的惯例）：

1. **API 层只管"怎么调"**：类型 + 请求函数，无状态；
2. **Store 管"共享状态"**：列表数据 + loading/submitting + 增删改后就地更新数组（乐观更新列表项，不整页重拉）；
3. **页面管"交互编排"**：弹窗开关、表单校验、二次确认、toast 文案、路由跳转。

## 三、接口契约（后端按此实现即可联调）

| 操作 | 方法与路径 | 请求体 | 说明 |
|---|---|---|---|
| 列表 | `GET /knowledge-bases` | - | 当前用户全部知识库，按 updated_at DESC |
| 创建 | `POST /knowledge-bases` | `{ name, description }` | 返回新建实体 |
| 重命名 | `PUT /knowledge-bases/:id` | `{ name, description }` | 返回更新后实体 |
| 删除 | `DELETE /knowledge-bases/:id` | - | 级联删除文档与索引数据 |

实体 `KnowledgeBase`：`id / name / description / doc_count / chunk_count / created_at / updated_at`。

- `doc_count`：文档总数；`chunk_count`：可检索片段数（仅统计索引完成文档）
- `updated_at`：创建、重命名、文档增删、索引完成都会刷新（列表据此排序）

## 四、Store 设计要点

- `bases` 列表 + `loading`（首屏）+ `submitting`（增删改防重复提交）
- `isEmpty` 计算属性：`!loading && bases.length === 0`，页面据此切换空状态
- **错误处理约定**：
  - `fetchAll` 失败**静默回退空列表**——axios 拦截器已统一 toast，页面显示空状态即可；在后端接口未上线的联调前阶段，页面也能正常浏览（V0.3 后端未 ready 时不会白屏）
  - `create / rename` 失败**原样抛出**——页面 catch 后保持弹窗开启、保留用户填写的表单，避免输入丢失
  - `remove` 依赖页面 `ElMessageBox.confirm` 二次确认后才调用，store 不重复确认

## 五、页面实现要点

1. **严格还原设计稿**：布局、配色、字号全部走 `base.css` 的 `--aws-*` 设计令牌；卡片网格 3 列（≤1024px 降 2 列）、悬浮抬升、staggered 入场动画（`animation-delay` 按索引）。
2. **卡片视觉无后端字段支持时的决策**：设计稿每张卡片有独立主题色与图标，但实体没有 color/icon 字段。方案：前端内置 6 色调色板（蓝/绿/紫/青/琥珀/灰，与设计稿一致），按**列表索引循环取色**——视觉丰富且稳定（不随刷新闪烁），无需后端加字段。
3. **弹窗复用**：创建与重命名共用一个弹窗（`dialogMode: 'create' | 'rename'`），标题/按钮文案/初始值动态切换。用 `Teleport + Transition` 自绘（复刻设计稿 EP 风格），而非 ElDialog——保证与设计稿像素级一致。
4. **表单交互**：名称必填（空提交 → 红框 + 提示 + 聚焦）、Enter 提交、Esc/点击遮罩关闭、提交中禁用按钮。
5. **时间格式化**：当年显示 `MM-DD`，跨年显示 `YYYY-MM-DD`。
6. **删除确认文案**：带知识库名与文档数（"删除后「xx」中的 N 份文档及索引数据将一并删除"），明确后果降低误删。

## 六、路由与导航

- 新增路由：`/knowledge`（列表页）、`/knowledge/:id`（详情页占位，下期替换）
- 均挂在 AppLayout 下（复用侧边栏/顶栏），加入 `PROTECTED_PATHS` 需登录
- 侧边栏 navItems 中 `/knowledge` 已存在（BookOpen 图标），本期补了 `isNavActive` 前缀匹配：详情页 `/knowledge/:id` 时导航仍保持高亮

## 七、文件清单

| 文件 | 说明 |
|---|---|
| `src/api/knowledgeBase.ts` | 新增：实体类型 + 4 个接口函数 |
| `src/stores/knowledgeBase.ts` | 新增：列表状态 + fetchAll/create/rename/remove |
| `src/views/knowledge-base/index.vue` | 新增：列表页（三态 + 全部交互） |
| `src/views/knowledge-base/detail.vue` | 新增：详情占位页（下期替换） |
| `src/router/index.ts` | 修改：注册两条路由 + 登录保护 |
| `src/components/layout/AppSidebar.vue` | 修改：isNavActive 前缀匹配 |

## 八、联调与后续计划

1. **联调前现状**：后端 4 个接口未实现时，页面可正常打开 → 显示空状态 + 拦截器 toast 报错；创建等操作会失败提示，不影响 UI 评审。
2. **下期（详情页）**：文档上传区（拖拽 + 点击，PDF/DOCX/TXT）、文档列表四态（待处理/处理中带进度/已完成/失败带重试）、"进入问答"（携带 kb_id 跳 chat，RAG 检索注入 system prompt）。
3. **再下期**：问答侧引用溯源展示（答案下方引用片段卡片，点击跳原文）、上传进度与索引状态轮询。

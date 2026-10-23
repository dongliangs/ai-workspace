# V0.3 知识库详情页 · 开发思路

> 对应设计稿：`design/knowledge-base-detail.html`（已评审通过）
> 前置：知识库列表页已完成（API/Store/页面三层已就绪）

## 一、本期范围

把详情页占位页替换为完整实现，覆盖效果图全部内容与交互：

1. **信息头卡**：图标、名称、描述、统计（文档数 / 可检索片段数 / 更新时间）
2. **知识库级操作**：进入问答、重命名（弹窗）、删除（二次确认 → 返回列表）
3. **上传区**：点击选择 + 拖拽上传，前端校验（PDF/DOCX/TXT 白名单、≤20MB），逐文件进度条
4. **文档列表**：四态渲染 —— 待处理（排队）/ 处理中（进度条）/ 已完成（片段数）/ 失败（错误摘要 + 重试）
5. **文档操作**：删除（二次确认）、失败重试
6. **空知识库**：上传区放大 + 索引流水线示意（上传 → 文本解析 → 智能分块 → 向量化索引）
7. **索引状态轮询**：pending/processing 文档存在时每 5s 静默刷新，全部到达终态自动停止

## 二、分层架构（延续列表页的三层结构）

```
views/knowledge-base/detail.vue   ← 页面：三态渲染 + 上传/拖拽/弹窗/确认等交互编排
        │
stores/knowledgeBase.ts           ← Store 追加详情态：current/docs + CRUD + 轮询管理
        │
api/knowledgeBase.ts              ← API 追加文档实体 + 5 个接口函数
        │
utils/request.ts                  ← 复用现有 get/post/del/upload 封装（upload 自带 60s 超时 + 进度回调）
```

原则不变：API 只管调用、Store 管共享状态（含跨页面复用的轮询）、页面管交互编排。
详情页直接复用列表页已有的 `rename`/`remove` action（重命名后同步更新 `current` 头卡）。

## 三、接口契约（本次新增，后端照此实现）

| 操作 | 方法与路径 | 说明 |
|---|---|---|
| 知识库详情 | `GET /knowledge-bases/:id` | 头卡信息 + 统计 |
| 文档列表 | `GET /knowledge-bases/:id/documents` | created_at DESC |
| 上传文档 | `POST /knowledge-bases/:id/documents` | multipart(file) 直传，返回 KnowledgeDoc（status=pending） |
| 删除文档 | `DELETE /knowledge-bases/:id/documents/:docId` | 连同索引片段删除 |
| 重试索引 | `POST /knowledge-bases/:id/documents/:docId/retry` | 状态回 processing |

**文档索引状态机**：`pending（排队）→ processing（解析/分块/向量化）→ indexed | failed`

实体 `KnowledgeDoc`：`id / name / size / ext / status / chunk_count / error_msg? / progress? / created_at`

- `error_msg`：failed 时的**可读**失败原因（如"PDF 文档包含加密内容，无法提取文本"），前端直接展示给用户
- `progress`：processing 时的百分比（0-100，可选）；后端不返回时前端显示"正在解析并建立索引..."不定进度文案

**上传方案决策**：multipart 直传（一步）而非"先传 /files/upload 拿 file_id 再绑定"（两步）。理由：
知识库文档上传是独立高频操作，单接口职责最清晰；复用 request.ts 的 `upload()` 封装天然获得进度条与 60s 大文件超时（项目工程惯例）。

## 四、Store 追加设计

在 `useKnowledgeBaseStore` 追加详情态（不动已有列表逻辑）：

```
current: KnowledgeBase | null   当前知识库（null = 加载失败 → 页面显示"不存在或已删除"）
docs: KnowledgeDoc[]            文档列表
docsLoading / uploading         加载中 / 上传中
fetchDetail(id)                 详情+文档列表并行加载（失败回退 null/[]）
refresh(id)                     静默刷新（轮询专用，失败不打扰，下轮重试）
uploadDoc(id, file, onProgress) 上传成功 unshift 到列表头
removeDoc / retryDoc            删除 filter / 重试就地替换
startPolling(id) / stopPolling  轮询管理（见下）
```

**轮询设计**（store 管理而非页面）：

- 触发点三处：进页 `fetchDetail` 后、每次上传成功后、重试成功后（`startPolling` 可重复调用，先清旧定时器即"续期"）
- **自愈停止**：每轮先检查 `hasActiveDocs()`，没有 pending/processing 就自动 `stopPolling`——不依赖调用方记得停止
- 页面 `onBeforeUnmount` 兜底 `stopPolling()`，防止后台空转
- `refresh` 同时刷新 kb + docs：头卡的 doc_count/chunk_count 统计跟随索引完成实时更新
- 为什么轮询不用 SSE/WebSocket：V0.3 索引是分钟级异步任务，轮询实现最简单、后端零改造成本；5s 间隔压力可忽略，量大后可平滑升级

## 五、页面实现要点

1. **布局**：1080px 内容宽度，全部使用 `--aws-*` 设计令牌，与效果图像素级对齐。
2. **头卡操作**：
   - 进入问答：`router.push('/chat')` + info 提示。V0.3 联调点：Chat 页后续需支持选择知识库（kb_id 注入检索上下文），届时改为携带状态跳转——当前不动 chat 页代码，最小侵入。
   - 重命名弹窗：与列表页同款自绘样式（Teleport + Transition），类名加 `kb-` 前缀避免与列表页弹窗样式冲突。
   - 删除知识库：确认文案带库名与文档数，删除后 `router.replace('/knowledge')`（replace 防止返回键回到已删除页）。
3. **上传交互**：
   - 拖拽：`dragover` 高亮边框 + `drop` 取 `dataTransfer.files`
   - 前端校验：扩展名白名单 + 20MB 上限，不合格 toast 跳过该文件（不中断批量中的其他文件）
   - **串行上传**（for-await）：避免并发争抢通道，进度条逐条推进更直观
   - 进度项是**页面本地状态**（不入 store）：上传成功即移除（列表顶部已有该文档）；失败保留标红 + 手动移除按钮
4. **文档列表四态**（效果图核心）：
   - 状态 tag 配色：绿=已完成、蓝=处理中（旋转 loader）、红=失败、灰=待处理
   - processing 子行：进度条（后端有 progress 显示百分比，没有显示不定进度文案）+ shimmer 动画
   - failed 子行：红底错误条展示 `error_msg` + 重试按钮（与操作列重试共用 `onRetry`）
   - 片段数列：仅 indexed 显示数值，其余 `--`
5. **加载失败空态**：`current === null` 时显示"知识库不存在或已被删除"+ 返回按钮（直接访问不存在的 id、或列表页删除后返回旧页的场景）。

## 六、文件清单

| 文件 | 变更 | 说明 |
|---|---|---|
| `src/api/knowledgeBase.ts` | 追加 | `KnowledgeDoc`/`DocStatus` 类型 + 5 个文档接口（import 增加 upload，移除未使用的 put） |
| `src/stores/knowledgeBase.ts` | 追加 | 详情态 + 轮询（未改动已有列表逻辑） |
| `src/views/knowledge-base/detail.vue` | 重写 | 占位页 → 完整详情页 |
| `notes/note.md` | 新增 | 本文档 |

路由 `/knowledge/:id` 列表页时期已注册，无需改动。

## 七、联调与后续计划

1. **联调前现状**：后端接口未实现时，详情页可正常打开 → 显示"不存在或已被删除"空态（fetchDetail 静默回退）+ 拦截器 toast；上传/重试失败会 toast 且保留现场。
2. **联调注意**：
   - `error_msg` 必须返回**用户可读**的中文原因（前端原样展示）
   - `progress` 可选，但返回后体验显著更好（进度条 vs 不定进度）
   - 状态流转中 processing → indexed/failed 要在 5s 轮询间隔内可见（即索引任务状态需落库，而非仅内存）
3. **后续接入点**：
   - "进入问答" → Chat 页支持知识库选择（kb_id → RAG 检索注入），当前已留 TODO 注释
   - 问答侧引用溯源展示（答案下方引用片段卡片，点击跳原文）

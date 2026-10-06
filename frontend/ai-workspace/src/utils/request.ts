/**
 * 全局请求库封装（基于 axios + fetch）
 * ===========================================================================
 * 封装思路（为什么这样设计）：
 *
 * 1. 统一 axios 实例：整个项目普通接口（JSON 收发）共用一个实例，baseURL / 超时 /
 *    header 默认值集中配置，避免每个 api 文件各自 new axios，保证行为一致。
 *
 * 2. 请求拦截器：每次请求自动从 auth store 读 token 注入 Authorization 头；
 *    额外处理 FormData——上传文件时不能强制设 application/json，否则会覆盖浏览器
 *    自动生成的 multipart/form-data; boundary=...，导致后端解析失败。
 *
 * 3. 响应拦截器：后端通常返回统一信封 { code, data, message }。
 *    - 成功(code===0)：剥离外层信封，只把 data 透传给业务。
 *    - 业务失败(code!==0)：统一用 ElMessage 弹错并 reject。
 *    - 401 鉴权失败：触发登出并跳转登录页。
 *    - 二进制响应(blob/arraybuffer)：下载/导出场景，response.data 是 Blob 不是 JSON，
 *      直接透传原始 response，不做信封拆包；同时兜底处理"后端用 JSON 报错但被包成 Blob"的情况。
 *
 * 4. 文件下载 download()：封装 responseType=blob + 文件名提取 + 浏览器触发保存，
 *    业务侧一行调用即可完成下载，无需手动拼 Blob URL。
 *
 * 5. 文件上传 upload()：封装 FormData + 上传进度回调，支持单/多文件，
 *    通过 onUploadProgress 把 axios 的进度事件透传给业务（如进度条）。
 *
 * 6. 流式请求 stream()：LLM Chat 场景后端返回 SSE(text/event-stream) 或 NDJSON 流。
 *    浏览器里 axios 底层走 XHR，无法边收边吐；这里用 fetch + ReadableStream 实现
 *    真正的流式读取，返回 async generator，调用方 for await...of 逐块消费，
 *    可直接增量写入 Vue 响应式变量实现打字机效果。
 *
 * 7. 类型友好：导出泛型方法，调用处拿到精确返回类型，编译期发现字段拼写错误。
 *
 * 8. 循环依赖规避：
 *    - auth store：顶层 import 的只是 store 工厂函数定义（不执行），真正 useAuthStore()
 *      调用放在拦截器/函数体内，运行时 Pinia 已就绪。
 *    - router：用动态 import('@/router') 懒加载，避免与 stores 形成模块级环引用。
 * ===========================================================================
 */
import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

/* -------------------------------------------------------------------------- */
/*  类型定义                                                                   */
/* -------------------------------------------------------------------------- */

/**
 * 后端统一响应体结构。
 * 绝大多数中后台后端都会用 { code, data, message } 信封包裹真实数据，
 * 在这里集中声明一次，响应拦截器据此拆包。
 */
export interface ApiResult<T = unknown> {
  code: number
  data: T
  message: string
}

/** 业务约定的成功 code。后端 code === 0 表示成功，非 0 表示业务错误。 */
const SUCCESS_CODE = 0

/** 流式响应支持的格式：SSE（标准 EventStream）或 NDJSON（逐行 JSON）。 */
export type StreamFormat = 'sse' | 'ndjson'

/* -------------------------------------------------------------------------- */
/*  实例创建                                                                   */
/* -------------------------------------------------------------------------- */

/**
 * 构建 baseURL：取 .env 中 VITE_APP_API_BASE_URL(后端域名) + VITE_GLOB_API_URL(接口前缀) 拼接。
 * Vite 只向客户端注入 VITE_ 前缀的环境变量；配 fallback 保证未配 .env 时也能开发。
 */
const BASE_URL =
  (import.meta.env.VITE_APP_API_BASE_URL as string | undefined) ?? 'http://127.0.0.1:8000'
const API_PREFIX = (import.meta.env.VITE_GLOB_API_URL as string | undefined) ?? '/api'

/** 完整前缀，stream() 用 fetch 时需要手动拼完整 URL（fetch 不走 axios 的 baseURL）。 */
const FULL_BASE = `${BASE_URL}${API_PREFIX}`

const service: AxiosInstance = axios.create({
  // 最终请求地址 = baseURL + 接口路径，例如 http://127.0.0.1:8000/api/auth/login
  baseURL: FULL_BASE,
  // 超时 15s：比常规接口略宽，兼容弱网与大数据量场景。
  // 注意：下载/上传/流式请求有自己的超时策略，不走这个全局值。
  timeout: 15000,
  // 默认请求头：声明 JSON 交互，后端按 application/json 解析 body。
  headers: {
    'Content-Type': 'application/json;charset=utf-8',
  },
})

/* -------------------------------------------------------------------------- */
/*  请求拦截器                                                                 */
/* -------------------------------------------------------------------------- */

/**
 * 为什么在这里注入 token：
 * 业务页面发请求时只关心"调哪个接口、传什么参数"，不应每次手动塞 Authorization。
 * 集中在拦截器里从 auth store 读 token，一处维护，所有请求自动带上。
 *
 * 为什么还要处理 Content-Type：
 * 实例默认头设了 application/json，但上传文件时传 FormData，浏览器必须自己设置
 * multipart/form-data; boundary=...（boundary 由浏览器根据内容生成）。
 * 如果不删掉默认的 application/json，后端拿不到 boundary，解析 FormData 会失败。
 */
service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 懒调用 useAuthStore：拦截器执行时 Pinia 已 install，避免模块加载顺序问题。
    const authStore = useAuthStore()
    if (authStore.token) {
      // 约定 Bearer 方案；若后端用其他鉴权头，改这一处即可。
      config.headers.Authorization = `Bearer ${authStore.token}`
    }

    // 上传文件场景：data 是 FormData 时，删掉默认 Content-Type，
    // 让浏览器自动设为 multipart/form-data; boundary=...，保证后端能正确解析。
    if (config.data instanceof FormData) {
      config.headers.delete('Content-Type')
    }

    return config
  },
  (error) => {
    // 请求构造阶段出错（极少见，如 config 非法），直接 reject，交由调用方处理。
    return Promise.reject(error)
  },
)

/* -------------------------------------------------------------------------- */
/*  响应拦截器                                                                 */
/* -------------------------------------------------------------------------- */

// 懒引用 router：避免与 stores/auth 形成模块级循环依赖。
// router/index.ts 仅在拦截器运行时被解析，此时 app 已 mount，路由可用。
let router: typeof import('@/router').default
async function getRouter() {
  if (!router) {
    router = (await import('@/router')).default
  }
  return router
}

service.interceptors.response.use(
  /**
   * 成功分支（HTTP 2xx）：
   * 注意 HTTP 200 不等于业务成功——后端可能用 code 表示业务状态。
   * 这里再按 code 拆分，保证业务层拿到的 Promise 一定代表"真成功"。
   */
  (response: AxiosResponse<ApiResult>) => {
    const config = response.config

    // ---- 二进制响应（下载/导出） bypass ----
    // responseType 为 blob/arraybuffer 时，response.data 是二进制而非 JSON 信封，
    // 不能按 code 拆包，直接透传原始 response，让 download() 自己处理。
    if (config.responseType === 'blob' || config.responseType === 'arraybuffer') {
      // 兜底：后端在下载接口出错时，可能仍以 JSON 返回错误体（被 axios 包成 Blob）。
      // 通过 content-type 判断：如果是 json，说明不是真正的文件，而是错误信息。
      const contentType = (response.headers['content-type'] || '') as string
      if (contentType.includes('application/json') && response.data instanceof Blob) {
        // 把 Blob 转成文本解析出业务错误，走统一错误处理。
        return response.data.text().then((text) => {
          try {
            const err = JSON.parse(text) as ApiResult
            if (err.code === 401) handleUnauthorized()
            ElMessage.error(err.message || '下载失败')
            return Promise.reject(new Error(err.message || '下载失败'))
          } catch {
            ElMessage.error('下载失败')
            return Promise.reject(new Error('下载失败'))
          }
        })
      }
      // 正常二进制文件：透传整个 response（download() 会从中取 data + headers）。
      return response as unknown as AxiosResponse
    }

    const res = response.data

    // 业务成功：剥离信封，只把 data 透传出去。
    // 拦截器按约定要返回 AxiosResponse，但我们把 data 直接透传是为了让调用方拿到
    // 干净的业务数据。这是 axios 社区常见的"拆包"做法，用 as unknown as AxiosResponse
    // 让类型对齐，最终在 request<T> 里再 as Promise<T> 收口。
    if (res.code === SUCCESS_CODE) {
	  // ElMessage.success(res.message || '请求成功')
      return res.data as unknown as AxiosResponse
    }

    // 401：token 失效或未登录，统一登出 + 跳转登录页，拦截后续无意义请求。
    if (res.code === 401) {
      handleUnauthorized()
      return Promise.reject(new Error(res.message || '登录已失效，请重新登录'))
    }

    // 其他业务错误：全局弹错 + reject，调用方用 catch 即可拿到错误。
    ElMessage.error(res.message || '请求失败')
    return Promise.reject(new Error(res.message || '请求失败'))
  },
  /**
   * 失败分支（HTTP 非 2xx / 网络错误）：
   * 集中把 axios 的各种网络/超时/状态码错误翻译成用户可读提示。
   */
  (error) => {
    // 超时：axios 把 code 设为 'ECONNABORTED'，message 含 timeout。
    if (error.code === 'ECONNABORTED' || /timeout/i.test(error.message)) {
      ElMessage.error('请求超时，请稍后重试')
      return Promise.reject(error)
    }

    // 有响应体：按 HTTP 状态码细分提示。
    if (error.response) {
      const status = error.response.status
      switch (status) {
        case 401:
          // HTTP 层 401：后端网关/鉴权中间件直接拦截，同样触发登出。
          handleUnauthorized()
          ElMessage.error('登录已失效，请重新登录')
          break
        case 403:
          ElMessage.error('没有访问权限')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 500:
          ElMessage.error('服务器内部错误')
          break
        default:
          ElMessage.error(`请求失败（${status}）`)
      }
    } else if (error.request) {
      // 请求已发出但无响应：通常是断网或后端未启动。
      ElMessage.error('网络异常，请检查网络连接')
    } else {
      // 请求配置阶段出错。
      ElMessage.error(error.message || '请求发送失败')
    }
    return Promise.reject(error)
  },
)

/* -------------------------------------------------------------------------- */
/*  鉴权失效统一处理                                                           */
/* -------------------------------------------------------------------------- */

/**
 * 为什么单独抽函数：
 * 401 可能出现在业务 code 或 HTTP status 两条路径，逻辑一致，抽出来复用避免重复。
 * 这里做两件事：清掉本地登录态（防止过期 token 继续被带出）+ 跳登录页。
 */
function handleUnauthorized() {
  const authStore = useAuthStore()
  authStore.logout()
  // 跳登录页，并带 redirect 参数，登录成功后可回跳原页面。
  getRouter().then((r) =>
    r.push({
      path: '/auth',
      query: { redirect: r.currentRoute.value.fullPath },
    }),
  )
}

/* ========================================================================== */
/*  对外暴露的请求方法                                                         */
/* ========================================================================== */

/**
 * 核心泛型请求方法（普通 JSON 接口）。
 * <T> 是后端 data 字段的真实类型，调用方传入后，返回值即为 Promise<T>，
 * 业务侧无需再做类型断言。
 *
 * @example
 * const user = await request<UserInfo>({ url: '/user/1', method: 'get' })
 */
export function request<T = unknown>(config: AxiosRequestConfig): Promise<T> {
  // service.request 返回 AxiosResponse，但经响应拦截器拆包后实际 resolve 的是 res.data。
  // 此处用 as Promise<T> 把类型对齐，让调用方拿到干净的业务数据类型。
  return service.request(config) as Promise<T>
}

/** GET 封装：把 params 放到 query string，最常用的查询方式。 */
export function get<T = unknown>(
  url: string,
  params?: Record<string, unknown>,
  config?: AxiosRequestConfig,
): Promise<T> {
  return request<T>({ url, method: 'get', params, ...config })
}

/** POST 封装：提交 body，常用于创建资源。 */
export function post<T = unknown>(
  url: string,
  data?: Record<string, unknown> | unknown[],
  config?: AxiosRequestConfig,
): Promise<T> {
  return request<T>({ url, method: 'post', data, ...config })
}

/** PUT 封装：整体更新资源。 */
export function put<T = unknown>(
  url: string,
  data?: Record<string, unknown> | unknown[],
  config?: AxiosRequestConfig,
): Promise<T> {
  return request<T>({ url, method: 'put', data, ...config })
}

/** DELETE 封装：删除资源，参数可能走 query 或 body，二者都支持。 */
export function del<T = unknown>(
  url: string,
  params?: Record<string, unknown>,
  config?: AxiosRequestConfig,
): Promise<T> {
  return request<T>({ url, method: 'delete', params, ...config })
}

/* -------------------------------------------------------------------------- */
/*  文件下载                                                                   */
/* -------------------------------------------------------------------------- */

/** 下载方法可选项。 */
export interface DownloadOptions {
  /** 请求参数（GET query）。 */
  params?: Record<string, unknown>
  /** 请求体（POST 场景的下载，如导出报表）。不传则默认用 GET。 */
  data?: Record<string, unknown>
  /** 使用 POST 方式下载（默认 GET）。导出报表类接口通常用 POST + body。 */
  method?: 'get' | 'post'
  /** 自定义文件名；不传则从响应头 Content-Disposition 里解析。 */
  filename?: string
  /** 额外的 axios 配置。 */
  config?: AxiosRequestConfig
}

/**
 * 文件下载封装。
 *
 * 为什么单独封装：
 * 下载涉及 responseType=blob、文件名解析、浏览器触发保存三步，每处都写一遍很啰嗦。
 * 统一封装后业务侧只需：await download('/export', { params: { id: 1 } })。
 *
 * 实现要点：
 * 1. 设 responseType: 'blob'，让 axios 把响应体当二进制接收。
 * 2. 响应拦截器识别 blob 后会透传原始 response（不做信封拆包），这里拿到的是完整 response。
 * 3. 文件名优先用调用方传入的；否则从 Content-Disposition: attachment; filename="xxx" 解析。
 * 4. 用 URL.createObjectURL 生成临时链接，<a> 标签 click 触发下载，最后 revoke 释放内存。
 *
 * @returns 返回 Blob，调用方如需预览（如图片/PDF）可直接用。
 */
export async function download(url: string, options: DownloadOptions = {}): Promise<Blob> {
  const { params, data, method = 'get', filename, config } = options

  // 用 service 直接发请求，responseType=blob 让拦截器走二进制 bypass 分支。
  const response = await service.request<
    Blob,
    AxiosResponse<Blob>
  >({
    url,
    method,
    params,
    data,
    responseType: 'blob',
    ...config,
  })

  const blob = response.data

  // 解析文件名：优先调用方指定 → Content-Disposition → 兜底用 URL 末段 + 扩展名猜测。
  let resolvedName = filename
  if (!resolvedName) {
    const disposition = (response.headers['content-disposition'] || '') as string
    // 匹配 filename="xxx.pdf" 或 filename=xxx.pdf（兼容有无引号两种写法）。
    const match = /filename\*?=(?:UTF-8'')?["']?([^"';]+)/i.exec(disposition)
    resolvedName = match?.[1] ? decodeURIComponent(match[1]) : url.split('/').pop() || 'download'
  }

  // 创建临时 URL → 隐藏 <a> 标签 click 触发下载 → 释放内存。
  const blobUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = resolvedName
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  // revoke 放在宏任务里，确保 click 下载已触发；立即释放部分浏览器会下载失败。
  setTimeout(() => URL.revokeObjectURL(blobUrl), 0)

  return blob
}

/* -------------------------------------------------------------------------- */
/*  文件上传                                                                   */
/* -------------------------------------------------------------------------- */

/** 上传进度回调参数（axios ProgressEvent 的简化版）。 */
export interface UploadProgress {
  /** 已上传字节数。 */
  loaded: number
  /** 总字节数（未知时为 0）。 */
  total: number
  /** 进度百分比 0-100；total 未知时为 0。 */
  percent: number
}

/** 上传方法可选项。 */
export interface UploadOptions {
  /** 额外的表单字段（会一起追加到 FormData 里）。 */
  extraData?: Record<string, string | Blob>
  /** 进度回调，用于驱动进度条。 */
  onProgress?: (progress: UploadProgress) => void
  /** 额外的 axios 配置。 */
  config?: AxiosRequestConfig
}

/**
 * 文件上传封装。
 *
 * 为什么单独封装：
 * 1. 帮调用方构造 FormData（追加文件 + 额外字段），省去重复样板代码。
 * 2. 把 axios 的 onUploadProgress 事件翻译成简洁的 { loaded, total, percent } 回调，
 *    业务侧拿到百分比直接绑进度条即可。
 * 3. 请求拦截器会自动删掉默认 application/json 头，让浏览器设 multipart boundary。
 * 4. 上传成功后走正常 JSON 响应拦截器拆包，返回值就是后端的业务数据。
 *
 * @param url    上传接口路径
 * @param file   要上传的文件（单个 File/Blob）；多文件场景传 file[] + field
 * @param field  文件在 FormData 中的字段名，默认 'file'
 * @param options 额外表单字段 + 进度回调
 *
 * @example
 * const res = await upload('/avatar', file, 'avatar', {
 *   onProgress: (p) => (progress.value = p.percent)
 * })
 */
export async function upload<T = unknown>(
  url: string,
  file: File | Blob | File[],
  field = 'file',
  options: UploadOptions = {},
): Promise<T> {
  const { extraData, onProgress, config } = options

  // 构造 FormData：先追加额外字段，再追加文件。
  const formData = new FormData()
  if (extraData) {
    for (const [key, value] of Object.entries(extraData)) {
      formData.append(key, value)
    }
  }
  // 多文件：同名 field 追加多次，后端按数组接收。
  if (Array.isArray(file)) {
    file.forEach((f) => formData.append(field, f))
  } else {
    formData.append(field, file)
  }

  return request<T>({
    url,
    method: 'post',
    data: formData,
    // 上传通常耗时较长，单独给个更宽的超时，避免大文件被全局 15s 超时打断。
    timeout: 60000,
    // axios 上传进度事件，这里翻译成简洁的 percent 回调。
    onUploadProgress: (e) => {
      if (onProgress) {
        onProgress({
          loaded: e.loaded,
          total: e.total || 0,
          // total 可能未知(浏览器不提供)，此时 percent=0，业务侧可按"上传中"态处理。
          percent: e.total ? Math.round((e.loaded / e.total) * 100) : 0,
        })
      }
    },
    ...config,
  })
}

/* -------------------------------------------------------------------------- */
/*  流式请求（LLM Chat 场景）                                                  */
/* -------------------------------------------------------------------------- */

/** 流式请求可选项。 */
export interface StreamOptions {
  /** 中断信号，用于用户手动停止生成（传 AbortController.signal）。 */
  signal?: AbortSignal
  /** 流格式；不传则按响应 content-type 自动判断。 */
  format?: StreamFormat
  /** 流式请求通常需要更长超时，这里用毫秒；0 表示不超时（推荐，LLM 生成可能很久）。 */
  timeout?: number
}

/**
 * 流式请求（LLM Chat 场景）。
 *
 * 为什么用 fetch 而不是 axios：
 * 浏览器里 axios 底层走 XMLHttpRequest，XHR 只能等整个响应接收完才回调，
 * 无法边接收边吐数据。而 fetch 返回的 Response.body 是 ReadableStream，
 * 配合 TextDecoder 可以实时逐块读取，实现打字机效果。
 *
 * 为什么返回 async generator：
 * 调用方用 for await...of 逐块消费，每 yield 一块就追加到响应式变量，
 * UI 自然流式渲染；比回调式更符合 JS 异步直觉，也方便用 break 提前中断。
 *
 * 格式说明：
 * - SSE (text/event-stream)：每条消息形如 `data: {...}\n\n`，以 `data: [DONE]` 结束。
 * - NDJSON (application/x-ndjson)：每行一个完整 JSON，以换行分隔。
 *
 * @param url   接口路径（会拼到 baseURL 后）
 * @param data  请求体（如 { messages, model, stream: true }）
 * @param options signal 中断、format 指定、timeout 超时
 *
 * @yields 每个数据块的字符串内容（已从 SSE/NDJSON 中提取出的 payload，通常是 JSON 字符串）
 *
 * @example
 * const ctrl = new AbortController()
 * try {
 *   for await (const chunk of stream('/chat/completions', payload, { signal: ctrl.signal })) {
 *     replyText.value += chunk   // 增量渲染打字机效果
 *   }
 * } catch (e) {
 *   if (e.name !== 'AbortError') throw e
 * }
 */
export async function* stream(
  url: string,
  data: Record<string, unknown>,
  options: StreamOptions = {},
): AsyncGenerator<string, void, unknown> {
  const { signal, format, timeout = 0 } = options

  // 构造完整 URL：fetch 不走 axios 的 baseURL，需手动拼接。
  const fullUrl = `${FULL_BASE}${url}`

  // 流式请求同样需要带 token 鉴权，这里从 auth store 读取。
  const authStore = useAuthStore()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
  }
  if (authStore.token) {
    headers.Authorization = `Bearer ${authStore.token}`
  }

  // 可选超时：用 AbortController + setTimeout 实现，超时后 abort 中断流。
  // timeout=0 表示不超时（LLM 生成可能持续很久，不该被强行打断）。
  const timeoutCtrl = new AbortController()
  let timer: ReturnType<typeof setTimeout> | undefined
  if (timeout > 0) {
    timer = setTimeout(() => timeoutCtrl.abort(), timeout)
  }
  // 把外部 signal 和内部超时 signal 合并：任一触发都会中断。
  const mergedSignal = signal
    ? mergeSignals([signal, timeoutCtrl.signal])
    : timeoutCtrl.signal

  const response = await fetch(fullUrl, {
    method: 'POST',
    headers,
    body: JSON.stringify(data),
    signal: mergedSignal,
  })

  // HTTP 非 2xx：尝试解析错误信息并抛出，让调用方 catch。
  if (!response.ok) {
    let msg = `请求失败（${response.status}）`
    try {
      const errBody = await response.json()
      msg = (errBody as ApiResult).message || msg
      if (response.status === 401) handleUnauthorized()
    } catch {
      // 响应体不是 JSON，用默认提示。
    }
    ElMessage.error(msg)
    throw new Error(msg)
  }

  // body 为空（后端没返回流）：直接结束。
  if (!response.body) {
    if (timer) clearTimeout(timer)
    return
  }

  // 按响应 content-type 判断格式：text/event-stream → sse；x-ndjson → ndjson。
  const contentType = response.headers.get('content-type') || ''
  const detectedFormat: StreamFormat = format ?? (contentType.includes('ndjson') ? 'ndjson' : 'sse')

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  // 缓冲区：一次 read() 可能读到半条消息（跨块），需攒够完整消息再处理。
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      // 把二进制 chunk 解码成文本，追加到缓冲区。
      buffer += decoder.decode(value, { stream: true })

      // 按格式切分缓冲区，提取完整消息，剩余半条留在 buffer 等下一块。
      if (detectedFormat === 'sse') {
        // SSE 以 \n\n 分隔事件，一个事件内可能有多行 data:，需拼接。
        let sepIndex: number
        while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
          const rawEvent = buffer.slice(0, sepIndex)
          buffer = buffer.slice(sepIndex + 2)

          // 一个 SSE 事件可能含多行 data:，按规范拼成一条。
          const dataLines = rawEvent
            .split('\n')
            .filter((line) => line.startsWith('data:'))
            .map((line) => line.slice(5).trim())

          if (dataLines.length === 0) continue
          const payload = dataLines.join('\n')

          // [DONE] 是 OpenAI 约定的流结束标记，收到即终止生成器。
          if (payload === '[DONE]') return

          // yield 出去让调用方消费（通常是 JSON 字符串，调用方自行 JSON.parse）。
          yield payload
        }
      } else {
        // NDJSON：每行一个完整 JSON，以 \n 分隔。
        let newlineIndex: number
        while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
          const line = buffer.slice(0, newlineIndex).trim()
          buffer = buffer.slice(newlineIndex + 1)
          if (line) yield line
        }
      }
    }

    // 流结束后，缓冲区可能还有最后一条没换行符结尾的残余数据。
    buffer += decoder.decode() // flush decoder
    if (buffer.trim()) {
      if (detectedFormat === 'sse') {
        // 处理最后一条不以 \n\n 结尾的事件。
        const dataLines = buffer
          .split('\n')
          .filter((line) => line.startsWith('data:'))
          .map((line) => line.slice(5).trim())
        if (dataLines.length > 0) {
          const payload = dataLines.join('\n')
          if (payload !== '[DONE]') yield payload
        }
      } else if (buffer.trim()) {
        yield buffer.trim()
      }
    }
  } finally {
    // 无论正常结束还是中断，都要释放 reader 并清理超时定时器。
    reader.releaseLock()
    if (timer) clearTimeout(timer)
  }
}

/**
 * 合并多个 AbortSignal：任一 abort 即触发结果 signal abort。
 *
 * 为什么需要：流式请求同时面临"用户手动停止"和"内部超时"两个中断来源，
 * fetch 只接受一个 signal，用合并器把两者汇总成一个。
 */
function mergeSignals(signals: AbortSignal[]): AbortSignal {
  const controller = new AbortController()
  for (const sig of signals) {
    if (sig.aborted) {
      controller.abort()
      break
    }
    sig.addEventListener('abort', () => controller.abort(), { once: true })
  }
  return controller.signal
}

/** 导出原始实例：极少数自定义场景可直接操作实例。 */
export default service

/**
 * 认证状态管理（Pinia Store）
 * ===========================================================================
 * 职责：
 *   集中管理登录态（token、用户信息），提供 login / register / logout 等方法，
 *   并通过 localStorage 持久化，刷新页面后登录态不丢失。
 *
 * 联调真实后端时你需要改哪里：
 *   1. 顶部 import 引入 request.ts 封装的 post 方法。
 *   2. login() / register() 里把 mock 构造 token/user 的代码替换为调用真实接口。
 *   3. 真实接口返回的 { token, user } 结构需与 AuthState 对齐（不一致则在接口层适配）。
 *   4. 用户已注册校验等本地 mock 逻辑（register 里的 registry）删除，由后端返回。
 *
 * 调用示例（真实接口联调版）：
 *   import { post } from '@/utils/request'
 *   const result = await post<AuthState>('/auth/login', { email, password })
 *   token.value = result.token
 *   user.value = result.user
 * ===========================================================================
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
// 联调时取消下一行注释，用 request.ts 封装的 post 调后端登录/注册接口
import { registerApi, loginApi, authMe } from '@/api/auth'

/**
 * 用户信息。
 * 联调时按后端返回的字段调整：
 *   - 如果后端返回的是 userId / avatar 等字段，在这里补充声明。
 *   - nickname 是可选字段（?），后端没返回也不报错。
 */
export interface AuthUser {
  email: string
  nickname: string
  id?: number,
  is_active: boolean
}

/**
 * 登录态整体结构。
 * 后端登录/注册接口成功后，通常返回 { token, user }；
 * 如果后端返回的字段名不同（如 accessToken / profile），在此处改名或在接口层做映射。
 */
export interface AuthState {
  access_token: string
  user: AuthUser
}

/* -------------------------------------------------------------------------- */
/*  常量：localStorage 的 key                                                  */
/* -------------------------------------------------------------------------- */

// 登录态持久化存储的 key，存的是 { token, user } 的 JSON 字符串。
const TOKEN_KEY = 'aws_auth_state'
// "记住我"功能存的邮箱，用于下次打开登录页自动回填邮箱。
const REMEMBER_KEY = 'aws_auth_remember'

// 存储用户信息，防止登录后刷新丢失
const USER_INFO = 'auth_user'

/* -------------------------------------------------------------------------- */
/*  工具函数                                                                   */
/* -------------------------------------------------------------------------- */

/** 邮箱格式校验正则（前端兜底校验，后端也应再校验一次）。 */
const EMAIL_RE = /^[\w.+-]+@[\w-]+\.[\w.-]+$/

/**
 * 从 localStorage 读取持久化的登录态。
 * 页面刷新时调用，恢复 token 和 user，避免用户被踢回登录页。
 * 解析失败（被篡改/损坏）时返回 null，走未登录分支。
 */
function loadPersistedState(): string | null {
  try {
    const raw = localStorage.getItem(TOKEN_KEY)
    return raw ? raw : ''
  } catch {
    return ''
  }
}

function loadUserInfo(): AuthUser | null {
  try {
    const user = localStorage.getItem(USER_INFO)
    return user ? JSON.parse(user) : null
  }catch {
    return null
  }
}

/**
 * 把token写入 localStorage。
 * 登录成功后调用，保证刷新后状态不丢失。
 */
function persistState(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

/**
 * 存储用户信息用户工作台页
 ***/ 
function saveUserInfo(info: AuthUser) {
  localStorage.setItem(USER_INFO, JSON.stringify(info))
}

/**
 * 清除持久化的登录态。
 * 登出或 token 失效时调用，同时清掉"记住我"的邮箱。
 */
function clearPersistedState() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REMEMBER_KEY)
  localStorage.removeItem(USER_INFO)
}

// /**
//  * 模拟网络延迟的工具函数（仅 mock 阶段用）。
//  * 联调真实接口后此函数可删除。
//  */
// function delay<T>(value: T, ms = 600): Promise<T> {
//   return new Promise((resolve) => setTimeout(() => resolve(value), ms))
// }

/* -------------------------------------------------------------------------- */
/*  Store 定义                                                                 */
/* -------------------------------------------------------------------------- */

export const useAuthStore = defineStore('auth', () => {
  // 初始化时从 localStorage 恢复登录态，无则为空（未登录）。
  const persisted = loadPersistedState()

  const userInfo = loadUserInfo()
  // ---- 状态 ----
  // 鉴权 token，请求拦截器会自动塞到 Authorization 头。
  const token = ref<string>(persisted ?? '')
  // 当前登录用户信息，UI 层展示用户名/头像等。
  const user = ref<AuthUser | null>(userInfo ?? null)

  // 请求中标记，UI 层据此显示 loading 态（按钮置灰、转圈等）。
  const loading = ref(false)
  // 错误信息，UI 层展示错误提示条。
  const error = ref('')

  // ---- 计算属性 ----
  // 是否已登录：token 非空即为已登录，路由守卫据此判断跳转。
  const isAuthenticated = computed(() => !!token.value)

  /* -------------------------------------------------------------------------- */
  /*  登录                                                                       */
  /* -------------------------------------------------------------------------- */

  /**
   * 登录。
   *
   *
   * @param email    邮箱
   * @param password 密码
   * @param remember 是否记住邮箱（勾选"记住我"）
   */
  async function login(email: string, password: string, remember: boolean) {
    // 每次调用前清掉上一次的错误信息。
    error.value = ''
    email = email.trim()

    // ---- 前端表单校验（后端也会校验，这里是为了即时反馈、减少无效请求） ----
    if (!email) {
      error.value = '请输入邮箱'
      throw new Error(error.value)
    }
    if (!EMAIL_RE.test(email)) {
      error.value = '邮箱格式不正确'
      throw new Error(error.value)
    }
    if (!password) {
      error.value = '请输入密码'
      throw new Error(error.value)
    }
    if (password.length < 6) {
      error.value = '密码至少 6 位'
      throw new Error(error.value)
    }

    loading.value = true
    try {
      const result: AuthState = await loginApi(email, password);
      if (result.access_token) {
        token.value = result.access_token
        user.value = result.user
        persistState(result.access_token)
      }
      // "记住我"：勾选则把邮箱存起来，下次登录页自动回填；不勾选则清除。
      if (remember) {
        localStorage.setItem(REMEMBER_KEY, email)
      } else {
        localStorage.removeItem(REMEMBER_KEY)
      }
    } finally {
      // 无论成功失败都关闭 loading，避免按钮一直转圈。
      loading.value = false
    }
  }

  /* -------------------------------------------------------------------------- */
  /*  注册                                                                       */
  /* -------------------------------------------------------------------------- */

  /**
   * 注册。
   *
   *
   * @param email    邮箱
   * @param password 密码
   * @param confirm  确认密码（前端校验一致性，后端可不传）
   */
  async function register(email: string, password: string, confirm: string, nickname: string) {
    error.value = ''
    email = email.trim()

    // ---- 前端表单校验 ----
    if (!email) {
      error.value = '请输入邮箱'
      throw new Error(error.value)
    }
    if (!EMAIL_RE.test(email)) {
      error.value = '邮箱格式不正确'
      throw new Error(error.value)
    }
    if (!password) {
      error.value = '请输入密码'
      throw new Error(error.value)
    }
    if (password.length < 6) {
      error.value = '密码至少 6 位'
      throw new Error(error.value)
    }
    if (password !== confirm) {
      error.value = '两次输入的密码不一致'
      throw new Error(error.value)
    }

    loading.value = true
    try {
      const params = {
        email,
        password,
        confirm_password: confirm,
        nickname
      }
      const result:AuthState = await registerApi(params);
      
      if (result.access_token){
        persistState(result.access_token)
      }
      
    } finally {
      loading.value = false
    }
  }

  /* -------------------------------------------------------------------------- */
  /*  登出                                                                       */
  /* -------------------------------------------------------------------------- */

  /**
   * 登出。
   * 清掉内存中的登录态 + localStorage 持久化数据。
   *
   * 联调时如果后端有"注销接口"（比如让 token 失效），可以在这里先调一下：
   *   await post('/auth/logout')
   * 但即使接口失败也应该清本地态，避免残留。
   */
  function logout() {
    token.value = ''
    user.value = null
    error.value = ''
    clearPersistedState()
  }

  /* -------------------------------------------------------------------------- */
  /*  辅助方法                                                                   */
  /* -------------------------------------------------------------------------- */

  /**
   * 读取"记住我"的邮箱。
   * 登录页打开时调用，自动回填邮箱输入框。
   */
  function rememberedEmail(): string {
    return localStorage.getItem(REMEMBER_KEY) ?? ''
  }

  /**
   * 清除错误信息。
   * 切换登录/注册 tab 或输入框获得焦点时调用，让错误提示消失。
   */
  function clearError() {
    error.value = ''
  }

  // 获取当前用户信息
  async function authCurrentUser() {
    loading.value = true
    try {
      const result:AuthUser = await authMe();
      user.value = result
      if (result?.is_active){
        saveUserInfo(result)
      }
    }catch (e) {
      console.error(e)
    } finally {
      loading.value = false
    }
    
  }
  // 对外暴露：组件/其他 store 通过 useAuthStore() 拿到这些响应式状态和方法。
  return {
    token,
    user,
    loading,
    error,
    isAuthenticated,
    login,
    register,
    logout,
    rememberedEmail,
    clearError,
    authCurrentUser
  }
})

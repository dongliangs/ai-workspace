<template>
  <div class="auth-container">
    <div class="auth-card">
      <!-- Tabs -->
      <nav class="auth-tabs">
        <button
          type="button"
          class="auth-tab"
          :class="{ 'tab-active': mode === 'login' }"
          @click="switchMode('login')"
        >
          登录
        </button>
        <button
          type="button"
          class="auth-tab"
          :class="{ 'tab-active': mode === 'register' }"
          @click="switchMode('register')"
        >
          注册
        </button>
      </nav>

      <!-- Login form -->
      <div
        v-if="mode === 'login'"
        class="form-section"
      >
        <header class="form-head">
          <h2 class="form-title">
            欢迎回来
          </h2>
          <p class="form-subtitle">
            请登录以继续 AI 工作台
          </p>
        </header>

        <form
          class="auth-form"
          novalidate
          @submit.prevent="handleLogin"
        >
          <div class="field">
            <div class="field-control">
              <Mail
                class="field-icon"
                :size="18"
              />
              <input
                v-model="loginForm.email"
                type="email"
                class="field-input"
                placeholder="请输入邮箱"
                autocomplete="email"
                @focus="clearFieldError"
              >
            </div>
          </div>

          <div class="field">
            <div class="field-control">
              <Lock
                class="field-icon"
                :size="18"
              />
              <input
                v-model="loginForm.password"
                :type="showLoginPwd ? 'text' : 'password'"
                class="field-input"
                placeholder="请输入密码"
                autocomplete="current-password"
                @focus="clearFieldError"
              >
              <button
                type="button"
                class="pwd-toggle"
                :aria-label="showLoginPwd ? '隐藏密码' : '显示密码'"
                @click="showLoginPwd = !showLoginPwd"
              >
                <Eye
                  v-if="showLoginPwd"
                  :size="18"
                />
                <EyeOff
                  v-else
                  :size="18"
                />
              </button>
            </div>
          </div>

          <div class="form-row">
            <label class="remember">
              <input
                v-model="loginForm.remember"
                type="checkbox"
                class="remember-check"
              >
              <span class="remember-label">记住我</span>
            </label>
            <a
              href="#"
              class="link-muted"
              @click.prevent="onForgotPassword"
            >忘记密码?</a>
          </div>

          <p
            v-if="authStore.error"
            class="form-error"
          >
            {{ authStore.error }}
          </p>

          <button
            type="submit"
            class="btn-primary"
            :disabled="authStore.loading"
          >
            <Loader2
              v-if="authStore.loading"
              class="spin"
              :size="18"
            />
            <span>{{ authStore.loading ? '登录中…' : '登录' }}</span>
          </button>

          <p class="switch-cta">
            还没有账号?
            <a
              href="#"
              class="link-accent"
              @click.prevent="switchMode('register')"
            >立即注册</a>
          </p>
        </form>
      </div>

      <!-- Register form -->
      <div
        v-else
        class="form-section"
      >
        <header class="form-head">
          <h2 class="form-title">
            创建账号
          </h2>
          <p class="form-subtitle">
            填写信息以开始使用 AI 工作台
          </p>
        </header>

        <form
          class="auth-form"
          novalidate
          @submit.prevent="handleRegister"
        >
          <!-- 设置昵称 -->
          <div class="field">
            <div class="field-control">
              <User
                class="field-icon"
                :size="18"
              />
              <input
                v-model="registerForm.nickname"
                type="nickname"
                class="field-input"
                placeholder="请设置一个昵称"
                autocomplete="nickname"
                @focus="clearFieldError"
              >
            </div>
          </div>
          <div class="field">
            <div class="field-control">
              <Mail
                class="field-icon"
                :size="18"
              />
              <input
                v-model="registerForm.email"
                type="email"
                class="field-input"
                placeholder="请输入邮箱"
                autocomplete="email"
                @focus="clearFieldError"
              >
            </div>
          </div>
          <div class="field">
            <div class="field-control">
              <Lock
                class="field-icon"
                :size="18"
              />
              <input
                v-model="registerForm.password"
                :type="showRegPwd ? 'text' : 'password'"
                class="field-input"
                placeholder="请输入密码"
                autocomplete="new-password"
                @focus="clearFieldError"
              >
              <button
                type="button"
                class="pwd-toggle"
                :aria-label="showRegPwd ? '隐藏密码' : '显示密码'"
                @click="showRegPwd = !showRegPwd"
              >
                <Eye
                  v-if="showRegPwd"
                  :size="18"
                />
                <EyeOff
                  v-else
                  :size="18"
                />
              </button>
            </div>
          </div>

          <div class="field">
            <div class="field-control">
              <Lock
                class="field-icon"
                :size="18"
              />
              <input
                v-model="registerForm.confirm"
                :type="showRegConfirm ? 'text' : 'password'"
                class="field-input"
                placeholder="请再次输入密码"
                autocomplete="new-password"
                @focus="clearFieldError"
              >
              <button
                type="button"
                class="pwd-toggle"
                :aria-label="showRegConfirm ? '隐藏密码' : '显示密码'"
                @click="showRegConfirm = !showRegConfirm"
              >
                <Eye
                  v-if="showRegConfirm"
                  :size="18"
                />
                <EyeOff
                  v-else
                  :size="18"
                />
              </button>
            </div>
          </div>

          <p
            v-if="authStore.error"
            class="form-error"
          >
            {{ authStore.error }}
          </p>

          <button
            type="submit"
            class="btn-primary"
            :disabled="authStore.loading"
          >
            <Loader2
              v-if="authStore.loading"
              class="spin"
              :size="18"
            />
            <span>{{ authStore.loading ? '注册中…' : '注册' }}</span>
          </button>

          <p class="switch-cta">
            已有账号?
            <a
              href="#"
              class="link-accent"
              @click.prevent="switchMode('login')"
            >立即登录</a>
          </p>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Mail, Lock, User, Eye, EyeOff, Loader2 } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'

type AuthMode = 'login' | 'register'

const router = useRouter()
const authStore = useAuthStore()

const mode = ref<AuthMode>('login')

const remembered = authStore.rememberedCredentials()
const loginForm = reactive({
  email: remembered.email,
  password: remembered.password,
  remember: !!remembered.email,
})

const registerForm = reactive({
  email: '', // 邮箱
  password: '', // 密码
  confirm: '', // 确认密码
  nickname: '' // 昵称
})

const showLoginPwd = ref(false)
const showRegPwd = ref(false)
const showRegConfirm = ref(false)

function switchMode(next: AuthMode) {
  if (mode.value === next) return
  mode.value = next
  authStore.clearError()
}

function clearFieldError() {
  if (authStore.error) authStore.clearError()
}

async function handleLogin() {
  try {
    await authStore.login(loginForm.email, loginForm.password, loginForm.remember)
    router.push('/workspace')
  } catch {
    /* error surfaced via store */
  }
}

async function handleRegister() {
  try {
    await authStore.register(registerForm.email, registerForm.password, registerForm.confirm, registerForm.nickname)
    // 注册成功后 切到登录窗口
    switchMode('login')
    // router.push('/workspace')
  } catch {
    /* error surfaced via store */
  }
}

function onForgotPassword() {
  authStore.clearError()
  // Stub: in a real app this would navigate to a forgot-password flow.
  mode.value = 'login'
  loginForm.password = ''
}
</script>

<style scoped>
.auth-container {
  width: 100%;
  max-width: 400px;
  padding: 40px 48px;
}

.auth-card {
  width: 100%;
}

/* ---------- Tabs ---------- */
.auth-tabs {
  display: flex;
  gap: 28px;
  border-bottom: 1px solid var(--aws-border);
  margin-bottom: 32px;
}
.auth-tab {
  position: relative;
  padding: 0 0 10px;
  font-size: 15px;
  font-weight: 500;
  color: var(--aws-placeholder);
  background: none;
  border: none;
  cursor: pointer;
  transition: color 0.15s;
}
.auth-tab:hover {
  color: var(--aws-muted);
}
.tab-active {
  color: var(--aws-foreground);
}
.tab-active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 2px;
  background: var(--aws-primary);
  border-radius: 2px;
}

/* ---------- Form header ---------- */
.form-head {
  margin-bottom: 24px;
}
.form-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--aws-foreground);
  line-height: 1.3;
}
.form-subtitle {
  margin-top: 6px;
  font-size: 13px;
  color: var(--aws-muted);
}

/* ---------- Fields ---------- */
.field {
  margin-bottom: 16px;
}
.field-control {
  position: relative;
  display: flex;
  align-items: center;
}
.field-icon {
  position: absolute;
  left: 12px;
  color: var(--aws-placeholder);
  pointer-events: none;
  flex: none;
}
.field-input {
  width: 100%;
  height: 44px;
  padding: 0 44px 0 40px;
  border: 1px solid var(--aws-border-strong);
  border-radius: var(--aws-radius-md);
  font-size: 14px;
  color: var(--aws-foreground);
  background: var(--aws-input);
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.field-input::placeholder {
  color: var(--aws-placeholder);
}
.field-input:focus {
  border-color: var(--aws-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}
.pwd-toggle {
  position: absolute;
  right: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: none;
  color: var(--aws-placeholder);
  cursor: pointer;
  border-radius: 4px;
  transition: color 0.15s, background-color 0.15s;
}
.pwd-toggle:hover {
  color: var(--aws-muted);
  background: var(--aws-sidebar-active);
}

/* ---------- Row: remember + forgot ---------- */
.form-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 4px 0 20px;
}
.remember {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  user-select: none;
}
.remember-check {
  width: 15px;
  height: 15px;
  accent-color: var(--aws-primary);
  cursor: pointer;
}
.remember-label {
  font-size: 13px;
  color: var(--aws-muted);
}
.link-muted {
  font-size: 13px;
  color: var(--aws-muted);
  transition: color 0.15s;
}
.link-muted:hover {
  color: var(--aws-primary);
}

/* ---------- Error ---------- */
.form-error {
  margin: 0 0 16px;
  padding: 8px 12px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: var(--aws-radius-md);
  color: #dc2626;
  font-size: 13px;
  line-height: 1.4;
}

/* ---------- Button ---------- */
.btn-primary {
  width: 100%;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: none;
  border-radius: var(--aws-radius-md);
  background: var(--aws-primary);
  color: var(--aws-primary-foreground);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.15s, opacity 0.15s;
}
.btn-primary:hover:not(:disabled) {
  background: var(--aws-primary-hover);
}
.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.spin {
  animation: aws-spin 0.7s linear infinite;
}
@keyframes aws-spin {
  to {
    transform: rotate(360deg);
  }
}

/* ---------- Switch CTA ---------- */
.switch-cta {
  margin-top: 20px;
  text-align: center;
  font-size: 13px;
  color: var(--aws-muted);
}
.link-accent {
  color: var(--aws-primary);
  font-weight: 500;
  transition: color 0.15s;
}
.link-accent:hover {
  color: var(--aws-primary-hover);
}

/* ---------- Form transition ---------- */
.form-section {
  animation: aws-fade 0.25s ease;
}
@keyframes aws-fade {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ---------- Responsive ---------- */
@media (max-width: 480px) {
  .auth-container {
    padding: 32px 24px;
  }
}
</style>

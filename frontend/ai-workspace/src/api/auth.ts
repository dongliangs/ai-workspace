
// 用户注册登录

import { post, get } from '@/utils/request'
import { rsaEncrypt, setPublicKey, hasPublicKey } from '@/utils/rsa'

import type { AuthState, AuthUser } from '@/stores/auth'

/**
 * 从后端获取 RSA 公钥并设置到 rsa 工具类中。
 * - 首次调用时发起请求，后续调用直接复用缓存的 Promise（同一会话只请求一次）。
 * - 请求失败时清除缓存，允许下次重试。
 */
let _fetchPromise: Promise<void> | null = null

export function fetchPublicKey(): Promise<void> {
	if (!_fetchPromise) {
		_fetchPromise = get<{ public_key: string }>('/auth/public-key')
			.then((res) => {
				setPublicKey(res.public_key)
			})
			.catch((err) => {
				// 获取失败时清除缓存，允许下次重试
				_fetchPromise = null
				throw err
			})
	}
	return _fetchPromise
}

interface regissterParams {
	email: string,
	password: string,
	confirm_password: string,
	nickname: string
}

/**
 * 注册接口。
 * 密码在发送前用 RSA 公钥加密，避免明文密码裸露在网络请求体中。
 * 公钥在加密前通过 fetchPublicKey() 从后端动态获取。
 */
export async function registerApi<T>(options: regissterParams) {
	// 确保公钥已获取（已获取则立即返回，不重复请求）
	await fetchPublicKey()
	const encryptedPassword = await rsaEncrypt(options.password)
	const encryptedConfirm = await rsaEncrypt(options.confirm_password)
	return post<T>('/auth/register', {
		email: options.email,
		password: encryptedPassword,
		confirm_password: encryptedConfirm,
		nickname: options.nickname,
	})
}

/**
 * 登录接口。
 * 密码在发送前用 RSA 公钥加密，避免明文密码裸露在网络请求体中。
 * 公钥在加密前通过 fetchPublicKey() 从后端动态获取。
 */
export async function loginApi(email: string, password: string) {
	// 确保公钥已获取（已获取则立即返回，不重复请求）
	await fetchPublicKey()
	const encryptedPassword = await rsaEncrypt(password)
	return post<AuthState>('/auth/login', { email, password: encryptedPassword })
}

export function authMe() {
	return get<AuthUser>('/auth/me')
}

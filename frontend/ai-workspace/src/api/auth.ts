
// 用户注册登录

import { post, get } from '@/utils/request'

import type { AuthState, AuthUser } from '@/stores/auth'

interface regissterParams {
	email: string,
	password: string,
	confirm_password: string,
	nickname: string
}
export function registerApi<T>(options: regissterParams) {
	return post<T>('/auth/register',{...options})
}

export function loginApi(email: string,password: string) {
	return post<AuthState>('/auth/login', {email, password})

}

export function authMe() {
	return get<AuthUser>('/auth/me')
}
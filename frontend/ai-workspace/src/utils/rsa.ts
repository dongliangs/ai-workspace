/**
 * RSA 非对称加密工具
 * ===========================================================================
 * 用途：登录/注册时对密码做应用层加密，避免明文密码裸露在网络请求体中。
 *
 * 方案：RSA-OAEP（浏览器内置 Web Crypto API，无需第三方依赖）。
 *   - 后端启动时自动生成 RSA 密钥对，私钥保留在服务端内存中
 *   - 前端通过 GET /auth/public-key 接口获取公钥，调用 setPublicKey() 设置
 *   - 前端用公钥加密密码 → 得到 base64 密文 → 发送给后端
 *   - 后端用私钥解密密文 → 得到明文密码 → 再交给 pwdlib 校验
 *
 * 注意：
 *   - RSA-OAEP 单次加密长度受限（2048 位密钥最多加密 190 字节），
 *     密码通常远小于此，足够使用。
 *   - 公钥不再硬编码，而是运行时从后端接口动态获取。
 *   - 传输层应同时启用 HTTPS，应用层加密是额外保护而非替代 TLS。
 * ===========================================================================
 */

/** 动态设置的 RSA 公钥（PEM 格式，SPKI），由 setPublicKey() 写入 */
let _publicKeyPem: string | null = null

/** 缓存导入后的 CryptoKey，避免每次加密都重新 import */
let cachedPublicKey: CryptoKey | null = null

/**
 * 设置 RSA 公钥（PEM 格式字符串）。
 * 调用后自动清除旧的 CryptoKey 缓存，下次加密时会重新导入新公钥。
 *
 * @param pem PEM 格式的公钥字符串
 */
export function setPublicKey(pem: string): void {
  _publicKeyPem = pem
  cachedPublicKey = null
}

/**
 * 判断公钥是否已设置。
 */
export function hasPublicKey(): boolean {
  return _publicKeyPem !== null
}

/**
 * 把 PEM 格式公钥转换为 ArrayBuffer（移除头尾和换行，base64 解码）。
 */
function pemToBuffer(pem: string): ArrayBuffer {
  const base64 = pem
    .replace(/-----BEGIN [A-Z ]+-----/g, '')
    .replace(/-----END [A-Z ]+-----/g, '')
    .replace(/\s+/g, '')
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes.buffer
}

/**
 * 导入 RSA 公钥（SPKI 格式）。
 * 只导入一次，后续复用缓存。
 * 如果公钥未设置，抛出错误。
 */
async function importPublicKey(): Promise<CryptoKey> {
  if (cachedPublicKey) return cachedPublicKey
  if (!_publicKeyPem) {
    throw new Error('RSA 公钥尚未设置，请先调用 fetchPublicKey() 获取公钥')
  }
  const keyData = pemToBuffer(_publicKeyPem)
  cachedPublicKey = await crypto.subtle.importKey(
    'spki',
    keyData,
    { name: 'RSA-OAEP', hash: 'SHA-256' },
    false, // 不可导出
    ['encrypt'],
  )
  return cachedPublicKey
}

/**
 * 用 RSA 公钥加密明文，返回 base64 编码的密文字符串。
 *
 * @param plaintext 待加密的明文字符串（如密码）
 * @returns base64 密文
 */
export async function rsaEncrypt(plaintext: string): Promise<string> {
  const publicKey = await importPublicKey()
  const encoder = new TextEncoder()
  const data = encoder.encode(plaintext)
  const encrypted = await crypto.subtle.encrypt(
    { name: 'RSA-OAEP' },
    publicKey,
    data,
  )
  // ArrayBuffer → base64
  const bytes = new Uint8Array(encrypted)
  let binary = ''
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}

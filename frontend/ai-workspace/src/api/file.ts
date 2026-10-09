/**
 * 文件上传相关接口
 * ===========================================================================
 * V0.2 新增：Agent 模式需要用户上传 Excel 等文件进行分析。
 * 前端选文件后调 POST /files/upload，后端保存文件并返回 file_id + 元信息。
 * 后续 Agent 工具（如 analyze_excel）只接收 file_id，由 File Service 解析路径。
 * ===========================================================================
 */
import { upload, type UploadProgress } from '@/utils/request'

/** 上传成功后后端返回的文件信息 */
export interface UploadedFile {
  id: number
  name: string
  size: number
  url?: string
}

/**
 * 上传单个文件到后端。
 *
 * 复用 request.ts 的 upload() 封装（FormData + 进度回调 + 60s 超时）。
 *
 * @param file       要上传的文件
 * @param onProgress 进度回调（百分比 0-100）
 * @returns 后端返回的文件信息（含 file_id）
 */
export function uploadFile(file: File, onProgress?: (p: UploadProgress) => void) {
  return upload<UploadedFile>('/files/upload', file, 'file', { onProgress })
}

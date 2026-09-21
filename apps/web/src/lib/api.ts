export type User = { id: string; email: string }
export type CVSummary = { id: string; title: string; folder: string; version: number; starred: boolean; updated_at: string }
export type Compilation = { id: string; cv_id: string; status: 'queued'|'compiling'|'success'|'failed'; log: string; download_url: string|null }
export type CV = CVSummary & { document: Record<string, unknown>; tex_source: string; latest_compilation: Compilation|null }
export type Annotation = { id:string; quoted_text:string; note:string; resolved:boolean; created_at:string; block_id?:string }
export type Revision = { id:string; version:number; created_at:string }
export type JobDescription = { id:string; title:string; content:string; source_type:string; created_at:string }

export class APIError extends Error { constructor(message:string, public status:number, public detail?:unknown) { super(message) } }

export async function api<T>(path:string, init:RequestInit = {}):Promise<T> {
  const response = await fetch(path, { credentials:'include', ...init, headers: init.body instanceof FormData ? init.headers : { 'Content-Type':'application/json', ...(init.headers || {}) } })
  if (response.status === 204) return undefined as T
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = data.detail
    const message = typeof detail === 'string' ? detail : detail?.message || data.message || `Request failed (${response.status})`
    throw new APIError(message, response.status, detail)
  }
  return data
}

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: unknown,
  ) {
    super(message)
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = init.body instanceof FormData
    ? init.headers
    : { 'Content-Type': 'application/json', ...(init.headers || {}) }
  const response = await fetch(path, {
    credentials: 'include',
    ...init,
    headers,
  })
  if (response.status === 204) return undefined as T
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = data.detail
    const message = typeof detail === 'string' ? detail : detail?.message || data.message || `Request failed (${response.status})`
    throw new APIError(message, response.status, detail)
  }
  return data
}

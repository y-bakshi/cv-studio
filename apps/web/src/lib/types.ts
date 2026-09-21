export type User = {
  id: string
  email: string
}

export type CVSummary = {
  id: string
  title: string
  folder: string
  version: number
  starred: boolean
  updated_at: string
}

export type CompilationStatus = 'queued' | 'compiling' | 'success' | 'failed'

export type Compilation = {
  id: string
  cv_id: string
  status: CompilationStatus
  log: string
  download_url: string | null
}

export type CV = CVSummary & {
  document: Record<string, unknown>
  tex_source: string
  latest_compilation: Compilation | null
}

export type Annotation = {
  id: string
  quoted_text: string
  note: string
  resolved: boolean
  created_at: string
  block_id?: string
}

export type Revision = {
  id: string
  version: number
  created_at: string
}

export type JobDescription = {
  id: string
  title: string
  content: string
  source_type: string
  created_at: string
}

export type EditorMode = 'visual' | 'tex' | 'pdf'

export type TextSelection = {
  text: string
  from: number
  to: number
}

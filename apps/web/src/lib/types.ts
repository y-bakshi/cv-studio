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

export type EditorMode = 'visual' | 'json' | 'tex' | 'pdf'

export type TextSelection = {
  text: string
  from: number
  to: number
}

export type ResumeStyle = {
  template: 'standard' | 'compact'
  paper: 'letter' | 'a4'
  font: 'sans' | 'serif' | 'classic'
  font_size: 10 | 11 | 12
  accent: string
  bullet: 'dot' | 'dash' | 'square'
}

export type SectionName = 'skills' | 'experience' | 'projects' | 'education'

export interface Resume {
  contact: {
    name: string; subtitle: string; email: string; phone: string; location: string
    tags: string[]; links: { id: string; label: string; url: string }[]
  }
  skills: { id: string; name: string; skills: string[] }[]
  experience: { id: string; company: string; role: string; location: string; start: string; end: string; summary: string; bullets: string[] }[]
  projects: { id: string; name: string; link_text: string; organization: string; location: string; start: string; end: string; bullets: string[] }[]
  education: { id: string; school: string; degree: string; location: string; start: string; end: string; gpa: string; achievements: string[]; coursework: string[]; bullets: string[] }[]
  section_order: SectionName[]
  style: ResumeStyle
}

export interface ResumeDocument { id: string; version: number; resume: Resume }

export interface TexDocument { id: string; version: number; tex_source: string; preamble: string | null }

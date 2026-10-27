import { useCallback, useEffect, useRef, useState } from 'react'

import type { ExportFormat } from '@/components/ExportSheet'
import { api, APIError } from '@/lib/api'
import type {
  Annotation,
  Compilation,
  CV,
  CVSummary,
  EditorMode,
  JobDescription,
  Resume,
  ResumeDocument,
  Revision,
  TexDocument,
  TextSelection,
} from '@/lib/types'

const COMPILE_POLL_INTERVAL_MS = 750
const COMPILE_POLL_ATTEMPTS = 40
const AUTO_SAVE_DELAY_MS = 900
const EMPTY_SELECTION: TextSelection = { text: '', from: 0, to: 0 }

export function useCVWorkspace() {
  const [items, setItems] = useState<CVSummary[]>([])
  const [cv, setCV] = useState<CV | null>(null)
  const [resume, setResume] = useState<Resume | null>(null)
  const [tex, setTex] = useState<TexDocument | null>(null)
  const [mode, setModeState] = useState<EditorMode>('visual')
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [selection, setSelection] = useState<TextSelection>(EMPTY_SELECTION)
  const [annotations, setAnnotations] = useState<Annotation[]>([])
  const [jobs, setJobs] = useState<JobDescription[]>([])
  const [revisions, setRevisions] = useState<Revision[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const [showExport, setShowExport] = useState(false)
  const [notice, setNotice] = useState('')

  // Latest values for async work; every write is chained so versions never race.
  const saveTimer = useRef<number | undefined>(undefined)
  const queue = useRef<Promise<unknown>>(Promise.resolve())
  const version = useRef(0)
  const pending = useRef<{ resume?: Resume; cv?: CV }>({})
  const cvId = useRef('')

  const notify = useCallback((message: string) => {
    setNotice(message)
    window.setTimeout(() => setNotice(''), 2500)
  }, [])

  const refreshList = useCallback(async () => {
    setItems(await api<CVSummary[]>('/api/cvs'))
  }, [])

  const loadResume = useCallback(async (id: string) => {
    const data = await api<ResumeDocument>(`/api/cvs/${id}/resume`)
    version.current = data.version
    setResume(data.resume)
    return data
  }, [])

  const loadRelatedData = useCallback(async (cvId: string) => {
    const [nextAnnotations, nextJobs, nextRevisions] = await Promise.all([
      api<Annotation[]>(`/api/cvs/${cvId}/annotations`),
      api<JobDescription[]>(`/api/cvs/${cvId}/job-descriptions`),
      api<Revision[]>(`/api/cvs/${cvId}/revisions`),
    ])
    setAnnotations(nextAnnotations)
    setJobs(nextJobs)
    setRevisions(nextRevisions)
  }, [])

  const fail = useCallback((error: unknown) => {
    if (error instanceof APIError && error.status === 409) {
      notify('Conflict detected — reopen the CV before saving')
    } else {
      notify(error instanceof Error ? error.message : 'Save failed')
    }
  }, [notify])

  /** Write whatever is pending (résumé content, then title/starred), in order. */
  const flush = useCallback((): Promise<void> => {
    window.clearTimeout(saveTimer.current)
    const run = async () => {
      const { resume: nextResume, cv: nextCV } = pending.current
      pending.current = {}
      if (!nextResume && !nextCV) return
      setSaving(true)
      try {
        if (nextResume) {
          const saved = await api<ResumeDocument>(`/api/cvs/${cvId.current}/resume`, {
            method: 'PUT',
            body: JSON.stringify({ resume: nextResume, expected_version: version.current }),
          })
          version.current = saved.version
          setCV((current) => current ? { ...current, version: saved.version } : current)
        }
        if (nextCV) {
          const saved = await api<CV>(`/api/cvs/${nextCV.id}`, {
            method: 'PATCH',
            body: JSON.stringify({
              title: nextCV.title,
              folder: nextCV.folder,
              starred: nextCV.starred,
              expected_version: version.current,
            }),
          })
          version.current = saved.version
          setCV((current) => current ? { ...current, version: saved.version } : current)
          await refreshList()
        }
        setDirty(Boolean(pending.current.resume || pending.current.cv))
      } catch (error) {
        fail(error)
      } finally {
        setSaving(false)
      }
    }
    queue.current = queue.current.then(run, run)
    return queue.current as Promise<void>
  }, [fail, refreshList])

  const schedule = useCallback(() => {
    setDirty(true)
    window.clearTimeout(saveTimer.current)
    saveTimer.current = window.setTimeout(() => void flush(), AUTO_SAVE_DELAY_MS)
  }, [flush])

  const openCV = useCallback(async (id: string) => {
    await flush()
    const data = await api<CV>(`/api/cvs/${id}`)
    setCV(data)
    setTex(null)
    setDirty(false)
    await loadResume(id)
    await loadRelatedData(id)
  }, [flush, loadRelatedData, loadResume])

  useEffect(() => { cvId.current = cv?.id ?? '' }, [cv?.id])

  useEffect(() => { void refreshList() }, [refreshList])

  useEffect(() => {
    if (items.length > 0 && !cv) void openCV(items[0].id)
  }, [cv, items, openCV])

  useEffect(() => () => window.clearTimeout(saveTimer.current), [])

  const createCV = async () => {
    const created = await api<CV>('/api/cvs', {
      method: 'POST',
      body: JSON.stringify({ title: 'Untitled CV' }),
    })
    await refreshList()
    setCV(created)
    setTex(null)
    await loadResume(created.id)
    setAnnotations([])
    setJobs([])
    setRevisions(await api(`/api/cvs/${created.id}/revisions`))
  }

  /** Edit résumé content from the visual editor (debounced save). */
  const editResume = (next: Resume) => {
    if (!cv) return
    setResume(next)
    pending.current = { ...pending.current, resume: next }
    schedule()
  }

  /** Edit title/starred. */
  const editCV = (next: CV) => {
    setCV(next)
    pending.current = { ...pending.current, cv: next }
    schedule()
  }

  const loadTex = useCallback(async () => {
    if (!cv) return
    await flush()
    setTex(await api<TexDocument>(`/api/cvs/${cv.id}/resume/tex`))
  }, [cv, flush])

  const setMode = (next: EditorMode) => {
    setModeState(next)
    if (next === 'tex') void loadTex()
  }

  /** Apply edited JSON text. Returns an error message, or null on success. */
  const applyJSON = async (text: string): Promise<string | null> => {
    if (!cv) return null
    let parsed: unknown
    try {
      parsed = JSON.parse(text)
    } catch (error) {
      return `Invalid JSON: ${(error as Error).message}`
    }
    try {
      await flush()
      const saved = await api<ResumeDocument>(`/api/cvs/${cv.id}/resume`, {
        method: 'PUT',
        body: JSON.stringify({ resume: parsed, expected_version: version.current }),
      })
      version.current = saved.version
      setResume(saved.resume)
      setTex(null)
      notify('JSON applied')
      return null
    } catch (error) {
      if (error instanceof APIError && Array.isArray(error.detail)) {
        const first = error.detail[0] as { loc?: string[]; msg?: string }
        return `${(first.loc || []).join('.')}: ${first.msg}`
      }
      return error instanceof Error ? error.message : 'Could not apply JSON'
    }
  }

  /** Apply edited LaTeX. Rejected when it leaves the structured dialect. */
  const applyTex = async (text: string): Promise<string | null> => {
    if (!cv) return null
    try {
      await flush()
      const saved = await api<TexDocument>(`/api/cvs/${cv.id}/resume/tex`, {
        method: 'PUT',
        body: JSON.stringify({ tex_source: text, expected_version: version.current }),
      })
      version.current = saved.version
      setTex(saved)
      await loadResume(cv.id)
      notify('LaTeX applied')
      return null
    } catch (error) {
      if (error instanceof APIError && error.status === 422) return error.message
      return error instanceof Error ? error.message : 'Could not apply LaTeX'
    }
  }

  const pollCompilation = async (id: string) => {
    // TODO(realtime-compilation): Replace polling with SSE or WebSocket events
    // when compilation moves to the durable worker.
    for (let attempt = 0; attempt < COMPILE_POLL_ATTEMPTS; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, COMPILE_POLL_INTERVAL_MS))
      const item = await api<Compilation>(`/api/compilations/${id}`)
      setCV((current) => current ? { ...current, latest_compilation: item } : current)
      if (item.status === 'success') {
        notify('PDF compiled successfully')
        return item
      }
      if (item.status === 'failed') {
        notify('Compilation failed — inspect the log')
        return item
      }
    }
    notify('Compilation is taking longer than expected')
    return null
  }

  const compile = async (show = true) => {
    if (!cv) return null
    await flush()
    const item = await api<Compilation>(`/api/cvs/${cv.id}/compile`, { method: 'POST' })
    setCV((current) => current ? { ...current, latest_compilation: item } : current)
    if (show) setModeState('pdf')
    return pollCompilation(item.id)
  }

  const download = (url: string) => {
    window.location.assign(url)
  }

  const exportAs = async (format: ExportFormat) => {
    if (!cv) return
    await flush()
    if (format === 'pdf') {
      const item = await compile(false)
      if (item?.status === 'success' && item.download_url) download(item.download_url)
      return
    }
    download(`/api/cvs/${cv.id}/resume/export/${format}`)
  }

  const annotate = async (note: string) => {
    if (!cv || !selection.text) return
    const item = await api<Annotation>(`/api/cvs/${cv.id}/annotations`, {
      method: 'POST',
      body: JSON.stringify({
        quoted_text: selection.text,
        start_offset: selection.from,
        end_offset: selection.to,
        note,
      }),
    })
    setAnnotations((current) => [item, ...current])
    setSelection(EMPTY_SELECTION)
  }

  const resolveAnnotation = async (id: string) => {
    const item = await api<Annotation>(`/api/annotations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ resolved: true }),
    })
    setAnnotations((current) => current.map((entry) => entry.id === id ? item : entry))
  }

  const deleteAnnotation = async (id: string) => {
    await api(`/api/annotations/${id}`, { method: 'DELETE' })
    setAnnotations((current) => current.filter((entry) => entry.id !== id))
  }

  const addJob = async (value: { title: string; content: string } | File) => {
    if (!cv) return
    let item: JobDescription
    if (value instanceof File) {
      const data = new FormData()
      data.append('file', value)
      item = await api(`/api/cvs/${cv.id}/job-descriptions/upload`, { method: 'POST', body: data })
    } else {
      item = await api(`/api/cvs/${cv.id}/job-descriptions`, { method: 'POST', body: JSON.stringify(value) })
    }
    setJobs((current) => [item, ...current])
    notify('Job description saved')
  }

  const restoreRevision = async (revision: Revision) => {
    if (!cv) return
    try {
      await flush()
      const restored = await api<CV>(`/api/cvs/${cv.id}/revisions/${revision.id}/restore`, { method: 'POST' })
      setCV(restored)
      setTex(null)
      await loadResume(cv.id)
      setShowHistory(false)
      setRevisions(await api(`/api/cvs/${cv.id}/revisions`))
      notify(`Restored version ${revision.version}`)
    } catch (error) {
      notify(error instanceof Error ? error.message : 'Restore failed')
    }
  }

  return {
    items, cv, resume, tex, mode, dirty, saving, selection, annotations, jobs, revisions,
    showHistory, showExport, notice,
    setMode, setSelection, setShowHistory, setShowExport,
    openCV, createCV, editResume, editCV, flush, applyJSON, applyTex, compile, exportAs,
    annotate, resolveAnnotation, deleteAnnotation, addJob, restoreRevision,
  }
}

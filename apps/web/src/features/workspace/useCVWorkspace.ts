import { useCallback, useEffect, useRef, useState } from 'react'

import { api, APIError } from '@/lib/api'
import type {
  Annotation,
  Compilation,
  CV,
  CVSummary,
  EditorMode,
  JobDescription,
  Revision,
  TextSelection,
} from '@/lib/types'

const COMPILE_POLL_INTERVAL_MS = 750
const COMPILE_POLL_ATTEMPTS = 40
const AUTO_SAVE_DELAY_MS = 900
const EMPTY_SELECTION: TextSelection = { text: '', from: 0, to: 0 }

export function useCVWorkspace() {
  const [items, setItems] = useState<CVSummary[]>([])
  const [cv, setCV] = useState<CV | null>(null)
  const [mode, setMode] = useState<EditorMode>('visual')
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [selection, setSelection] = useState<TextSelection>(EMPTY_SELECTION)
  const [annotations, setAnnotations] = useState<Annotation[]>([])
  const [jobs, setJobs] = useState<JobDescription[]>([])
  const [revisions, setRevisions] = useState<Revision[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const [notice, setNotice] = useState('')
  const saveTimer = useRef<number | undefined>(undefined)

  const notify = useCallback((message: string) => {
    setNotice(message)
    window.setTimeout(() => setNotice(''), 2500)
  }, [])

  const refreshList = useCallback(async () => {
    setItems(await api<CVSummary[]>('/api/cvs'))
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

  const save = useCallback(async (snapshot: CV | null = cv): Promise<CV | null> => {
    if (!snapshot || saving) return snapshot
    setSaving(true)
    try {
      const saved = await api<CV>(`/api/cvs/${snapshot.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          title: snapshot.title,
          folder: snapshot.folder,
          document: snapshot.document,
          tex_source: mode === 'tex' ? snapshot.tex_source : undefined,
          starred: snapshot.starred,
          expected_version: snapshot.version,
        }),
      })
      setCV(saved)
      setDirty(false)
      await refreshList()
      return saved
    } catch (error) {
      if (error instanceof APIError && error.status === 409) {
        notify('Conflict detected — reopen the CV before saving')
      } else {
        notify(error instanceof Error ? error.message : 'Save failed')
      }
      return null
    } finally {
      setSaving(false)
    }
  }, [cv, mode, notify, refreshList, saving])

  const openCV = useCallback(async (id: string) => {
    if (dirty) await save()
    const data = await api<CV>(`/api/cvs/${id}`)
    setCV(data)
    setDirty(false)
    await loadRelatedData(id)
  }, [dirty, loadRelatedData, save])

  useEffect(() => {
    refreshList()
  }, [refreshList])

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
    setAnnotations([])
    setJobs([])
    setRevisions([])
  }

  const scheduleSave = (next: CV) => {
    setCV(next)
    setDirty(true)
    window.clearTimeout(saveTimer.current)
    saveTimer.current = window.setTimeout(() => void save(next), AUTO_SAVE_DELAY_MS)
  }

  const updateTeX = (next: CV) => {
    // TeX mode is intentionally explicit: unlike visual edits, raw source waits
    // for Save so an incomplete command is not persisted mid-keystroke.
    setCV(next)
    setDirty(true)
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
        return
      }
      if (item.status === 'failed') {
        notify('Compilation failed — inspect the log')
        return
      }
    }
    notify('Compilation is taking longer than expected')
  }

  const compile = async () => {
    if (!cv) return
    const current = dirty ? (await save()) || cv : cv
    const item = await api<Compilation>(`/api/cvs/${current.id}/compile`, {
      method: 'POST',
    })
    setCV({ ...current, latest_compilation: item })
    setMode('pdf')
    void pollCompilation(item.id)
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
      item = await api(`/api/cvs/${cv.id}/job-descriptions/upload`, {
        method: 'POST',
        body: data,
      })
    } else {
      item = await api(`/api/cvs/${cv.id}/job-descriptions`, {
        method: 'POST',
        body: JSON.stringify(value),
      })
    }
    setJobs((current) => [item, ...current])
    notify('Job description saved')
  }

  const restoreRevision = async (revision: Revision) => {
    if (!cv) return
    const restored = await api<CV>(
      `/api/cvs/${cv.id}/revisions/${revision.id}/restore`,
      { method: 'POST' },
    )
    setCV(restored)
    setDirty(false)
    setShowHistory(false)
    setRevisions(await api(`/api/cvs/${cv.id}/revisions`))
    notify(`Restored version ${revision.version}`)
  }

  return {
    items,
    cv,
    mode,
    dirty,
    saving,
    selection,
    annotations,
    jobs,
    revisions,
    showHistory,
    notice,
    setMode,
    setSelection,
    setShowHistory,
    setCV,
    openCV,
    createCV,
    scheduleSave,
    updateTeX,
    save,
    compile,
    annotate,
    resolveAnnotation,
    deleteAnnotation,
    addJob,
    restoreRevision,
  }
}

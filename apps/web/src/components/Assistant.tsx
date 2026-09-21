import { type FormEvent, useState } from 'react'
import { Check, ChevronUp, MessageSquare, Paperclip, Trash2 } from 'lucide'

import type { Annotation, JobDescription } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { MorphGlyph } from './MorphGlyph'

type AssistantProps = {
  annotations: Annotation[]
  jobs: JobDescription[]
  selection: string
  onAnnotate: (note: string) => void
  onResolve: (id: string) => void
  onDelete: (id: string) => void
  onAddJob: (value: { title: string; content: string } | File) => void
}

export default function Assistant({
  annotations,
  jobs,
  selection,
  onAnnotate,
  onResolve,
  onDelete,
  onAddJob,
}: AssistantProps) {
  const [note, setNote] = useState('')
  const [jobOpen, setJobOpen] = useState(false)
  const [job, setJob] = useState('')

  const submitAnnotation = (event: FormEvent) => {
    event.preventDefault()
    if (!note.trim()) return
    onAnnotate(note)
    setNote('')
  }

  const saveJob = () => {
    if (!job.trim()) return
    onAddJob({ title: 'Pasted job description', content: job })
    setJob('')
    setJobOpen(false)
  }

  return (
    <aside className="assistant">
      <header><p className="eyebrow">Review workspace</p><h2>Annotations</h2></header>

      {selection && (
        <section className="selection-card">
          <small>Selected text</small>
          <p>“{selection}”</p>
          <form onSubmit={submitAnnotation}>
            <Textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Add a note or change request…"
            />
            <Button size="sm"><MorphGlyph icon={MessageSquare} size={13} />Annotate</Button>
          </form>
        </section>
      )}

      <div className="annotation-list">
        {annotations.map((annotation) => (
          <article key={annotation.id} className={annotation.resolved ? 'resolved' : ''}>
            <p>“{annotation.quoted_text}”</p>
            {annotation.note && <strong>{annotation.note}</strong>}
            <div>
              <Button
                variant="ghost"
                size="sm"
                disabled={annotation.resolved}
                onClick={() => onResolve(annotation.id)}
              >
                <MorphGlyph icon={Check} size={12} />
                {annotation.resolved ? 'Resolved' : 'Resolve'}
              </Button>
              <Button variant="ghost" size="icon" onClick={() => onDelete(annotation.id)}>
                <MorphGlyph icon={Trash2} size={12} />
              </Button>
            </div>
          </article>
        ))}
        {!annotations.length && (
          <p className="empty">Select text in the visual editor to create an annotation.</p>
        )}
      </div>

      <section className="job-area">
        <Button variant="outline" className="wide" onClick={() => setJobOpen(!jobOpen)}>
          <MorphGlyph icon={jobOpen ? ChevronUp : Paperclip} size={14} />
          Job description {jobs.length ? `(${jobs.length})` : ''}
        </Button>
        {jobOpen && (
          <>
            <Textarea
              value={job}
              onChange={(event) => setJob(event.target.value)}
              placeholder="Paste a job description…"
            />
            <Button className="wide" onClick={saveJob}>Save description</Button>
            <label className="upload">
              or upload TXT, Markdown, or PDF
              <input
                type="file"
                accept=".txt,.md,.pdf"
                onChange={(event) => {
                  const file = event.target.files?.[0]
                  if (file) onAddJob(file)
                }}
              />
            </label>
          </>
        )}
      </section>

      <div className="chat-coming">
        <span>✦</span>
        <p>
          <strong>AI assistant comes next</strong><br />
          Ollama and hosted providers will create reviewable change proposals here.
        </p>
      </div>
    </aside>
  )
}

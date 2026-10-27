import { useState } from 'react'
import { Check, Copy, Download } from 'lucide'

import { MorphGlyph } from '@/components/MorphGlyph'
import { Button } from '@/components/ui/button'

type SourceEditorProps = {
  kind: 'json' | 'tex'
  value: string
  filename: string
  /** Resolves to an error message when the source was rejected, else null. */
  onApply: (text: string) => Promise<string | null>
}

const COPY = {
  json: {
    label: 'Résumé JSON',
    hint: 'The whole résumé as one JSON document. Copy it, or edit it and apply.',
  },
  tex: {
    label: 'LaTeX source',
    hint: 'Edit the \\resume… commands and apply to sync the visual editor. Anything outside that dialect is rejected.',
  },
}

export default function SourceEditor({ kind, value, filename, onApply }: SourceEditorProps) {
  const [text, setText] = useState(value)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [applying, setApplying] = useState(false)
  const changed = text !== value

  const copy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1500)
  }

  const download = () => {
    const url = URL.createObjectURL(new Blob([text], { type: 'text/plain' }))
    const link = Object.assign(document.createElement('a'), { href: url, download: filename })
    link.click()
    URL.revokeObjectURL(url)
  }

  const apply = async () => {
    setApplying(true)
    setError(await onApply(text))
    setApplying(false)
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b bg-background px-4 py-2">
        <p className="text-xs text-muted-foreground">{COPY[kind].hint}</p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => void copy()}>
            <MorphGlyph icon={copied ? Check : Copy} size={14} />{copied ? 'Copied' : 'Copy'}
          </Button>
          <Button variant="outline" size="sm" onClick={download}>
            <MorphGlyph icon={Download} size={14} />Download
          </Button>
          <Button size="sm" disabled={!changed || applying} onClick={() => void apply()}>Apply changes</Button>
        </div>
      </div>
      {error && (
        <p role="alert" className="border-b border-destructive/30 bg-destructive/10 px-4 py-2 text-xs text-destructive">
          {error}
        </p>
      )}
      <textarea
        aria-label={COPY[kind].label}
        spellCheck={false}
        value={text}
        onChange={(event) => setText(event.target.value)}
        className="flex-1 resize-none bg-zinc-900 p-5 font-mono text-xs leading-relaxed text-zinc-100 outline-none"
      />
    </div>
  )
}

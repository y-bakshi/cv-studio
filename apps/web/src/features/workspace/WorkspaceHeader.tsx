import {
  Braces,
  Check,
  CircleCheck,
  Download,
  FileText,
  History,
  LoaderCircle,
  Play,
  Save,
  Star,
  StarOff,
} from 'lucide'

import { MorphGlyph } from '@/components/MorphGlyph'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import type { CV, EditorMode } from '@/lib/types'

type WorkspaceHeaderProps = {
  cv: CV | null
  mode: EditorMode
  dirty: boolean
  saving: boolean
  onModeChange: (mode: EditorMode) => void
  onChange: (cv: CV) => void
  onHistory: () => void
  onSave: () => void
  onCompile: () => void
}

export function WorkspaceHeader({
  cv,
  mode,
  dirty,
  saving,
  onModeChange,
  onChange,
  onHistory,
  onSave,
  onCompile,
}: WorkspaceHeaderProps) {
  if (!cv) {
    return <header className="topbar"><strong>Select or create a CV</strong></header>
  }

  const compiling = ['queued', 'compiling'].includes(cv.latest_compilation?.status || '')
  const compileIcon = compiling
    ? LoaderCircle
    : cv.latest_compilation?.status === 'success'
      ? CircleCheck
      : Play
  const saveIcon = saving ? LoaderCircle : dirty ? Save : Check

  return (
    <header className="topbar">
      <div className="title-area">
        <span className="status-dot" />
        <input
          aria-label="CV title"
          value={cv.title}
          onChange={(event) => onChange({ ...cv, title: event.target.value })}
        />
        <button
          className={cv.starred ? 'starred' : ''}
          onClick={() => onChange({ ...cv, starred: !cv.starred })}
          aria-label={cv.starred ? 'Remove from favorites' : 'Add to favorites'}
        >
          <MorphGlyph
            icon={cv.starred ? Star : StarOff}
            size={15}
            fill={cv.starred ? 'currentColor' : 'none'}
          />
        </button>
        <small>{saving ? 'Saving…' : dirty ? 'Unsaved' : `Saved · v${cv.version}`}</small>
      </div>

      <div className="top-actions">
        <Tabs value={mode} onValueChange={(value) => onModeChange(value as EditorMode)}>
          <TabsList>
            <TabsTrigger value="visual"><MorphGlyph icon={FileText} />Visual</TabsTrigger>
            <TabsTrigger value="tex"><MorphGlyph icon={Braces} />TeX</TabsTrigger>
            <TabsTrigger value="pdf"><MorphGlyph icon={FileText} />PDF</TabsTrigger>
          </TabsList>
        </Tabs>
        <Button variant="outline" size="sm" onClick={onHistory}>
          <MorphGlyph icon={History} />History
        </Button>
        <Button variant="outline" size="sm" onClick={onSave} disabled={!dirty}>
          <MorphGlyph icon={saveIcon} className={saving ? 'spin' : undefined} />Save
        </Button>
        <Button size="sm" onClick={onCompile} disabled={saving || compiling}>
          <MorphGlyph icon={compileIcon} className={compiling ? 'spin' : undefined} />
          {compiling ? 'Compiling' : 'Recompile'}
        </Button>
        {cv.latest_compilation?.status === 'success' && (
          <Button size="sm" asChild>
            <a href={cv.latest_compilation.download_url || undefined}>
              <MorphGlyph icon={Download} />Download
            </a>
          </Button>
        )}
      </div>
    </header>
  )
}

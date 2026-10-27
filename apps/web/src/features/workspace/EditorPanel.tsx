import PDFPreview from '@/components/PDFPreview'
import ResumeEditor from '@/components/ResumeEditor'
import SourceEditor from '@/components/SourceEditor'
import type { CV, EditorMode, Resume, TexDocument, TextSelection } from '@/lib/types'

type EditorPanelProps = {
  cv: CV
  resume: Resume
  tex: TexDocument | null
  mode: EditorMode
  onResumeChange: (resume: Resume) => void
  onApplyJSON: (text: string) => Promise<string | null>
  onApplyTex: (text: string) => Promise<string | null>
  onSelection: (selection: TextSelection) => void
}

const slug = (title: string) => title.replace(/[^A-Za-z0-9._-]+/g, '_') || 'resume'

export function EditorPanel({
  cv, resume, tex, mode, onResumeChange, onApplyJSON, onApplyTex, onSelection,
}: EditorPanelProps) {
  const json = JSON.stringify(resume, null, 2)
  return (
    <section className="editor-panel">
      {mode === 'visual' && <ResumeEditor resume={resume} onChange={onResumeChange} onSelection={onSelection} />}
      {mode === 'json' && (
        <SourceEditor key={json} kind="json" value={json} filename={`${slug(cv.title)}.json`} onApply={onApplyJSON} />
      )}
      {mode === 'tex' && (tex
        ? <SourceEditor key={tex.version + tex.tex_source} kind="tex" value={tex.tex_source} filename={`${slug(cv.title)}.tex`} onApply={onApplyTex} />
        : <div className="pdf-empty"><p>Loading LaTeX…</p></div>)}
      {mode === 'pdf' && <PDFPreview compilation={cv.latest_compilation} />}
    </section>
  )
}

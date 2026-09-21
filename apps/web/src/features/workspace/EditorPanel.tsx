import PDFPreview from '@/components/PDFPreview'
import VisualEditor from '@/components/VisualEditor'
import type { CV, EditorMode, TextSelection } from '@/lib/types'

type EditorPanelProps = {
  cv: CV
  mode: EditorMode
  onChange: (cv: CV) => void
  onTeXChange: (cv: CV) => void
  onSelection: (selection: TextSelection) => void
}

export function EditorPanel({
  cv,
  mode,
  onChange,
  onTeXChange,
  onSelection,
}: EditorPanelProps) {
  return (
    <section className="editor-panel">
      {mode === 'visual' && (
        <VisualEditor
          content={cv.document}
          onChange={(document) => onChange({ ...cv, document })}
          onSelection={(text, from, to) => onSelection({ text, from, to })}
        />
      )}
      {mode === 'tex' && (
        <div className="tex-mode">
          <div className="mode-warning">
            Advanced mode: visual edits regenerate TeX. Save source changes before switching modes.
          </div>
          <textarea
            aria-label="LaTeX source"
            spellCheck={false}
            value={cv.tex_source}
            onChange={(event) => onTeXChange({ ...cv, tex_source: event.target.value })}
          />
        </div>
      )}
      {mode === 'pdf' && <PDFPreview compilation={cv.latest_compilation} />}
    </section>
  )
}

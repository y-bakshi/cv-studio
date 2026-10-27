import Assistant from '@/components/Assistant'
import ExportSheet from '@/components/ExportSheet'
import Library from '@/components/Library'
import { Button } from '@/components/ui/button'
import type { User } from '@/lib/types'

import { EditorPanel } from './EditorPanel'
import { RevisionHistory } from './RevisionHistory'
import { useCVWorkspace } from './useCVWorkspace'
import { WorkspaceHeader } from './WorkspaceHeader'

type WorkspaceProps = {
  user: User
  onLogout: () => void
}

export function Workspace({ user, onLogout }: WorkspaceProps) {
  const workspace = useCVWorkspace()

  return (
    <div className="app-shell">
      <Library
        user={user}
        items={workspace.items}
        activeId={workspace.cv?.id}
        onOpen={workspace.openCV}
        onCreate={workspace.createCV}
        onLogout={onLogout}
      />
      <main className="workspace">
        <WorkspaceHeader
          cv={workspace.cv}
          mode={workspace.mode}
          dirty={workspace.dirty}
          saving={workspace.saving}
          onModeChange={workspace.setMode}
          onChange={workspace.editCV}
          onHistory={() => workspace.setShowHistory(true)}
          onSave={() => void workspace.flush()}
          onCompile={() => void workspace.compile()}
          onExport={() => workspace.setShowExport(true)}
        />

        <div className="workbody">
          {!workspace.cv ? (
            <section className="welcome">
              <span>CV</span>
              <h1>Create your first LaTeX-backed résumé</h1>
              <p>Your revisions, annotations, source, and compiled PDFs stay together.</p>
              <Button onClick={() => void workspace.createCV()}>Create CV</Button>
            </section>
          ) : !workspace.resume ? null : (
            <>
              <EditorPanel
                cv={workspace.cv}
                resume={workspace.resume}
                tex={workspace.tex}
                mode={workspace.mode}
                onResumeChange={workspace.editResume}
                onApplyJSON={workspace.applyJSON}
                onApplyTex={workspace.applyTex}
                onSelection={workspace.setSelection}
              />
              <Assistant
                annotations={workspace.annotations}
                jobs={workspace.jobs}
                selection={workspace.selection.text}
                onAnnotate={workspace.annotate}
                onResolve={workspace.resolveAnnotation}
                onDelete={workspace.deleteAnnotation}
                onAddJob={workspace.addJob}
              />
            </>
          )}
        </div>

        {workspace.resume && (
          <ExportSheet
            open={workspace.showExport}
            style={workspace.resume.style}
            onOpenChange={workspace.setShowExport}
            onStyleChange={(style) => workspace.editResume({ ...workspace.resume!, style })}
            onExport={(format) => void workspace.exportAs(format)}
          />
        )}
        <RevisionHistory
          open={workspace.showHistory}
          revisions={workspace.revisions}
          onOpenChange={workspace.setShowHistory}
          onRestore={workspace.restoreRevision}
        />
      </main>
      {workspace.notice && <div className="toast">{workspace.notice}</div>}
    </div>
  )
}

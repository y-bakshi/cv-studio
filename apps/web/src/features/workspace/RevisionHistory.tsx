import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import type { Revision } from '@/lib/types'

type RevisionHistoryProps = {
  open: boolean
  revisions: Revision[]
  onOpenChange: (open: boolean) => void
  onRestore: (revision: Revision) => void
}

export function RevisionHistory({
  open,
  revisions,
  onOpenChange,
  onRestore,
}: RevisionHistoryProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        <SheetHeader><SheetTitle>Revision history</SheetTitle></SheetHeader>
        <div className="history-list">
          {revisions.map((revision) => (
            <button key={revision.id} onClick={() => onRestore(revision)}>
              <strong>Version {revision.version}</strong>
              <small>{new Date(revision.created_at).toLocaleString()}</small>
            </button>
          ))}
        </div>
      </SheetContent>
    </Sheet>
  )
}

import { FileCode, FileJson, FileText, FileType } from 'lucide'

import { MorphGlyph } from '@/components/MorphGlyph'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import type { ResumeStyle } from '@/lib/types'

export type ExportFormat = 'pdf' | 'docx' | 'tex' | 'json'

type ExportSheetProps = {
  open: boolean
  style: ResumeStyle
  onOpenChange: (open: boolean) => void
  onStyleChange: (style: ResumeStyle) => void
  onExport: (format: ExportFormat) => void
}

const FORMATS: { id: ExportFormat; title: string; note: string; icon: typeof FileText }[] = [
  { id: 'pdf', title: 'PDF', note: 'Compiled with pdflatex', icon: FileText },
  { id: 'docx', title: 'Word', note: 'ATS-friendly .docx', icon: FileType },
  { id: 'tex', title: 'LaTeX', note: 'Editable .tex source', icon: FileCode },
  { id: 'json', title: 'JSON', note: 'Whole résumé data', icon: FileJson },
]

function Row({ label, htmlFor, children }: { label: string; htmlFor?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
    </div>
  )
}

export default function ExportSheet({ open, style, onOpenChange, onStyleChange, onExport }: ExportSheetProps) {
  const set = <K extends keyof ResumeStyle>(key: K, value: ResumeStyle[K]) => onStyleChange({ ...style, [key]: value })

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full overflow-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Export résumé</SheetTitle>
          <SheetDescription>Style options apply to the LaTeX, PDF and Word output.</SheetDescription>
        </SheetHeader>

        <div className="flex flex-col gap-5 px-4 pb-6">
          <div className="grid grid-cols-2 gap-2">
            {FORMATS.map(({ id, title, note, icon }) => (
              <Button key={id} variant="outline" className="h-auto justify-start gap-3 p-3 text-left" onClick={() => onExport(id)}>
                <MorphGlyph icon={icon} size={18} />
                <span className="flex flex-col"><strong>{title}</strong><small className="font-normal text-muted-foreground">{note}</small></span>
              </Button>
            ))}
          </div>

          <Separator />

          <Row label="Template">
            <ToggleGroup type="single" value={style.template} onValueChange={(v) => v && set('template', v as ResumeStyle['template'])} aria-label="Template">
              <ToggleGroupItem value="standard">Standard</ToggleGroupItem>
              <ToggleGroupItem value="compact">Compact</ToggleGroupItem>
            </ToggleGroup>
          </Row>

          <div className="grid grid-cols-2 gap-3">
            <Row label="Paper size" htmlFor="paper">
              <Select value={style.paper} onValueChange={(v) => set('paper', v as ResumeStyle['paper'])}>
                <SelectTrigger id="paper"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="letter">Letter (8.5" × 11")</SelectItem>
                  <SelectItem value="a4">A4</SelectItem>
                </SelectContent>
              </Select>
            </Row>
            <Row label="Body text size" htmlFor="size">
              <Select value={String(style.font_size)} onValueChange={(v) => set('font_size', Number(v) as ResumeStyle['font_size'])}>
                <SelectTrigger id="size"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {[10, 11, 12].map((size) => <SelectItem key={size} value={String(size)}>{size} pt</SelectItem>)}
                </SelectContent>
              </Select>
            </Row>
          </div>

          <Row label="Font family" htmlFor="font">
            <Select value={style.font} onValueChange={(v) => set('font', v as ResumeStyle['font'])}>
              <SelectTrigger id="font"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="sans">Helvetica (sans-serif)</SelectItem>
                <SelectItem value="serif">Times (serif)</SelectItem>
                <SelectItem value="classic">Palatino (classic)</SelectItem>
              </SelectContent>
            </Select>
          </Row>

          <Row label="Accent color" htmlFor="accent">
            <div className="flex items-center gap-2">
              <input
                type="color" aria-label="Pick accent color" value={style.accent}
                onChange={(event) => set('accent', event.target.value)}
                className="size-9 cursor-pointer rounded-md border border-input bg-background p-1"
              />
              <Input id="accent" value={style.accent} onChange={(event) => /^#[0-9a-fA-F]{0,6}$/.test(event.target.value) && set('accent', event.target.value)} className="font-mono" />
            </div>
          </Row>

          <Row label="Bullet icon">
            <ToggleGroup type="single" value={style.bullet} onValueChange={(v) => v && set('bullet', v as ResumeStyle['bullet'])} aria-label="Bullet icon">
              <ToggleGroupItem value="dot" aria-label="Dot">•</ToggleGroupItem>
              <ToggleGroupItem value="dash" aria-label="Dash">–</ToggleGroupItem>
              <ToggleGroupItem value="square" aria-label="Square">▪</ToggleGroupItem>
            </ToggleGroup>
          </Row>
        </div>
      </SheetContent>
    </Sheet>
  )
}

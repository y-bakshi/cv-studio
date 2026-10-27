import { type KeyboardEvent, type ReactNode, useId, useState } from 'react'
import {
  ArrowRight, ChevronDown, ChevronUp, Link as LinkIcon, Mail, MapPin, Phone, Plus, Trash2, X,
} from 'lucide'

import { MorphGlyph } from '@/components/MorphGlyph'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Textarea } from '@/components/ui/textarea'
import type { Resume, SectionName, TextSelection } from '@/lib/types'

type Props = {
  resume: Resume
  onChange: (resume: Resume) => void
  onSelection: (selection: TextSelection) => void
}

const newId = () => crypto.randomUUID().replace(/-/g, '').slice(0, 12)

const SECTION_TITLES: Record<SectionName, string> = {
  skills: 'Skills',
  experience: 'Professional Experience',
  projects: 'Projects',
  education: 'Education',
}

export default function ResumeEditor({ resume, onChange, onSelection }: Props) {
  // Every edit works on a copy so React state is never mutated in place.
  const edit = (change: (draft: Resume) => void) => {
    const draft = structuredClone(resume)
    change(draft)
    onChange(draft)
  }

  const selectable = (event: { currentTarget: HTMLInputElement | HTMLTextAreaElement }) => {
    const { selectionStart, selectionEnd, value } = event.currentTarget
    if (selectionStart !== null && selectionEnd !== null && selectionEnd > selectionStart) {
      onSelection({ text: value.slice(selectionStart, selectionEnd), from: selectionStart, to: selectionEnd })
    }
  }

  const text = (value: string, set: (value: string) => void, label: string, placeholder = '') => (
    <Input
      aria-label={label}
      placeholder={placeholder || label}
      value={value}
      onChange={(event) => set(event.target.value)}
      onSelect={selectable}
    />
  )

  const bullets = (items: string[], set: (items: string[]) => void) => (
    <div className="flex flex-col gap-2">
      {items.map((item, index) => (
        <div key={index} className="flex items-start gap-2">
          <Textarea
            aria-label={`Bullet point ${index + 1}`}
            rows={2}
            className="min-h-0 [field-sizing:content]"
            value={item}
            onChange={(event) => set(items.map((entry, i) => i === index ? event.target.value : entry))}
            onSelect={selectable}
          />
          <Button
            variant="ghost" size="icon" aria-label={`Remove bullet point ${index + 1}`}
            onClick={() => set(items.filter((_, i) => i !== index))}
          ><MorphGlyph icon={X} size={14} /></Button>
        </div>
      ))}
      <AddButton onClick={() => set([...items, ''])}>Bullet Points</AddButton>
    </div>
  )

  const move = (name: SectionName, direction: -1 | 1) => edit((draft) => {
    const order = [...draft.section_order]
    const index = order.indexOf(name)
    const target = index + direction
    if (target < 0 || target >= order.length) return
    ;[order[index], order[target]] = [order[target], order[index]]
    draft.section_order = order
  })

  const sections: Record<SectionName, ReactNode> = {
    skills: (
      <div className="flex flex-col gap-5">
        {resume.skills.map((group, gi) => (
          <div key={group.id} className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <Input
                aria-label="Skill group name"
                className="h-8 max-w-xs font-semibold"
                value={group.name}
                placeholder="Group name"
                onChange={(event) => edit((d) => { d.skills[gi].name = event.target.value })}
              />
              <Button
                variant="ghost" size="icon" aria-label={`Delete skill group ${group.name}`}
                onClick={() => edit((d) => { d.skills.splice(gi, 1) })}
              ><MorphGlyph icon={Trash2} size={14} /></Button>
            </div>
            <Chips
              label={`Add skill to ${group.name || 'group'}`}
              placeholder="Add skill…"
              items={group.skills}
              onChange={(items) => edit((d) => { d.skills[gi].skills = items })}
            />
          </div>
        ))}
        <AddButton onClick={() => edit((d) => { d.skills.push({ id: newId(), name: '', skills: [] }) })}>Skill group</AddButton>
      </div>
    ),

    experience: (
      <div className="flex flex-col gap-6">
        {resume.experience.map((job, i) => (
          <EntryCard key={job.id} title={job.company || 'New experience'} onDelete={() => edit((d) => { d.experience.splice(i, 1) })}>
            <div className="grid gap-2 sm:grid-cols-2">
              {text(job.company, (v) => edit((d) => { d.experience[i].company = v }), 'Company')}
              {text(job.role, (v) => edit((d) => { d.experience[i].role = v }), 'Job title')}
              {text(job.location, (v) => edit((d) => { d.experience[i].location = v }), 'Location')}
              <DateRange
                start={job.start} end={job.end}
                onStart={(v) => edit((d) => { d.experience[i].start = v })}
                onEnd={(v) => edit((d) => { d.experience[i].end = v })}
              />
            </div>
            {text(job.summary, (v) => edit((d) => { d.experience[i].summary = v }), 'Summary', 'Summary…')}
            {bullets(job.bullets, (items) => edit((d) => { d.experience[i].bullets = items }))}
          </EntryCard>
        ))}
        <AddButton onClick={() => edit((d) => {
          d.experience.push({ id: newId(), company: '', role: '', location: '', start: '', end: '', summary: '', bullets: [] })
        })}>Experience</AddButton>
      </div>
    ),

    projects: (
      <div className="flex flex-col gap-6">
        {resume.projects.map((project, i) => (
          <EntryCard key={project.id} title={project.name || 'New project'} onDelete={() => edit((d) => { d.projects.splice(i, 1) })}>
            <div className="grid gap-2 sm:grid-cols-2">
              {text(project.name, (v) => edit((d) => { d.projects[i].name = v }), 'Project name')}
              {text(project.link_text, (v) => edit((d) => { d.projects[i].link_text = v }), 'Link text', 'Link text…')}
              {text(project.organization, (v) => edit((d) => { d.projects[i].organization = v }), 'Organization', 'Organization…')}
              {text(project.location, (v) => edit((d) => { d.projects[i].location = v }), 'Location', 'Location…')}
              <DateRange
                start={project.start} end={project.end}
                onStart={(v) => edit((d) => { d.projects[i].start = v })}
                onEnd={(v) => edit((d) => { d.projects[i].end = v })}
              />
            </div>
            {bullets(project.bullets, (items) => edit((d) => { d.projects[i].bullets = items }))}
          </EntryCard>
        ))}
        <AddButton onClick={() => edit((d) => {
          d.projects.push({ id: newId(), name: '', link_text: '', organization: '', location: '', start: '', end: '', bullets: [] })
        })}>Projects</AddButton>
      </div>
    ),

    education: (
      <div className="flex flex-col gap-6">
        {resume.education.map((school, i) => (
          <EntryCard key={school.id} title={school.school || 'New education'} onDelete={() => edit((d) => { d.education.splice(i, 1) })}>
            <div className="grid gap-2 sm:grid-cols-2">
              {text(school.school, (v) => edit((d) => { d.education[i].school = v }), 'School')}
              {text(school.degree, (v) => edit((d) => { d.education[i].degree = v }), 'Degree')}
              {text(school.location, (v) => edit((d) => { d.education[i].location = v }), 'Location', 'Location…')}
              {text(school.gpa, (v) => edit((d) => { d.education[i].gpa = v }), 'GPA', 'GPA…')}
              <DateRange
                start={school.start} end={school.end}
                onStart={(v) => edit((d) => { d.education[i].start = v })}
                onEnd={(v) => edit((d) => { d.education[i].end = v })}
              />
            </div>
            <Chips
              label="Add achievement" placeholder="Add achievement…" items={school.achievements}
              onChange={(items) => edit((d) => { d.education[i].achievements = items })}
            />
            <Chips
              label="Add coursework" placeholder="Add coursework…" items={school.coursework}
              onChange={(items) => edit((d) => { d.education[i].coursework = items })}
            />
            {bullets(school.bullets, (items) => edit((d) => { d.education[i].bullets = items }))}
          </EntryCard>
        ))}
        <AddButton onClick={() => edit((d) => {
          d.education.push({ id: newId(), school: '', degree: '', location: '', start: '', end: '', gpa: '', achievements: [], coursework: [], bullets: [] })
        })}>Education</AddButton>
      </div>
    ),
  }

  const { contact } = resume

  return (
    <div className="h-full overflow-auto bg-muted p-6">
      <Card className="mx-auto flex max-w-4xl flex-col gap-8 p-8">
        <section aria-label="Contact" className="flex flex-col gap-3">
          <Input
            aria-label="Full name"
            placeholder="Your name"
            className="h-14 border-transparent text-3xl font-bold shadow-none md:text-3xl"
            value={contact.name}
            onChange={(event) => edit((d) => { d.contact.name = event.target.value })}
            onSelect={selectable}
          />
          {text(contact.subtitle, (v) => edit((d) => { d.contact.subtitle = v }), 'Subtitle', 'Add a subtitle')}
          <div className="grid gap-2 sm:grid-cols-3">
            <IconField icon={Mail} label="Email" value={contact.email} onChange={(v) => edit((d) => { d.contact.email = v })} />
            <IconField icon={Phone} label="Phone" value={contact.phone} onChange={(v) => edit((d) => { d.contact.phone = v })} />
            <IconField icon={MapPin} label="Location" value={contact.location} onChange={(v) => edit((d) => { d.contact.location = v })} />
          </div>
          <Chips
            label="Add tag" placeholder="Add tag…" items={contact.tags}
            onChange={(items) => edit((d) => { d.contact.tags = items })}
          />
          <div className="grid gap-2 sm:grid-cols-3">
            {contact.links.map((link, i) => (
              <Card key={link.id} className="flex flex-col gap-2 bg-muted/40 p-3 shadow-none">
                <div className="flex items-center gap-1">
                  <MorphGlyph icon={LinkIcon} size={14} />
                  <Input
                    aria-label="Link label" placeholder="Label" className="h-7 border-transparent bg-transparent px-1 shadow-none"
                    value={link.label} onChange={(event) => edit((d) => { d.contact.links[i].label = event.target.value })}
                  />
                  <Button
                    variant="ghost" size="icon" className="size-7" aria-label={`Remove link ${link.label}`}
                    onClick={() => edit((d) => { d.contact.links.splice(i, 1) })}
                  ><MorphGlyph icon={X} size={12} /></Button>
                </div>
                <Input
                  aria-label="Link URL" placeholder="https://" value={link.url}
                  onChange={(event) => edit((d) => { d.contact.links[i].url = event.target.value })}
                />
              </Card>
            ))}
          </div>
          <div>
            <AddButton onClick={() => edit((d) => { d.contact.links.push({ id: newId(), label: '', url: '' }) })}>Link</AddButton>
          </div>
        </section>

        {resume.section_order.map((name, index) => (
          <section key={name} aria-label={SECTION_TITLES[name]} className="flex flex-col gap-4">
            <Separator />
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold tracking-wide uppercase">{SECTION_TITLES[name]}</h2>
              <div className="flex gap-1">
                <Button variant="ghost" size="icon" aria-label={`Move ${SECTION_TITLES[name]} up`} disabled={index === 0} onClick={() => move(name, -1)}>
                  <MorphGlyph icon={ChevronUp} size={14} />
                </Button>
                <Button variant="ghost" size="icon" aria-label={`Move ${SECTION_TITLES[name]} down`} disabled={index === resume.section_order.length - 1} onClick={() => move(name, 1)}>
                  <MorphGlyph icon={ChevronDown} size={14} />
                </Button>
              </div>
            </div>
            {sections[name]}
          </section>
        ))}
      </Card>
    </div>
  )
}

function AddButton({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return (
    <Button variant="outline" size="sm" onClick={onClick}>
      <MorphGlyph icon={Plus} size={14} />{children}
    </Button>
  )
}

function IconField({ icon, label, value, onChange }: {
  icon: Parameters<typeof MorphGlyph>[0]['icon']; label: string; value: string; onChange: (value: string) => void
}) {
  return (
    <div className="relative">
      <span className="pointer-events-none absolute top-2.5 left-3 text-muted-foreground"><MorphGlyph icon={icon} size={16} /></span>
      <Input aria-label={label} placeholder={label} className="pl-9" value={value} onChange={(event) => onChange(event.target.value)} />
    </div>
  )
}

function DateRange({ start, end, onStart, onEnd }: {
  start: string; end: string; onStart: (value: string) => void; onEnd: (value: string) => void
}) {
  return (
    <div className="flex items-center gap-2">
      <Input aria-label="Start date" placeholder="Start date" value={start} onChange={(event) => onStart(event.target.value)} />
      <span className="text-muted-foreground"><MorphGlyph icon={ArrowRight} size={14} /></span>
      <Input aria-label="End date" placeholder="End date" value={end} onChange={(event) => onEnd(event.target.value)} />
    </div>
  )
}

function EntryCard({ title, onDelete, children }: { title: string; onDelete: () => void; children: ReactNode }) {
  return (
    <Card className="flex flex-col gap-3 bg-card p-4 shadow-none">
      <div className="flex items-center justify-between">
        <h3 className="text-[15px] font-semibold">{title}</h3>
        <Button variant="ghost" size="icon" aria-label={`Delete ${title}`} onClick={onDelete}>
          <MorphGlyph icon={Trash2} size={14} />
        </Button>
      </div>
      {children}
    </Card>
  )
}

function Chips({ items, onChange, label, placeholder }: {
  items: string[]; onChange: (items: string[]) => void; label: string; placeholder: string
}) {
  const [draft, setDraft] = useState('')
  const inputId = useId()

  const commit = () => {
    const value = draft.trim()
    if (value) onChange([...items, value])
    setDraft('')
  }

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault()
      commit()
    } else if (event.key === 'Backspace' && !draft && items.length) {
      onChange(items.slice(0, -1))
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {items.map((item, index) => (
        <Badge key={`${item}-${index}`} variant="secondary" className="h-8 gap-1 rounded-md pr-1 text-sm font-medium">
          {item}
          <button
            type="button"
            aria-label={`Remove ${item}`}
            className="grid size-5 place-items-center rounded-sm hover:bg-black/10"
            onClick={() => onChange(items.filter((_, i) => i !== index))}
          ><MorphGlyph icon={X} size={12} /></button>
        </Badge>
      ))}
      <Label className="sr-only" htmlFor={inputId}>{label}</Label>
      <Input
        id={inputId} value={draft} placeholder={placeholder} className="h-8 w-44"
        onChange={(event) => setDraft(event.target.value)} onKeyDown={onKeyDown} onBlur={commit}
      />
    </div>
  )
}

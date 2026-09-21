import { useState } from 'react'
import Highlight from '@tiptap/extension-highlight'
import Placeholder from '@tiptap/extension-placeholder'
import UniqueID from '@tiptap/extension-unique-id'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { Bold, Highlighter, Italic, List, ListOrdered, Redo2, Undo2 } from 'lucide'

import { MorphGlyph } from './MorphGlyph'

type VisualEditorProps = {
  content: Record<string, unknown>
  onChange: (document: Record<string, unknown>) => void
  onSelection: (text: string, from: number, to: number) => void
}

export default function VisualEditor({ content, onChange, onSelection }: VisualEditorProps) {
  const [menu, setMenu] = useState<{ x: number; y: number } | null>(null)
  const editor = useEditor({
    extensions: [
      StarterKit,
      Highlight,
      Placeholder.configure({ placeholder: 'Start writing…' }),
      UniqueID.configure({ types: ['heading', 'paragraph', 'bulletList', 'orderedList'] }),
    ],
    content,
    onUpdate: ({ editor: current }) => onChange(current.getJSON()),
    onSelectionUpdate: ({ editor: current }) => {
      const { from, to } = current.state.selection
      onSelection(current.state.doc.textBetween(from, to, ' '), from, to)
      if (from === to) setMenu(null)
    },
  })

  if (!editor) return null

  const run = (command: () => void) => (event: React.MouseEvent) => {
    event.preventDefault()
    command()
  }

  return (
    <div className="visual-wrap" onClick={() => setMenu(null)}>
      <div className="format-bar" role="toolbar" aria-label="Text formatting">
        <button
          aria-label="Bold"
          className={editor.isActive('bold') ? 'on' : ''}
          onMouseDown={run(() => editor.chain().focus().toggleBold().run())}
        ><MorphGlyph icon={Bold} size={15} /></button>
        <button
          aria-label="Italic"
          className={editor.isActive('italic') ? 'on' : ''}
          onMouseDown={run(() => editor.chain().focus().toggleItalic().run())}
        ><MorphGlyph icon={Italic} size={15} /></button>
        <button
          aria-label="Highlight"
          className={editor.isActive('highlight') ? 'on' : ''}
          onMouseDown={run(() => editor.chain().focus().toggleHighlight().run())}
        ><MorphGlyph icon={Highlighter} size={15} /></button>
        <i />
        <button aria-label="Bullet list" onMouseDown={run(() => editor.chain().focus().toggleBulletList().run())}>
          <MorphGlyph icon={List} size={15} />
        </button>
        <button aria-label="Numbered list" onMouseDown={run(() => editor.chain().focus().toggleOrderedList().run())}>
          <MorphGlyph icon={ListOrdered} size={15} />
        </button>
        <i />
        <button aria-label="Undo" onMouseDown={run(() => editor.chain().focus().undo().run())}>
          <MorphGlyph icon={Undo2} size={15} />
        </button>
        <button aria-label="Redo" onMouseDown={run(() => editor.chain().focus().redo().run())}>
          <MorphGlyph icon={Redo2} size={15} />
        </button>
      </div>

      <div className="page-scroll">
        <div
          onContextMenu={(event) => {
            if (!editor.state.selection.empty) {
              event.preventDefault()
              setMenu({ x: event.clientX, y: event.clientY })
            }
          }}
        >
          <EditorContent editor={editor} className="resume-page" />
        </div>
      </div>

      {menu && (
        <div className="selection-menu" style={{ left: menu.x, top: menu.y }}>
          <button onClick={() => setMenu(null)}>Add annotation in review panel</button>
          <button disabled>Ask AI to revise — coming soon</button>
        </div>
      )}
    </div>
  )
}

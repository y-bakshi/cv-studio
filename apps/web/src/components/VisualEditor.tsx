import { type MouseEvent, useEffect, useState } from 'react'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Highlight from '@tiptap/extension-highlight'
import Placeholder from '@tiptap/extension-placeholder'
import UniqueID from '@tiptap/extension-unique-id'
import { Bold, Highlighter, Italic, List, ListOrdered, Redo2, Undo2 } from 'lucide'
import { MorphGlyph } from './MorphGlyph'

export default function VisualEditor({content,onChange,onSelection}:{content:Record<string,unknown>;onChange:(doc:Record<string,unknown>)=>void;onSelection:(text:string,from:number,to:number)=>void}){
  const [menu,setMenu]=useState<{x:number;y:number}|null>(null)
  const editor=useEditor({extensions:[StarterKit,Highlight.configure({multicolor:false}),Placeholder.configure({placeholder:'Start writing…'}),UniqueID.configure({types:['heading','paragraph','bulletList','orderedList']})],content,onUpdate:({editor})=>onChange(editor.getJSON()),onSelectionUpdate:({editor})=>{const {from,to}=editor.state.selection;if(from!==to)onSelection(editor.state.doc.textBetween(from,to,' '),from,to)}})
  useEffect(()=>{if(editor&&!editor.isFocused&&JSON.stringify(editor.getJSON())!==JSON.stringify(content))editor.commands.setContent(content)},[content,editor])
  if(!editor)return null
  const action=(fn:()=>void)=>(event:MouseEvent)=>{event.preventDefault();fn()}
  return <div className="visual-wrap" onClick={()=>setMenu(null)}>
    <div className="format-bar">
      <button className={editor.isActive('bold')?'on':''} onMouseDown={action(()=>editor.chain().focus().toggleBold().run())}><MorphGlyph icon={Bold} size={15}/></button>
      <button className={editor.isActive('italic')?'on':''} onMouseDown={action(()=>editor.chain().focus().toggleItalic().run())}><MorphGlyph icon={Italic} size={15}/></button>
      <button className={editor.isActive('highlight')?'on':''} onMouseDown={action(()=>editor.chain().focus().toggleHighlight().run())}><MorphGlyph icon={Highlighter} size={15}/></button><i/>
      <button onMouseDown={action(()=>editor.chain().focus().toggleBulletList().run())}><MorphGlyph icon={List} size={15}/></button>
      <button onMouseDown={action(()=>editor.chain().focus().toggleOrderedList().run())}><MorphGlyph icon={ListOrdered} size={15}/></button><i/>
      <button onMouseDown={action(()=>editor.chain().focus().undo().run())}><MorphGlyph icon={Undo2} size={15}/></button>
      <button onMouseDown={action(()=>editor.chain().focus().redo().run())}><MorphGlyph icon={Redo2} size={15}/></button>
    </div>
    <div className="page-scroll"><div onContextMenu={event=>{if(!editor.state.selection.empty){event.preventDefault();setMenu({x:event.clientX,y:event.clientY})}}}><EditorContent editor={editor} className="resume-page"/></div></div>
    {menu&&<div className="selection-menu" style={{left:menu.x,top:menu.y}}><button onClick={()=>setMenu(null)}>Add annotation</button><button disabled>Ask AI · coming next</button></div>}
  </div>
}

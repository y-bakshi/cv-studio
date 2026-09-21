import React from 'react'
import { FileText, LogOut, Plus, Search, Star } from 'lucide-react'
import { CVSummary, User } from '../lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

export default function Library({user,items,activeId,onOpen,onCreate,onLogout}:{user:User;items:CVSummary[];activeId?:string;onOpen:(id:string)=>void;onCreate:()=>void;onLogout:()=>void}){
  const [query,setQuery]=React.useState(''); const filtered=items.filter(i=>i.title.toLowerCase().includes(query.toLowerCase()))
  return <aside className="library"><div className="brand"><span>CV</span><strong>CV Studio</strong></div><Button className="new-button" onClick={onCreate}><Plus size={16}/>New CV</Button><label className="search"><Search size={14}/><Input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search CVs"/></label><div className="side-heading">Documents <span>{items.length}</span></div><nav className="document-list">{filtered.map(item=><button key={item.id} className={activeId===item.id?'active':''} onClick={()=>onOpen(item.id)}><span className="doc-icon"><FileText size={14}/></span><span><strong>{item.title}</strong><small>{item.folder} · v{item.version}</small></span>{item.starred&&<Star size={12} fill="currentColor"/>}</button>)}</nav><div className="account"><span>{user.email.slice(0,2).toUpperCase()}</span><div><strong>{user.email}</strong><small>Personal workspace</small></div><Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" onClick={onLogout}><LogOut size={15}/></Button></TooltipTrigger><TooltipContent>Sign out</TooltipContent></Tooltip></div></aside>
}

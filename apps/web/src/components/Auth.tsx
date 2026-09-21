import { FormEvent, useState } from 'react'
import { FileText } from 'lucide-react'
import { api, User } from '../lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

export default function Auth({ onAuthenticated }:{ onAuthenticated:(user:User)=>void }) {
  const [mode,setMode]=useState<'login'|'register'>('login'); const [email,setEmail]=useState(''); const [password,setPassword]=useState(''); const [error,setError]=useState(''); const [busy,setBusy]=useState(false)
  async function submit(event:FormEvent){ event.preventDefault(); setBusy(true); setError(''); try { onAuthenticated(await api<User>(`/api/auth/${mode}`,{method:'POST',body:JSON.stringify({email,password})})) } catch(error){setError(error instanceof Error?error.message:'Authentication failed')} finally{setBusy(false)} }
  return <main className="auth-page"><section className="auth-card"><div className="auth-brand"><span><FileText size={20}/></span>CV Studio</div><p className="eyebrow">LaTeX-backed résumé workspace</p><h1>{mode==='login'?'Welcome back':'Create your workspace'}</h1><p className="auth-copy">Edit visually, compile with LaTeX, and keep every revision.</p><form onSubmit={submit}><label>Email<Input type="email" value={email} onChange={e=>setEmail(e.target.value)} required autoFocus/></label><label>Password<Input type="password" minLength={8} value={password} onChange={e=>setPassword(e.target.value)} required/></label>{error&&<p className="form-error">{error}</p>}<Button className="wide" disabled={busy}>{busy?'Please wait…':mode==='login'?'Sign in':'Create account'}</Button></form><Button variant="link" className="wide" onClick={()=>{setMode(mode==='login'?'register':'login');setError('')}}>{mode==='login'?'New here? Create an account':'Already have an account? Sign in'}</Button></section></main>
}

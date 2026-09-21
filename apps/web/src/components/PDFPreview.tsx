import { useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import { FileText, LoaderCircle, ZoomIn, ZoomOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { Compilation } from '@/lib/api'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString()

export default function PDFPreview({ compilation }:{ compilation:Compilation|null }) {
  const [pages,setPages]=useState(0)
  const [scale,setScale]=useState(1.15)
  if(!compilation)return <div className="pdf-empty"><FileText/><h3>No compiled PDF yet</h3><p>Choose Recompile to generate the authoritative PDF.</p></div>
  if(compilation.status==='queued'||compilation.status==='compiling')return <div className="pdf-empty"><LoaderCircle className="spin"/><h3>Compiling with pdflatex…</h3></div>
  if(compilation.status==='failed')return <div className="compile-error"><h3>Compilation failed</h3><pre>{compilation.log}</pre></div>
  return <div className="pdf-viewer">
    <div className="pdf-toolbar"><span>{pages} {pages===1?'page':'pages'}</span><div><Button variant="ghost" size="icon" onClick={()=>setScale(Math.max(.65,scale-.1))}><ZoomOut/></Button><span>{Math.round(scale*100)}%</span><Button variant="ghost" size="icon" onClick={()=>setScale(Math.min(2,scale+.1))}><ZoomIn/></Button></div></div>
    <div className="pdf-scroll"><Document file={compilation.download_url!} options={{withCredentials:true}} onLoadSuccess={({numPages})=>setPages(numPages)} loading={<div className="pdf-empty"><LoaderCircle className="spin"/>Loading PDF…</div>} error={<div className="pdf-empty"><p>Could not load the compiled PDF.</p></div>}>{Array.from({length:pages},(_,index)=><Page key={index+1} pageNumber={index+1} scale={scale} renderTextLayer renderAnnotationLayer className="pdf-page"/>)}</Document></div>
  </div>
}

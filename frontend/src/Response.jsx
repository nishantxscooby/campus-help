import React, {useState} from 'react';
import {Icon} from './Icons';

function OriginalPage({source}) {
  const [open,setOpen] = useState(false);
  if (!/^\/documents\/(?:handbook|[a-f0-9]{64})\/pdf#page=\d+$/.test(source.pdf_url)) return null;
  return <details onToggle={event=>setOpen(event.currentTarget.open)}>
    <summary>Read original page {source.pdf_page_number}</summary>
    {open && <iframe title={source.title+' · Page '+source.pdf_page_number} src={source.pdf_url}
                     style={{width:'100%',height:'min(65vh, 40rem)',border:0}}/>}
  </details>;
}

export default function Response({reply, retry, ask, busy}) {
  const [copied,setCopied] = useState('');
  if (!reply) return <p role="status" className="quiet">Reading the handbook…</p>;
  if (reply.error) return <div role="alert"><p>{reply.error}</p><button onClick={retry} disabled={busy}>Retry</button></div>;
  const verified = reply.status === 'answered';
  const sources = verified ? reply.citations : reply.excerpts || [];
  const pages = [...new Map(sources.map(s=>[s.pdf_url,s])).values()];
  const primary = sources.at(-1);
  const row = sources.find(s=>s.table?.values);
  let intro = reply.message;
  if (reply.reason === 'possible_typo') intro = 'Did you mean rustication?';
  if (reply.reason === 'awaiting_review' && primary) intro = 'I found this passage in the handbook.';
  if (reply.reason === 'source_context') intro = 'I couldn’t confirm the complete rule. Which decision, incident or procedure are you asking about?';
  if (!intro && verified) intro = primary.exact_quotation;
  const note = verified ? 'Verified from handbook' : 'Not independently verified';
  // Keep the governing sentence visible when a numbered penalty depends on it.
  const excerpts = !verified && primary && !row ? sources.filter(s=>reply.reason === 'reading_material' || s === primary ||
    (s.chunk_id && s.exact_quotation.trim().endsWith('.') && s.pdf_page_number === primary.pdf_page_number)) : [];
  async function copy() {
    const lines = [intro, ...sources.map(s=>s.exact_quotation), ...(sources.length ? [note] : []),
      ...pages.map(s=>s.title+' · Page '+s.pdf_page_number+' '+new URL(s.pdf_url, location.origin).href)];
    try { await navigator.clipboard.writeText([...new Set(lines)].join('\n\n')); setCopied('Copied'); }
    catch { setCopied('Copy unavailable'); }
  }
  return <div className="answer">
    <p>{intro}</p>
    {row && <div className="policy-row"><table>
      <caption>{row.section}</caption>
      <thead><tr>{row.table.headers.map((name,i)=><th key={i} scope="col">{name}</th>)}</tr></thead>
      <tbody><tr>{row.table.values.map((value,i)=><td key={i}>{value}</td>)}</tr></tbody>
    </table></div>}
    {excerpts.map(s=><div key={s.pdf_url+s.start+s.chunk_id}>
      {reply.reason === 'reading_material' && s.section && s.section !== s.exact_quotation &&
        <small className="quiet">{s.section}</small>}
      <blockquote>{s.exact_quotation}</blockquote>
      {pages.length > 1 && <a className="chip" href={s.pdf_url} target="_blank" rel="noreferrer">{s.title} · Page {s.pdf_page_number}</a>}
    </div>)}
    {sources.length > 0 && <>
      <div className="citation-row">{(pages.length === 1 || !excerpts.length ? pages : []).map(s=><a className="chip" key={s.pdf_url} href={s.pdf_url} target="_blank" rel="noreferrer"><Icon name="book" size={14}/>{s.title === 'Students’ Discipline and Conduct Rules' ? 'Discipline Handbook' : s.title} · Page {s.pdf_page_number}<Icon name="open" size={12}/></a>)}</div>
      <p className="note">{note}{!verified && ' · For reference only.'}</p>
      <details><summary>View source details</summary>{reply.retrieval_mode && <small>Search: {reply.retrieval_mode === 'bm25' ? 'keyword search (offline fallback)' : 'keywords and local semantic search'}</small>}{sources.map((s,i)=><section key={i}><strong>{s.title} · Page {s.pdf_page_number}</strong><p>{s.exact_quotation}</p><small>{s.coordinates === 'ocr_transcript' && ('Scanned text · '+(s.confidence < 80 ? 'check uncertain transcription' : 'check against original')+' · ')}{s.table && ('Table row '+s.table.row+', column '+s.table.column+' · ')}{s.version && (s.version+' · ')}{s.document_name} · {s.chunk_id || 'PDF page text'} · Characters [{s.start}, {s.end}) · {note}</small></section>)}</details>
      {pages.filter(s=>s.coordinates === 'ocr_transcript' || s.table || s.pdf_url===row?.pdf_url).map(s=><OriginalPage key={s.pdf_url} source={s}/>)}
    </>}
    {reply.reason === 'possible_typo' && <button className="follow" disabled={busy} onClick={()=>ask('Can I be rusticated?')}>Ask “Can I be rusticated?” <Icon name="open" size={13}/></button>}
    <button className="copy" aria-label="Copy response" onClick={copy}><Icon name="copy" size={15}/>{copied}</button>
  </div>;
}

import React, {useEffect, useLayoutEffect, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Icon, Mark} from './Icons';
import Response from './Response';
import {historyKey, loadHistory, read, save, validReply} from './storage';
import './style.css';

const prompts = [
  ['clock','Appeal deadline','What is the deadline to file an appeal?'],
  ['book','Rustication','What does the handbook say about rustication?'],
  ['scales','Penalty reviews','Who reviews major disciplinary penalties?'],
  ['list','Campus conduct','Is gambling on University premises listed as misconduct?'],
];

function Composer({value, change, send, pending}) {
  const input = useRef(null);
  useLayoutEffect(()=>{
    input.current.style.height='auto';
    input.current.style.height=Math.min(input.current.scrollHeight,150)+'px';
  },[value]);
  return <form className="composer" onSubmit={e=>{e.preventDefault();send(value);}}>
    <textarea ref={input} aria-label="Message Campus Help" placeholder="Ask about your university policies…" rows="1" maxLength="800"
      value={value} disabled={pending} onChange={e=>change(e.target.value)} onKeyDown={e=>{
        if (e.key==='Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {e.preventDefault();e.currentTarget.form.requestSubmit();}
      }}/>
    <button className="send" aria-label="Send question" disabled={pending || !value.trim()}><Icon name="arrow"/></button>
  </form>;
}

function App() {
  const [history,update] = useState(loadHistory);
  const {chats,active} = history;
  const current = chats.find(c=>c.id===active);
  const [draft,setDraft] = useState('');
  const [search,setSearch] = useState('');
  const [collapsed,collapse] = useState(false);
  const [busy,setBusy] = useState(false);
  const [storageError,setStorageError] = useState(false);
  const [documents,setDocuments] = useState([]);
  const [docError,setDocError] = useState(false);
  const [attempt,setAttempt] = useState(0);
  const [theme,setTheme] = useState(()=>{
    const stored=read('campus-help.theme');
    return ['dark','light'].includes(stored) ? stored : matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });
  const mobile = useRef(null);
  const scrolling = useRef(null);
  const follow = useRef(true);
  const sending = useRef(false);
  useEffect(()=>{setStorageError(!save(historyKey,history));},[history]);
  useEffect(()=>{document.documentElement.dataset.theme=theme;},[theme]);
  useEffect(()=>{
    const media=matchMedia('(prefers-color-scheme: dark)');
    const listener=()=>{if (!read('campus-help.theme')) setTheme(media.matches?'dark':'light');};
    media.addEventListener('change',listener);
    return ()=>media.removeEventListener('change',listener);
  },[]);
  useEffect(()=>{
    const controller=new AbortController();
    fetch('/documents',{signal:controller.signal}).then(r=>{if(!r.ok) throw Error();return r.json();})
      .then(d=>{setDocuments(d);setDocError(false);}).catch(()=>{if(!controller.signal.aborted)setDocError(true);});
    return ()=>controller.abort();
  },[attempt]);
  useLayoutEffect(()=>{
    if (follow.current && scrolling.current) scrolling.current.scrollTop=scrolling.current.scrollHeight;
  },[current]);
  function switchChat(id) {
    follow.current=true;
    update(h=>({...h,active:id}));
    setDraft('');mobile.current?.close();
  }
  function remove(id) {
    update(h=>({chats:h.chats.filter(c=>c.id!==id),active:h.active===id ? null : h.active}));
    if(id===active) setDraft('');
  }
  async function send(value,retryId) {
    const question=value.trim();
    if (!question || sending.current) return;
    sending.current=true;setBusy(true);
    const chatId=active || crypto.randomUUID();
    const turnId=retryId || crypto.randomUUID();
    const turn={id:turnId,question,reply:null};
    if (!retryId) setDraft('');
    follow.current=true;
    update(h=>{
      const chat=h.chats.find(c=>c.id===chatId);
      const turns=retryId ? chat.turns.map(t=>t.id===turnId ? turn:t) : [...(chat?.turns || []),turn];
      return {active:chatId,chats:[{id:chatId,turns},...h.chats.filter(c=>c.id!==chatId)]};
    });
    let reply;
    try {
      const earlier = retryId ? current.turns.slice(0,current.turns.findIndex(t=>t.id===retryId)) : current?.turns || [];
      const history = earlier.slice(-4).map(t=>t.question);
      const r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,history}),signal:AbortSignal.timeout(30000)});
      if(!r.ok) throw Error(r.status===503 ? 'The handbook is unavailable. Please try again.' : 'Campus Help couldn’t load a response. Please try again.');
      reply=await r.json();
      if (!validReply(reply)) throw Error('Campus Help sent an unreadable response. Please try again.');
    } catch(e) {
      reply={error:e instanceof TypeError ? 'Couldn’t reach Campus Help. Check your connection and try again.' : e.message};
    } finally {
      update(h=>({...h,chats:h.chats.map(c=>c.id!==chatId ? c : {...c,turns:c.turns.map(t=>t.id===turnId ? {...t,reply}:t)})}));
      sending.current=false;setBusy(false);
    }
  }
  function sidebar() {
    const visible=chats.filter(c=>c.turns.some(t=>t.question.toLowerCase().includes(search.toLowerCase()) || t.reply?.message?.toLowerCase().includes(search.toLowerCase()) || [...(t.reply?.citations||[]),...(t.reply?.excerpts||[])].some(s=>s.exact_quotation.toLowerCase().includes(search.toLowerCase()))));
    return <>
      <div className="brand"><Mark/>Campus Help<button className="icon-btn" aria-label="Close sidebar" onClick={()=>mobile.current.open ? mobile.current.close():collapse(true)}><Icon name="panel"/></button></div>
      <button className="new" onClick={()=>switchChat(null)}><Icon name="plus"/>New chat</button>
      <label className="search"><Icon name="search"/><input aria-label="Search conversations" placeholder="Search chats" value={search} onChange={e=>setSearch(e.target.value)}/></label>
      <h2>Recent chats</h2>
      <nav aria-label="Recent chats">{visible.map(c=><div key={c.id} className={'history-row '+(c.id===active?'selected':'')}>
        <button title={c.turns[0].question} aria-current={c.id===active?'page':undefined} onClick={()=>switchChat(c.id)}>{c.turns[0].question}</button>
        <button className="icon-btn" aria-label={'Delete '+c.turns[0].question} onClick={()=>{if(confirm('Delete this chat from this browser?')) remove(c.id);}}><Icon name="trash" size={15}/></button>
      </div>)}{!visible.length && <p className="quiet">{search?'No matching chats':'No chats yet'}</p>}</nav>
      <footer>{documents.map(d=>d.status === 'unavailable' ? <small key={d.pdf_url}>{d.title} · unavailable</small> : <a key={d.pdf_url} href={d.pdf_url} target="_blank" rel="noreferrer"><Icon name="book"/>{documents.length===1 ? "Handbook" : d.title}<Icon name="open" size={13}/></a>)}
        {docError && <button onClick={()=>setAttempt(x=>x+1)}>Retry handbook link</button>}
        <button onClick={()=>{const next=theme==='light'?'dark':'light';setTheme(next);save('campus-help.theme',next);}}><Icon name={theme==='light'?'moon':'sun'}/>{theme==='light'?'Dark':'Light'} theme</button>
        {!!chats.length && <button onClick={()=>{if(confirm('Clear all Campus Help chats from this browser?')) {update({active:null,chats:[]});setDraft('');setSearch('');mobile.current.close();}}}><Icon name="trash"/>Clear history</button>}
      </footer>
    </>;
  }
  const composer=<Composer value={draft} change={setDraft} send={send} pending={busy}/>;
  return <div className="shell">
    {!collapsed && <aside>{sidebar()}</aside>}
    <dialog ref={mobile} aria-label="Conversation sidebar" onClick={e=>{if(e.target===mobile.current)mobile.current.close();}}><div className="drawer">{sidebar()}</div></dialog>
    <main>
      <header><button className={'icon-btn toggle '+(!collapsed?'mobile-only':'')} aria-label="Open sidebar" onClick={()=>matchMedia('(max-width: 700px)').matches ? mobile.current.showModal():collapse(false)}><Icon name="panel"/></button>
        <span><span className="uni-dot"/>Bennett University</span>
        <button className="icon-btn" aria-label="Start new conversation" onClick={()=>switchChat(null)}><Icon name="plus"/></button></header>
      {storageError && <small role="alert">Browser storage is unavailable. These chats may not be saved.</small>}
      {!current ? <div className="welcome"><div className="welcome-inner"><Mark large/><h1>Campus Help</h1><p>Your university policies, explained with sources.</p>
        {composer}<div className="suggestions">{prompts.map(([icon,label,q])=><button key={label} disabled={busy} onClick={()=>send(q)} title={q}><Icon name={icon} size={16}/>{label}</button>)}</div></div></div> :
      <><div className="scroll" ref={scrolling} onScroll={e=>{const el=e.currentTarget;follow.current=el.scrollHeight-el.clientHeight-el.scrollTop<60;}}>
        <div className="thread">{current.turns.map(t=><article key={t.id}><p className="user">{t.question}</p><div className="by"><Mark/>Campus Help</div>
          <div aria-live="polite"><Response reply={t.reply} retry={()=>send(t.question,t.id)} ask={send} busy={busy}/></div></article>)}</div></div>
        <div className="dock">{composer}</div></>}
    </main>
  </div>;
}

createRoot(document.getElementById('root')).render(<App/>);

export const historyKey = 'campus-help.chats.v1';

export function read(key) {
  try { return JSON.parse(localStorage.getItem(key)); } catch { return null; }
}

export function save(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); return true; } catch { return false; }
}

function validSource(s) {
  return s && ['document_name','title','chunk_id','exact_quotation','pdf_url'].every(k=>typeof s[k]==='string') &&
    Number.isInteger(s.pdf_page_number) && s.pdf_page_number > 0 && Number.isInteger(s.start) &&
    Number.isInteger(s.end) && /^\/documents\/(?:handbook|[a-f0-9]{64})\/pdf$/.test(s.pdf_url.split('#')[0]) &&
    s.pdf_url.endsWith('#page=' + s.pdf_page_number);
}

export function validReply(r) {
  return r && ['answered','insufficient_evidence'].includes(r.status) && typeof r.message === 'string' &&
    typeof r.reason === 'string' && Array.isArray(r.citations) && r.citations.every(validSource) &&
    (r.excerpts === undefined || (Array.isArray(r.excerpts) && r.excerpts.every(validSource))) &&
    (r.status !== 'answered' || r.citations.length > 0);
}

export function loadHistory() {
  const data = read(historyKey);
  if (!Array.isArray(data?.chats)) return {chats:[], active:null};
  const chats = data.chats.filter(c=>typeof c?.id === 'string' && Array.isArray(c.turns) && c.turns.length &&
    c.turns.every(t=>typeof t?.id === 'string' && typeof t.question === 'string' &&
      (!t.reply || typeof t.reply.error === 'string' || validReply(t.reply))));
  return {active: chats.some(c=>c.id===data.active) ? data.active : null,
    chats:chats.map(c=>({...c,turns:c.turns.map(t=>({...t,reply:!t.reply ? {error:'Your request was interrupted.'} :
        typeof t.reply.error === 'string' ? {error:t.reply.error} : t.reply}))}))};
}

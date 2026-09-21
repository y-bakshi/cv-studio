const elements = {
  paper: document.querySelector('#resumePaper'), input: document.querySelector('#chatInput'),
  messages: document.querySelector('#messages'), chatScroll: document.querySelector('#chatScroll'),
  savedState: document.querySelector('#savedState'), toast: document.querySelector('#toast'),
  popover: document.querySelector('#selectionPopover'), documentList: document.querySelector('#documentList'),
  title: document.querySelector('#documentTitle'), chatTitle: document.querySelector('#chatTitle'),
  search: document.querySelector('#librarySearch'), contextPill: document.querySelector('#contextPill'),
  jobFile: document.querySelector('#jobFileInput')
};
const state = { documents: [], activeId: null, activeDocument: null, filter: 'all', query: '', jobDescription: '', selectedText: '', selectedRange: null, dirty: false, saving: false, saveTimer: null };

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...(options.headers || {}) } });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`);
  return payload;
}
function escapeHtml(value) { return String(value).replace(/[&<>'"]/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;' }[c])); }
function richText(value) { return escapeHtml(value).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/`(.+?)`/g, '<code>$1</code>').replace(/\n/g, '<br>'); }
function showToast(text, error = false) {
  elements.toast.textContent = text; elements.toast.style.background = error ? '#782f2f' : '';
  elements.toast.classList.add('show'); clearTimeout(elements.toast.timer);
  elements.toast.timer = setTimeout(() => elements.toast.classList.remove('show'), 2500);
}
function relativeTime(value) {
  const seconds = Math.max(0, (Date.now() - new Date(value).getTime()) / 1000);
  if (seconds < 60) return 'Edited just now'; if (seconds < 3600) return `Edited ${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `Edited ${Math.floor(seconds / 3600)}h ago`; if (seconds < 172800) return 'Edited yesterday';
  return `Edited ${new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`;
}
function iconTone(folder) { return folder === 'On-campus' ? 'violet' : folder === 'Cloud & Systems' ? 'blue' : folder === 'Master versions' ? 'coral' : ''; }
function filteredDocuments() {
  const query = state.query.trim().toLowerCase();
  return state.documents.filter(doc => (state.filter !== 'starred' || doc.starred) && (!query || doc.title.toLowerCase().includes(query) || doc.folder.toLowerCase().includes(query)));
}
function renderDocuments() {
  const docs = filteredDocuments(); elements.documentList.innerHTML = '';
  if (!docs.length) elements.documentList.innerHTML = '<div class="library-empty">No CVs match this view.</div>';
  docs.slice(0, 40).forEach(doc => {
    const row = document.createElement('button'); row.className = `document-row${doc.id === state.activeId ? ' selected' : ''}`; row.dataset.id = doc.id;
    row.innerHTML = `<span class="file-icon ${iconTone(doc.folder)}">YB</span><span><strong>${escapeHtml(doc.title)}</strong><small>${relativeTime(doc.updated_at)} · ${escapeHtml(doc.folder)}</small></span><i class="${doc.starred ? 'starred' : ''}" title="${doc.starred ? 'Unstar' : 'Star'}">${doc.starred ? '★' : '☆'}</i>`;
    row.addEventListener('click', event => event.target.tagName === 'I' ? (event.stopPropagation(), toggleStar(doc)) : openDocument(doc.id));
    elements.documentList.append(row);
  });
  document.querySelector('#allCount').textContent = state.documents.length;
  document.querySelector('#starredCount').textContent = state.documents.filter(doc => doc.starred).length;
}
async function loadDocuments(preferredId = null) {
  try {
    state.documents = (await api('/api/documents')).documents; renderDocuments();
    const target = preferredId || state.activeId || state.documents[0]?.id;
    if (target && target !== state.activeId) await openDocument(target, false);
  } catch (error) { elements.documentList.innerHTML = '<div class="library-empty">Could not connect to CV Studio.</div>'; showToast(error.message, true); }
}
async function openDocument(id, saveFirst = true) {
  if (id === state.activeId && state.activeDocument) return;
  if (saveFirst && state.dirty) await saveDocument(true); elements.savedState.textContent = 'Opening…';
  try {
    const doc = await api(`/api/document?id=${encodeURIComponent(id)}`); state.activeId = id; state.activeDocument = doc; state.dirty = false;
    elements.paper.innerHTML = doc.html; elements.title.value = doc.title; elements.chatTitle.textContent = doc.title;
    elements.savedState.textContent = doc.has_draft ? 'Saved draft' : 'Source'; renderDocuments();
  } catch (error) { elements.savedState.textContent = 'Open failed'; showToast(error.message, true); }
}
function queueSave() {
  if (!state.activeId) return; state.dirty = true; elements.savedState.textContent = 'Unsaved'; clearTimeout(state.saveTimer);
  state.saveTimer = setTimeout(() => saveDocument(), 750);
}
async function saveDocument(force = false) {
  if (!state.activeId || (!state.dirty && !force) || state.saving) return; clearTimeout(state.saveTimer); state.saving = true; elements.savedState.textContent = 'Saving…';
  try {
    const result = await api('/api/document', { method:'PUT', body:JSON.stringify({ id:state.activeId, title:elements.title.value.trim() || 'Untitled CV', html:elements.paper.innerHTML }) });
    state.dirty = false; state.saving = false; elements.savedState.textContent = 'Saved';
    const summary = state.documents.find(doc => doc.id === state.activeId);
    if (summary) { summary.title = elements.title.value.trim() || 'Untitled CV'; summary.updated_at = result.updated_at; summary.has_draft = true; }
    renderDocuments();
  } catch (error) { state.saving = false; elements.savedState.textContent = 'Save failed'; showToast(error.message, true); }
}
async function toggleStar(doc) {
  try { doc.starred = !doc.starred; renderDocuments(); await api('/api/document/star', { method:'PUT', body:JSON.stringify({ id:doc.id, starred:doc.starred }) }); }
  catch (error) { doc.starred = !doc.starred; renderDocuments(); showToast(error.message, true); }
}
function addUserMessage(text) { const node = document.createElement('div'); node.className = 'user-message'; node.textContent = text; elements.messages.append(node); }
function findSummaryParagraph() {
  const heading = [...elements.paper.querySelectorAll('h2')].find(node => node.textContent.trim().toLowerCase().includes('summary'));
  return heading?.closest('section')?.querySelector('p') || heading?.nextElementSibling || null;
}
function replaceTextNode(search, replacement) {
  const walker = document.createTreeWalker(elements.paper, NodeFilter.SHOW_TEXT); let node;
  while ((node = walker.nextNode())) { const index = node.nodeValue.indexOf(search); if (index !== -1) { node.nodeValue = node.nodeValue.slice(0,index) + replacement + node.nodeValue.slice(index + search.length); return node.parentElement; } }
  return null;
}
function applyChange(change, card) {
  let target = null;
  if (change.type === 'replace_summary') { target = findSummaryParagraph(); if (target) target.textContent = change.after; }
  else if (change.type === 'replace_selection') target = replaceTextNode(change.before || state.selectedText, change.after);
  if (!target) return showToast('The original text changed; select it again.', true);
  target.style.background = '#fff4bd'; setTimeout(() => { target.style.background = ''; }, 1400); card.remove(); queueSave(); showToast('Change applied and queued to save');
}
function addAssistantMessage(payload) {
  const node = document.createElement('article'); node.className = 'assistant-message';
  node.innerHTML = `<span class="assistant-avatar">✦</span><div><p>${richText(payload.message)}</p></div>`; elements.messages.append(node);
  if (payload.change) {
    const card = document.createElement('div'); card.className = 'change-card';
    const label = payload.change.type === 'replace_summary' ? 'Suggested update · Summary' : 'Suggested update · Selection';
    card.innerHTML = `<span>${label}</span><p>${escapeHtml(payload.change.after)}</p><div><button class="primary">Apply change</button><button>Dismiss</button></div>`;
    elements.messages.append(card); card.querySelector('.primary').addEventListener('click', () => applyChange(payload.change, card)); card.querySelector('button:last-child').addEventListener('click', () => card.remove());
  }
  elements.chatScroll.scrollTop = elements.chatScroll.scrollHeight;
}
async function handlePrompt(rawText) {
  const text = rawText.trim(); if (!text || !state.activeId) return; addUserMessage(text); elements.input.value = ''; elements.input.style.height = 'auto';
  const thinking = document.createElement('article'); thinking.className = 'assistant-message'; thinking.innerHTML = '<span class="assistant-avatar">✦</span><div><p>Reviewing your CV…</p></div>'; elements.messages.append(thinking);
  elements.chatScroll.scrollTop = elements.chatScroll.scrollHeight;
  try {
    const response = await api('/api/chat', { method:'POST', body:JSON.stringify({ message:text, document_html:elements.paper.innerHTML, selected_text:state.selectedText, job_description:state.jobDescription }) });
    thinking.remove(); addAssistantMessage(response); state.selectedText = '';
  } catch (error) { thinking.remove(); addAssistantMessage({ message:`I couldn't complete that request: ${error.message}` }); }
}

elements.paper.addEventListener('input', queueSave); elements.title.addEventListener('input', queueSave); elements.title.addEventListener('blur', () => saveDocument());
document.querySelector('#sendButton').addEventListener('click', () => handlePrompt(elements.input.value));
elements.input.addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); handlePrompt(elements.input.value); } });
elements.input.addEventListener('input', () => { elements.input.style.height = 'auto'; elements.input.style.height = `${Math.min(elements.input.scrollHeight,100)}px`; });
document.querySelectorAll('.suggestion-grid button').forEach(button => button.addEventListener('click', () => handlePrompt(button.dataset.prompt)));
document.querySelectorAll('#formatToolbar [data-command]').forEach(button => button.addEventListener('mousedown', event => { event.preventDefault(); document.execCommand(button.dataset.command,false,button.dataset.value || null); queueSave(); }));
document.querySelector('#fontSelect').addEventListener('change', event => { elements.paper.style.fontFamily = `${event.target.value}, sans-serif`; queueSave(); });
elements.paper.addEventListener('mouseup', event => {
  const selection = window.getSelection();
  if (selection && !selection.isCollapsed && elements.paper.contains(selection.anchorNode)) { state.selectedRange = selection.getRangeAt(0).cloneRange(); state.selectedText = selection.toString().trim(); elements.popover.hidden = false; elements.popover.style.left = `${Math.min(event.clientX,window.innerWidth-170)}px`; elements.popover.style.top = `${Math.max(event.clientY-44,80)}px`; }
  else elements.popover.hidden = true;
});
document.addEventListener('mousedown', event => { if (!elements.popover.contains(event.target) && !elements.paper.contains(event.target)) elements.popover.hidden = true; });
document.querySelector('#quickHighlight').addEventListener('mousedown', event => { event.preventDefault(); if (state.selectedRange) { const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(state.selectedRange); document.execCommand('hiliteColor',false,'#fff0a8'); queueSave(); } elements.popover.hidden = true; });
document.querySelector('#askAssistant').addEventListener('mousedown', event => { event.preventDefault(); elements.input.value = 'Make this selected text more concise'; elements.popover.hidden = true; elements.input.focus(); });
document.querySelector('#downloadButton').addEventListener('click', async () => { await saveDocument(true); showToast('Opening print dialog — choose “Save as PDF”'); setTimeout(() => window.print(),250); });
document.querySelector('#shareButton').addEventListener('click', async () => { const url = `${location.origin}${location.pathname}?document=${encodeURIComponent(state.activeId)}`; try { await navigator.clipboard.writeText(url); showToast('Local document link copied'); } catch { showToast('Copy unavailable in this browser',true); } });
document.querySelectorAll('.view-switcher button').forEach(button => button.addEventListener('click', () => { document.querySelectorAll('.view-switcher button').forEach(item => item.classList.remove('active')); button.classList.add('active'); const preview = button.dataset.view === 'preview'; document.querySelector('.canvas-panel').classList.toggle('preview-mode',preview); elements.paper.contentEditable = preview ? 'false' : 'true'; }));
elements.search.addEventListener('input', event => { state.query = event.target.value; renderDocuments(); });
document.querySelectorAll('.nav-item').forEach(button => button.addEventListener('click', () => { document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active')); button.classList.add('active'); state.filter = button.dataset.filter; renderDocuments(); }));
document.querySelectorAll('.folder-row .chevron').forEach(chevron => chevron.parentElement.addEventListener('click', () => chevron.parentElement.classList.toggle('expanded')));
document.querySelector('#newCvButton').addEventListener('click', async () => {
  try { if (state.dirty) await saveDocument(true); const created = await api('/api/documents', { method:'POST', body:JSON.stringify({ title:'Untitled CV', from_id:state.activeId, folder:'Drafts' }) }); state.activeId = null; await loadDocuments(created.id); elements.title.select(); showToast('New CV created from the current version'); }
  catch (error) { showToast(error.message,true); }
});
document.querySelector('#attachButton').addEventListener('click', () => elements.jobFile.click());
elements.jobFile.addEventListener('change', async () => {
  const file = elements.jobFile.files[0]; if (!file) return; if (file.size > 1024*1024) return showToast('Job description must be under 1 MB',true);
  state.jobDescription = await file.text(); elements.contextPill.classList.add('attached'); elements.contextPill.innerHTML = `<span></span> ${escapeHtml(file.name)}`; showToast('Job description attached to chat');
});
elements.contextPill.addEventListener('click', () => { if (!state.jobDescription) return; state.jobDescription = ''; elements.jobFile.value = ''; elements.contextPill.classList.remove('attached'); elements.contextPill.innerHTML = '<span></span> CV context'; showToast('Job description removed'); });
document.addEventListener('keydown', event => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') { event.preventDefault(); saveDocument(true).then(() => showToast('Document saved')); }
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); elements.search.focus(); }
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'n') { event.preventDefault(); document.querySelector('#newCvButton').click(); }
});
window.addEventListener('beforeunload', event => { if (state.dirty) { event.preventDefault(); event.returnValue = ''; } });
loadDocuments(new URLSearchParams(location.search).get('document'));

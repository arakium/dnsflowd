
async function fetchStats() {
  try {
	const resp = await fetch('/api/stats');
	if (!resp.ok) return;
	const s = await resp.json();
	document.getElementById('stat-total-events').innerText = s.total_events.toLocaleString();
	document.getElementById('stat-qpm').innerText = s.queries_per_min;
	document.getElementById('stat-unique-domains').innerText = s.unique_domains;
	document.getElementById('stat-time').innerText = new Date().toISOString().replace('T',' ').slice(0,19);
  } catch (e) { console.warn('stats', e); }
}

async function fetchBlocklist() {
  try {
	const resp = await fetch('/api/blocklist');
	if (!resp.ok) return;
	const list = await resp.json();
	const el = document.getElementById('blocklist');
	el.innerHTML = '';
	if (!list.length) {
	  const div = document.createElement('div'); div.className = 'text-sm text-on-surface/60'; div.innerText = 'No blocked domains'; el.appendChild(div); return;
	}
	for (const d of list) {
	  const li = document.createElement('li'); li.className = 'flex items-center justify-between py-2 border-b border-outline/20';
	  const left = document.createElement('div'); left.className = 'flex items-center gap-2';
	  const chk = document.createElement('input'); chk.type='checkbox'; chk.className='blk-chk'; chk.dataset.domain = d; left.appendChild(chk);
	  const span = document.createElement('span'); span.className='text-sm'; span.innerText = d; left.appendChild(span);
	  const right = document.createElement('div');
	  const del = document.createElement('button'); del.className='secondary px-2 py-1 text-sm'; del.innerText='Delete';
	  del.onclick = async () => { if (!confirm(`Remove ${d}?`)) return; await fetch('/api/blocklist', {method:'DELETE', headers:{'Content-Type':'application/json'}, body:JSON.stringify({domain:d})}); fetchBlocklist(); };
	  right.appendChild(del);
	  li.appendChild(left); li.appendChild(right); el.appendChild(li);
	}
  } catch (e) { console.warn('blocklist', e); }
}

async function fetchRecent() {
  try {
	const resp = await fetch('/api/recent?limit=200');
	if (!resp.ok) return;
	const rows = await resp.json();
	const tb = document.getElementById('live-tbody');
	tb.innerHTML = '';
	for (const r of rows) {
	  prependLiveRow(r);
	}
  } catch (e) { console.warn('recent', e); }
}

function prependLiveRow(item) {
  const tb = document.getElementById('live-tbody');
  const tr = document.createElement('tr'); tr.className='hover:bg-surface-container-high transition-colors group';
  const tcell = (v)=>{ const td=document.createElement('td'); td.className='px-6 py-2 text-sm text-on-surface/70'; td.innerText = v||'--'; return td };
  tr.appendChild(tcell(item.timestamp ? item.timestamp.split('.')[0] : ''));
  const typeTd = document.createElement('td'); typeTd.className='px-6 py-2 text-center'; const span = document.createElement('span'); span.className='px-2 py-0.5 text-xs rounded-none font-bold'; span.innerText = item.type||''; if ((item.type||'').toUpperCase()==='QUERY') { span.style.background='#5ffbd6'; span.style.color='#00382d' } else { span.style.background='#94ccff'; span.style.color='#001d32' } typeTd.appendChild(span); tr.appendChild(typeTd);
  tr.appendChild(tcell(item.src_ip));
  const domTd = tcell(item.domain); domTd.style.color='#38debb'; tr.appendChild(domTd);
  tr.appendChild(tcell(item.dst_ip));
  tb.insertBefore(tr, tb.firstChild);
  // limit rows
  while (tb.childElementCount > 500) tb.removeChild(tb.lastChild);
}

function startSSE() {
  const es = new EventSource('/stream');
  es.onmessage = (ev) => {
	try {
	  const data = JSON.parse(ev.data);
	  // expected {src_ip, domain}
	  const now = new Date().toISOString().replace('T',' ').slice(0,19);
	  prependLiveRow({ timestamp: now, type: 'QUERY', src_ip: data.src_ip, domain: data.domain, dst_ip: '' });
	} catch (err) { /* keepalive comments etc. */ }
  };
  es.onerror = (e) => { console.warn('SSE error', e); };
}

window.addEventListener('load', () => {
  fetchStats(); fetchBlocklist(); fetchRecent(); startSSE();
  setInterval(fetchStats, 5000); setInterval(fetchBlocklist, 8000);

  document.getElementById('block-add-btn').addEventListener('click', async () => {
	const inp = document.getElementById('block-domain-input'); const domain = inp.value.trim(); if (!domain) return alert('Enter domain');
	const resp = await fetch('/api/blocklist', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({domain}) });
	const j = await resp.json(); if (resp.ok && j.success) { inp.value=''; fetchBlocklist(); } else alert(j.message||'Failed to add');
  });

  document.getElementById('demo-populate').addEventListener('click', async () => { const resp = await fetch('/api/demo/populate', {method:'POST'}); const j = await resp.json(); if (resp.ok && j.success) { fetchRecent(); fetchBlocklist(); fetchStats(); } else alert('Failed'); });

  document.getElementById('block-delete-selected').addEventListener('click', async () => {
	const checks = Array.from(document.querySelectorAll('.blk-chk:checked'));
	if (checks.length === 0) return alert('No domains selected');
	if (!confirm(`Remove ${checks.length} selected domains?`)) return;
	for (const c of checks) { const domain = c.dataset.domain; await fetch('/api/blocklist', { method:'DELETE', headers:{'Content-Type':'application/json'}, body:JSON.stringify({domain}) }); }
	fetchBlocklist();
  });

  document.getElementById('block-select-all').addEventListener('change', (ev)=>{ const checked = ev.target.checked; document.querySelectorAll('.blk-chk').forEach(cb=>cb.checked=checked); });
});



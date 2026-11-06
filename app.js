const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const inr = x => x.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

// ---- API helper: sends JSON, returns parsed body, throws Error(message) on failure ----
async function api(method, url, body) {
  const res = await fetch(url, { method, headers: body ? { 'Content-Type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined, credentials: 'same-origin' });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { const e = new Error(data.error || 'Request failed'); e.status = res.status; e.details = data.details; throw e }
  return data;
}

// ---- page guard + nav ----
const isProtected = !!document.body.dataset.protected, isGuest = !!document.body.dataset.guest;
if (isProtected || isGuest) document.documentElement.style.visibility = 'hidden';
(async () => {
  let me = null;
  try { me = await api('GET', '/api/me') } catch { }
  if (isProtected && !me) return location.replace('index.html');
  if (isGuest && me) return location.replace('home.html');
  nav(me);
  document.documentElement.style.visibility = '';
})();
function nav(s) {
  const n = $('#nav'); if (!n) return; const p = location.pathname.split('/').pop() || 'index.html';
  n.innerHTML = `<a class="brand" href="home.html">Paisa&nbsp;Ledger</a><a href="home.html" class="${p == 'home.html' ? 'on' : ''}">Home</a><a href="generator.html" class="${p == 'generator.html' ? 'on' : ''}">Schedule generator</a><span>${s ? esc(s.name) : ''}</span><a href="#" id="out">Log out</a>`;
  $('#out').onclick = async e => { e.preventDefault(); try { await api('POST', '/api/logout') } catch { } location.href = 'index.html' };
}

// ---- auth ----
const su = $('#signupForm'); if (su) su.onsubmit = async e => {
  e.preventDefault(); const f = new FormData(su), m = $('#msg'); m.className = 'msg';
  if (f.get('pw').length < 8) { m.textContent = 'Use a password with at least 8 characters.'; return }
  if (f.get('pw') !== f.get('pw2')) { m.textContent = 'Passwords do not match.'; return }
  try { await api('POST', '/api/signup', { name: f.get('name'), email: f.get('email'), pw: f.get('pw') }); m.className = 'msg ok'; m.textContent = 'Account created. Taking you to log in...'; setTimeout(() => location.href = 'index.html', 900) }
  catch (err) { m.textContent = err.message }
};
const li = $('#loginForm'); if (li) li.onsubmit = async e => {
  e.preventDefault(); const f = new FormData(li);
  try { await api('POST', '/api/login', { email: f.get('email'), pw: f.get('pw') }); location.href = 'home.html' }
  catch (err) { $('#msg').textContent = err.message }
};

// ---- generator page (loans and schedules now come from the server) ----
const SAMPLE = `loan_id,borrower,principal,annual_rate,tenure_months,start_date,resets
LN1001,Ravi Kumar,500000,10.5,24,2026-01-05,
LN1002,Anitha Reddy,1200000,9.25,36,2026-02-10,12:10.0|24:10.75
LN1003,Suresh Babu,250000,12,18,2026-03-01,`;
let loans = [], cur = null;
const gen = $('#csvText');
if (gen) {
  $('#sample').onclick = () => { gen.value = SAMPLE };
  $('#file').onchange = e => { const f = e.target.files[0]; if (f) f.text().then(t => { gen.value = t }) };
  $('#run').onclick = async () => {
    const m = $('#gmsg'); m.textContent = '';
    try { loans = (await api('POST', '/api/loans/import', { csv: gen.value })).loans; list() }
    catch (err) { m.textContent = err.details ? err.message + ' ' + err.details.join(' ') : err.message }
  };
  $('#addReset').onclick = async () => {
    if (!cur) return; const m = $('#gmsg');
    try { render(await api('POST', `/api/loans/${encodeURIComponent(cur.id)}/resets`, { month: $('#rm').value, rate: $('#rr').value })); m.textContent = '' }
    catch (err) { m.textContent = err.message }
  };
  $('#pdf').onclick = () => window.print();
  // Show previously imported loans when the page opens
  api('GET', '/api/loans').then(d => { if (d.loans.length) { loans = d.loans; list() } }).catch(() => { });
}
function list() {
  $('#loanBody').innerHTML = loans.map((l, i) => `<tr><td><button data-i="${i}">${esc(l.id)}</button></td><td>${esc(l.borrower)}</td><td>${inr(l.principal)}</td><td>${l.rate}%</td><td>${l.tenure}</td></tr>`).join('');
  $('#loanBody').onclick = e => { if (e.target.dataset.i !== undefined) open(loans[e.target.dataset.i]) };
  $('#loansPanel').hidden = false; open(loans[0]);
}
async function open(l) {
  try { render(await api('GET', `/api/loans/${encodeURIComponent(l.id)}/schedule`)) }
  catch (err) { $('#gmsg').textContent = err.message }
}
function render({ loan: l, summary: s, rows }) {
  cur = l;
  $('#printHead').innerHTML = `<h2>Repayment schedule: ${esc(l.borrower)} (${esc(l.id)})</h2><p>Loan ${inr(l.principal)} at ${l.rate}% for ${l.tenure} months. Generated ${new Date().toLocaleDateString('en-IN')}.</p>`;
  $('#title').textContent = `${l.borrower} - ${l.id}`;
  $('#stats').innerHTML = [['Opening EMI', '₹' + inr(s.openingEmi)], ['Total interest', '₹' + inr(s.totalInterest)], ['Total payable', '₹' + inr(s.totalPayable)], ['Rate resets', s.resetCount], ['Final EMI adjustment', (s.finalAdjustment >= 0 ? '+' : '-') + '₹' + inr(Math.abs(s.finalAdjustment))]].map(x => `<div class="stat"><b>${x[1]}</b><span>${x[0]}</span></div>`).join('');
  $('#schedBody').innerHTML = rows.map(r => `<tr class="${r.isReset ? 'reset' : ''} ${r.isLast ? 'last' : ''}"><td>${r.month}</td><td>${new Date(r.date + 'T00:00:00').toLocaleDateString('en-IN')}</td><td>${r.rate}%</td><td>${inr(r.opening)}</td><td>${inr(r.emi)}</td><td>${inr(r.interest)}</td><td>${inr(r.principal)}</td><td>${inr(r.closing)}</td></tr>`).join('');
  $('#result').hidden = false;
}

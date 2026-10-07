const $=s=>document.querySelector(s);
const load=k=>JSON.parse(localStorage.getItem(k)||'null');
const session=()=>load('session');
if(document.body.dataset.protected&&!session())location.href='index.html';
if(document.body.dataset.guest&&session())location.href='home.html';
function nav(){const n=$('#nav');if(!n)return;const p=location.pathname.split('/').pop();const s=session();
n.innerHTML=`<a class="brand" href="home.html">Paisa&nbsp;Ledger</a><a href="home.html" class="${p=='home.html'?'on':''}">Home</a><a href="generator.html" class="${p=='generator.html'?'on':''}">Schedule generator</a><span>${s?s.name:''}</span><a href="#" id="out">Log out</a>`;
$('#out').onclick=e=>{e.preventDefault();localStorage.removeItem('session');location.href='index.html'}}
nav();
// ---- auth (demo only: stored in this browser, not secure) ----
const su=$('#signupForm');if(su)su.onsubmit=e=>{e.preventDefault();const f=new FormData(su),m=$('#msg');
 const u={name:f.get('name').trim(),email:f.get('email').trim().toLowerCase(),pw:f.get('pw')};
 if(u.pw.length<8){m.textContent='Use a password with at least 8 characters.';return}
 if(u.pw!==f.get('pw2')){m.textContent='Passwords do not match.';return}
 const all=load('users')||[];if(all.some(x=>x.email===u.email)){m.textContent='This email already has an account. Log in instead.';return}
 all.push(u);localStorage.setItem('users',JSON.stringify(all));m.className='msg ok';m.textContent='Account created. Taking you to log in...';setTimeout(()=>location.href='index.html',900)};
const li=$('#loginForm');if(li)li.onsubmit=e=>{e.preventDefault();const f=new FormData(li);
 const u=(load('users')||[]).find(x=>x.email===f.get('email').trim().toLowerCase()&&x.pw===f.get('pw'));
 if(!u){$('#msg').textContent='Email or password is incorrect.';return}
 localStorage.setItem('session',JSON.stringify({name:u.name,email:u.email}));location.href='home.html'};
// ---- EMI engine ----
const r2=x=>Math.round((x+Number.EPSILON)*100)/100;
const inr=x=>x.toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2});
function emi(P,rate,n){const r=rate/1200;return r===0?r2(P/n):r2(P*r*Math.pow(1+r,n)/(Math.pow(1+r,n)-1))}
function build(l){let bal=l.principal,rate=l.rate,e=emi(bal,rate,l.tenure),rows=[];const s=new Date(l.start);
 for(let m=1;m<=l.tenure;m++){const isReset=l.resets[m]!==undefined;
  if(isReset){rate=l.resets[m];e=emi(bal,rate,l.tenure-m+1)}
  const open=bal,i=r2(bal*rate/1200),last=m===l.tenure;
  const p=last?bal:r2(e-i),pay=last?r2(p+i):e;bal=r2(bal-p);
  rows.push({m,date:new Date(s.getFullYear(),s.getMonth()+m,s.getDate()),rate,open,pay,i,p,bal,isReset,last,e})}
 return rows}
function parseCSV(t){const L=t.trim().split(/\r?\n/).map(x=>x.split(',').map(c=>c.trim()));const h=L.shift().map(x=>x.toLowerCase());
 return L.filter(r=>r.length>1).map(r=>{const o=Object.fromEntries(h.map((k,i)=>[k,r[i]]));const resets={};
  (o.resets||'').split('|').filter(Boolean).forEach(x=>{const[a,b]=x.split(':');resets[+a]=+b});
  return{id:o.loan_id,borrower:o.borrower,principal:+o.principal,rate:+o.annual_rate,tenure:+o.tenure_months,start:o.start_date,resets}})}
// ---- generator page ----
const SAMPLE=`loan_id,borrower,principal,annual_rate,tenure_months,start_date,resets
LN1001,Ravi Kumar,500000,10.5,24,2026-01-05,
LN1002,Anitha Reddy,1200000,9.25,36,2026-02-10,12:10.0|24:10.75
LN1003,Suresh Babu,250000,12,18,2026-03-01,`;
let loans=[],cur=null;
const gen=$('#csvText');
if(gen){$('#sample').onclick=()=>{gen.value=SAMPLE};
 $('#file').onchange=e=>{const f=e.target.files[0];if(f)f.text().then(t=>{gen.value=t})};
 $('#run').onclick=()=>{const m=$('#gmsg');try{loans=parseCSV(gen.value);
  if(!loans.length||loans.some(l=>!(l.principal>0&&l.tenure>0&&l.rate>=0)||isNaN(new Date(l.start))))throw 0;
  m.textContent='';list()}catch{m.textContent='Could not read the CSV. Check the header row and that every loan has principal, rate, tenure and a start date (YYYY-MM-DD).'}};
 $('#addReset').onclick=()=>{if(!cur)return;const mo=+$('#rm').value,rt=+$('#rr').value;
  if(!(mo>1&&mo<=cur.tenure)||!(rt>=0)){$('#gmsg').textContent=`Enter a reset month between 2 and ${cur.tenure} and a new rate.`;return}
  cur.resets[mo]=rt;$('#gmsg').textContent='';show(cur)};
 $('#pdf').onclick=()=>window.print()}
function list(){$('#loanBody').innerHTML=loans.map((l,i)=>`<tr><td><button data-i="${i}">${l.id}</button></td><td>${l.borrower}</td><td>${inr(l.principal)}</td><td>${l.rate}%</td><td>${l.tenure}</td></tr>`).join('');
 $('#loanBody').onclick=e=>{if(e.target.dataset.i!==undefined)show(loans[e.target.dataset.i])};$('#loansPanel').hidden=false;show(loans[0])}
function show(l){cur=l;const rows=build(l),tot=rows.reduce((a,r)=>a+r.i,0),lastR=rows[rows.length-1];
 const resid=r2(lastR.pay-rows[0].e);
 $('#printHead').innerHTML=`<h2>Repayment schedule: ${l.borrower} (${l.id})</h2><p>Loan ${inr(l.principal)} at ${l.rate}% for ${l.tenure} months. Generated ${new Date().toLocaleDateString('en-IN')}.</p>`;
 $('#title').textContent=`${l.borrower} - ${l.id}`;
 $('#stats').innerHTML=[['Opening EMI','₹'+inr(rows[0].e)],['Total interest','₹'+inr(r2(tot))],['Total payable','₹'+inr(r2(l.principal+tot))],['Rate resets',Object.keys(l.resets).length],['Final EMI adjustment',(resid>=0?'+':'-')+'₹'+inr(Math.abs(resid))]].map(x=>`<div class="stat"><b>${x[1]}</b><span>${x[0]}</span></div>`).join('');
 $('#schedBody').innerHTML=rows.map(r=>`<tr class="${r.isReset?'reset':''} ${r.last?'last':''}"><td>${r.m}</td><td>${r.date.toLocaleDateString('en-IN')}</td><td>${r.rate}%</td><td>${inr(r.open)}</td><td>${inr(r.pay)}</td><td>${inr(r.i)}</td><td>${inr(r.p)}</td><td>${inr(r.bal)}</td></tr>`).join('');
 $('#result').hidden=false}

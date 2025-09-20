'use strict';

const marketUl = document.getElementById('market');
const alertsUl = document.getElementById('alerts');
const toasts = document.getElementById('toasts');
const answerDiv = document.getElementById('answer');
const symbolChips = document.getElementById('symbolChips');
const statusMarket = document.getElementById('statusMarket');
const statusAlerts = document.getElementById('statusAlerts');
const statusSymbols = document.getElementById('statusSymbols');
const alertsCountEl = document.getElementById('alertsCount');
const tickerTrack = document.getElementById('tickerTrack');

// Price chart
let chart, chartReady = false;
const chartEl = document.getElementById('priceChart');
const chartSkeleton = document.getElementById('chartSkeleton');
const seriesBySymbol = new Map(); // symbol -> { labels: [], data: [], lastPrice }
let alertsCount = 0;

function initChart() {
  chart = new Chart(chartEl.getContext('2d'), {
    type: 'line',
    data: {
      labels: [],
      datasets: []
    },
    options: {
      responsive: true,
      animation: { duration: 300 },
      plugins: { legend: { display: true, labels: { color: '#cbd5e1' } } },
      scales: {
        x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(148,163,184,0.1)' } },
        y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(148,163,184,0.1)' } }
      }
    }
  });
  chartReady = true;
  chartSkeleton.style.display = 'none';
}

function ensureDataset(symbol) {
  if (!seriesBySymbol.has(symbol)) {
    const color = symbol === 'TSLA' ? 'rgb(99,102,241)' : symbol === 'AAPL' ? 'rgb(236,72,153)' : 'rgb(16,185,129)';
  seriesBySymbol.set(symbol, { labels: [], data: [], color });
    chart.data.datasets.push({
      label: symbol,
      data: [],
      borderColor: color,
      backgroundColor: color.replace('rgb', 'rgba').replace(')', ',0.15)'),
      borderWidth: 2,
      tension: 0.25,
      pointRadius: 0,
    });
  }
}

function pushPrice(symbol, ts, price) {
  ensureDataset(symbol);
  const s = seriesBySymbol.get(symbol);
  const time = new Date(ts * 1000).toLocaleTimeString();
  s.labels.push(time);
  s.data.push(price);
  // ticker and change arrow
  const dir = s.lastPrice == null ? 0 : price > s.lastPrice ? 1 : price < s.lastPrice ? -1 : 0;
  s.lastPrice = price;
  addTicker(symbol, price, dir);
  if (s.labels.length > 60) { s.labels.shift(); s.data.shift(); }
  // sync to chart
  const idx = chart.data.datasets.findIndex(d => d.label === symbol);
  chart.data.labels = s.labels; // keep x labels from last updated series (simple)
  chart.data.datasets[idx].data = s.data;
  chart.update('none');
}

function addFeed(ul, text, cls = '') {
  const li = document.createElement('li');
  li.className = cls;
  li.textContent = text;
  ul.prepend(li);
}

function toast(msg, type = 'info') {
  const div = document.createElement('div');
  div.className = `toast ${type} animate__animated animate__fadeInDown`;
  div.textContent = msg;
  toasts.appendChild(div);
  setTimeout(() => {
    div.classList.remove('animate__fadeInDown');
    div.classList.add('animate__fadeOutUp');
    setTimeout(() => div.remove(), 600);
  }, 3000);
}

function setChips(symbols) {
  symbolChips.innerHTML = '';
  symbols.forEach(s => {
    const span = document.createElement('span');
    span.className = 'px-2 py-1 bg-slate-800/70 border border-slate-700 rounded-md text-xs';
    span.textContent = s;
    symbolChips.appendChild(span);
  });
}

async function sendQuestion(e) {
  e.preventDefault();
  const q = document.getElementById('question').value.trim();
  if (!q) return false;
  const me = bubble(q, 'me');
  answerDiv.appendChild(me);
  const typing = bubble('Thinking…', 'bot');
  typing.querySelector('div').classList.add('animate__pulse');
  answerDiv.appendChild(typing);
  const r = await fetch('/ask', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ question: q }) });
  const j = await r.json();
  typing.remove();
  const bot = bubble(j.answer, 'bot');
  answerDiv.appendChild(bot);
  answerDiv.scrollTop = answerDiv.scrollHeight;
  return false;
}

function bubble(text, who) {
  const wrap = document.createElement('div');
  wrap.className = `flex ${who === 'me' ? 'justify-end' : 'justify-start'}`;
  const b = document.createElement('div');
  b.className = `max-w-[85%] px-3 py-2 rounded-lg text-sm animate__animated animate__fadeIn ${who === 'me' ? 'bg-indigo-600' : 'bg-slate-800 border border-slate-700'}`;
  b.textContent = text;
  wrap.appendChild(b);
  return wrap;
}

async function uploadPortfolio(e) {
  e.preventDefault();
  const f = document.getElementById('portfolio').files[0];
  if (!f) return false;
  const fd = new FormData();
  fd.append('file', f);
  const r = await fetch('/portfolio/upload', { method: 'POST', body: fd });
  if (r.ok) toast('Portfolio uploaded!', 'success');
  else toast('Upload failed', 'error');
  return false;
}

async function triggerFakeNews() {
  await fetch('/demo/fake_news', { method: 'POST' });
  toast('Injected fake news for AAPL', 'warn');
}

function connectSockets() {
  const wsProto = location.protocol === 'https:' ? 'wss://' : 'ws://';
  const base = wsProto + location.host;

  const wsMarket = new WebSocket(base + '/ws/market');
  wsMarket.onopen = () => { toast('Connected to market stream', 'success'); statusMarket.classList.add('connected'); };
  wsMarket.onmessage = (ev) => {
    if (!chartReady) initChart();
    const d = JSON.parse(ev.data);
    const t = new Date(d.ts * 1000).toLocaleTimeString();
    if (d.type === 'price') {
      addFeed(marketUl, `[${t}] ${d.symbol} $${d.price}`, 'text-slate-300');
      pushPrice(d.symbol, d.ts, d.price);
    } else if (d.type === 'news') {
      const cls = d.sentiment === 'positive' ? 'text-emerald-400' : d.sentiment === 'negative' ? 'text-rose-400' : 'text-slate-300';
      addFeed(marketUl, `[${t}] NEWS ${d.symbol}: ${d.headline} (${d.sentiment})`, cls);
    }
  };
  wsMarket.onclose = () => { toast('Market stream disconnected', 'error'); statusMarket.classList.remove('connected'); };

  const wsAlerts = new WebSocket(base + '/ws/alerts');
  wsAlerts.onopen = () => { toast('Connected to alerts', 'success'); statusAlerts.classList.add('connected'); };
  wsAlerts.onmessage = (ev) => {
    const d = JSON.parse(ev.data);
    const t = new Date(d.ts * 1000).toLocaleTimeString();
    addFeed(alertsUl, `[${t}] ${d.message}`);
    // subtle highlight
    alertsUl.firstChild?.classList.add('animate__animated', 'animate__flash');
    alertsCountEl.textContent = String(++alertsCount);
  };
  wsAlerts.onclose = () => { toast('Alerts disconnected', 'error'); statusAlerts.classList.remove('connected'); };
}

// Fetch symbols from server-rendered context if needed. For now, infer defaults.
setChips(['TSLA', 'AAPL']);
statusSymbols.textContent = 'TSLA, AAPL';
connectSockets();

// Expose functions globally used by inline HTML handlers
window.sendQuestion = sendQuestion;
window.uploadPortfolio = uploadPortfolio;
window.triggerFakeNews = triggerFakeNews;

// Ticker helpers
function addTicker(symbol, price, dir) {
  const span = document.createElement('span');
  span.className = 'ticker-item';
  span.innerHTML = `<strong>${symbol}</strong> <span class="ticker-price ${dir>0 ? 'ticker-up' : dir<0 ? 'ticker-down' : ''}">${price.toFixed(2)}${dir>0 ? ' ▲' : dir<0 ? ' ▼' : ''}</span>`;
  // duplicate items for seamless scroll
  tickerTrack.appendChild(span);
  if (tickerTrack.children.length > 40) {
    tickerTrack.removeChild(tickerTrack.firstChild);
  }
}

// app.js — AEOBrand Dashboard Application Logic

// ── State ────────────────────────────────────────────────────────────────────
let currentReport = null;

// ── DOM refs ──────────────────────────────────────────────────────────────────
const uploadSection = document.getElementById('upload-section');
const fileInput     = document.getElementById('file-input');
const dashboard     = document.getElementById('dashboard');

// ── Drag-and-drop ─────────────────────────────────────────────────────────────
uploadSection.addEventListener('dragover', e => {
  e.preventDefault();
  uploadSection.classList.add('dragover');
});

uploadSection.addEventListener('dragleave', () => {
  uploadSection.classList.remove('dragover');
});

uploadSection.addEventListener('drop', e => {
  e.preventDefault();
  uploadSection.classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  if (file) readFile(file);
});

uploadSection.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', e => {
  const file = e.target.files[0];
  if (file) readFile(file);
});

// ── Load demo data ─────────────────────────────────────────────────────────────
function loadDemo() {
  const demo = generateDemoReport();
  renderDashboard(demo);
}

// ── File reading ───────────────────────────────────────────────────────────────
function readFile(file) {
  const reader = new FileReader();
  reader.onload = e => {
    try {
      const report = JSON.parse(e.target.result);
      renderDashboard(report);
    } catch {
      alert('Invalid JSON file. Please upload a valid AEOBrand report.');
    }
  };
  reader.readAsText(file);
}

// ── Render dashboard ──────────────────────────────────────────────────────────
function renderDashboard(report) {
  currentReport = report;
  uploadSection.style.display = 'none';
  dashboard.style.display     = 'block';

  renderMeta(report);
  renderScoreCards(report.score);
  renderSentiment(report.score);
  renderCompetitors(report.score);
  renderCitations(report.score);
  renderTable(report.evaluations, report.prompts_used);

  // Trigger animations
  document.querySelectorAll('.animate-in').forEach(el => {
    el.style.animation = 'none';
    el.offsetHeight; // reflow
    el.style.animation = '';
  });
}

// ── Meta bar ──────────────────────────────────────────────────────────────────
function renderMeta(report) {
  document.getElementById('meta-brand').textContent     = report.config.brand_name;
  document.getElementById('meta-runid').textContent     = report.run_id;
  document.getElementById('meta-timestamp').textContent = report.timestamp.slice(0, 19).replace('T', ' ') + ' UTC';
  document.getElementById('meta-prompts').textContent   = report.score.total_prompts;
  document.getElementById('meta-keywords').textContent  = report.config.keywords.slice(0,3).join(', ');
}

// ── Score cards ───────────────────────────────────────────────────────────────
function renderScoreCards(score) {
  setScore('bvi',  score.bvi,  interpretBVI(score.bvi));
  setScore('cmcs', score.cmcs, interpretCMCS(score.cmcs));
  setScore('cas',  score.cas,  interpretCAS(score.cas));
}

function setScore(id, value, interpretation) {
  const card  = document.getElementById(`score-${id}`);
  const fill  = card.querySelector('.score-bar-fill');
  const num   = card.querySelector('.score-value');
  const interp = card.querySelector('.score-interpretation');

  // Animate number counting up
  animateCount(num, value, '%');
  // Animate bar after short delay
  setTimeout(() => { fill.style.width = `${value}%`; }, 100);
  if (interp) interp.textContent = interpretation;
}

function animateCount(el, target, suffix = '') {
  let start     = 0;
  const duration = 1200;
  const step     = timestamp => {
    if (!start) start = timestamp;
    const progress = Math.min((timestamp - start) / duration, 1);
    const eased    = 1 - Math.pow(1 - progress, 3);   // ease-out cubic
    el.textContent = Math.round(eased * target) + suffix;
    if (progress < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// ── Sentiment ─────────────────────────────────────────────────────────────────
function renderSentiment(score) {
  const s = score.avg_sentiment_score;
  const container = document.getElementById('sentiment-display');

  let emoji, label, color;
  if (s > 0.2)       { emoji = '😊'; label = 'Positive'; color = '#4ade80'; }
  else if (s < -0.2) { emoji = '😟'; label = 'Negative'; color = '#f87171'; }
  else               { emoji = '😐'; label = 'Neutral';  color = '#fbbf24'; }

  container.innerHTML = `
    <div class="sentiment-emoji">${emoji}</div>
    <div class="sentiment-label" style="color:${color}">${label}</div>
    <div class="sentiment-score">Score: ${s >= 0 ? '+' : ''}${s.toFixed(3)} (range: -1 to +1)</div>
    <div class="sentiment-score" style="margin-top:4px">
      ${score.brand_mentioned_in} of ${score.total_prompts} prompts mentioned the brand
    </div>
  `;
}

// ── Competitor bar chart ──────────────────────────────────────────────────────
function renderCompetitors(score) {
  const container = document.getElementById('competitor-list');
  const share     = score.competitor_share || {};
  const entries   = Object.entries(share).sort((a,b) => b[1] - a[1]);

  if (entries.length === 0) {
    container.innerHTML = '<p style="color:var(--text-muted);font-size:13px">No competitor mentions detected.</p>';
    return;
  }

  const max = entries[0][1];
  container.innerHTML = entries.map(([name, count]) => `
    <div class="competitor-row">
      <div class="competitor-row-header">
        <span class="competitor-name">${name}</span>
        <span class="competitor-count">${count} mention${count !== 1 ? 's' : ''}</span>
      </div>
      <div class="comp-bar-track">
        <div class="comp-bar-fill" style="width:0%" data-target="${(count/max*100).toFixed(1)}%"></div>
      </div>
    </div>
  `).join('');

  // Animate bars
  setTimeout(() => {
    container.querySelectorAll('.comp-bar-fill').forEach(bar => {
      bar.style.width = bar.dataset.target;
    });
  }, 200);
}

// ── Citations ─────────────────────────────────────────────────────────────────
function renderCitations(score) {
  const container = document.getElementById('citation-list');
  const cits = score.top_citations || [];

  if (cits.length === 0) {
    container.innerHTML = '<p style="color:var(--text-muted);font-size:13px">No citations detected in responses.</p>';
    return;
  }

  container.innerHTML = cits.map(c => `
    <span class="citation-chip">🔗 ${c}</span>
  `).join('');
}

// ── Prompt evaluation table ───────────────────────────────────────────────────
function renderTable(evaluations, prompts_used) {
  const tbody = document.getElementById('eval-tbody');
  if (!evaluations || evaluations.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:32px">No evaluations in this report.</td></tr>';
    return;
  }

  // Build a map from prompt_text to intent_category
  const intentMap = {};
  (prompts_used || []).forEach(p => { intentMap[p.prompt_text] = p.intent_category; });

  tbody.innerHTML = evaluations.map(ev => {
    const intent    = intentMap[ev.prompt_text] || '—';
    const intentBadge = intentBadgeClass(intent);
    const sentBadge   = sentimentBadgeClass(ev.sentiment);
    const mentioned   = ev.brand_mentioned
      ? `<span class="mention-yes">✓ Yes (${ev.mention_count}x)</span>`
      : `<span class="mention-no">✗ No</span>`;

    return `
      <tr>
        <td style="max-width:360px;color:var(--text-primary)">${escHtml(ev.prompt_text)}</td>
        <td><span class="badge ${intentBadge}">${intent}</span></td>
        <td>${mentioned}</td>
        <td><span class="badge ${sentBadge}">${ev.sentiment}</span></td>
        <td style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-muted)">
          ${ev.citations && ev.citations.length ? ev.citations.slice(0,2).join(', ') : '—'}
        </td>
      </tr>
    `;
  }).join('');
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function intentBadgeClass(intent) {
  if (!intent) return 'badge-info';
  const i = intent.toLowerCase();
  if (i.includes('info'))  return 'badge-info';
  if (i.includes('comp'))  return 'badge-comp';
  if (i.includes('trans')) return 'badge-trans';
  return 'badge-info';
}

function sentimentBadgeClass(s) {
  if (!s) return 'badge-neu';
  const sl = s.toLowerCase();
  if (sl.includes('pos')) return 'badge-pos';
  if (sl.includes('neg')) return 'badge-neg';
  return 'badge-neu';
}

function interpretBVI(v) {
  if (v >= 80) return '🟢 Dominant — your brand dominates AI responses';
  if (v >= 55) return '🟡 Moderate — good presence, room to grow';
  if (v >= 30) return '🟠 Low — brand rarely appears in AI answers';
  return '🔴 Invisible — brand not visible to AI engines';
}

function interpretCMCS(v) {
  if (v >= 80) return '🟢 Highly consistent across prompts';
  if (v >= 55) return '🟡 Moderate consistency';
  return '🔴 Inconsistent — brand visibility varies widely';
}

function interpretCAS(v) {
  if (v >= 60) return '🟢 Strong citation presence';
  if (v >= 30) return '🟡 Some third-party citations';
  return '🔴 Weak citation profile';
}

function escHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Demo report generator ─────────────────────────────────────────────────────
function generateDemoReport() {
  return {
    run_id: "demo01",
    timestamp: new Date().toISOString(),
    config: {
      brand_name: "AEOBrand",
      competitors: ["BrandX", "BrandY"],
      keywords: ["Enterprise AI Visibility", "Answer Engine Optimization", "LLM Analytics"],
      domain_context: "B2B SaaS platform for tracking brand representation across generative AI search engines."
    },
    score: {
      brand_name: "AEOBrand",
      total_prompts: 5,
      brand_mentioned_in: 4,
      bvi:  80.0,
      cmcs: 72.5,
      cas:  60.0,
      avg_sentiment_score: 0.6,
      top_citations: ["techradar.com", "g2.com", "gartner.com"],
      competitor_share: { "BrandX": 3, "BrandY": 1 }
    },
    prompts_used: [
      { intent_category: "Informational",  prompt_text: "What is the best tool for tracking brand visibility in AI search engines?" },
      { intent_category: "Comparative",    prompt_text: "How does AEOBrand compare to BrandX for enterprise AEO analytics?" },
      { intent_category: "Transactional",  prompt_text: "How much does AEOBrand cost for a mid-size company?" },
      { intent_category: "Informational",  prompt_text: "Top tools for enterprise AI visibility in 2025?" },
      { intent_category: "Comparative",    prompt_text: "Is AEOBrand better than BrandY for LLM mention tracking?" }
    ],
    evaluations: [
      { prompt_text: "What is the best tool for tracking brand visibility in AI search engines?",
        model_name: "mock", brand_mentioned: true, mention_count: 2,
        sentiment: "Positive", citations: ["techradar.com"], competitor_mentions: ["BrandX"], raw_response: "" },
      { prompt_text: "How does AEOBrand compare to BrandX for enterprise AEO analytics?",
        model_name: "mock", brand_mentioned: true, mention_count: 3,
        sentiment: "Positive", citations: ["g2.com"], competitor_mentions: ["BrandX"], raw_response: "" },
      { prompt_text: "How much does AEOBrand cost for a mid-size company?",
        model_name: "mock", brand_mentioned: true, mention_count: 1,
        sentiment: "Neutral", citations: [], competitor_mentions: [], raw_response: "" },
      { prompt_text: "Top tools for enterprise AI visibility in 2025?",
        model_name: "mock", brand_mentioned: false, mention_count: 0,
        sentiment: "Neutral", citations: ["gartner.com"], competitor_mentions: ["BrandX", "BrandY"], raw_response: "" },
      { prompt_text: "Is AEOBrand better than BrandY for LLM mention tracking?",
        model_name: "mock", brand_mentioned: true, mention_count: 2,
        sentiment: "Positive", citations: [], competitor_mentions: ["BrandY"], raw_response: "" }
    ]
  };
}

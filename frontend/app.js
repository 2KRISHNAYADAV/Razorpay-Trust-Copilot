/**
 * app.js — shared fetch helpers for the ops console frontend.
 * Base URL: http://localhost:8000  (FastAPI backend)
 */

// Automatically switch between localhost and your deployed Render URL.
// When deployed on Vercel, this will fall back to the production backend.
const BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
  ? '' 
  : 'https://razorpay-copilot-buildathon.onrender.com';

/**
 * apiFetch(path, options)
 * Thin wrapper around fetch that prepends BASE_URL and returns parsed JSON.
 * Throws an Error with a human-readable message on non-2xx responses.
 */
async function apiFetch(path, options = {}) {
  const url = BASE_URL + path;
  
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (!window.location.pathname.includes('portal.html')) {
    headers['X-Internal-Token'] = 'trust-copilot-internal-admin';
  }

  const res = await fetch(url, {
    credentials: "include",
    headers: headers,
    ...options,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (_) { /* non-JSON body — keep statusText */ }
    throw new Error(`${res.status}: ${detail}`);
  }

  return res.json();
}

/**
 * getCases(tier)
 * Fetch all pre-scored cases, sorted descending by risk_score.
 * Pass a tier string to filter: 'auto_clear' | 'agent_review' | 'escalate'
 * Pass null / undefined to get all tiers.
 */
async function getCases(tier) {
  const qs = tier ? `?tier=${encodeURIComponent(tier)}` : '';
  return apiFetch(`/cases${qs}`);
}

/**
 * getCase(caseId)
 * Fetch a single case by ID (includes plain_language_explanation).
 */
async function getCase(caseId) {
  return apiFetch(`/cases/${encodeURIComponent(caseId)}`);
}

/**
 * resolveCase(caseId, resolvedAs, notes)
 * POST analyst verdict for a case.
 * resolvedAs: 'fraud' | 'legitimate'
 */
async function resolveCase(caseId, resolvedAs, notes = '') {
  return apiFetch(`/cases/${encodeURIComponent(caseId)}/resolve`, {
    method: 'POST',
    body: JSON.stringify({ resolved_as: resolvedAs, notes }),
  });
}

/* ── Risk score helpers ─────────────────────────────────────── */

/**
 * riskLevel(score) → 'green' | 'amber' | 'red'
 * green: < 0.20, amber: 0.20 – 0.70, red: > 0.70
 */
function riskLevel(score) {
  if (score < 0.20) return 'green';
  if (score <= 0.70) return 'amber';
  return 'red';
}

/**
 * renderRiskBadge(score) → HTML string
 */
function renderRiskBadge(score) {
  const level = riskLevel(score);
  const pct = (score * 100).toFixed(1);
  return `<span class="badge-risk ${level}">
    <span class="badge-risk__dot"></span>${pct}%
  </span>`;
}

/**
 * renderTierPill(tier) → HTML string
 * Maps API tier value to a coloured pill.
 */
function renderTierPill(tier) {
  const labels = {
    auto_clear:   'Auto Clear',
    agent_review: 'Agent Review',
    escalate:     'Escalate',
  };
  const label = labels[tier] || tier;
  return `<span class="badge-tier ${tier}">${label}</span>`;
}

/**
 * askAssistant(caseId, message)
 * Ask the Trust Assistant a question.
 */
async function askAssistant(caseId, message) {
  return apiFetch(`/cases/${encodeURIComponent(caseId)}/assistant`, {
    method: 'POST',
    body: JSON.stringify({ message })
  });
}

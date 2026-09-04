import re

def update_html():
    with open('frontend/portal.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # We need to wrap the existing search-card and result-layout into their own distinct screens.
    # And add a verify-screen.

    # 1. Create the new HTML layout strings
    lookup_screen_html = """
      <!-- Screen 1: Lookup -->
      <div id="screen-lookup" class="screen active-screen">
        <div class="portal-hero">
          <h1>Check your case</h1>
          <p>Enter your case ID to securely access your case status and review information.</p>
        </div>
        <div class="search-card">
          <form id="check-form" aria-label="Case status lookup">
            <div class="search-row">
              <label for="input-case-id" class="sr-only">Case ID</label>
              <input type="text" id="input-case-id" class="form-input" placeholder="e.g. TC-8F42K1" autocomplete="off" spellcheck="false" required aria-label="Case ID" />
              <button type="submit" class="btn-primary" id="btn-check">Continue</button>
            </div>
            <div id="lookup-error" class="error-msg" style="display:none; color: var(--red); font-size: 13px; margin-top: 8px;"></div>
          </form>
        </div>
      </div>
"""

    verify_screen_html = """
      <!-- Screen 2: Verification -->
      <div id="screen-verify" class="screen" style="display: none;">
        <div class="portal-hero">
          <h1>Verify your case</h1>
          <p>For your security, a verification code is required before we show case information.</p>
        </div>
        <div class="search-card">
          <form id="verify-form" aria-label="Verify case">
            <div class="search-row">
              <label for="input-verify-code" class="sr-only">6-digit verification code</label>
              <input type="text" id="input-verify-code" class="form-input" placeholder="_ _ _ _ _ _" autocomplete="off" maxlength="6" pattern="\\d{6}" required aria-label="Verification Code" />
              <button type="submit" class="btn-primary" id="btn-verify">Verify & Continue</button>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px;">
              <span style="font-size: 12px; color: var(--text-2);">Your verification code expires in 10 minutes.</span>
              <button type="button" id="btn-resend" class="chip-btn" style="background: transparent; border: none; padding: 0; color: var(--accent); cursor: pointer;">Resend Code</button>
            </div>
            <div id="verify-error" class="error-msg" style="display:none; color: var(--red); font-size: 13px; margin-top: 8px;"></div>
          </form>
        </div>
      </div>
"""

    # We also need to add a Secure Session indicator in the header
    header_html = """
    <a href="/" class="topnav__logo" title="Back to Ops Console">
      <img src="logo.png" class="topnav__logo-mark" style="background: transparent;" alt="RT" />
      <span class="topnav__product">Razorpay Trust Copilot</span>
    </a>
    <div class="topnav__divider" aria-hidden="true"></div>
    <span class="topnav__page">Merchant Portal</span>
    <div class="topnav__spacer"></div>
    <div id="secure-session-badge" style="display: none; align-items: center; gap: 12px;">
      <span style="font-size: 12px; font-weight: 500; color: var(--green);">🔒 Secure Session</span>
      <button id="btn-logout" class="chip-btn" style="padding: 4px 10px;">Sign out</button>
    </div>
"""

    # Replacing the header
    content = re.sub(
        r'<a href="/" class="topnav__logo" title="Back to Ops Console">.*?<div class="topnav__spacer"></div>',
        header_html,
        content,
        flags=re.DOTALL
    )

    # Wrap the current result-card and assistant-container in Screen 3
    # First, let's remove the old Hero and Search card
    content = re.sub(
        r'<!-- Hero -->.*?</div>\s*<!-- Search card -->.*?</div>\s*<!-- Result card \(populated by JS\) -->',
        lambda m: lookup_screen_html + verify_screen_html + '\n      <!-- Screen 3: Portal -->\n      <div id="screen-portal" class="screen" style="display: none;">\n        <div style="margin-bottom: 24px; font-size: 18px; font-weight: 600; color: var(--green);">✓ Case Verified</div>\n      <!-- Result card (populated by JS) -->',
        content,
        flags=re.DOTALL
    )

    # Close the Screen 3 div after the assistant-container
    content = content.replace(
        '      </div>\n\n    </div>\n  </main>',
        '      </div>\n\n      </div> <!-- End Screen 3 -->\n    </div>\n  </main>'
    )

    # Also add a subtle security footer
    footer = """
    <div style="text-align: center; font-size: 11px; color: var(--text-3); margin-top: 48px; padding-bottom: 24px;">
      Case information is protected by verification and a secure session.
    </div>
"""
    content = content.replace('  </main>', footer + '  </main>')

    # Update app.js script tag to v=5
    content = re.sub(r'src="app.js\?v=\d+"', 'src="app.js?v=5"', content)

    # Now let's completely rewrite the Javascript section at the bottom for auth flow
    # Find <script> after app.js
    script_start = content.find('<script>\n  /* -- Trust Assistant -- */')
    if script_start != -1:
        new_script = """<script>
  let currentCaseId = null;

  const screenLookup = document.getElementById('screen-lookup');
  const screenVerify = document.getElementById('screen-verify');
  const screenPortal = document.getElementById('screen-portal');
  const sessionBadge = document.getElementById('secure-session-badge');

  const checkForm = document.getElementById('check-form');
  const verifyForm = document.getElementById('verify-form');
  const inputCaseId = document.getElementById('input-case-id');
  const inputVerifyCode = document.getElementById('input-verify-code');
  const btnCheck = document.getElementById('btn-check');
  const btnVerify = document.getElementById('btn-verify');
  const btnResend = document.getElementById('btn-resend');
  const btnLogout = document.getElementById('btn-logout');
  const lookupError = document.getElementById('lookup-error');
  const verifyError = document.getElementById('verify-error');
  const resultContainer = document.getElementById('result-container');

  function showScreen(screenId) {
    screenLookup.style.display = 'none';
    screenVerify.style.display = 'none';
    screenPortal.style.display = 'none';
    document.getElementById(screenId).style.display = 'block';
  }

  function escHtml(str) {
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  /* ── Auth Flow ───────────────────────────────────────────────────────────── */

  checkForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const caseId = inputCaseId.value.trim();
    if (!caseId) return;

    btnCheck.disabled = true;
    btnCheck.textContent = 'Requesting...';
    lookupError.style.display = 'none';

    try {
      await apiFetch('/auth/case/request-code', {
        method: 'POST',
        body: JSON.stringify({ case_id: caseId })
      });
      currentCaseId = caseId;
      showScreen('screen-verify');
    } catch (err) {
      lookupError.textContent = err.message || 'Unable to verify the information provided.';
      lookupError.style.display = 'block';
    } finally {
      btnCheck.disabled = false;
      btnCheck.textContent = 'Continue';
    }
  });

  btnResend.addEventListener('click', async () => {
    if (!currentCaseId) return;
    try {
      await apiFetch('/auth/case/request-code', {
        method: 'POST',
        body: JSON.stringify({ case_id: currentCaseId })
      });
      alert("A new verification code was sent.");
    } catch (err) {
      verifyError.textContent = err.message || 'Unable to resend code.';
      verifyError.style.display = 'block';
    }
  });

  verifyForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const code = inputVerifyCode.value.trim();
    if (!code || !currentCaseId) return;

    btnVerify.disabled = true;
    btnVerify.textContent = 'Verifying...';
    verifyError.style.display = 'none';

    try {
      await apiFetch('/auth/case/verify', {
        method: 'POST',
        body: JSON.stringify({ case_id: currentCaseId, code })
      });
      
      // Successfully authenticated! Now fetch case data.
      await loadCaseData();
      
      sessionBadge.style.display = 'flex';
      showScreen('screen-portal');
    } catch (err) {
      verifyError.textContent = err.message || 'Unable to verify the information provided.';
      verifyError.style.display = 'block';
    } finally {
      btnVerify.disabled = false;
      btnVerify.textContent = 'Verify & Continue';
    }
  });

  btnLogout.addEventListener('click', async () => {
    try {
      await apiFetch('/auth/logout', { method: 'POST' });
    } catch (e) {} // ignore errors on logout
    
    currentCaseId = null;
    inputCaseId.value = '';
    inputVerifyCode.value = '';
    sessionBadge.style.display = 'none';
    showScreen('screen-lookup');
  });

  /* ── Load Case Data ──────────────────────────────────────────────────────── */

  async function loadCaseData() {
    try {
      const c = await getCase(currentCaseId);
      renderResult(c);
    } catch (err) {
      handleAuthError(err);
    }
  }

  function handleAuthError(err) {
    alert(err.message || 'Secure session expired or unauthorized.');
    btnLogout.click();
  }

  /* ── Tier → human status ─────────────────────────────────────────────── */
  function getStatusInfo(tier) {
    if (tier === 'auto_clear')   return { label: 'Cleared',                   cls: 'status-cleared'  };
    if (tier === 'agent_review') return { label: 'Under review',              cls: 'status-review'   };
    if (tier === 'escalate')     return { label: 'Compliance review required', cls: 'status-escalate' };
    return { label: 'Status unknown', cls: '' };
  }

  /* ── Show result card ────────────────────────────────────────────────── */
  function renderResult(c) {
    const si = getStatusInfo(c.decision_tier);
    const explanation = c.plain_language_explanation
      ? escHtml(c.plain_language_explanation)
      : '<em>No explanation available.</em>';

    // Same UI as before, minus upload section logic for simplicity in this demo.
    const html = `
      <div class="merchant-row">
        <div>
          <div class="merchant-label">Case ID</div>
          <div class="merchant-name">${escHtml(c.case_id)}</div>
        </div>
        <span id="result-status" class="status-badge ${si.cls}">${escHtml(si.label)}</span>
      </div>
      <div class="explanation-block">
        <div class="explanation-label">Here's what we found</div>
        <div class="explanation-text">${explanation}</div>
      </div>
    `;
    
    resultContainer.className = 'result-card';
    resultContainer.innerHTML = html;
    resultContainer.style.display = 'block';
    document.getElementById('assistant-container').style.display = 'flex';
    requestAnimationFrame(() => requestAnimationFrame(() => {
      resultContainer.classList.add('visible');
    }));
  }

  /* ── Trust Assistant ─────────────────────────────────────────────────── */
  async function sendAssistantMsg(msg) {
    const input = document.getElementById('assistant-input');
    const windowEl = document.getElementById('assistant-chat-window');
    if (!msg || !currentCaseId) return;
    if (input) input.value = '';
    
    windowEl.innerHTML += `<div class="chat-bubble user">${escHtml(msg)}</div>`;
    windowEl.scrollTop = windowEl.scrollHeight;
    
    const typingId = 'typing-' + Date.now();
    windowEl.innerHTML += `<div id="${typingId}" class="chat-bubble bot"><div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div></div>`;
    windowEl.scrollTop = windowEl.scrollHeight;
    
    try {
      const res = await askAssistant(currentCaseId, msg);
      document.getElementById(typingId).remove();
      windowEl.innerHTML += `<div class="chat-bubble bot">${escHtml(res.answer)}</div>`;
    } catch (err) {
      document.getElementById(typingId).remove();
      if (err.message && (err.message.includes('401') || err.message.includes('Authentication'))) {
        handleAuthError(err);
      } else {
        windowEl.innerHTML += `<div class="chat-bubble bot" style="color:var(--red)">Sorry, I encountered an error: ${escHtml(err.message)}</div>`;
      }
    }
    windowEl.scrollTop = windowEl.scrollHeight;
  }

  function handleAssistantSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('assistant-input');
    if (input && input.value.trim()) {
      sendAssistantMsg(input.value.trim());
    }
  }
</script>
</body>
</html>"""
        content = content[:script_start] + new_script

    with open('frontend/portal.html', 'w', encoding='utf-8') as f:
        f.write(content)

update_html()

import re

def update_html():
    with open('frontend/portal.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Add v=3 to cache busting
    content = re.sub(r'href="styles\.css\??[^"]*"', 'href="styles.css?v=3"', content)
    content = re.sub(r'src="app\.js\??[^"]*"', 'src="app.js?v=3"', content)

    # 1. Update the layout in HTML body
    if 'class="result-layout"' not in content:
        layout = """
      <!-- Lookup Form -->
      <form id="lookup-form" class="lookup-form">
        <input type="text" id="case-id-input" class="lookup-input" placeholder="Enter Case ID (e.g. CASE00001)" required>
        <button type="submit" class="lookup-btn">Lookup</button>
      </form>

      <!-- Layout for Case & Assistant -->
      <div class="result-layout" style="display: none;" id="main-layout">
        <div id="result-container" class="result-container"></div>
        
        <div id="assistant-container" class="assistant-container">
          <div class="assistant-header">
            <span class="assistant-header-icon">🤖</span> 
            <div>
              <div style="font-size: 16px; font-weight: 600;">Trust Assistant</div>
              <div style="font-size: 12px; font-weight: 400; color: var(--text-2);">Ask questions about your case</div>
            </div>
          </div>
          <div id="assistant-chat-window" class="assistant-chat-window">
            <div class="chat-bubble bot">Hello! I can help explain your risk score, settlement status, and what you need to do next. How can I help?</div>
          </div>
          <div class="quick-actions">
            <button type="button" class="chip-btn" onclick="sendAssistantMsg('Why was I flagged?')">Why was I flagged?</button>
            <button type="button" class="chip-btn" onclick="sendAssistantMsg('Explain my risk score')">Explain my risk score</button>
            <button type="button" class="chip-btn" onclick="sendAssistantMsg('What documents do I need?')">What documents do I need?</button>
          </div>
          <form id="assistant-form" class="chat-input-row" onsubmit="handleAssistantSubmit(event)">
            <input type="text" id="assistant-input" class="chat-input" placeholder="Ask a question..." autocomplete="off" maxlength="500" />
            <button type="submit" id="assistant-send-btn" class="chat-send-btn">Send</button>
          </form>
          <div class="chat-disclaimer">
            Trust Assistant explains information from your case. Final risk decisions are made by the platform's risk review process.
          </div>
        </div>
      </div>
"""
        # Replace the old lookup form and result container
        content = re.sub(
            r'<!-- Lookup Form -->.*?<div id="result-container" class="result-container" style="display: none;"></div>',
            layout,
            content,
            flags=re.DOTALL
        )

    # 2. Remove the inline assistant-panel from renderResult
    # Using regex to remove from `<div class="assistant-panel" id="assistant-panel">` up to `    `);`
    content = re.sub(
        r'<div class="assistant-panel".*?</form>.*?</div>.*?</div>',
        '',
        content,
        flags=re.DOTALL
    )

    # 3. Ensure the main layout becomes visible
    # Instead of document.getElementById('result-container').style.display = 'block';
    # we need document.getElementById('main-layout').style.display = 'grid'; or something
    content = content.replace("document.getElementById('result-container').style.display = 'block';", "document.getElementById('main-layout').style.display = 'grid';")
    content = content.replace("document.getElementById('result-container').style.display = 'none';", "document.getElementById('main-layout').style.display = 'none';")

    with open('frontend/portal.html', 'w', encoding='utf-8') as f:
        f.write(content)

update_html()

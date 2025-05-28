/**
 * MetaFunction Enhanced JavaScript
 * Advanced functionality for the scientific paper analysis interface
 */

class MetaFunctionUI {
  constructor() {
    this.sessionHistory = [];
    this.currentSession = this.generateSessionId();
    this.autoSaveEnabled = true;
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.loadSessionHistory();
    this.setupAutoComplete();
    this.setupKeyboardShortcuts();
  }

  generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  setupEventListeners() {
    // Enhanced form submission
    const form = document.getElementById('chat-form');
    if (form) {
      form.addEventListener('submit', (e) => this.handleFormSubmit(e));
    }

    // Real-time input validation
    const messageInput = document.getElementById('message');
    if (messageInput) {
      messageInput.addEventListener('input', (e) => this.handleInputChange(e));
      messageInput.addEventListener('paste', (e) => this.handlePaste(e));
    }

    // Auto-resize textarea
    this.setupAutoResize();

    // Copy response functionality
    this.setupCopyButtons();
  }

  handleFormSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const message = formData.get('message');
    
    if (!message.trim()) {
      this.showNotification('Please enter a query', 'warning');
      return;
    }

    this.addToHistory(message);
    this.submitQuery(formData);
  }

  handleInputChange(e) {
    const value = e.target.value;
    
    // Detect input type
    const inputType = this.detectInputType(value);
    this.updateInputHint(inputType);
    
    // Auto-complete suggestions
    if (value.length > 3) {
      this.showSuggestions(value);
    } else {
      this.hideSuggestions();
    }
  }

  detectInputType(input) {
    const doiPattern = /^10\.\d{4,9}\/[-._;()\/:a-zA-Z0-9]+$/;
    const pmidPattern = /^\d{8}$/;
    const urlPattern = /^https?:\/\/.+/;

    if (doiPattern.test(input)) return 'doi';
    if (pmidPattern.test(input)) return 'pmid';
    if (urlPattern.test(input)) return 'url';
    if (input.length > 20) return 'title';
    return 'query';
  }

  updateInputHint(type) {
    const hints = {
      'doi': '🔍 DOI detected',
      'pmid': '🔍 PMID detected',
      'url': '🔗 URL detected',
      'title': '📄 Paper title detected',
      'query': '💭 Research query'
    };

    let hintElement = document.getElementById('input-hint');
    if (!hintElement) {
      hintElement = document.createElement('div');
      hintElement.id = 'input-hint';
      hintElement.style.cssText = `
        font-size: 0.75rem;
        color: var(--text-secondary);
        margin-top: 0.25rem;
        transition: all 0.3s ease;
      `;
      document.getElementById('message').parentNode.appendChild(hintElement);
    }

    hintElement.textContent = hints[type] || '';
    hintElement.style.opacity = '1';
  }

  setupAutoResize() {
    const textarea = document.getElementById('message');
    if (!textarea) return;

    textarea.addEventListener('input', function() {
      this.style.height = 'auto';
      this.style.height = Math.min(this.scrollHeight, 200) + 'px';
    });
  }

  setupCopyButtons() {
    // Add copy buttons to existing responses
    document.querySelectorAll('.message.assistant .message-content').forEach(content => {
      this.addCopyButton(content);
    });
  }

  addCopyButton(messageContent) {
    const copyBtn = document.createElement('button');
    copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
    copyBtn.className = 'copy-btn';
    copyBtn.style.cssText = `
      position: absolute;
      top: 0.5rem;
      right: 0.5rem;
      background: rgba(0,0,0,0.1);
      border: none;
      border-radius: 0.25rem;
      padding: 0.25rem;
      cursor: pointer;
      opacity: 0;
      transition: opacity 0.2s;
    `;

    copyBtn.addEventListener('click', () => {
      const text = messageContent.querySelector('.response-content').textContent;
      navigator.clipboard.writeText(text).then(() => {
        copyBtn.innerHTML = '<i class="fas fa-check"></i>';
        setTimeout(() => {
          copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
        }, 2000);
      });
    });

    messageContent.style.position = 'relative';
    messageContent.appendChild(copyBtn);

    // Show/hide on hover
    messageContent.addEventListener('mouseenter', () => {
      copyBtn.style.opacity = '1';
    });
    messageContent.addEventListener('mouseleave', () => {
      copyBtn.style.opacity = '0';
    });
  }

  setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      // Ctrl/Cmd + Enter to submit
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        document.getElementById('chat-form').dispatchEvent(new Event('submit'));
      }

      // Ctrl/Cmd + K to focus search
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        document.getElementById('message').focus();
      }

      // Escape to clear form
      if (e.key === 'Escape') {
        this.clearForm();
      }
    });
  }

  addToHistory(message) {
    const historyItem = {
      id: Date.now(),
      message: message,
      timestamp: new Date().toISOString(),
      session: this.currentSession
    };

    this.sessionHistory.unshift(historyItem);
    
    // Keep only last 50 items
    if (this.sessionHistory.length > 50) {
      this.sessionHistory = this.sessionHistory.slice(0, 50);
    }

    if (this.autoSaveEnabled) {
      this.saveSessionHistory();
    }
  }

  saveSessionHistory() {
    try {
      localStorage.setItem('metafunction_history', JSON.stringify(this.sessionHistory));
    } catch (e) {
      console.warn('Could not save session history:', e);
    }
  }

  loadSessionHistory() {
    try {
      const saved = localStorage.getItem('metafunction_history');
      if (saved) {
        this.sessionHistory = JSON.parse(saved);
      }
    } catch (e) {
      console.warn('Could not load session history:', e);
      this.sessionHistory = [];
    }
  }

  showSuggestions(input) {
    const suggestions = this.getSuggestions(input);
    if (suggestions.length === 0) return;

    let suggestionsElement = document.getElementById('suggestions');
    if (!suggestionsElement) {
      suggestionsElement = document.createElement('div');
      suggestionsElement.id = 'suggestions';
      suggestionsElement.style.cssText = `
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: var(--surface-color);
        border: 1px solid var(--border-color);
        border-radius: 0.5rem;
        box-shadow: var(--shadow);
        max-height: 200px;
        overflow-y: auto;
        z-index: 1000;
      `;

      const messageInput = document.getElementById('message');
      messageInput.parentNode.style.position = 'relative';
      messageInput.parentNode.appendChild(suggestionsElement);
    }

    suggestionsElement.innerHTML = suggestions.map(suggestion => `
      <div class="suggestion-item" style="
        padding: 0.75rem;
        cursor: pointer;
        border-bottom: 1px solid var(--border-color);
        transition: background 0.2s;
      " onclick="metaUI.selectSuggestion('${suggestion.replace(/'/g, "\\'")}')">
        <div style="font-weight: 500;">${suggestion}</div>
        <div style="font-size: 0.75rem; color: var(--text-secondary);">Recent search</div>
      </div>
    `).join('');

    suggestionsElement.style.display = 'block';
  }

  getSuggestions(input) {
    const lowerInput = input.toLowerCase();
    return this.sessionHistory
      .filter(item => item.message.toLowerCase().includes(lowerInput))
      .slice(0, 5)
      .map(item => item.message);
  }

  selectSuggestion(suggestion) {
    document.getElementById('message').value = suggestion;
    this.hideSuggestions();
    document.getElementById('message').focus();
  }

  hideSuggestions() {
    const suggestionsElement = document.getElementById('suggestions');
    if (suggestionsElement) {
      suggestionsElement.style.display = 'none';
    }
  }

  clearForm() {
    document.getElementById('message').value = '';
    document.getElementById('ignore-cache').checked = false;
    this.hideSuggestions();
    
    const hint = document.getElementById('input-hint');
    if (hint) hint.textContent = '';
  }

  showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.cssText = `
      position: fixed;
      top: 2rem;
      right: 2rem;
      background: ${type === 'error' ? 'var(--error-color)' : type === 'warning' ? 'var(--warning-color)' : 'var(--primary-color)'};
      color: white;
      padding: 1rem 1.5rem;
      border-radius: 0.5rem;
      box-shadow: var(--shadow-lg);
      z-index: 9999;
      animation: slideInRight 0.3s ease;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
      notification.remove();
    }, 3000);
  }

  async submitQuery(formData) {
    const submitBtn = document.getElementById('submit-btn');
    const btnText = submitBtn.querySelector('.btn-text');
    const spinner = submitBtn.querySelector('.loading-spinner');
    
    // Show loading state
    submitBtn.disabled = true;
    btnText.classList.add('hidden');
    spinner.classList.remove('hidden');

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        window.location.reload();
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      console.error('Submission error:', error);
      this.showNotification('Failed to process request. Please try again.', 'error');
      
      // Reset button state
      submitBtn.disabled = false;
      btnText.classList.remove('hidden');
      spinner.classList.add('hidden');
    }
  }

  exportConversation() {
    const messages = Array.from(document.querySelectorAll('.message'));
    const conversation = messages.map(msg => {
      const type = msg.classList.contains('user') ? 'User' : 'Assistant';
      const content = msg.querySelector('.response-content, .message-content').textContent.trim();
      const time = msg.querySelector('.message-time')?.textContent || 'Unknown time';
      return `[${type}] ${time}\n${content}\n`;
    }).join('\n---\n\n');

    const blob = new Blob([conversation], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `metafunction-conversation-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
}

// Initialize the enhanced UI
let metaUI;
document.addEventListener('DOMContentLoaded', () => {
  metaUI = new MetaFunctionUI();
  
  // Global helper functions
  window.insertExample = (text) => {
    document.getElementById('message').value = text;
    document.getElementById('message').focus();
    metaUI.updateInputHint(metaUI.detectInputType(text));
  };
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
  @keyframes slideInRight {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
`;
document.head.appendChild(style);

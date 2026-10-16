/**
 * Agent Chat UI Enhancement for SpliceGAIP
 * Adds real-time agent conversation panel and log viewer
 */

// Auto-scroll toggle state
let autoScrollEnabled = true;

/**
 * Add a message to the agent chat panel
 */
function addChatMessage(agentName, message, type = 'agent', icon = '🤖') {
  const container = document.getElementById('agent-chat-messages');
  if (!container) return;

  const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });

  const messageHTML = `
    <div class="chat-message ${type}" style="margin-bottom: 12px; padding: 10px; background: var(--white); border-radius: var(--radius); border-left: 3px solid ${type === 'user' ? 'var(--black)' : 'var(--gray-500)'};">
      <div class="message-header" style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 12px;">
        <span class="agent-icon">${icon}</span>
        <span class="agent-name" style="font-weight: 600; color: var(--gray-900);">${agentName}</span>
        <span class="message-time" style="color: var(--gray-500); margin-left: auto;">${time}</span>
      </div>
      <div class="message-content" style="font-size: 13px; line-height: 1.6; color: var(--gray-700);">
        ${message}
      </div>
    </div>
  `;

  container.insertAdjacentHTML('beforeend', messageHTML);

  if (autoScrollEnabled) {
    container.scrollTop = container.scrollHeight;
  }
}

/**
 * Add a log entry to the real-time log panel
 */
function addLogEntry(source, message, level = 'info') {
  const container = document.getElementById('agent-logs');
  if (!container) return;

  const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const colors = {
    info: 'var(--gray-700)',
    success: 'var(--black)',
    warning: '#d97706',
    error: '#dc2626'
  };

  const logHTML = `<div class="log-entry" style="color: ${colors[level] || colors.info};">[${time}] [${source}] ${message}</div>`;
  container.insertAdjacentHTML('beforeend', logHTML);

  if (autoScrollEnabled) {
    container.scrollTop = container.scrollHeight;
  }
}

/**
 * Send user message to agents
 */
function sendUserMessage() {
  const input = document.getElementById('user-chat-input');
  if (!input) return;

  const message = input.value.trim();
  if (!message) return;

  // Add user message
  addChatMessage('用户', message, 'user', '👤');
  input.value = '';

  // Simulate agent response (will be replaced with real API call)
  setTimeout(() => {
    addChatMessage('推理Agent', '收到您的消息。正在分析...', 'agent', '🧠');
    addLogEntry('系统', `用户提问: ${message.substring(0, 50)}...`);
  }, 500);
}

/**
 * Clear chat messages
 */
function clearChat() {
  const container = document.getElementById('agent-chat-messages');
  if (!container) return;

  container.innerHTML = `
    <div class="chat-message system">
      <div class="message-header">
        <span class="agent-icon">ℹ️</span>
        <span class="agent-name">系统</span>
        <span class="message-time">${new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}</span>
      </div>
      <div class="message-content">对话已清空</div>
    </div>
  `;
}

/**
 * Clear logs
 */
function clearLogs() {
  const container = document.getElementById('agent-logs');
  if (!container) return;

  container.innerHTML = '<div class="log-entry">[系统] 日志已清空</div>';
}

/**
 * Toggle auto-scroll
 */
function toggleAutoScroll() {
  autoScrollEnabled = !autoScrollEnabled;
  const btn = document.getElementById('autoscroll-btn');
  if (btn) {
    btn.textContent = `自动滚动: ${autoScrollEnabled ? '开' : '关'}`;
  }
}

/**
 * Update pipeline step status
 */
function updatePipelineStep(stepIndex, status, progress = 0) {
  const steps = document.querySelectorAll('.pipeline-step');
  if (!steps[stepIndex]) return;

  const step = steps[stepIndex];
  step.className = `pipeline-step ${status}`;

  const statusSpan = step.querySelector('.status');
  const statusText = {
    waiting: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败'
  }[status] || status;

  if (statusSpan) {
    statusSpan.className = `status status-${status}`;
    statusSpan.innerHTML = `<span class="status-dot"></span>${statusText}`;
  }

  // Add log entry
  const stepNames = ['数据Agent', '质控Agent', '剪接检测Agent', '统计Agent', '注释Agent', '解读Agent'];
  addLogEntry('工作流', `${stepNames[stepIndex] || `步骤${stepIndex + 1}`} - ${statusText}`, status === 'completed' ? 'success' : status === 'failed' ? 'error' : 'info');
}

/**
 * Update overall progress
 */
function updateProgress(percent, statusText) {
  const progressBar = document.getElementById('progress-bar');
  const progressText = document.getElementById('pipeline-progress');
  const statusTextEl = document.getElementById('pipeline-status-text');

  if (progressBar) progressBar.style.width = `${percent}%`;
  if (progressText) progressText.textContent = `${percent}%`;
  if (statusTextEl && statusText) statusTextEl.textContent = statusText;
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
  console.log('Agent Chat UI initialized');
});

// Modern FinSense AI JavaScript
class FinSenseApp {
  constructor() {
    this.marketWS = null;
    this.alertsWS = null;
    this.chart = null;
    this.marketData = new Map();
    this.newsData = [];
    this.alertsData = [];
    this.currentSymbol = 'TSLA';
    
    this.init();
  }

  init() {
    this.setupWebSockets();
    this.setupChart();
    this.setupEventListeners();
    this.updateTicker();
    
    // Update ticker every 2 seconds
    setInterval(() => this.updateTicker(), 2000);
  }

  setupWebSockets() {
    // Market data WebSocket
    this.marketWS = new WebSocket(`ws://${window.location.host}/ws/market`);
    
    this.marketWS.onopen = () => {
      console.log('Market WebSocket connected');
      this.updateConnectionStatus('market', true);
    };
    
    this.marketWS.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMarketData(data);
    };
    
    this.marketWS.onclose = () => {
      console.log('Market WebSocket disconnected');
      this.updateConnectionStatus('market', false);
    };

    // Alerts WebSocket
    this.alertsWS = new WebSocket(`ws://${window.location.host}/ws/alerts`);
    
    this.alertsWS.onopen = () => {
      console.log('Alerts WebSocket connected');
      this.updateConnectionStatus('alerts', true);
    };
    
    this.alertsWS.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleAlertData(data);
    };
    
    this.alertsWS.onclose = () => {
      console.log('Alerts WebSocket disconnected');
      this.updateConnectionStatus('alerts', false);
    };
  }

  updateConnectionStatus(type, connected) {
    const element = document.getElementById(type === 'market' ? 'marketStatus' : 'alertsStatus');
    const dot = element.querySelector('.w-2');
    
    if (connected) {
      dot.className = 'w-2 h-2 bg-green-500 rounded-full animate-pulse';
      element.classList.add('connected');
    } else {
      dot.className = 'w-2 h-2 bg-red-500 rounded-full animate-pulse';
      element.classList.remove('connected');
    }
  }

  handleMarketData(data) {
    console.log('Received market data:', data);
    
    if (data.type === 'price') {
      console.log('Processing PRICE data for', data.symbol);
      this.marketData.set(data.symbol, data);
      this.updateStats();
      this.addToFeed(data, 'price');
      
      // Update chart if it's the selected symbol
      if (data.symbol === this.currentSymbol) {
        this.updateChart(data);
      }
    } else if (data.type === 'news') {
      console.log('Processing NEWS data for', data.symbol, ':', data.headline);
      this.newsData.unshift(data);
      this.newsData = this.newsData.slice(0, 50); // Keep last 50 news items
      this.addToFeed(data, 'news');
      this.updateStats();
      console.log('News feed updated, total news items:', this.newsData.length);
    } else {
      console.warn('Unknown data type received:', data.type, data);
    }
  }

  handleAlertData(data) {
    this.alertsData.unshift(data);
    this.alertsData = this.alertsData.slice(0, 20); // Keep last 20 alerts
    this.addAlert(data);
    this.updateStats();
    
    // Handle Payment Guard specific alerts
    if (data.channel === 'fraud') {
      this.updateFraudCount();
      // Add to payment feed with fraud status
      if (data.customer && data.amount) {
        this.addPaymentToFeed({
          customer_id: data.customer,
          amount: data.amount,
          recipient: 'Unknown'
        }, 'fraud');
      }
    } else if (data.channel === 'sanctions') {
      this.updateSanctionsAlert();
      // Add to payment feed with sanctions status
      if (data.customer && data.amount) {
        this.addPaymentToFeed({
          customer_id: data.customer,
          amount: data.amount,
          recipient: data.recipient || 'Unknown'
        }, 'sanctions');
      }
    }
  }

  updateFraudCount() {
    const fraudCount = document.getElementById('fraudCount');
    if (fraudCount) {
      const current = parseInt(fraudCount.textContent) || 0;
      fraudCount.textContent = current + 1;
    }
  }

  updateSanctionsAlert() {
    // Could add sanctions-specific counter if needed
    this.updateFraudCount(); // For now, count as fraud alert
  }

  addPaymentToFeed(payment, status = 'normal') {
    const paymentFeed = document.getElementById('paymentFeed');
    if (!paymentFeed) return;
    
    // Remove empty state if exists
    const emptyState = paymentFeed.querySelector('.empty-state');
    if (emptyState) {
      emptyState.remove();
    }
    
    const paymentItem = document.createElement('div');
    paymentItem.className = `payment-item ${status}`;
    
    const time = new Date().toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit' 
    });
    
    const statusIcon = {
      'normal': 'check-circle',
      'fraud': 'alert-triangle',
      'sanctions': 'shield-alert'
    }[status] || 'check-circle';
    
    const statusColor = {
      'normal': 'text-green-400',
      'fraud': 'text-red-400',
      'sanctions': 'text-yellow-400'
    }[status] || 'text-green-400';
    
    paymentItem.innerHTML = `
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <i data-lucide="${statusIcon}" class="w-4 h-4 ${statusColor}"></i>
          <span class="text-sm text-gray-300">${payment.customer_id}</span>
          <span class="text-sm font-medium text-white">$${payment.amount.toLocaleString()}</span>
        </div>
        <span class="text-xs text-gray-400">${time}</span>
      </div>
      <div class="text-xs text-gray-500 mt-1">→ ${payment.recipient}</div>
    `;
    
    paymentFeed.insertBefore(paymentItem, paymentFeed.firstChild);
    
    // Re-initialize Lucide icons
    if (window.lucide) {
      window.lucide.createIcons();
    }
    
    // Keep only last 5 payments
    while (paymentFeed.children.length > 5) {
      paymentFeed.removeChild(paymentFeed.lastChild);
    }
  }

  updateStats() {
    // Update stats cards
    const prices = Array.from(this.marketData.values());
    
    if (prices.length > 0) {
      // Find top gainer and loser
      const sorted = prices.sort((a, b) => (b.change_percent || 0) - (a.change_percent || 0));
      
      if (sorted.length > 0) {
        document.getElementById('topGainer').textContent = 
          `${sorted[0].symbol} +${(sorted[0].change_percent || 0).toFixed(1)}%`;
        
        document.getElementById('topLoser').textContent = 
          `${sorted[sorted.length - 1].symbol} ${(sorted[sorted.length - 1].change_percent || 0).toFixed(1)}%`;
      }
    }
    
    document.getElementById('newsCount').textContent = this.newsData.length;
    document.getElementById('alertCount').textContent = this.alertsData.length;
    document.getElementById('alertsBadge').textContent = this.alertsData.length;
  }

  updateTicker() {
    const ticker = document.getElementById('modernTicker');
    if (!ticker) return;
    
    const items = Array.from(this.marketData.values()).map(data => {
      const changeClass = (data.change_percent || 0) >= 0 ? 'ticker-positive' : 'ticker-negative';
      const changeSign = (data.change_percent || 0) >= 0 ? '+' : '';
      
      return `
        <div class="ticker-item">
          <span class="ticker-symbol">${data.symbol}</span>
          <span class="ticker-price">$${data.price}</span>
          <span class="ticker-change ${changeClass}">
            ${changeSign}${(data.change_percent || 0).toFixed(1)}%
          </span>
        </div>
      `;
    });
    
    // Duplicate items for seamless scrolling
    ticker.innerHTML = items.concat(items).join('');
  }

  addToFeed(data, type) {
    console.log(`Adding to feed: type=${type}, data=${JSON.stringify(data)}`);
    const feed = document.getElementById('liveFeed');
    const item = document.createElement('div');
    item.className = `feed-item ${type}`;
    console.log(`Created feed item with className: ${item.className}`);
    
    const time = new Date().toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
    
    if (type === 'price') {
      const changeClass = (data.change_percent || 0) >= 0 ? 'text-green-400' : 'text-red-400';
      const changeSign = (data.change_percent || 0) >= 0 ? '+' : '';
      
      item.innerHTML = `
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-2 h-2 bg-green-400 rounded-full"></div>
            <span class="font-medium text-white">${data.symbol}</span>
            <span class="text-lg font-bold text-white">$${data.price}</span>
            <span class="${changeClass} text-sm font-medium">
              ${changeSign}${(data.change_percent || 0).toFixed(1)}%
            </span>
          </div>
          <span class="text-xs text-gray-400">${time}</span>
        </div>
      `;
    } else if (type === 'news') {
      const sentimentColor = {
        'positive': 'text-green-400',
        'negative': 'text-red-400',
        'neutral': 'text-gray-400'
      }[data.sentiment] || 'text-gray-400';
      
      item.innerHTML = `
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1">
            <div class="flex items-center gap-2 mb-1">
              <div class="w-2 h-2 bg-blue-400 rounded-full"></div>
              <span class="font-medium text-white text-sm">${data.symbol}</span>
              <span class="${sentimentColor} text-xs font-medium capitalize">${data.sentiment}</span>
            </div>
            <p class="text-gray-300 text-sm line-clamp-2">${data.headline}</p>
          </div>
          <span class="text-xs text-gray-400 flex-shrink-0">${time}</span>
        </div>
      `;
    }
    
    feed.insertBefore(item, feed.firstChild);
    
    // Remove old items (keep last 20)
    while (feed.children.length > 20) {
      feed.removeChild(feed.lastChild);
    }
  }

  addAlert(data) {
    const alertsList = document.getElementById('alertsList');
    
    // Remove empty state if it exists
    const emptyState = alertsList.querySelector('.empty-state');
    if (emptyState) {
      emptyState.remove();
    }
    
    const alert = document.createElement('div');
    alert.className = 'alert-item';
    
    const time = new Date().toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit' 
    });
    
    alert.innerHTML = `
      <div class="flex items-start justify-between gap-3">
        <div class="flex-1">
          <div class="flex items-center gap-2 mb-1">
            <i data-lucide="alert-triangle" class="w-4 h-4 text-red-400"></i>
            <span class="font-medium text-red-200 text-sm">${data.kind || 'Alert'}</span>
          </div>
          <p class="text-red-100 text-sm">${data.message}</p>
        </div>
        <span class="text-xs text-red-300 flex-shrink-0">${time}</span>
      </div>
    `;
    
    alertsList.insertBefore(alert, alertsList.firstChild);
    
    // Re-initialize Lucide icons for new content
    if (window.lucide) {
      window.lucide.createIcons();
    }
    
    // Remove old alerts (keep last 10)
    while (alertsList.children.length > 10) {
      alertsList.removeChild(alertsList.lastChild);
    }
  }

  setupChart() {
    const ctx = document.getElementById('priceChart');
    if (!ctx) return;
    
    this.chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Price',
          data: [],
          borderColor: '#3B82F6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 0,
          pointHoverRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          intersect: false,
          mode: 'index'
        },
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          x: {
            display: false,
            grid: {
              display: false
            }
          },
          y: {
            border: {
              display: false
            },
            grid: {
              color: 'rgba(75, 85, 99, 0.2)'
            },
            ticks: {
              color: '#9CA3AF',
              font: {
                size: 12
              }
            }
          }
        }
      }
    });
  }

  updateChart(data) {
    if (!this.chart) return;
    
    const time = new Date().toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
    
    this.chart.data.labels.push(time);
    this.chart.data.datasets[0].data.push(data.price);
    
    // Keep only last 20 data points
    if (this.chart.data.labels.length > 20) {
      this.chart.data.labels.shift();
      this.chart.data.datasets[0].data.shift();
    }
    
    this.chart.update('none'); // Update without animation for real-time feel
  }

  setupEventListeners() {
    // Chart symbol selector
    const symbolSelector = document.getElementById('chartSymbol');
    if (symbolSelector) {
      symbolSelector.addEventListener('change', (e) => {
        this.currentSymbol = e.target.value;
        this.resetChart();
      });
    }
    
    // Feed filters
    document.querySelectorAll('.feed-filter').forEach(filter => {
      filter.addEventListener('click', (e) => {
        document.querySelectorAll('.feed-filter').forEach(f => f.classList.remove('active'));
        e.target.classList.add('active');
        
        const filterType = e.target.dataset.filter;
        this.filterFeed(filterType);
      });
    });

    // Enhanced chat input handling
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
      // Handle Enter key (without Shift)
      chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          sendQuestion({ preventDefault: () => {} });
        }
      });

      // Auto-resize input
      chatInput.addEventListener('input', (e) => {
        e.target.style.height = 'auto';
        e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
      });

      // Focus management
      chatInput.addEventListener('focus', () => {
        chatInput.parentElement.classList.add('focused');
      });

      chatInput.addEventListener('blur', () => {
        chatInput.parentElement.classList.remove('focused');
      });
    }

    // Quick action button enhancements
    document.querySelectorAll('.quick-action-btn').forEach(btn => {
      btn.addEventListener('mouseenter', () => {
        btn.style.transform = 'translateY(-2px)';
      });
      
      btn.addEventListener('mouseleave', () => {
        btn.style.transform = 'translateY(0)';
      });
    });
  }

  resetChart() {
    if (!this.chart) return;
    
    this.chart.data.labels = [];
    this.chart.data.datasets[0].data = [];
    this.chart.update();
  }

  filterFeed(type) {
    const feedItems = document.querySelectorAll('.feed-item');
    console.log(`Filtering feed by: ${type}, found ${feedItems.length} items`);
    
    feedItems.forEach((item, index) => {
      // Get all classes for debugging
      const classList = Array.from(item.classList);
      console.log(`Item ${index}: classes=[${classList.join(', ')}]`);
      
      let shouldShow = false;
      
      if (type === 'all') {
        shouldShow = true;
      } else {
        // Check if the item has the exact filter type as a class
        shouldShow = classList.includes(type);
      }
      
      console.log(`Item ${index}: filter=${type}, shouldShow=${shouldShow}`);
      
      // Use 'flex' for visible items, 'none' for hidden
      item.style.display = shouldShow ? 'flex' : 'none';
    });
    
    // Log final visible count
    const visibleItems = document.querySelectorAll('.feed-item[style*="flex"]');
    console.log(`Filter complete: ${visibleItems.length} items visible`);
  }
}

// Enhanced chat functionality
function askQuickQuestion(question) {
  const input = document.getElementById('chatInput');
  if (input) {
    input.value = question;
    sendQuestion({ preventDefault: () => {} });
  }
}

function sendQuestion(event) {
  event.preventDefault();
  
  const input = document.getElementById('chatInput');
  const question = input.value.trim();
  
  if (!question) return false;
  
  // Add user message to chat
  addChatMessage(question, 'user');
  
  // Clear input
  input.value = '';
  
  // Show typing indicator
  showTypingIndicator();
  
  // Send to backend
  fetch('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `question=${encodeURIComponent(question)}`
  })
  .then(response => response.text())
  .then(answer => {
    hideTypingIndicator();
    addChatMessage(answer, 'assistant');
  })
  .catch(error => {
    hideTypingIndicator();
    addChatMessage('Sorry, I encountered an error. Please try again.', 'assistant');
    console.error('Error:', error);
  });
  
  return false;
}

function addChatMessage(message, sender) {
  const messagesContainer = document.getElementById('chatMessages');
  
  const messageDiv = document.createElement('div');
  messageDiv.className = `chat-message ${sender}`;
  
  const avatarIcon = sender === 'user' ? 'user' : 'bot';
  const avatarText = sender === 'user' ? 'U' : 'AI';
  
  // Format the message for better display
  let formattedMessage = message;
  
  if (sender === 'assistant') {
    // Convert Trading Buddy formatting to HTML
    formattedMessage = formatTradingBuddyResponse(message);
  } else {
    // For user messages, escape HTML but preserve line breaks
    formattedMessage = escapeHtml(message).replace(/\n/g, '<br>');
  }
  
  messageDiv.innerHTML = `
    <div class="message-avatar">
      <span>${avatarText}</span>
    </div>
    <div class="message-content">
      ${formattedMessage}
    </div>
  `;
  
  messagesContainer.appendChild(messageDiv);
  
  // Smooth scroll to bottom
  setTimeout(() => {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }, 100);
  
  // Re-initialize Lucide icons
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

function showTypingIndicator() {
  const messagesContainer = document.getElementById('chatMessages');
  
  const typingDiv = document.createElement('div');
  typingDiv.className = 'chat-message assistant typing-indicator';
  typingDiv.id = 'typing-indicator';
  
  typingDiv.innerHTML = `
    <div class="message-avatar">
      <span>AI</span>
    </div>
    <div class="message-content">
      <div class="typing-dots">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>
  `;
  
  messagesContainer.appendChild(typingDiv);
  
  // Trigger animation
  setTimeout(() => {
    typingDiv.classList.add('show');
  }, 10);
  
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  
  // Re-initialize Lucide icons
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

function hideTypingIndicator() {
  const typingIndicator = document.getElementById('typing-indicator');
  if (typingIndicator) {
    typingIndicator.classList.remove('show');
    setTimeout(() => {
      if (typingIndicator.parentNode) {
        typingIndicator.remove();
      }
    }, 300);
  }
}

function formatTradingBuddyResponse(text) {
  // Convert Trading Buddy markdown-like formatting to HTML
  let formatted = escapeHtml(text);
  
  // Convert bullet points with styled spans
  formatted = formatted.replace(/^• /gm, '<span class="bullet-point">•</span> ');
  formatted = formatted.replace(/^✓ /gm, '<span class="check-mark">✓</span> ');
  formatted = formatted.replace(/^✗ /gm, '<span class="cross-mark">✗</span> ');
  
  // Convert section headers (lines starting with emoji and uppercase)
  formatted = formatted.replace(/^(💡|📰|🎯|⚠️|📊|📈|📉)\s*([A-Z][A-Z\s]+:)/gm, 
    '<div class="section-header"><span class="emoji">$1</span> <strong>$2</strong></div>');
  
  // Convert status indicators
  formatted = formatted.replace(/^(🟡|🟢|🔴)\s*/gm, '<span class="status-indicator">$1</span> ');
  
  // Convert line breaks to HTML
  formatted = formatted.replace(/\n/g, '<br>');
  
  // Convert multiple line breaks to paragraph breaks
  formatted = formatted.replace(/(<br>\s*){2,}/g, '</p><p>');
  
  // Wrap content in paragraphs if it doesn't start with a header
  if (!formatted.includes('<div class="section-header">')) {
    formatted = '<p>' + formatted + '</p>';
  } else {
    // Add paragraph tags around content after headers
    formatted = formatted.replace(/(<\/div>)([^<])/g, '$1<p>$2');
    if (!formatted.endsWith('</p>') && !formatted.endsWith('</div>')) {
      formatted += '</p>';
    }
  }
  
  return formatted;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Portfolio upload
function uploadPortfolio(event) {
  const file = event.target.files[0];
  if (!file) return;
  
  const formData = new FormData();
  formData.append('portfolio', file);
  
  fetch('/upload-portfolio', {
    method: 'POST',
    body: formData
  })
  .then(response => response.text())
  .then(result => {
    // Show success message
    showNotification('Portfolio uploaded successfully!', 'success');
  })
  .catch(error => {
    showNotification('Error uploading portfolio', 'error');
    console.error('Error:', error);
  });
}

// Demo alert trigger
function triggerFakeNews() {
  fetch('/trigger-fake-news', { method: 'POST' })
  .then(response => response.text())
  .then(result => {
    showNotification('Demo alert triggered!', 'info');
  })
  .catch(error => {
    console.error('Error:', error);
  });
}

// Payment Guard Functions
function triggerTestPayment() {
  const customers = ['cust_1', 'cust_2', 'cust_3'];
  const recipients = ['John Doe', 'CleanVendor', 'Ivan Petrov', 'SuspiciousEntity'];
  
  const testPayment = {
    customer_id: customers[Math.floor(Math.random() * customers.length)],
    amount: Math.random() > 0.7 ? Math.random() * 100000 + 50000 : Math.random() * 10000 + 1000, // Sometimes large amounts
    recipient: recipients[Math.floor(Math.random() * recipients.length)],
    timestamp: Date.now() / 1000
  };
  
  fetch('/payment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(testPayment)
  })
  .then(response => response.text())
  .then(result => {
    showNotification('Test payment processed!', 'info');
    updatePaymentStats();
  })
  .catch(error => {
    console.error('Error:', error);
    showNotification('Payment processing failed', 'error');
  });
}

function updatePaymentStats() {
  // Increment payment count
  const paymentCount = document.getElementById('paymentCount');
  if (paymentCount) {
    const current = parseInt(paymentCount.textContent) || 0;
    paymentCount.textContent = current + 1;
  }
}

function addPaymentToFeed(payment, status = 'normal') {
  const paymentFeed = document.getElementById('paymentFeed');
  if (!paymentFeed) return;
  
  // Remove empty state if exists
  const emptyState = paymentFeed.querySelector('.empty-state');
  if (emptyState) {
    emptyState.remove();
  }
  
  const paymentItem = document.createElement('div');
  paymentItem.className = `payment-item ${status}`;
  
  const time = new Date().toLocaleTimeString('en-US', { 
    hour12: false, 
    hour: '2-digit', 
    minute: '2-digit' 
  });
  
  const statusIcon = {
    'normal': 'check-circle',
    'fraud': 'alert-triangle',
    'sanctions': 'shield-alert'
  }[status] || 'check-circle';
  
  const statusColor = {
    'normal': 'text-green-400',
    'fraud': 'text-red-400',
    'sanctions': 'text-yellow-400'
  }[status] || 'text-green-400';
  
  paymentItem.innerHTML = `
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <i data-lucide="${statusIcon}" class="w-4 h-4 ${statusColor}"></i>
        <span class="text-sm text-gray-300">${payment.customer_id}</span>
        <span class="text-sm font-medium text-white">$${payment.amount.toLocaleString()}</span>
      </div>
      <span class="text-xs text-gray-400">${time}</span>
    </div>
    <div class="text-xs text-gray-500 mt-1">→ ${payment.recipient}</div>
  `;
  
  paymentFeed.insertBefore(paymentItem, paymentFeed.firstChild);
  
  // Re-initialize Lucide icons
  if (window.lucide) {
    window.lucide.createIcons();
  }
  
  // Keep only last 5 payments
  while (paymentFeed.children.length > 5) {
    paymentFeed.removeChild(paymentFeed.lastChild);
  }
}

// Notification system
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg border max-w-sm transform transition-all duration-300 translate-x-full opacity-0`;
  
  const colors = {
    info: 'bg-blue-900/90 border-blue-500/50 text-blue-100',
    success: 'bg-green-900/90 border-green-500/50 text-green-100',
    error: 'bg-red-900/90 border-red-500/50 text-red-100',
    warning: 'bg-yellow-900/90 border-yellow-500/50 text-yellow-100'
  };
  
  notification.className += ` ${colors[type] || colors.info}`;
  notification.textContent = message;
  
  document.body.appendChild(notification);
  
  // Animate in
  setTimeout(() => {
    notification.classList.remove('translate-x-full', 'opacity-0');
  }, 100);
  
  // Animate out and remove
  setTimeout(() => {
    notification.classList.add('translate-x-full', 'opacity-0');
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 300);
  }, 3000);
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new FinSenseApp();
});

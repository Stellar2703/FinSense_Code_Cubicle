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
    this.selectedTradeAction = 'buy';
    this.portfolio = { holdings: {}, total_value: 0, positions: [] };
    
    this.init();
  }

  init() {
    this.setupWebSockets();
    this.setupChart();
    this.setupEventListeners();
    this.setupTradingForm();
    this.updateTicker();
    this.updatePortfolio();
    this.updateMarketOverview();
  this.setupFeedFilters();
    
    // Update ticker every 2 seconds
    setInterval(() => this.updateTicker(), 2000);
    
    // Update portfolio every 5 seconds
    setInterval(() => this.updatePortfolio(), 5000);
  }

  setupFeedFilters() {
    const buttons = document.querySelectorAll('.feed-filter');
    if (!buttons.length) return;
    buttons.forEach(btn => {
      btn.addEventListener('click', () => {
        buttons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.renderFilteredFeed();
      });
    });
  }

  renderFilteredFeed() {
    const feed = document.getElementById('liveFeed');
    if (!feed) return;
    const activeFilterBtn = document.querySelector('.feed-filter.active');
    const activeFilter = activeFilterBtn ? activeFilterBtn.getAttribute('data-filter') : 'all';
    // Rebuild from internal arrays (marketData map & newsData array)
    feed.innerHTML = '';
    const items = [];
    if (activeFilter === 'all' || activeFilter === 'price') {
      this.marketData.forEach(val => items.push({type: 'price', data: val}));
    }
    if (activeFilter === 'all' || activeFilter === 'news') {
      this.newsData.forEach(n => items.push({type: 'news', data: n}));
    }
    // Sort by ts descending if available
    items.sort((a,b) => (b.data.ts || 0) - (a.data.ts || 0));
    items.slice(0,30).forEach(entry => this.addToFeed(entry.data, entry.type));
  }

  setupWebSockets() {
    // Market and alerts WebSockets
    // Use secure WebSocket (wss) when the page is loaded over HTTPS to avoid Mixed Content errors.
    const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsBase = `${wsProtocol}://${window.location.host}`;
    // Market data WebSocket
    this.marketWS = new WebSocket(`${wsBase}/ws/market`);
    
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
  this.alertsWS = new WebSocket(`${wsBase}/ws/alerts`);
    
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
  const dot = element.querySelector('.status-indicator-dot');
  if (!dot) return;
  dot.classList.remove('bg-green-500','bg-red-500');
  dot.classList.add(connected ? 'bg-green-500' : 'bg-red-500');
  element.classList.toggle('connected', connected);
  }

  handleMarketData(data) {
    console.log('Received market data:', data);
    
    if (data.type === 'price') {
      console.log('Processing PRICE data for', data.symbol);
      this.marketData.set(data.symbol, data);
      this.updateStats();
      this.addToFeed(data, 'price');
      this.updateTradingPanelPrices();
      this.updateMarketOverview();
      
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
    } 
    // Insert trade handler
    else if (data.type === 'trade') {
      console.log('Trade event received, updating portfolio', data);
      this.updatePortfolio();
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
    if (!feed) return;

    // Determine active filter (buttons with .feed-filter)
    const activeFilterBtn = document.querySelector('.feed-filter.active');
    const activeFilter = activeFilterBtn ? activeFilterBtn.getAttribute('data-filter') : 'all';
    // If current filter is 'news' and this is a price update, skip adding
    if (activeFilter === 'news' && type !== 'news') {
      return;
    }
    // If current filter is 'price' and this is news, skip
    if (activeFilter === 'price' && type !== 'price') {
      return;
    }
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

    // Only remove old items when new ones arrive; preserve existing unless overflowing
    const MAX_ITEMS = 30;
    while (feed.children.length > MAX_ITEMS) {
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

  // Trading functionality
  setupTradingForm() {
    const tradeForm = document.getElementById('tradeForm');
    const symbolSelect = document.getElementById('tradeSymbol');
    const quantityInput = document.getElementById('tradeQuantity');
    
    console.log('Setting up trading form...', { tradeForm, symbolSelect, quantityInput });
    
    if (tradeForm) {
      tradeForm.addEventListener('submit', (e) => this.executeTrade(e));
      console.log('Trade form event listener added');
    }
    
    if (symbolSelect) {
      symbolSelect.addEventListener('change', () => this.updateTradingPanelPrices());
    }
    
    if (quantityInput) {
      quantityInput.addEventListener('input', () => this.updateEstimatedTotal());
    }
    
    // Set default action to buy and update UI
    setTimeout(() => {
      this.selectTradeAction('buy');
      this.updateTradingPanelPrices();
      
      // Set default quantity to make button clickable
      const quantityInput = document.getElementById('tradeQuantity');
      if (quantityInput && !quantityInput.value) {
        quantityInput.value = '1';
        this.updateEstimatedTotal();
      }
    }, 500); // Increased delay to make sure market data has time to load
  }

  selectTradeAction(action) {
    console.log('Selecting trade action:', action);
    this.selectedTradeAction = action;
    
    const buyBtn = document.getElementById('buyBtn');
    const sellBtn = document.getElementById('sellBtn');
    
    if (action === 'buy') {
      buyBtn.className = 'flex-1 py-2 px-3 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors';
      sellBtn.className = 'flex-1 py-2 px-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors';
    } else {
      buyBtn.className = 'flex-1 py-2 px-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors';
      sellBtn.className = 'flex-1 py-2 px-3 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors';
    }
  }

  async executeTrade(event) {
    event.preventDefault();
    console.log('Executing trade...');
    
    const symbol = document.getElementById('tradeSymbol').value;
    const quantity = parseFloat(document.getElementById('tradeQuantity').value);
    const action = this.selectedTradeAction;
    
    console.log('Trade details:', { symbol, quantity, action });
    
    if (!symbol || !quantity || quantity <= 0) {
      showNotification('Please enter a valid quantity', 'error');
      return;
    }
    
    const executeBtn = document.getElementById('executeTradeBtn');
    executeBtn.disabled = true;
    executeBtn.textContent = 'Processing...';
    
    try {
      console.log('Sending trade request to /trading/execute');
      const response = await fetch('/trading/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: symbol,
          action: action,
          quantity: quantity
        })
      });
      
      console.log('Trade response status:', response.status);
      const result = await response.json();
      console.log('Trade result:', result);
      
      if (result.success) {
        showNotification(result.message, 'success');
        document.getElementById('tradeQuantity').value = '';
        this.updatePortfolio();
        
        // Add visual feedback - show the trade in the feed immediately
        this.showTradeConfirmation(symbol, action, quantity, result.executed_price);
      } else {
        showNotification(result.message || 'Trade failed', 'error');
      }
    } catch (error) {
      console.error('Trade execution error:', error);
      showNotification('Failed to execute trade: ' + error.message, 'error');
    } finally {
      executeBtn.disabled = false;
      executeBtn.textContent = 'Execute Trade';
    }
  }

  showTradeConfirmation(symbol, action, quantity, price) {
    // Create a visual confirmation
    const confirmationDiv = document.createElement('div');
    confirmationDiv.className = 'fixed top-20 right-6 z-50 bg-gradient-to-r from-green-600 to-blue-600 text-white p-4 rounded-lg shadow-lg animate-fade-in';
    confirmationDiv.innerHTML = `
      <div class="flex items-center gap-3">
        <i data-lucide="check-circle" class="w-6 h-6"></i>
        <div>
          <div class="font-bold">Trade Executed!</div>
          <div class="text-sm">${action.toUpperCase()} ${quantity} ${symbol} @ $${price.toFixed(2)}</div>
        </div>
      </div>
    `;
    
    document.body.appendChild(confirmationDiv);
    
    // Initialize Lucide icons
    if (window.lucide) {
      window.lucide.createIcons();
    }
    
    // Remove after 3 seconds
    setTimeout(() => {
      confirmationDiv.remove();
    }, 3000);
  }

  updateTradingPanelPrices() {
    const symbol = document.getElementById('tradeSymbol')?.value;
    if (!symbol) return;
    
    const marketData = this.marketData.get(symbol);
    let price = marketData ? marketData.price : 0;
    
    // Use fallback price if no market data yet
    if (price === 0) {
      const fallbackPrices = {
        'TSLA': 400,
        'AAPL': 250,
        'GOOGL': 250,
        'MSFT': 500,
        'NVDA': 175
      };
      price = fallbackPrices[symbol] || 100;
    }
    
    console.log('updateTradingPanelPrices:', { symbol, marketData, price });
    
    const currentPriceElement = document.getElementById('currentPrice');
    if (currentPriceElement) {
      currentPriceElement.textContent = `$${price.toFixed(2)}`;
    }
    
    this.updateEstimatedTotal();
  }

  updateEstimatedTotal() {
    const symbol = document.getElementById('tradeSymbol')?.value;
    const quantity = parseFloat(document.getElementById('tradeQuantity')?.value) || 0;
    
    console.log('updateEstimatedTotal:', { symbol, quantity });
    
    if (!symbol || quantity <= 0) {
      document.getElementById('estimatedTotal').textContent = '$0.00';
      document.getElementById('executeTradeBtn').disabled = true;
      console.log('Button disabled: invalid quantity or symbol');
      return;
    }
    
    const marketData = this.marketData.get(symbol);
    let price = marketData ? marketData.price : 0;
    
    // Fallback: If no market data yet, use a reasonable default price for demo
    if (price === 0) {
      const fallbackPrices = {
        'TSLA': 400,
        'AAPL': 250,
        'GOOGL': 250,
        'MSFT': 500,
        'NVDA': 175
      };
      price = fallbackPrices[symbol] || 100;
      console.log('Using fallback price:', price, 'for', symbol);
    }
    
    const total = price * quantity;
    
    console.log('Market data:', { marketData, price, total });
    
    document.getElementById('estimatedTotal').textContent = `$${total.toFixed(2)}`;
    const shouldDisable = total === 0;
    document.getElementById('executeTradeBtn').disabled = shouldDisable;
    
    console.log('Button disabled:', shouldDisable, 'total:', total);
  }

  async updatePortfolio() {
    try {
      console.log('Updating portfolio...');
      const response = await fetch('/trading/portfolio', { cache: 'no-store', headers: { 'Cache-Control': 'no-cache' } });
      const portfolio = await response.json();
      
      console.log('Portfolio data received:', portfolio);
      this.portfolio = portfolio;
      this.displayPortfolio(portfolio);
      // If we have value but no rendered holdings yet, schedule a second pass
      setTimeout(() => {
        const container = document.getElementById('portfolioHoldings');
        if (portfolio.total_value > 0 && container && /No holdings yet/i.test(container.innerText)) {
          console.log('Holdings fallback rerender triggered');
          this.displayPortfolio(this.portfolio);
        }
      }, 500);
      
      // Also fetch and display transaction history
      const transactionResponse = await fetch('/trading/transactions');
      const transactionData = await transactionResponse.json();
      this.displayTransactionHistory(transactionData);
    } catch (error) {
      console.error('Error updating portfolio:', error);
    }
  }

  displayPortfolio(portfolio) {
    console.log('Displaying enhanced portfolio:', portfolio);
    
    // Update main portfolio value
    const portfolioValue = document.getElementById('portfolioValue');
    if (portfolioValue) {
      portfolioValue.textContent = `$${portfolio.total_value.toFixed(2)}`;
    }
    
    // Update financial summary cards
    const totalPortfolioValue = document.getElementById('totalPortfolioValue');
    const holdingsValue = document.getElementById('holdingsValue');
    const cashBalance = document.getElementById('cashBalance');
    const totalPnL = document.getElementById('totalPnL');
    const pnlPercentage = document.getElementById('pnlPercentage');
    const totalInvested = document.getElementById('totalInvested');
    const portfolioAllocation = document.getElementById('portfolioAllocation');
    
    if (totalPortfolioValue) {
      totalPortfolioValue.textContent = `$${portfolio.total_portfolio_value.toFixed(2)}`;
    }
    
    if (holdingsValue) {
      holdingsValue.textContent = `$${portfolio.total_value.toFixed(2)}`;
    }
    
    if (cashBalance) {
      cashBalance.textContent = `$${portfolio.cash_balance.toFixed(2)}`;
    }
    
    // Update P&L with color coding
    if (totalPnL) {
      const pnlValue = portfolio.total_pnl || 0;
      totalPnL.textContent = `${pnlValue >= 0 ? '+' : ''}$${pnlValue.toFixed(2)}`;
      totalPnL.className = `text-xl font-bold ${pnlValue >= 0 ? 'text-green-400' : 'text-red-400'}`;
      
      // Update P&L icon
      const pnlIcon = document.getElementById('pnlIcon');
      if (pnlIcon) {
        const newCls = `w-3 h-3 ${pnlValue >= 0 ? 'text-green-500' : 'text-red-500'}`;
        try {
          // For regular HTMLElements
          pnlIcon.className = newCls;
        } catch (e) {
          // Fallback for SVG elements where className is SVGAnimatedString
            pnlIcon.setAttribute('class', newCls);
        }
      }
    }
    
    if (pnlPercentage) {
      const pnlPercent = portfolio.total_pnl_percentage || 0;
      pnlPercentage.innerHTML = `<span class="text-gray-400">${pnlPercent >= 0 ? '+' : ''}${pnlPercent.toFixed(2)}% return</span>`;
    }
    
    // Update invested amount and allocation
    if (totalInvested) {
      const investedAmount = portfolio.total_invested || 0;
      totalInvested.textContent = `$${investedAmount.toFixed(2)}`;
    }
    
    if (portfolioAllocation) {
      const totalValue = portfolio.total_portfolio_value || 10000;
      const investedAmount = portfolio.total_invested || 0;
      const allocationPercent = totalValue > 0 ? (investedAmount / totalValue * 100) : 0;
      portfolioAllocation.innerHTML = `<span class="text-gray-400">${allocationPercent.toFixed(1)}% allocated</span>`;
    }
    
    // Update portfolio change in header
    const portfolioChange = document.getElementById('portfolioChange');
    if (portfolioChange) {
      const changePercent = portfolio.total_pnl_percentage || 0;
      portfolioChange.textContent = `${changePercent >= 0 ? '+' : ''}${changePercent.toFixed(2)}%`;
      portfolioChange.className = `text-xs ${changePercent >= 0 ? 'text-green-400' : 'text-red-400'}`;
    }
    
    // Render holdings cards from backend data
    const portfolioHoldings = document.getElementById('portfolioHoldings');
    if (portfolioHoldings) {
  const positions = portfolio.positions || [];
  if (positions.length > 0) {
        portfolioHoldings.innerHTML = positions.map(pos => {
          const pnlColor = pos.pnl >= 0 ? 'text-green-400' : 'text-red-400';
          return `
            <div class="bg-gray-800/60 rounded-lg p-4 border border-gray-700 hover:border-gray-500 transition-colors">
              <div class="flex justify-between items-start">
                <div>
                  <div class="flex items-center gap-2">
                    <span class="text-white font-semibold text-sm">${pos.symbol}</span>
                    <span class="text-xs text-gray-400">${pos.quantity} sh</span>
                  </div>
                  <div class="mt-1 grid grid-cols-2 gap-x-6 gap-y-1 text-xs text-gray-300">
                    <div>Price: <span class="text-white font-medium">$${(pos.current_price||0).toFixed(2)}</span></div>
                    <div>Value: <span class="text-white font-medium">$${(pos.position_value||0).toFixed(2)}</span></div>
                    <div>Avg Cost: <span class="text-white font-medium">$${(pos.avg_cost||0).toFixed(2)}</span></div>
                    <div>Cost Basis: <span class="text-white font-medium">$${(pos.cost_basis||0).toFixed(2)}</span></div>
                    <div>Allocation: <span class="text-white font-medium">${(pos.percentage||0).toFixed(1)}%</span></div>
                    <div>PnL: <span class="font-medium ${pnlColor}">${pos.pnl>=0?'+':''}$${(pos.pnl||0).toFixed(2)} (${(pos.pnl_percentage||0).toFixed(2)}%)</span></div>
                  </div>
                </div>
              </div>
            </div>
          `;
        }).join('');
      } else {
        // Fallback: positions not yet calculated but holdings dict has entries
  const holdingsDict = portfolio.holdings || {};
        const holdingEntries = Object.entries(holdingsDict);
        if (holdingEntries.length > 0) {
          portfolioHoldings.innerHTML = holdingEntries.map(([sym, qty]) => {
            // Try to derive price
            let currentPrice = 0;
            const existingPos = positions.find(p => p.symbol === sym) || {};
            if (existingPos.current_price) currentPrice = existingPos.current_price;
            else {
              const md = this.marketData.get(sym);
              if (md && md.price) currentPrice = md.price;
            }
            if (!currentPrice) {
              const fallbackPrices = { TSLA:400, AAPL:250, GOOGL:250, MSFT:500, NVDA:175, AMZN:220, META:300, NFLX:500, AMD:120, UBER:70 };
              currentPrice = fallbackPrices[sym] || 0;
            }
            const value = qty * currentPrice;
            // Derive avg cost & cost basis from transactions if available
            let avgCost = currentPrice;
            let costBasis = value;
            if (this.portfolio && Array.isArray(this.portfolio.transactions)) {
              const buys = this.portfolio.transactions.filter(t => t.symbol === sym && t.action === 'buy');
              const totalQty = buys.reduce((a,b)=>a + (b.quantity||0),0);
              const totalSpent = buys.reduce((a,b)=>a + (b.quantity||0)*(b.price||0),0);
              if (totalQty > 0) {
                avgCost = totalSpent / totalQty;
                costBasis = avgCost * qty;
              }
            }
            return `
              <div class="bg-gray-800/60 rounded-lg p-4 border border-gray-700">
                <div class="flex justify-between">
                  <div class="text-white font-semibold text-sm">${sym}</div>
                  <div class="text-white font-medium">$${value.toFixed(2)}</div>
                </div>
                <div class="mt-1 text-xs text-gray-400 flex gap-4 flex-wrap">
                  <span>${qty} sh</span>
                  <span>Price $${currentPrice.toFixed(2)}</span>
                  <span>Avg $${avgCost.toFixed(2)}</span>
                  <span>Cost Basis $${costBasis.toFixed(2)}</span>
                  <span class="italic text-gray-500">PnL loading…</span>
                </div>
              </div>
            `;
          }).join('');
        } else {
          portfolioHoldings.innerHTML = `
            <div class="text-sm text-gray-400 text-center py-4">
              No holdings yet. Start trading to build your portfolio.
            </div>
          `;
        }
      }
    }
  }

  displayTransactionHistory(data) {
    const recentTransactions = document.getElementById('recentTransactions');
    if (!recentTransactions) return;
    
    if (data.transactions.length === 0) {
      recentTransactions.innerHTML = `
        <div class="text-sm text-gray-400 text-center py-4">
          No transactions yet.
        </div>
      `;
    } else {
      recentTransactions.innerHTML = data.transactions.map(transaction => {
        const actionClass = transaction.action === 'buy' ? 'text-green-400' : 'text-red-400';
        const actionIcon = transaction.action === 'buy' ? 'trending-up' : 'trending-down';
        const actionText = transaction.action === 'buy' ? 'Bought' : 'Sold';
        
        return `
          <div class="bg-gray-800/30 rounded-lg p-3 border border-gray-700">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="w-6 h-6 rounded-full ${transaction.action === 'buy' ? 'bg-green-500/20' : 'bg-red-500/20'} flex items-center justify-center">
                  <i data-lucide="${actionIcon}" class="w-3 h-3 ${actionClass}"></i>
                </div>
                <div>
                  <div class="text-sm font-medium text-white">
                    ${actionText} ${transaction.quantity} ${transaction.symbol}
                  </div>
                  <div class="text-xs text-gray-400">${transaction.date}</div>
                </div>
              </div>
              <div class="text-right">
                <div class="text-sm font-semibold text-white">$${transaction.price.toFixed(2)}</div>
                <div class="text-xs text-gray-400">$${transaction.total_value.toFixed(2)} total</div>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }
    
    // Re-initialize Lucide icons for the new content
    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
  }

  updateMarketOverview() {
    const marketOverview = document.getElementById('marketOverview');
    if (!marketOverview) return;
    
    const symbols = ['TSLA', 'AAPL', 'GOOGL', 'MSFT', 'NVDA'];
    
    marketOverview.innerHTML = symbols.map(symbol => {
      const data = this.marketData.get(symbol);
      const price = data ? data.price : 0;
      const change = data ? data.change_percent || 0 : 0;
      const changeClass = change >= 0 ? 'text-green-400' : 'text-red-400';
      const changeSign = change >= 0 ? '+' : '';
      
      return `
        <div class="flex items-center justify-between py-2">
          <span class="font-medium text-white text-sm">${symbol}</span>
          <div class="text-right">
            <div class="text-sm font-semibold text-white">$${price.toFixed(2)}</div>
            <div class="${changeClass} text-xs">${changeSign}${change.toFixed(1)}%</div>
          </div>
        </div>
      `;
    }).join('');
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
    // Replace literal \n with actual newlines before passing to the chat
    answer = answer.replace(/\\n/g, '\n');
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
    // Normalize Windows CRLF just in case
    message = message.replace(/\r\n/g, '\n');
    // If backend still sent escaped \n sequences, convert them
    message = message.replace(/\\n/g, '\n');
    
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
  // Trim stray quotes/newlines
  text = text.trim();
  // Convert any literal "\n" sequences (backslash + n) into actual newlines first
  // This handles cases where the backend response was still escaped
  if (text.includes('\\n')) {
    text = text.replace(/\\n/g, '\n');
  }
  // Replace multiple blank lines with two to standardize
  text = text.replace(/\n{3,}/g, '\n\n');
  
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
  formData.append('file', file); // use 'file' field for broader compatibility
  
  fetch('/upload-portfolio', {
    method: 'POST',
    body: formData
  })
  .then(async r => {
    const ct = r.headers.get('content-type') || '';
    if (!r.ok) {
      const text = await r.text();
      throw new Error(text || 'Upload failed');
    }
    let result = null;
    if (ct.includes('application/json')) {
      result = await r.json();
    } else {
      // Fallback: attempt to parse plain text
      const text = await r.text();
      try { result = JSON.parse(text); } catch { result = { raw: text }; }
    }
    showNotification('Portfolio uploaded successfully!', 'success');
    // Auto-fetch analysis if backend did not include it
    if (!result.analysis) {
      try {
        const a = await fetch('/trading/portfolio/analysis').then(r2 => r2.json());
        if (a && a.summary_text) {
          addChatMessage(a.summary_text, 'assistant');
        }
      } catch (e) {
        console.warn('Analysis fetch failed', e);
      }
    } else if (result.analysis.summary_text) {
      addChatMessage(result.analysis.summary_text, 'assistant');
    }
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

// Trading functions
function selectTradeAction(action) {
  console.log('Global selectTradeAction called:', action);
  
  // Update the app instance
  if (window.finSenseApp) {
    window.finSenseApp.selectTradeAction(action);
  } else {
    console.error('finSenseApp not found on window');
  }
}

// Enable trade button manually (for debugging)
function enableTradeButton() {
  const btn = document.getElementById('executeTradeBtn');
  const symbol = document.getElementById('tradeSymbol').value;
  const quantity = document.getElementById('tradeQuantity').value;
  
  if (btn) {
    btn.disabled = false;
    console.log('Trade button manually enabled');
    showNotification('Trade button enabled! Make sure to enter quantity first.', 'info');
  }
  
  // Force update the prices and total
  if (window.finSenseApp) {
    window.finSenseApp.updateTradingPanelPrices();
    
    // Set default values if empty
    if (!quantity) {
      document.getElementById('tradeQuantity').value = '1';
      window.finSenseApp.updateEstimatedTotal();
    }
  }
}

// Test function for debugging
async function testTradeSystem() {
  console.log('Testing trade system...');
  
  try {
    // Test the trading endpoint
    const testResponse = await fetch('/trading/test');
    const testResult = await testResponse.json();
    console.log('Trade system test:', testResult);
    
    if (testResult.status === 'ok') {
      showNotification('Trading system test passed!', 'success');
      
      // Try a small test trade
      const tradeResponse = await fetch('/trading/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: 'TSLA',
          action: 'buy',
          quantity: 0.1
        })
      });
      
      const tradeResult = await tradeResponse.json();
      console.log('Test trade result:', tradeResult);
      
      if (tradeResult.success) {
        showNotification('Test trade executed successfully!', 'success');
      } else {
        showNotification('Test trade failed: ' + tradeResult.message, 'error');
      }
    } else {
      showNotification('Trading system test failed', 'error');
    }
  } catch (error) {
    console.error('Test trade system error:', error);
    showNotification('Test failed: ' + error.message, 'error');
  }
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
  window.finSenseApp = new FinSenseApp();
});

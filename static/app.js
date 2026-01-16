const API_BASE = '/api';

// チャート設定定数
const CHART_CONFIG = {
    MA: {
        periods: [5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
        maxSelection: 2,
        defaultSelection: [5, 15],
        colors: [
            '#fbbf24',  // 黄色
            '#8b5cf6',  // 紫色
            '#3b82f6',  // 青色
            '#10b981',  // 緑色
            '#f59e0b',  // オレンジ色
            '#ef4444',  // 赤色
            '#06b6d4',  // シアン
            '#a855f7',  // 紫
            '#ec4899',  // ピンク
            '#14b8a6'   // ティール
        ]
    },
    CANDLE: {
        upColor: '#22c55e',
        downColor: '#ef4444',
        borderUpColor: '#22c55e',
        borderDownColor: '#ef4444',
        wickUpColor: '#22c55e',
        wickDownColor: '#ef4444'
    },
    VOLUME: {
        upColor: 'rgba(34, 197, 94, 0.5)',
        downColor: 'rgba(239, 68, 68, 0.5)'
    },
    PERIOD: {
        default: '3mo',
        options: ['1mo', '3mo', '6mo', '1y', '2y'],
        labels: { '1mo': '1M', '3mo': '3M', '6mo': '6M', '1y': '1Y', '2y': '2Y' }
    }
};

// アプリケーション状態管理オブジェクト
const AppState = {
    currentStock: null,
    currentPeriod: CHART_CONFIG.PERIOD.default,
    currentTab: 'chart',
    chart: null,
    autoRefreshInterval: null,
    stocksData: [],

    // チャート関連の状態
    selectedMAPeriods: [...CHART_CONFIG.MA.defaultSelection],
    maSeries: [],
    lwChart: null,
    currentPriceData: null,
    currentAnalysisData: null,

    // 状態更新メソッド
    setCurrentStock(symbol) {
        this.currentStock = symbol;
    },

    setPeriod(period) {
        this.currentPeriod = period;
    },

    setTab(tab) {
        this.currentTab = tab;
    },

    setChart(chartInstance) {
        this.chart = chartInstance;
    },

    setAutoRefreshInterval(interval) {
        this.autoRefreshInterval = interval;
    },

    setStocksData(data) {
        this.stocksData = data;
    },

    setLwChart(chartInstance) {
        this.lwChart = chartInstance;
    },

    setMASeries(series) {
        this.maSeries = series;
    },

    setSelectedMAPeriods(periods) {
        this.selectedMAPeriods = periods;
    },

    setPriceData(data) {
        this.currentPriceData = data;
    },

    setAnalysisData(data) {
        this.currentAnalysisData = data;
    }
};

// 既存コードとの互換性のため、グローバル変数も維持（AppStateへの参照として）
// 将来的にはAppStateに統一することを推奨
let currentStock = null;
let currentPeriod = CHART_CONFIG.PERIOD.default;
let currentTab = 'chart';
let chart = null;  // Chart.js用（配当チャートなど）
let lwChart = null;  // Lightweight Charts用（価格チャート）
let autoRefreshInterval = null;
let stocksData = [];
let selectedMAPeriods = [...CHART_CONFIG.MA.defaultSelection];  // 選択された移動平均線の期間（最大2本）
let maSeries = [];  // 移動平均線のシリーズを管理

// AppStateとグローバル変数の同期ヘルパー関数
function syncAppState() {
    currentStock = AppState.currentStock;
    currentPeriod = AppState.currentPeriod;
    currentTab = AppState.currentTab;
    chart = AppState.chart;
    lwChart = AppState.lwChart;
    autoRefreshInterval = AppState.autoRefreshInterval;
    stocksData = AppState.stocksData;
    selectedMAPeriods = AppState.selectedMAPeriods;
    maSeries = AppState.maSeries;
}

function updateAppState() {
    AppState.currentStock = currentStock;
    AppState.currentPeriod = currentPeriod;
    AppState.currentTab = currentTab;
    AppState.chart = chart;
    AppState.lwChart = lwChart;
    AppState.autoRefreshInterval = autoRefreshInterval;
    AppState.stocksData = stocksData;
    AppState.selectedMAPeriods = selectedMAPeriods;
    AppState.maSeries = maSeries;
}

// 初期化
document.addEventListener('DOMContentLoaded', () => {
    loadStocks();
    setupEventListeners();
    initAutoRefresh();
});

function setupEventListeners() {
    document.getElementById('addStockForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const input = document.getElementById('symbolInput');
        const button = document.getElementById('addStockBtn');
        const symbol = input.value.trim().toUpperCase();

        if (symbol) {
            // Loading State
            const originalText = button.textContent;
            button.disabled = true;
            button.innerHTML = '<span class="button-loader"></span>追加中';

            await addStock(symbol);

            // Reset State
            button.disabled = false;
            button.textContent = originalText;
            input.value = '';
        }
    });
}

// ========================================
// 通貨フォーマット関連
// ========================================

function formatPrice(price, currencySymbol = '$', currency = 'USD') {
    if (price === null || price === undefined) return 'N/A';
    if (currency === 'JPY' || currency === 'KRW') {
        return `${currencySymbol}${price.toLocaleString('ja-JP', { maximumFractionDigits: 0 })}`;
    }
    return `${currencySymbol}${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatChange(change, changePercent, currencySymbol = '$', currency = 'USD') {
    if (change === null || change === undefined) return { str: 'N/A', percent: 'N/A' };
    const sign = change >= 0 ? '+' : '';
    let changeStr;
    if (currency === 'JPY' || currency === 'KRW') {
        changeStr = `${sign}${currencySymbol}${change.toLocaleString('ja-JP', { maximumFractionDigits: 0 })}`;
    } else {
        changeStr = `${sign}${currencySymbol}${change.toFixed(2)}`;
    }
    const percentStr = `${sign}${changePercent.toFixed(2)}%`;
    return { str: changeStr, percent: percentStr };
}

function formatLargeNumber(num, currencySymbol = '$', currency = 'USD') {
    if (num === null || num === undefined) return 'N/A';
    if (currency === 'JPY') {
        if (num >= 1e12) return `${currencySymbol}${(num / 1e12).toFixed(2)}兆`;
        if (num >= 1e8) return `${currencySymbol}${(num / 1e8).toFixed(2)}億`;
        if (num >= 1e4) return `${currencySymbol}${(num / 1e4).toFixed(2)}万`;
        return `${currencySymbol}${num.toLocaleString('ja-JP')}`;
    }
    if (num >= 1e12) return `${currencySymbol}${(num / 1e12).toFixed(2)}T`;
    if (num >= 1e9) return `${currencySymbol}${(num / 1e9).toFixed(2)}B`;
    if (num >= 1e6) return `${currencySymbol}${(num / 1e6).toFixed(2)}M`;
    if (num >= 1e3) return `${currencySymbol}${(num / 1e3).toFixed(2)}K`;
    return `${currencySymbol}${num.toLocaleString('en-US')}`;
}

// ========================================
// ポートフォリオ管理
// ========================================

function updatePortfolioSummary(stocks) {
    // Portfolio summary removed
}

let editingSymbol = null;

function openEditModal() {
    if (!currentStock) return;
    const stock = stocksData.find(s => s.symbol === currentStock);
    if (!stock) return;

    editingSymbol = stock.symbol;
    document.getElementById('editQuantity').value = stock.quantity || '';
    document.getElementById('editAvgPrice').value = stock.avg_price || '';

    document.getElementById('editModal').classList.add('show');
}

function closeEditModal() {
    document.getElementById('editModal').classList.remove('show');
    editingSymbol = null;
}

async function savePortfolio() {
    if (!editingSymbol) return;

    const quantity = parseFloat(document.getElementById('editQuantity').value) || 0;
    const avgPrice = parseFloat(document.getElementById('editAvgPrice').value) || 0;

    try {
        const response = await fetch(`${API_BASE}/stocks/${editingSymbol}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ quantity, avg_price: avgPrice })
        });

        if (response.ok) {
            Toastify({
                text: "ポートフォリオ情報を更新しました",
                duration: 3000,
                gravity: "top",
                position: "right",
                className: "toast-success",
                style: { background: "var(--bg-secondary)", borderLeft: "4px solid var(--positive)" }
            }).showToast();

            closeEditModal();

            // 銘柄リストを更新
            await loadStocks();

            // ポートフォリオタブが表示されている場合は再描画
            if (AppState.currentTab === 'portfolio' || currentTab === 'portfolio') {
                const priceData = AppState.currentPriceData || window.currentPriceData;
                if (priceData) {
                    const currencySymbol = priceData.currency_symbol || '$';
                    const currency = priceData.currency || 'USD';
                    const tabContent = document.getElementById('tabContent');
                    if (tabContent) {
                        renderPortfolioTab(tabContent, priceData, currencySymbol, currency);
                    }
                }
            }
        } else {
            throw new Error('Update failed');
        }
    } catch (error) {
        console.error('Save failed:', error);
        Toastify({
            text: "更新に失敗しました",
            duration: 3000,
            gravity: "top",
            position: "right",
            className: "error-toast",
            style: { background: "rgba(239, 68, 68, 0.15)", color: "var(--negative)" }
        }).showToast();
    }
}

// ========================================
// 自動更新
// ========================================

// Auto Refresh Logic
function initAutoRefresh() {
    const toggle = document.getElementById('autoRefreshToggle');
    const savedState = localStorage.getItem('autoRefresh') === 'true';

    toggle.checked = savedState;
    if (savedState) {
        startAutoRefresh();
    }

    toggle.addEventListener('change', (e) => {
        const isChecked = e.target.checked;
        localStorage.setItem('autoRefresh', isChecked);
        if (isChecked) {
            startAutoRefresh();
        } else {
            stopAutoRefresh();
        }
    });
}

function startAutoRefresh(intervalMs = 60000) {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    autoRefreshInterval = setInterval(() => {
        loadStocks(false); // Pass false to indicate background refresh if supported
    }, intervalMs);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// ========================================
// 銘柄管理
// ========================================

async function loadStocks() {
    try {
        const [stocksResponse, dashboardResponse] = await Promise.all([
            fetch(`${API_BASE}/stocks`),
            fetch(`${API_BASE}/dashboard`)
        ]);

        if (!stocksResponse.ok) throw new Error('Failed to fetch stocks');
        const stocks = await stocksResponse.json();

        let dashboard = [];
        if (dashboardResponse.ok) {
            try {
                dashboard = await dashboardResponse.json();
                if (!Array.isArray(dashboard)) dashboard = [];
            } catch (e) {
                console.error('Dashboard parse error:', e);
            }
        }

        stocksData = stocks.map(stock => {
            const data = dashboard.find(d => d.symbol === stock.symbol) || {};
            // データがない場合でも、最低限の情報を保持してエラーにならないようにする
            return {
                ...stock,
                current_price: data.current_price || data.price || 0,
                change_percent: data.change_percent || 0,
                ...data
            };
        });

        renderStockList(stocksData);
        updatePortfolioSummary(stocksData);
        document.getElementById('stockCount').textContent = stocks.length;

        // 現在選択中の銘柄があれば、データを更新
        if (currentStock) {
            const currentData = stocksData.find(s => s.symbol === currentStock);
            if (currentData) {
                // 詳細を再表示しない（チラつき防止）
            }
        }
    } catch (error) {
        console.error('銘柄の読み込みに失敗:', error);
        // エラー時でもリストを表示できるようにする (キャッシュや partial data)
        const listContainer = document.getElementById('stockList');
        if (listContainer.innerHTML.trim() === '') {
            listContainer.innerHTML = '<div class="error-message">データの読み込みに失敗しました。再読み込みしてください。</div>';
        }
    }
}

async function addStock(symbol) {
    try {
        const response = await fetch(`${API_BASE}/stocks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol })
        });

        const data = await response.json();

        if (response.ok) {
            await loadStocks();
            showMessage(data.message || '銘柄を追加しました', 'success');
            // 追加された銘柄を自動選択
            selectStock(data.symbol || symbol.toUpperCase());
        } else {
            showError(data.error || '銘柄の追加に失敗しました');
        }
    } catch (error) {
        showError(`ネットワークエラー: ${error.message}`);
    }
}

async function removeStock(symbol, event) {
    event.stopPropagation();
    if (!confirm(`${symbol}を削除しますか？`)) return;

    try {
        const response = await fetch(`${API_BASE}/stocks/${symbol}`, { method: 'DELETE' });
        if (response.ok) {
            if (currentStock === symbol) {
                currentStock = null;
                showEmptyDetail();
            }
            await loadStocks();
            showMessage('銘柄を削除しました', 'success');
        }
    } catch (error) {
        showError('銘柄の削除に失敗しました');
    }
}

// ========================================
// 銘柄リスト表示
// ========================================

function renderStockList(stocks) {
    const listContainer = document.getElementById('stockList');

    if (stocks.length === 0) {
        listContainer.innerHTML = `
            <div class="empty-list">
                <div class="icon">📈</div>
                <p>銘柄を追加してください</p>
            </div>
        `;
        return;
    }

    listContainer.innerHTML = stocks.map(stock => {
        const currencySymbol = stock.currency_symbol || '$';
        const currency = stock.currency || 'USD';
        const price = stock.price || stock.current_price;
        const priceStr = price ? formatPrice(price, currencySymbol, currency) : 'N/A';
        const changeInfo = formatChange(stock.change || 0, stock.change_percent || 0, currencySymbol, currency);
        const changeClass = (stock.change || 0) >= 0 ? 'positive' : 'negative';
        const isActive = currentStock === stock.symbol ? 'active' : '';
        const name = stock.name || stock.symbol;

        return `
            <div class="stock-item ${isActive}" data-symbol="${stock.symbol}" onclick="selectStock('${stock.symbol}')">
                <div class="stock-item-info">
                    <div class="stock-item-symbol">${stock.symbol}</div>
                    <div class="stock-item-name">${name}</div>
                </div>
                <div class="stock-item-price">
                    <div class="price">${priceStr}</div>
                    <div class="change ${changeClass}">${changeInfo.percent}</div>
                </div>
                <button class="stock-item-delete" onclick="removeStock('${stock.symbol}', event)" title="削除">×</button>
            </div>
        `;
    }).join('');
}

// ========================================
// 銘柄選択・詳細表示
// ========================================

function selectStock(symbol) {
    currentStock = symbol;
    currentTab = 'chart';

    // リストのアクティブ状態を更新
    document.querySelectorAll('.stock-item').forEach(item => {
        item.classList.toggle('active', item.dataset.symbol === symbol);
    });

    showStockDetail(symbol);
}

async function showStockDetail(symbol) {
    const detailPanel = document.getElementById('stockDetail');
    detailPanel.innerHTML = '<div class="loading"><div class="spinner"></div>読み込み中...</div>';

    try {
        const [priceResponse, analysisResponse] = await Promise.all([
            fetch(`${API_BASE}/stocks/${symbol}/price?period=${currentPeriod}`),
            fetch(`${API_BASE}/stocks/${symbol}/analysis?period=${currentPeriod}`)
        ]);

        const priceData = await priceResponse.json();
        const analysisData = await analysisResponse.json();

        if (!priceResponse.ok) {
            throw new Error(priceData.error || 'データの取得に失敗しました');
        }

        renderStockDetail(priceData, analysisData);
    } catch (error) {
        detailPanel.innerHTML = `
            <div class="detail-container">
                <div class="detail-header">
                    <div class="detail-title"><h2>${symbol}</h2></div>
                </div>
                <div class="error">${error.message}</div>
            </div>
        `;
    }
}

function renderStockDetail(priceData, analysisData) {
    const detailPanel = document.getElementById('stockDetail');
    const currencySymbol = priceData.currency_symbol || '$';
    const currency = priceData.currency || 'USD';
    const changeClass = priceData.change >= 0 ? 'positive' : 'negative';
    const changeInfo = formatChange(priceData.change, priceData.change_percent, currencySymbol, currency);

    const periodButtons = CHART_CONFIG.PERIOD.options.map(period => {
        const label = CHART_CONFIG.PERIOD.labels[period];
        return `<button class="period-btn ${period === currentPeriod ? 'active' : ''}" onclick="changePeriod('${period}', event)">${label}</button>`;
    }).join('');

    const tabButtons = `
        <button class="tab-btn ${currentTab === 'chart' ? 'active' : ''}" onclick="switchTab('chart')">📈 チャート</button>
        <button class="tab-btn ${currentTab === 'analysis' ? 'active' : ''}" onclick="switchTab('analysis')">📊 分析</button>
        <button class="tab-btn ${currentTab === 'financials' ? 'active' : ''}" onclick="switchTab('financials')">🏢 財務</button>
        <button class="tab-btn ${currentTab === 'dividends' ? 'active' : ''}" onclick="switchTab('dividends')">💵 配当</button>
        <button class="tab-btn ${currentTab === 'portfolio' ? 'active' : ''}" onclick="switchTab('portfolio')">💼 保有状況</button>
        <button class="tab-btn ${currentTab === 'prediction' ? 'active' : ''}" onclick="switchTab('prediction')">🔮 予測</button>
    `;

    detailPanel.innerHTML = `
        <div class="detail-container">
            <div class="detail-header">
                <div class="detail-title">
                    <h2>${priceData.symbol} - ${priceData.name} <span class="market-badge">${priceData.market || ''}</span></h2>
                    <div class="market-info">${currency}</div>
                </div>
            </div>
            
            <div class="price-summary">
                <div class="current-price">${formatPrice(priceData.current_price, currencySymbol, currency)}</div>
                <div class="price-change ${changeClass}">${changeInfo.str} (${changeInfo.percent})</div>
            </div>
            
            ${priceData.cached && priceData.message ? `<div class="cache-notice">⚠️ ${priceData.message}</div>` : ''}
            
            <div class="controls-row">
                <div class="period-selector">${periodButtons}</div>
                <div class="tab-buttons">${tabButtons}</div>
            </div>
            
            <div id="tabContent" class="tab-content"></div>
        </div>
    `;

    window.currentPriceData = priceData;
    window.currentAnalysisData = analysisData;
    renderTabContent(currentTab, priceData, analysisData);
}

function switchTab(tab) {
    currentTab = tab;
    AppState.setTab(tab);
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(btn => {
        if (btn.textContent.includes(getTabLabel(tab))) btn.classList.add('active');
    });
    // AppStateから取得、なければwindowから取得
    const priceData = AppState.currentPriceData || window.currentPriceData;
    const analysisData = AppState.currentAnalysisData || window.currentAnalysisData;
    renderTabContent(tab, priceData, analysisData);
}

function getTabLabel(tab) {
    return { 'chart': 'チャート', 'analysis': '分析', 'financials': '財務', 'dividends': '配当', 'portfolio': '保有状況' }[tab] || tab;
}

function renderTabContent(tab, priceData, analysisData) {
    const tabContent = document.getElementById('tabContent');
    if (!tabContent) return;

    // priceDataがnullの場合は、AppStateまたはwindowから取得を試みる
    if (!priceData) {
        priceData = AppState.currentPriceData || window.currentPriceData;
    }
    if (!analysisData) {
        analysisData = AppState.currentAnalysisData || window.currentAnalysisData;
    }

    // priceDataがまだnullの場合はエラー表示
    if (!priceData) {
        tabContent.innerHTML = '<div class="error">データが読み込まれていません。銘柄を選択してください。</div>';
        return;
    }

    const currencySymbol = priceData.currency_symbol || '$';
    const currency = priceData.currency || 'USD';

    switch (tab) {
        case 'chart': renderChartTab(tabContent, priceData, currencySymbol, currency); break;
        case 'analysis': renderAnalysisTab(tabContent, analysisData, currencySymbol, currency); break;
        case 'financials': renderFinancialsTab(tabContent, priceData.symbol, currencySymbol, currency); break;
        case 'dividends': renderDividendsTab(tabContent, priceData.symbol, currencySymbol, currency); break;
        case 'portfolio': renderPortfolioTab(tabContent, priceData, currencySymbol, currency); break;
        case 'prediction': renderPredictionTab(tabContent, priceData.symbol, currencySymbol, currency); break;
    }
}

function renderPortfolioTab(container, priceData, currencySymbol, currency) {
    const stock = stocksData.find(s => s.symbol === priceData.symbol);
    const qty = stock ? (stock.quantity || 0) : 0;
    const avgPrice = stock ? (stock.avg_price || 0) : 0;
    const currentValue = qty * priceData.current_price;
    const totalCost = qty * avgPrice;
    const gain = currentValue - totalCost;
    const gainPercent = totalCost > 0 ? (gain / totalCost) * 100 : 0;
    const gainClass = gain >= 0 ? 'text-positive' : 'text-negative';

    container.innerHTML = `
        <div class="portfolio-section">
            <div class="portfolio-header">
                <button class="edit-portfolio-btn" onclick="openEditModal()">
                    <i class="fas fa-edit"></i> 保有情報を編集
                </button>
            </div>
            <div class="portfolio-grid">
                <div class="financial-item">
                    <span class="label">保有数量</span>
                    <span class="value">${qty}</span>
                </div>
                <div class="financial-item">
                    <span class="label">取得単価</span>
                    <span class="value">${formatPrice(avgPrice, currencySymbol, currency)}</span>
                </div>
                <div class="financial-item">
                    <span class="label">取得総額</span>
                    <span class="value">${formatPrice(totalCost, currencySymbol, currency)}</span>
                </div>
                <div class="financial-item">
                    <span class="label">現在評価額</span>
                    <span class="value">${formatPrice(currentValue, currencySymbol, currency)}</span>
                </div>
                <div class="financial-item">
                    <span class="label">評価損益</span>
                    <span class="value ${gainClass}">
                        ${gain >= 0 ? '+' : ''}${formatPrice(gain, currencySymbol, currency).replace(currencySymbol, '')} 
                    </span>
                </div>
            </div>
        </div>
    `;
}

/**
 * UIテンプレート生成ユーティリティ
 */
const Templates = {
    /**
     * 価格情報HTMLを生成
     */
    priceInfo(priceData, currencySymbol, currency) {
        return `
            <div class="price-info">
                <div class="info-box"><h4>現在価格</h4><div class="value">${formatPrice(priceData.current_price, currencySymbol, currency)}</div></div>
                <div class="info-box"><h4>前日終値</h4><div class="value">${formatPrice(priceData.previous_close, currencySymbol, currency)}</div></div>
                <div class="info-box"><h4>出来高</h4><div class="value">${formatNumber(priceData.volume)}</div></div>
                <div class="info-box"><h4>時価総額</h4><div class="value">${formatLargeNumber(priceData.market_cap, currencySymbol, currency)}</div></div>
                <div class="info-box"><h4>52週高値</h4><div class="value">${formatPrice(priceData['52_week_high'], currencySymbol, currency)}</div></div>
                <div class="info-box"><h4>52週安値</h4><div class="value">${formatPrice(priceData['52_week_low'], currencySymbol, currency)}</div></div>
            </div>
        `;
    },

    /**
     * 移動平均線選択UIを生成
     */
    maSelector(periods, selected) {
        const checkboxes = periods.map(period => {
            const isSelected = selected.includes(period);
            return `
                <label class="ma-checkbox-label">
                    <input type="checkbox" 
                           class="ma-period-checkbox" 
                           value="${period}" 
                           ${isSelected ? 'checked' : ''}
                           data-period="${period}">
                    <span>MA${period}</span>
                </label>
            `;
        }).join('');

        return `
            <div class="ma-selector">
                <div class="ma-selector-label">移動平均線:</div>
                <div class="ma-checkbox-group">
                    ${checkboxes}
                </div>
            </div>
        `;
    },

    /**
     * チャートコンテナHTMLを生成
     */
    chartContainer() {
        return '<div class="chart-container"><div id="candlestickChart" style="height: 400px;"></div></div>';
    }
};

function renderChartTab(container, priceData, currencySymbol, currency) {
    container.innerHTML =
        Templates.priceInfo(priceData, currencySymbol, currency) +
        Templates.maSelector(CHART_CONFIG.MA.periods, AppState.selectedMAPeriods) +
        Templates.chartContainer();

    // イベントハンドラを設定（イベント委譲）
    container.querySelector('.ma-checkbox-group').addEventListener('change', (e) => {
        if (e.target.classList.contains('ma-period-checkbox')) {
            const period = parseInt(e.target.value);
            toggleMAPeriod(period);
        }
    });

    drawChart(priceData.history, currencySymbol, currency);
}

function renderAnalysisTab(container, analysisData, currencySymbol, currency) {
    const scoreColor = analysisData.score >= 80 ? '#22c55e' : analysisData.score >= 60 ? '#84cc16' : analysisData.score >= 40 ? '#eab308' : analysisData.score >= 20 ? '#f97316' : '#ef4444';

    container.innerHTML = `
        <div class="analysis-section">
            <div class="analysis-header">
                <div class="analysis-score">
                    <div class="score-circle" style="border-color: ${scoreColor}; color: ${scoreColor}">${Math.round(analysisData.score)}</div>
                    <div class="analysis-level">評価: <strong>${analysisData.level}</strong></div>
                    <div class="analysis-recommendation">推奨: ${analysisData.recommendation}</div>
                </div>
                <div class="analysis-summary">
                    <div class="summary-item"><span class="label">トレンド</span><span class="value">${analysisData.summary.trend}</span></div>
                    <div class="summary-item"><span class="label">モメンタム</span><span class="value">${analysisData.summary.momentum}</span></div>
                    <div class="summary-item"><span class="label">リスク</span><span class="value">${analysisData.summary.risk}</span></div>
                </div>
            </div>
            <div class="analysis-details">
                <div class="analysis-item">
                    <h5>RSI (14日)</h5><p>${analysisData.indicators.rsi.toFixed(2)}</p>
                    <div class="indicator-bar"><div class="indicator-fill" style="width: ${analysisData.indicators.rsi}%; background: ${getRSIColor(analysisData.indicators.rsi)}"></div></div>
                    <small>${getRSIDescription(analysisData.indicators.rsi)}</small>
                </div>
                <div class="analysis-item">
                    <h5>MACD (12, 26, 9)</h5>
                    <p>${analysisData.indicators.macd ? `${analysisData.indicators.macd.macd.toFixed(2)} / ${analysisData.indicators.macd.signal.toFixed(2)}` : 'N/A'}</p>
                    <small>ヒストグラム: ${analysisData.indicators.macd ? analysisData.indicators.macd.histogram.toFixed(2) : 'N/A'}</small>
                </div>
                <div class="analysis-item"><h5>ボラティリティ</h5><p>${analysisData.indicators.volatility.toFixed(2)}%</p><small>${getVolatilityDescription(analysisData.indicators.volatility)}</small></div>
                <div class="analysis-item"><h5>移動平均（20日）</h5><p>${formatPrice(analysisData.moving_averages.ma_20, currencySymbol, currency)}</p></div>
                <div class="analysis-item"><h5>移動平均（50日）</h5><p>${formatPrice(analysisData.moving_averages.ma_50, currencySymbol, currency)}</p></div>
                <div class="analysis-item">
                    <h5>価格位置</h5><p>${analysisData.price_range.current_position.toFixed(1)}%</p>
                    <div class="indicator-bar"><div class="indicator-fill" style="width: ${analysisData.price_range.current_position}%; background: #667eea"></div></div>
                </div>
                <div class="analysis-item"><h5>期間内高値/安値</h5><p>${formatPrice(analysisData.price_range.max, currencySymbol, currency)} / ${formatPrice(analysisData.price_range.min, currencySymbol, currency)}</p></div>
            </div>
        </div>
        `;
}

async function renderFinancialsTab(container, symbol, currencySymbol, currency) {
    container.innerHTML = '<div class="loading"><div class="spinner"></div>読み込み中...</div>';

    try {
        const response = await fetch(`${API_BASE}/stocks/${symbol}/financials`);
        const data = await response.json();
        if (data.error) { container.innerHTML = `<div class="error">${data.error}</div>`; return; }

        const cs = data.currency_symbol || currencySymbol;
        const cur = data.currency || currency;

        container.innerHTML = `
            <div class="financials-section">
                <div class="financials-group">
                    <h4>📊 評価指標</h4>
                    <div class="financials-grid">
                        <div class="financial-item"><span class="label">時価総額</span><span class="value">${formatLargeNumber(data.market_cap, cs, cur)}</span></div>
                        <div class="financial-item"><span class="label">企業価値</span><span class="value">${formatLargeNumber(data.enterprise_value, cs, cur)}</span></div>
                        <div class="financial-item"><span class="label">PER</span><span class="value">${formatRatio(data.pe_ratio)}</span></div>
                        <div class="financial-item"><span class="label">PBR</span><span class="value">${formatRatio(data.price_to_book)}</span></div>
                    </div>
                </div>
                <div class="financials-group">
                    <h4>💰 収益性</h4>
                    <div class="financials-grid">
                        <div class="financial-item"><span class="label">EPS</span><span class="value">${formatPrice(data.eps, cs, cur)}</span></div>
                        <div class="financial-item"><span class="label">売上高</span><span class="value">${formatLargeNumber(data.revenue, cs, cur)}</span></div>
                        <div class="financial-item"><span class="label">利益率</span><span class="value">${formatPercent(data.profit_margin)}</span></div>
                        <div class="financial-item"><span class="label">ROE</span><span class="value">${formatPercent(data.return_on_equity)}</span></div>
                    </div>
                </div>
                <div class="financials-group">
                    <h4>💵 配当</h4>
                    <div class="financials-grid">
                        <div class="financial-item"><span class="label">配当金</span><span class="value">${formatPrice(data.dividend_rate, cs, cur)}</span></div>
                        <div class="financial-item"><span class="label">配当利回り</span><span class="value">${formatPercent(data.dividend_yield)}</span></div>
                    </div>
                </div>
                <div class="financials-group">
                    <h4>🏦 財務健全性</h4>
                    <div class="financials-grid">
                        <div class="financial-item"><span class="label">現金</span><span class="value">${formatLargeNumber(data.total_cash, cs, cur)}</span></div>
                        <div class="financial-item"><span class="label">負債</span><span class="value">${formatLargeNumber(data.total_debt, cs, cur)}</span></div>
                        <div class="financial-item"><span class="label">D/E比率</span><span class="value">${formatRatio(data.debt_to_equity)}</span></div>
                        <div class="financial-item"><span class="label">β値</span><span class="value">${formatRatio(data.beta)}</span></div>
                    </div>
                </div>
            </div>
        `;
    } catch (error) {
        container.innerHTML = `<div class="error">財務データの取得に失敗: ${error.message}</div>`;
    }
}

async function renderDividendsTab(container, symbol, currencySymbol, currency) {
    container.innerHTML = '<div class="loading"><div class="spinner"></div>読み込み中...</div>';

    try {
        const response = await fetch(`${API_BASE}/stocks/${symbol}/dividends`);
        const data = await response.json();
        if (data.error) { container.innerHTML = `<div class="error">${data.error}</div>`; return; }
        if (!data.has_data || data.dividends.length === 0) {
            container.innerHTML = `<div class="empty-detail" style="height:auto;padding:40px"><div class="empty-icon">💵</div><h2>配当データなし</h2><p>この銘柄は配当を実施していないか、データがありません</p></div>`;
            return;
        }

        const cs = data.currency_symbol || currencySymbol;
        const cur = data.currency || currency;
        const recentDividends = data.dividends.slice(-12).reverse();

        container.innerHTML = `
            <div class="dividends-section">
                <div class="dividend-summary">
                    <div class="summary-card"><h4>年間配当（推定）</h4><div class="value">${formatPrice(data.annual_dividend, cs, cur)}</div></div>
                </div>
                <div class="dividend-table-container">
                    <table class="dividend-table">
                        <thead><tr><th>支払日</th><th>配当金額</th></tr></thead>
                        <tbody>${recentDividends.map(d => `<tr><td>${d.date}</td><td>${formatPrice(d.amount, cs, cur)}</td></tr>`).join('')}</tbody>
                    </table>
                </div>
                <div class="dividend-chart-container"><canvas id="dividendChart"></canvas></div>
            </div>
        `;
        drawDividendChart(data.dividends.slice(-12), cs, cur);
    } catch (error) {
        container.innerHTML = `<div class="error">配当データの取得に失敗: ${error.message}</div>`;
    }
}

// ========================================
// チャート描画
// ========================================

/**
 * データ変換ユーティリティ
 */
const DataTransformer = {
    /**
     * OHLC形式に変換
     * @param {Array} history - 履歴データ配列
     * @returns {Array} OHLCデータ配列
     */
    toOHLC(history) {
        return history.map(d => ({
            time: d.date,
            open: d.open,
            high: d.high,
            low: d.low,
            close: d.close
        }));
    },

    /**
     * 出来高形式に変換
     * @param {Array} history - 履歴データ配列
     * @returns {Array} 出来高データ配列
     */
    toVolume(history) {
        return history.map(d => ({
            time: d.date,
            value: d.volume,
            color: d.close >= d.open ? CHART_CONFIG.VOLUME.upColor : CHART_CONFIG.VOLUME.downColor
        }));
    },

    /**
     * 移動平均形式に変換
     * @param {Array} history - 履歴データ配列
     * @param {number} period - 期間（日数）
     * @returns {Array} 移動平均データ配列（計算できない期間は除外）
     */
    toMA(history, period) {
        const maData = [];
        const closes = history.map(d => d.close);

        for (let i = 0; i < history.length; i++) {
            if (i >= period - 1) {
                // 過去period日間の平均を計算（計算できる場合のみ追加）
                const sum = closes.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0);
                const average = sum / period;
                maData.push({ time: history[i].date, value: average });
            }
            // 期間に満たない場合は追加しない（非表示）
        }

        return maData;
    }
};

/**
 * 移動平均を計算（後方互換性のため残す）
 * @param {Array} history - 履歴データ配列
 * @param {number} period - 期間（日数）
 * @returns {Array} 移動平均データ配列（計算できない期間は除外）
 */
function calculateMovingAverage(history, period) {
    return DataTransformer.toMA(history, period);
}

/**
 * チャート管理クラス
 */
const ChartManager = {
    chart: null,
    series: {
        candle: null,
        volume: null,
        ma: []
    },

    /**
     * チャートインスタンス生成
     * @param {HTMLElement} element - チャートコンテナ要素
     * @returns {Object} Lightweight Chartsインスタンス
     */
    create(element) {
        this.chart = LightweightCharts.createChart(element, {
            layout: {
                background: { color: 'transparent' },
                textColor: '#64748b',
            },
            grid: {
                vertLines: { visible: false },
                horzLines: { color: 'rgba(255,255,255,0.05)' },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
                vertLine: { labelVisible: true },
                horzLine: { labelVisible: true }
            },
            rightPriceScale: {
                borderVisible: false,
                scaleMargins: { top: 0.1, bottom: 0.1 }
            },
            leftPriceScale: {
                visible: true,
                borderVisible: false,
                scaleMargins: { top: 0.8, bottom: 0 }
            },
            timeScale: {
                borderVisible: false,
                timeVisible: true,
                secondsVisible: false
            },
        });
        return this.chart;
    },

    /**
     * チャート破棄
     */
    destroy() {
        this.series.ma = [];
        if (this.chart) {
            try {
                this.chart.remove();
            } catch (e) {
                console.warn('チャートの削除に失敗:', e);
            }
            this.chart = null;
        }
        this.series.candle = null;
        this.series.volume = null;
    },

    /**
     * ローソク足描画
     * @param {Array} history - 履歴データ配列
     */
    renderCandles(history) {
        this.series.candle = this.chart.addCandlestickSeries({
            upColor: CHART_CONFIG.CANDLE.upColor,
            downColor: CHART_CONFIG.CANDLE.downColor,
            borderDownColor: CHART_CONFIG.CANDLE.borderDownColor,
            borderUpColor: CHART_CONFIG.CANDLE.borderUpColor,
            wickDownColor: CHART_CONFIG.CANDLE.wickDownColor,
            wickUpColor: CHART_CONFIG.CANDLE.wickUpColor,
        });
        this.series.candle.setData(DataTransformer.toOHLC(history));
    },

    /**
     * 出来高描画
     * @param {Array} history - 履歴データ配列
     */
    renderVolume(history) {
        this.series.volume = this.chart.addHistogramSeries({
            color: '#26a69a',
            priceFormat: {
                type: 'volume',
                precision: 0,
                minMove: 1
            },
            priceScaleId: 'left',
            scaleMargins: { top: 0.8, bottom: 0 },
        });
        this.series.volume.setData(DataTransformer.toVolume(history));
    },

    /**
     * 移動平均線描画
     * @param {Array} history - 履歴データ配列
     * @param {Array} periods - 移動平均線の期間配列
     */
    renderMA(history, periods) {
        this.series.ma = [];
        periods.forEach((period, index) => {
            const maData = DataTransformer.toMA(history, period);
            if (maData.length > 0) {
                const maSeriesItem = this.chart.addLineSeries({
                    color: CHART_CONFIG.MA.colors[index % CHART_CONFIG.MA.colors.length],
                    lineWidth: 2,
                    title: `MA${period}`,
                    priceLineVisible: false,
                    lastValueVisible: true,
                });
                maSeriesItem.setData(maData);
                this.series.ma.push(maSeriesItem);
            }
        });
    },

    /**
     * メイン描画処理
     * @param {HTMLElement} element - チャートコンテナ要素
     * @param {Array} history - 履歴データ配列
     * @param {Array} periods - 移動平均線の期間配列
     * @returns {Object} Lightweight Chartsインスタンス
     */
    draw(element, history, periods) {
        this.destroy();
        this.create(element);
        this.renderCandles(history);
        this.renderVolume(history);
        this.renderMA(history, periods);
        this.chart.timeScale().fitContent();
        return this.chart;
    }
};

/**
 * チャート描画関数（後方互換性のため残す）
 * @param {Array} history - 履歴データ配列
 * @param {string} currencySymbol - 通貨記号
 * @param {string} currency - 通貨コード
 */
function drawChart(history, currencySymbol = '$', currency = 'USD') {
    const chartElement = document.getElementById('candlestickChart');
    if (!chartElement) return;

    // ChartManagerを使用してチャートを描画
    const newChart = ChartManager.draw(chartElement, history, AppState.selectedMAPeriods);

    // AppStateに保存（互換性のため）
    AppState.setLwChart(newChart);
    AppState.setMASeries(ChartManager.series.ma);
    lwChart = newChart;  // 互換性のため
    maSeries = ChartManager.series.ma;  // 互換性のため
    AppState.setChart(newChart);  // Chart.js用（配当チャートなど）
}

/**
 * 移動平均線の期間をトグル
 * @param {number} period - 移動平均線の期間
 */
function toggleMAPeriod(period) {
    // AppStateから現在の選択状態を取得
    const currentPeriods = [...AppState.selectedMAPeriods];
    const index = currentPeriods.indexOf(period);

    if (index > -1) {
        // 既に選択されている場合は削除
        currentPeriods.splice(index, 1);
    } else {
        // 最大選択数まで選択可能
        if (currentPeriods.length < CHART_CONFIG.MA.maxSelection) {
            currentPeriods.push(period);
            currentPeriods.sort((a, b) => a - b);  // 昇順でソート
        } else {
            // 既に最大数選択されている場合は、チェックボックスを元に戻す
            const checkbox = document.querySelector(`input.ma-period-checkbox[value="${period}"]`);
            if (checkbox) checkbox.checked = false;
            alert(`移動平均線は最大${CHART_CONFIG.MA.maxSelection}本まで選択できます`);
            return;
        }
    }

    // AppStateを更新
    AppState.setSelectedMAPeriods(currentPeriods);
    // グローバル変数も同期（互換性のため）
    selectedMAPeriods = [...currentPeriods];

    // チャートを再描画
    // AppStateまたはwindowからpriceDataを取得
    const priceData = AppState.currentPriceData || window.currentPriceData;
    if (priceData && priceData.history) {
        drawChart(priceData.history,
            priceData.currency_symbol || '$',
            priceData.currency || 'USD');
    } else {
        console.warn('価格データが読み込まれていません');
    }
}

function drawDividendChart(dividends, currencySymbol = '$', currency = 'USD') {
    const ctx = document.getElementById('dividendChart')?.getContext('2d');
    if (!ctx) return;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dividends.map(d => d.date),
            datasets: [{ label: '配当金', data: dividends.map(d => d.amount), backgroundColor: 'rgba(34, 197, 94, 0.7)', borderColor: '#22c55e', borderWidth: 1 }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => formatPrice(ctx.parsed.y, currencySymbol, currency) } } },
            scales: { x: { grid: { display: false }, ticks: { maxTicksLimit: 8 } }, y: { beginAtZero: true, ticks: { callback: v => formatPrice(v, currencySymbol, currency) } } }
        }
    });
}

// ========================================
// ヘルパー関数
// ========================================

function changePeriod(period, event) {
    currentPeriod = period;
    document.querySelectorAll('.period-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    if (currentStock) showStockDetail(currentStock);
}

function showEmptyDetail() {
    document.getElementById('stockDetail').innerHTML = `
        <div class="empty-detail">
            <div class="empty-icon">📊</div>
            <h2>銘柄を選択してください</h2>
            <p>左のリストから銘柄をクリックすると、<br>詳細な情報がここに表示されます</p>
        </div>
    `;
}

function formatNumber(num) {
    if (num === null || num === undefined) return 'N/A';
    if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B';
    if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M';
    if (num >= 1e3) return (num / 1e3).toFixed(2) + 'K';
    return num.toLocaleString();
}

function formatRatio(value) {
    if (value === null || value === undefined) return 'N/A';
    return value.toFixed(2);
}

function formatPercent(value) {
    if (value === null || value === undefined) return 'N/A';
    return (value * 100).toFixed(2) + '%';
}

function getRSIColor(rsi) {
    if (rsi < 30) return '#22c55e';
    if (rsi > 70) return '#ef4444';
    return '#667eea';
}

function getRSIDescription(rsi) {
    if (rsi < 30) return '売られすぎ';
    if (rsi > 70) return '買われすぎ';
    return '中立';
}

function getVolatilityDescription(v) {
    if (v < 20) return '低（安定）';
    if (v > 40) return '高（変動大）';
    return '中程度';
}

function showMessage(message, type = 'info') {
    const bgColor = type === 'success' ? '#22c55e' : (type === 'error' ? '#ef4444' : '#667eea');

    Toastify({
        text: message,
        duration: 3000,
        gravity: "top", // `top` or `bottom`
        position: "right", // `left`, `center` or `right`
        stopOnFocus: true, // Prevents dismissing of toast on hover
        style: {
            background: bgColor,
            borderRadius: "8px",
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
            padding: "12px 20px",
            fontSize: "0.95rem",
        },
    }).showToast();
}

function showError(message) {
    showMessage(message, 'error');
}

async function renderPredictionTab(container, symbol, currencySymbol, currency) {
    container.innerHTML = '<div class="loading"><div class="spinner"></div>AI予測を計算中... (数秒かかります)</div>';

    try {
        const response = await fetch(`${API_BASE}/stocks/${symbol}/prediction?periods=30`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || '予測データの取得に失敗しました');
        }

        const lastPrice = data.current_price;
        const nextDay = data.summary.next_day;
        const trendIcon = nextDay.trend_direction === '上昇' ? '📈' : '📉';
        const trendClass = nextDay.diff >= 0 ? 'text-positive' : 'text-negative';

        container.innerHTML = `
            <div class="prediction-section">
                <div class="prediction-header">
                    <div class="prediction-summary-card">
                        <div class="card-title">翌営業日 (${nextDay.date}) の予測</div>
                        <div class="card-main-value ${trendClass}">
                            ${formatPrice(nextDay.price, currencySymbol, currency)}
                            <span class="trend-icon">${trendIcon}</span>
                        </div>
                        <div class="card-sub-value">
                            予想変動: ${nextDay.diff >= 0 ? '+' : ''}${formatPrice(nextDay.diff, currencySymbol, currency)} 
                            (${nextDay.diff >= 0 ? '+' : ''}${nextDay.diff_percent}%)
                        </div>
                        <div class="confidence-interval">
                            信頼区間: ${formatPrice(nextDay.range_low, currencySymbol, currency)} 〜 ${formatPrice(nextDay.range_high, currencySymbol, currency)}
                        </div>
                    </div>
                    <div class="prediction-note">
                        <small>※ この予測はProphetモデル（ベイズ推定）による統計的な推計値です。投資の確実な利益を保証するものではありません。</small>
                    </div>
                </div>
                <div class="chart-container" style="position: relative; height: 400px; width: 100%;">
                    <canvas id="predictionChart"></canvas>
                </div>
            </div>
        `;

        // チャート描画
        const ctx = document.getElementById('predictionChart').getContext('2d');

        // データセットの準備
        // Chart.jsで信頼区間を描画:
        // 1. Upper Bound (fill: '+1' -> 下のデータセットへ塗りつぶし? V3では 'origin' or index. Stacked? No)
        // 一般的な方法: 
        // Dataset 1: Mean (Line)
        // Dataset 2: Upper (Transparent Line, fill: '+1' -> fill to required dataset? No, '1' means dataset index 1? No 'origin', 'start', 'end', or boolean/string)
        // Docs: fill: {target: 'origin' | 'start' | 'end' | number (dataset index) | boolean }

        // 構成:
        // 0: Upper Bound (Line transparent, fill: 1) -> Fills area between 0 and 1
        // 1: Lower Bound (Line transparent, fill: false)
        // 2: Mean (Line visible)

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: [
                    {
                        label: '予測上限 (Upper)',
                        data: data.forecast.upper,
                        borderColor: 'transparent',
                        backgroundColor: 'rgba(102, 126, 234, 0.2)', // Fill color
                        pointRadius: 0,
                        fill: 1, // Fill to dataset index 1 (Lower)
                        tension: 0.4
                    },
                    {
                        label: '予測下限 (Lower)',
                        data: data.forecast.lower,
                        borderColor: 'transparent',
                        pointRadius: 0,
                        fill: false,
                        tension: 0.4
                    },
                    {
                        label: '予測値 (Forecast)',
                        data: data.forecast.yhat,
                        borderColor: '#667eea',
                        backgroundColor: '#667eea',
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: false,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index',
                },
                plugins: {
                    legend: {
                        display: true,
                        labels: {
                            filter: function (item, chart) {
                                // Upper/Lowerのラベルは隠して、予測値だけ見せる、あるいはまとめて見せる
                                return item.text === '予測値 (Forecast)';
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += formatPrice(context.parsed.y, currencySymbol, currency);
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            callback: function (value) {
                                return formatPrice(value, currencySymbol, currency);
                            }
                        }
                    }
                }
            }
        });

    } catch (error) {
        container.innerHTML = `<div class="error">予測の生成に失敗しました: ${error.message}</div>`;
    }
}

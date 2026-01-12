const API_BASE = 'http://localhost:5000/api';

// グローバル状態
let currentStock = null;
let currentPeriod = '1mo';
let chart = null;

// 初期化
document.addEventListener('DOMContentLoaded', () => {
    loadStocks();
    setupEventListeners();
});

function setupEventListeners() {
    // 銘柄追加フォーム
    document.getElementById('addStockForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const symbol = document.getElementById('symbolInput').value.trim().toUpperCase();
        if (symbol) {
            await addStock(symbol);
            document.getElementById('symbolInput').value = '';
        }
    });
}

async function loadStocks() {
    try {
        const response = await fetch(`${API_BASE}/stocks`);
        const stocks = await response.json();
        displayDashboard(stocks);
    } catch (error) {
        console.error('銘柄の読み込みに失敗:', error);
        showError('銘柄の読み込みに失敗しました');
    }
}

async function addStock(symbol) {
    try {
        const response = await fetch(`${API_BASE}/stocks`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ symbol })
        });
        
        let data;
        try {
            data = await response.json();
        } catch (jsonError) {
            // JSONパースエラーの場合
            showError(`サーバーからの応答を解析できませんでした。ステータス: ${response.status}`);
            return;
        }
        
        if (response.ok) {
            loadStocks();
            let message = data.message || '銘柄を追加しました';
            if (data.warning) {
                message += `\n注意: ${data.warning}`;
            }
            showMessage(message, 'success');
        } else {
            let errorMsg = data.error || '銘柄の追加に失敗しました';
            if (data.hint) {
                errorMsg += `\n${data.hint}`;
            }
            if (response.status === 429 && data.retry_after) {
                errorMsg += `\n推奨待機時間: ${data.retry_after}秒`;
            }
            showError(errorMsg);
        }
    } catch (error) {
        console.error('銘柄の追加に失敗:', error);
        showError(`ネットワークエラーが発生しました: ${error.message}\n接続を確認してください。`);
    }
}

async function removeStock(symbol) {
    if (!confirm(`本当に${symbol}を削除しますか？`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/stocks/${symbol}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            loadStocks();
            if (currentStock === symbol) {
                hideStockDetail();
            }
            showMessage('銘柄を削除しました', 'success');
        }
    } catch (error) {
        console.error('銘柄の削除に失敗:', error);
        showError('銘柄の削除に失敗しました');
    }
}

function displayDashboard(stocks) {
    const dashboard = document.getElementById('dashboard');
    
    if (stocks.length === 0) {
        dashboard.innerHTML = '<div class="loading">追跡中の銘柄がありません。上記のフォームから銘柄を追加してください。</div>';
        return;
    }
    
    // ダッシュボードデータを取得
    fetch(`${API_BASE}/dashboard`)
        .then(res => res.json())
        .then(data => {
            dashboard.innerHTML = stocks.map(stock => {
                const stockData = data.find(s => s.symbol === stock.symbol);
                const price = stockData ? stockData.price.toFixed(2) : 'N/A';
                const change = stockData ? stockData.change.toFixed(2) : '0.00';
                const changePercent = stockData ? stockData.change_percent.toFixed(2) : '0.00';
                const changeClass = stockData && stockData.change >= 0 ? 'positive' : 'negative';
                const changeSign = stockData && stockData.change >= 0 ? '+' : '';
                const cachedBadge = stockData && stockData.cached ? '<span style="font-size: 0.7em; color: #999; margin-left: 5px;">(キャッシュ)</span>' : '';
                
                return `
                    <div class="stock-card" onclick="showStockDetail('${stock.symbol}')">
                        <div class="stock-card-header">
                            <h3>${stock.symbol}${cachedBadge}</h3>
                            <button class="remove-btn" onclick="event.stopPropagation(); removeStock('${stock.symbol}')">削除</button>
                        </div>
                        <div class="stock-price">$${price}</div>
                        <div class="stock-change ${changeClass}">
                            ${changeSign}${change} (${changeSign}${changePercent}%)
                        </div>
                        <div style="margin-top: 10px; color: #666; font-size: 0.9em;">${stock.name || stock.symbol}</div>
                    </div>
                `;
            }).join('');
        })
        .catch(error => {
            console.error('ダッシュボードデータの取得に失敗:', error);
            dashboard.innerHTML = '<div class="error">データの取得に失敗しました</div>';
        });
}

async function showStockDetail(symbol) {
    currentStock = symbol;
    const detailSection = document.getElementById('stockDetail');
    detailSection.classList.add('active');
    detailSection.innerHTML = '<div class="loading">データを読み込んでいます...</div>';
    
    // 期間選択ボタン
    const periodButtons = ['1mo', '3mo', '6mo', '1y', '2y'].map(period => {
        const label = {
            '1mo': '1ヶ月',
            '3mo': '3ヶ月',
            '6mo': '6ヶ月',
            '1y': '1年',
            '2y': '2年'
        }[period] || period;
        return `<button class="period-btn ${period === currentPeriod ? 'active' : ''}" 
                        onclick="changePeriod('${period}')">${label}</button>`;
    }).join('');
    
    try {
        // 株価データと分析を並行取得
        const [priceResponse, analysisResponse] = await Promise.all([
            fetch(`${API_BASE}/stocks/${symbol}/price?period=${currentPeriod}`),
            fetch(`${API_BASE}/stocks/${symbol}/analysis?period=${currentPeriod}`)
        ]);
        
        let priceData, analysisData;
        try {
            priceData = await priceResponse.json();
        } catch (e) {
            priceData = { error: '価格データの解析に失敗しました' };
        }
        
        try {
            analysisData = await analysisResponse.json();
        } catch (e) {
            analysisData = { error: '分析データの解析に失敗しました' };
        }
        
        if (!priceResponse.ok || !analysisResponse.ok) {
            const errorMsg = priceData.error || analysisData.error || 'データの取得に失敗しました';
            let fullErrorMsg = errorMsg;
            
            // レート制限エラーの場合
            if (errorMsg.includes('rate limit') || errorMsg.includes('Too Many Requests')) {
                fullErrorMsg = 'APIのレート制限に達しました。\nしばらく待ってから再度お試しください。\n推奨待機時間: 60秒';
            }
            
            throw new Error(fullErrorMsg);
        }
        
        displayStockDetail(priceData, analysisData, periodButtons);
    } catch (error) {
        console.error('詳細データの取得に失敗:', error);
        detailSection.innerHTML = `
            <div class="detail-header">
                <h2>${symbol}</h2>
                <button class="close-btn" onclick="hideStockDetail()">閉じる</button>
            </div>
            <div class="error" style="white-space: pre-line; margin: 20px 0;">${error.message}</div>
            <p style="color: #666; margin-top: 20px;">しばらく待ってから再度お試しください。</p>
        `;
    }
}

function displayStockDetail(priceData, analysisData, periodButtons) {
    const detailSection = document.getElementById('stockDetail');
    const changeClass = priceData.change >= 0 ? 'positive' : 'negative';
    const changeSign = priceData.change >= 0 ? '+' : '';
    
    detailSection.innerHTML = `
        <div class="detail-header">
            <h2>${priceData.symbol} - ${priceData.name}</h2>
            <button class="close-btn" onclick="hideStockDetail()">閉じる</button>
        </div>
        
        <div class="period-selector">
            ${periodButtons}
        </div>
        
        ${priceData.cached && priceData.message ? `
            <div class="error" style="background: #fff3cd; border-left-color: #ffc107; color: #856404; margin-bottom: 20px;">
                ${priceData.message}
            </div>
        ` : ''}
        <div class="price-info">
            <div class="info-box">
                <h4>現在の価格</h4>
                <div class="value">$${priceData.current_price.toFixed(2)}</div>
            </div>
            <div class="info-box">
                <h4>変動</h4>
                <div class="value ${changeClass}">${changeSign}${priceData.change.toFixed(2)}</div>
            </div>
            <div class="info-box">
                <h4>変動率</h4>
                <div class="value ${changeClass}">${changeSign}${priceData.change_percent.toFixed(2)}%</div>
            </div>
            <div class="info-box">
                <h4>出来高</h4>
                <div class="value">${formatNumber(priceData.volume)}</div>
            </div>
        </div>
        
        <div class="chart-container">
            <canvas id="priceChart"></canvas>
        </div>
        
        <div class="analysis-section">
            <div class="analysis-score">
                <div class="score-circle">${Math.round(analysisData.score)}</div>
                <div class="analysis-level">評価: ${analysisData.level}</div>
                <div class="analysis-recommendation">推奨: ${analysisData.recommendation}</div>
            </div>
            
            <div class="analysis-details">
                <div class="analysis-item">
                    <h5>トレンド</h5>
                    <p>${analysisData.summary.trend}</p>
                </div>
                <div class="analysis-item">
                    <h5>モメンタム</h5>
                    <p>${analysisData.summary.momentum}</p>
                </div>
                <div class="analysis-item">
                    <h5>リスク</h5>
                    <p>${analysisData.summary.risk}</p>
                </div>
                <div class="analysis-item">
                    <h5>RSI</h5>
                    <p>${analysisData.indicators.rsi.toFixed(2)}</p>
                </div>
                <div class="analysis-item">
                    <h5>ボラティリティ</h5>
                    <p>${analysisData.indicators.volatility.toFixed(2)}%</p>
                </div>
                <div class="analysis-item">
                    <h5>移動平均（20日）</h5>
                    <p>$${analysisData.moving_averages.ma_20.toFixed(2)}</p>
                </div>
                <div class="analysis-item">
                    <h5>移動平均（50日）</h5>
                    <p>$${analysisData.moving_averages.ma_50.toFixed(2)}</p>
                </div>
                <div class="analysis-item">
                    <h5>価格位置</h5>
                    <p>${analysisData.price_range.current_position.toFixed(1)}%</p>
                </div>
            </div>
        </div>
    `;
    
    // チャートを描画
    drawChart(priceData.history);
}

function changePeriod(period) {
    currentPeriod = period;
    if (currentStock) {
        showStockDetail(currentStock);
    }
}

function drawChart(history) {
    const ctx = document.getElementById('priceChart').getContext('2d');
    
    // 既存のチャートを破棄
    if (chart) {
        chart.destroy();
    }
    
    const labels = history.map(d => d.date);
    const closes = history.map(d => d.close);
    const volumes = history.map(d => d.volume);
    
    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: '終値',
                data: closes,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toFixed(2);
                        }
                    }
                }
            }
        }
    });
}

function hideStockDetail() {
    document.getElementById('stockDetail').classList.remove('active');
    currentStock = null;
    if (chart) {
        chart.destroy();
        chart = null;
    }
}

function formatNumber(num) {
    if (num >= 1e9) {
        return (num / 1e9).toFixed(2) + 'B';
    } else if (num >= 1e6) {
        return (num / 1e6).toFixed(2) + 'M';
    } else if (num >= 1e3) {
        return (num / 1e3).toFixed(2) + 'K';
    }
    return num.toString();
}

function showMessage(message, type = 'info') {
    // シンプルなアラート（必要に応じて改善可能）
    alert(message);
}

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    // 改行を保持
    errorDiv.style.whiteSpace = 'pre-line';
    errorDiv.textContent = message;
    document.querySelector('.container').insertBefore(errorDiv, document.querySelector('.container').firstChild);
    
    // スクロールしてエラーが見えるように
    errorDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    
    setTimeout(() => {
        errorDiv.remove();
    }, 8000);
}

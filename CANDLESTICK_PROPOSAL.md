# Candlestick Chart（ローソク足チャート）変更提案

## 作成日: 2026-01-16

## 1. 概要

現在の折れ線グラフをCandlestick Chart（ローソク足チャート）に変更する提案です。

---

## 2. 現状分析

| 項目 | 現状 |
|------|------|
| **ライブラリ** | Chart.js (CDN) |
| **チャートタイプ** | 折れ線グラフ (`type: 'line'`) |
| **表示データ** | 終値 (`close`) のみ |
| **利用可能データ** | `date`, `open`, `high`, `low`, `close`, `volume` |

### 現在のコード（app.js L678-725）

```javascript
function drawChart(history, currencySymbol = '$', currency = 'USD') {
    const ctx = document.getElementById('priceChart')?.getContext('2d');
    if (!ctx) return;
    if (chart) chart.destroy();

    const labels = history.map(d => d.date);
    const closes = history.map(d => d.close);
    // ... 折れ線グラフの実装
    chart = new Chart(ctx, {
        type: 'line',
        // ...
    });
}
```

### APIレスポンス（stock_api.py L131-143）

```python
def format_history_data(hist: pd.DataFrame) -> List[Dict]:
    """履歴データを整形"""
    data = []
    for date, row in hist.iterrows():
        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'open': float(row['Open']),    # ← 始値（未使用）
            'high': float(row['High']),    # ← 高値（未使用）
            'low': float(row['Low']),      # ← 安値（未使用）
            'close': float(row['Close']),  # ← 終値のみ使用中
            'volume': int(row['Volume'])   # ← 出来高（未使用）
        })
    return data
```

**結論**: バックエンドは既にOHLCデータを提供しており、フロントエンドの変更のみで対応可能

---

## 3. 実装オプション

### オプション1: Chart.js + Financial Plugin（推奨）

#### メリット
- 既存のChart.jsを活かせる
- 学習コストが低い
- 他のチャート（配当グラフ等）との統一感
- 実装工数が最小

#### デメリット
- プラグインの追加が必要
- 専用ライブラリほど機能は豊富でない

#### 必要な変更

**index.html**
```html
<!-- 既存のChart.js CDNの後に追加 -->
<script src="https://cdn.jsdelivr.net/npm/luxon@3"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-luxon@1"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-chart-financial@0.2"></script>
```

**app.js - drawChart関数**
```javascript
function drawChart(history, currencySymbol = '$', currency = 'USD') {
    const ctx = document.getElementById('priceChart')?.getContext('2d');
    if (!ctx) return;
    if (chart) chart.destroy();

    // OHLCデータを整形
    const ohlcData = history.map(d => ({
        x: new Date(d.date).getTime(),
        o: d.open,
        h: d.high,
        l: d.low,
        c: d.close
    }));

    chart = new Chart(ctx, {
        type: 'candlestick',
        data: {
            datasets: [{
                label: '株価',
                data: ohlcData,
                color: {
                    up: '#22c55e',      // 陽線（緑）
                    down: '#ef4444',    // 陰線（赤）
                    unchanged: '#64748b'
                }
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const d = ctx.raw;
                            return [
                                `始値: ${formatPrice(d.o, currencySymbol, currency)}`,
                                `高値: ${formatPrice(d.h, currencySymbol, currency)}`,
                                `安値: ${formatPrice(d.l, currencySymbol, currency)}`,
                                `終値: ${formatPrice(d.c, currencySymbol, currency)}`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: { unit: 'day', displayFormats: { day: 'MM/dd' } },
                    grid: { display: false },
                    ticks: { color: '#64748b' }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: {
                        color: '#64748b',
                        callback: v => formatPrice(v, currencySymbol, currency)
                    }
                }
            }
        }
    });
}
```

---

### オプション2: Lightweight Charts（TradingView）

#### メリット
- TradingViewと同じ高品質なチャート
- ズーム・パン機能が標準搭載
- 出来高バーを同時表示可能
- 軽量で高パフォーマンス
- 金融チャートに特化した設計

#### デメリット
- Chart.jsとの置き換えが必要
- 他のチャート（配当等）との統一感が失われる
- 学習コストがやや高い

#### 必要な変更

**index.html**
```html
<!-- Chart.jsの代わりに使用 -->
<script src="https://unpkg.com/lightweight-charts@4/dist/lightweight-charts.standalone.production.js"></script>
```

**app.js - drawChart関数**
```javascript
let lwChart = null;

function drawChart(history, currencySymbol = '$', currency = 'USD') {
    const container = document.getElementById('priceChart').parentElement;
    container.innerHTML = '<div id="candlestickChart" style="height: 300px;"></div>';
    
    const chartElement = document.getElementById('candlestickChart');
    
    // 既存のチャートを破棄
    if (lwChart) {
        lwChart.remove();
    }
    
    lwChart = LightweightCharts.createChart(chartElement, {
        layout: {
            background: { color: 'transparent' },
            textColor: '#64748b',
        },
        grid: {
            vertLines: { visible: false },
            horzLines: { color: 'rgba(255,255,255,0.05)' },
        },
        crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
        rightPriceScale: { borderVisible: false },
        timeScale: { borderVisible: false },
    });

    const candlestickSeries = lwChart.addCandlestickSeries({
        upColor: '#22c55e',
        downColor: '#ef4444',
        borderDownColor: '#ef4444',
        borderUpColor: '#22c55e',
        wickDownColor: '#ef4444',
        wickUpColor: '#22c55e',
    });

    // データを整形
    const data = history.map(d => ({
        time: d.date,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close
    }));

    candlestickSeries.setData(data);
    lwChart.timeScale().fitContent();
    
    // 出来高バーを追加（オプション）
    const volumeSeries = lwChart.addHistogramSeries({
        color: '#26a69a',
        priceFormat: { type: 'volume' },
        priceScaleId: '',
        scaleMargins: { top: 0.8, bottom: 0 },
    });
    
    const volumeData = history.map(d => ({
        time: d.date,
        value: d.volume,
        color: d.close >= d.open ? '#22c55e80' : '#ef444480'
    }));
    
    volumeSeries.setData(volumeData);
}
```

---

### オプション3: 切り替え可能なハイブリッド

#### メリット
- ユーザーが折れ線/ローソク足を選択可能
- 柔軟性が高い
- 将来の拡張性

#### デメリット
- 実装工数が大きい
- 両方のチャートタイプをメンテナンスする必要がある

#### 必要な変更

**app.js - UI追加**
```javascript
// グローバル変数に追加
let chartType = 'candlestick';  // 'line' or 'candlestick'

// renderChartTab関数を修正
function renderChartTab(container, priceData, currencySymbol, currency) {
    container.innerHTML = `
        <div class="price-info">
            <!-- 既存の価格情報 -->
        </div>
        <div class="chart-type-selector">
            <button class="chart-type-btn ${chartType === 'line' ? 'active' : ''}" 
                    onclick="setChartType('line')">📈 折れ線</button>
            <button class="chart-type-btn ${chartType === 'candlestick' ? 'active' : ''}" 
                    onclick="setChartType('candlestick')">🕯️ ローソク足</button>
        </div>
        <div class="chart-container"><canvas id="priceChart"></canvas></div>
    `;
    drawChart(priceData.history, currencySymbol, currency);
}

function setChartType(type) {
    chartType = type;
    document.querySelectorAll('.chart-type-btn').forEach(btn => {
        btn.classList.toggle('active', btn.textContent.includes(type === 'line' ? '折れ線' : 'ローソク'));
    });
    drawChart(window.currentPriceData.history, 
              window.currentPriceData.currency_symbol, 
              window.currentPriceData.currency);
}

function drawChart(history, currencySymbol = '$', currency = 'USD') {
    if (chartType === 'candlestick') {
        drawCandlestickChart(history, currencySymbol, currency);
    } else {
        drawLineChart(history, currencySymbol, currency);
    }
}
```

**style.css - スタイル追加**
```css
.chart-type-selector {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
}

.chart-type-btn {
    padding: 6px 12px;
    border: 1px solid #374151;
    border-radius: 6px;
    background: transparent;
    color: #9ca3af;
    cursor: pointer;
    transition: all 0.2s;
}

.chart-type-btn:hover {
    border-color: #667eea;
    color: #667eea;
}

.chart-type-btn.active {
    background: #667eea;
    border-color: #667eea;
    color: white;
}
```

---

## 4. 比較表

| 観点 | オプション1 | オプション2 | オプション3 |
|------|------------|------------|------------|
| **実装工数** | 小 | 中 | 中〜大 |
| **学習コスト** | 低 | 中 | 中 |
| **既存コードへの影響** | 最小 | 中 | 中 |
| **チャート品質** | 良 | 優 | 良〜優 |
| **ズーム/パン機能** | なし | あり | 依存 |
| **出来高表示** | 別途実装 | 標準搭載 | 依存 |
| **統一感** | 維持 | 低下 | 維持 |
| **将来の拡張性** | 中 | 高 | 高 |

---

## 5. 推奨案

### 総合推奨: オプション1（Chart.js + Financial Plugin）

**理由:**
1. 既存コードへの影響が最小限
2. 配当チャートとの統一感を維持
3. 実装工数が最も小さい
4. 将来的にハイブリッド（オプション3）への拡張も容易
5. プラグインの信頼性（Chart.js公式エコシステム）

### 段階的実装の提案

1. **Phase 1**: オプション1でCandlestickチャートを実装
2. **Phase 2**: ユーザーフィードバックを収集
3. **Phase 3**: 必要に応じてオプション3（切り替え機能）を追加
4. **Phase 4**: 高機能が必要ならオプション2への移行を検討

---

## 6. 実装工数見積り

| オプション | 工数 | 影響ファイル |
|------------|------|--------------|
| オプション1 | 1-2時間 | `index.html`, `app.js` |
| オプション2 | 3-4時間 | `index.html`, `app.js`, `style.css` |
| オプション3 | 4-6時間 | `index.html`, `app.js`, `style.css` |

---

## 7. 参考リンク

- [Chart.js Financial Plugin](https://github.com/chartjs/chartjs-chart-financial)
- [Lightweight Charts (TradingView)](https://www.tradingview.com/lightweight-charts/)
- [Chart.js 公式ドキュメント](https://www.chartjs.org/docs/)

---

## 8. 実施記録

| 日付 | 項目 | 備考 |
|------|------|------|
| 2026-01-16 | 提案作成 | 3オプションを比較検討 |
| 2026-01-16 | 実装開始 | オプション2（Lightweight Charts）で実装 |
| 2026-01-16 | 実装完了 | index.html, app.jsを更新、ローソク足チャート+出来高バーを実装 |
| 2026-01-16 | 動作確認 | Chrome DevToolsで動作確認・デバッグ完了 |
| 2026-01-16 | 完了 | 正常動作を確認 |

### 実装内容

**変更ファイル:**
- `templates/index.html`: Lightweight Charts CDNを追加
- `static/app.js`: 
  - `lwChart`グローバル変数を追加
  - `renderChartTab`: canvasをdivに変更
  - `drawChart`: Lightweight Chartsを使用したローソク足チャート+出来高バーに全面書き換え

**実装機能:**
- ローソク足チャート（陽線: 緑、陰線: 赤）
- 出来高バー（価格変動に応じた色分け）
- ズーム・パン機能（Lightweight Charts標準機能）
- クロスヘア表示

**動作確認結果（2026-01-16）:**
- ✅ Lightweight Chartsライブラリの正常ロード確認
- ✅ ローソク足チャートの正常表示確認（AAPL、MSFTでテスト）
- ✅ 出来高バーの正常表示確認
- ✅ period変更時の動作確認（1M → 3M）
- ✅ 銘柄切り替え時の動作確認（AAPL → MSFT）
- ✅ データ形式確認（OHLCデータが正しく取得されている）
- ⚠️ 軽微なエラー: favicon.ico 404（機能に影響なし）、/api/stocks 400（原因調査が必要だがチャート表示には影響なし）

**確認事項:**
- チャート要素（candlestickChart）は正常に作成されている
- lwChartオブジェクトは正常に生成されている
- 日付形式（'YYYY-MM-DD'文字列）はLightweight Chartsで正常に処理されている
- スクリーンショットでチャートの視覚的表示を確認済み

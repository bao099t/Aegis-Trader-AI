const API_BASE = window.location.origin;

async function fetchStats() {
    try {
        const res = await fetch(`${API_BASE}/stats`);
        const data = await res.json();
        document.getElementById('stat-total').textContent = data.total_alerts;
        document.getElementById('stat-sent').textContent = data.alerts_sent;
        document.getElementById('stat-winrate').textContent = `${data.win_rate}%`;
        document.getElementById('stat-pnl').textContent = `${data.avg_pnl > 0 ? '+' : ''}${data.avg_pnl}% (NET)`;

        // Add Max Drawdown (Phase 24)
        if (data.max_drawdown !== undefined) {
            document.getElementById('stat-drawdown').textContent = `-${data.max_drawdown}%`;
        }

        const pnlEl = document.getElementById('stat-pnl');
        pnlEl.style.color = data.avg_pnl >= 0 ? 'var(--success)' : 'var(--danger)';
    } catch (e) {
        console.error("Stats error", e);
    }
}

async function fetchAlerts() {
    try {
        const res = await fetch(`${API_BASE}/alerts?limit=50`);
        const alerts = await res.json();
        renderAlerts(alerts);
        document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
    } catch (e) {
        console.error("Alerts error", e);
    }
}

async function fetchWatchlist() {
    try {
        const res = await fetch(`${API_BASE}/watchlist`);
        const list = await res.json();
        const container = document.getElementById('watchlist-items');
        container.innerHTML = list.map(item => `<li>${item}</li>`).join('');
    } catch (e) {
        console.error("Watchlist error", e);
    }
}

async function fetchMacro() {
    try {
        const res = await fetch(`${API_BASE}/macro`);
        const data = await res.json();
        const container = document.getElementById('macro-status');

        let statusClass = data.risk_status === "RISK-ON" ? "tag sentiment-pos" : "tag sentiment-neg";

        container.innerHTML = `
            <p><strong>VIX Index:</strong> ${data.vix} (${data.mood})</p>
            <p><strong>SPY Trend:</strong> ${data.spy_trend}</p>
            <span class="${statusClass}">${data.risk_status}</span>
        `;
    } catch (e) {
        console.error("Macro error", e);
    }
}

async function fetchHealth() {
    try {
        const res = await fetch(`${API_BASE}/health`);
        const data = await res.json();

        const statusEl = document.getElementById('heartbeat-status');
        const latencyEl = document.getElementById('cycle-latency');

        statusEl.innerHTML = `<span class="dot ${data.status === 'HEALTHY' ? 'live' : ''}"></span> ${data.status}`;
        latencyEl.textContent = `${data.latency_ms}ms`;

        if (data.status !== 'HEALTHY') {
            statusEl.parentElement.style.background = 'rgba(239, 68, 68, 0.1)';
            statusEl.parentElement.style.color = 'var(--danger)';
        } else {
            statusEl.parentElement.style.background = 'rgba(16, 185, 129, 0.1)';
            statusEl.parentElement.style.color = 'var(--success)';
        }
    } catch (e) {
        console.error("Health error", e);
    }
}

async function addTicker() {
    const input = document.getElementById('new-ticker');
    const ticker = input.value.trim().toUpperCase();
    if (!ticker) return;

    try {
        const res = await fetch(`${API_BASE}/watchlist`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker })
        });
        const data = await res.json();
        if (data.status === "success") {
            input.value = '';
            fetchWatchlist();
        }
    } catch (e) {
        console.error("Add ticker error", e);
    }
}

function renderAlerts(alerts) {
    const list = document.getElementById('alert-feed');

    if (alerts.length === 0) {
        list.innerHTML = '<div class="loading">No alerts found yet.</div>';
        return;
    }

    list.innerHTML = alerts.map(alert => {
        let sentClass = 'sentiment-neu';
        if (alert.sentiment_score > 0.3) sentClass = 'sentiment-pos';
        if (alert.sentiment_score < -0.3) sentClass = 'sentiment-neg';

        return `
            <div class="alert-item ${sentClass}">
                <div class="alert-header">
                    <span class="alert-source">${alert.source}</span>
                    <span class="alert-time">${new Date(alert.published_at).toLocaleString()}</span>
                </div>
                <a href="${alert.link}" target="_blank" class="alert-title">${alert.title}</a>
                <div>
                     ${alert.reason ? `<span class="alert-reason">${alert.reason}</span>` : ''}
                     ${alert.keyword ? `<span class="tag">${alert.keyword.toUpperCase()}</span>` : ''}
                     ${alert.stop_loss_price ? `<span class="tag" style="border: 1px solid var(--danger)">SL: $${alert.stop_loss_price.toFixed(2)}</span>` : ''}
                     ${alert.is_verified === false ? `<span class="tag" style="background: var(--danger); color: white">⚠️ DECEPTION RISK</span>` : ''}
                </div>
                <div style="margin-top:10px">
                    <button class="buy-btn" onclick="simulateExecution('${alert.published_at}', this)">⚡ SIMULATE BUY</button>
                    <span class="latency-result" style="margin-left:10px; font-size: 0.8em; color: var(--secondary)"></span>
                </div>
            </div>
        `;
    }).join('');
}

function simulateExecution(publishedAt, btn) {
    const pubDate = new Date(publishedAt).getTime();
    const now = new Date().getTime();
    const diffSec = Math.round((now - pubDate) / 1000);

    const resultSpan = btn.nextElementSibling;

    let msg = `Execution Lag: ${diffSec}s. `;
    if (diffSec > 60) {
        msg += `<span style="color:var(--danger)">⚠️ Institutional disadvantage. Alpha lost.</span>`;
    } else {
        msg += `<span style="color:var(--success)">⚡ Competitive entry.</span>`;
    }

    resultSpan.innerHTML = msg;
    btn.disabled = true;
    btn.style.opacity = 0.5;
}

// Init
fetchStats();
fetchAlerts();
fetchWatchlist();
fetchMacro();
fetchHealth();
fetchOrders();
fetchKillStatus();

// Poll
setInterval(() => {
    fetchStats();
    fetchAlerts();
    fetchMacro();
    fetchHealth();
    fetchOrders();
    fetchKillStatus();
}, 30000);

async function fetchOrders() {
    try {
        const res = await fetch(`${API_BASE}/orders`);
        const data = await res.json();
        const container = document.getElementById('order-feed');
        if (data.length === 0) {
            container.innerHTML = '<p style="color:var(--text-secondary)">No orders today.</p>';
            return;
        }

        container.innerHTML = data.reverse().slice(0, 5).map(o => `
            <div style="margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border)">
                <div style="display:flex; justify-content:space-between">
                    <span style="font-weight:bold">${o.ticker}</span>
                    <span style="font-size:0.7rem; color:var(--text-secondary)">${o.timestamp.split(' ')[1]}</span>
                </div>
                <div style="color: ${o.direction === 'BULLISH' ? 'var(--success)' : 'var(--danger)'}">
                    ${o.direction} @ $${o.entry_price}
                </div>
                <div style="font-size:0.7rem; color:var(--text-secondary)">
                    Size: ${o.size} | SL: $${o.stop_loss}
                </div>
            </div>
        `).join('');
    } catch (e) { }
}

async function fetchKillStatus() {
    try {
        const res = await fetch(`${API_BASE}/kill-switch`);
        const data = await res.json();
        const btn = document.getElementById('kill-switch-btn');
        if (data.is_killed) {
            btn.textContent = "🛡️ RE-ARM SYSTEM";
            btn.classList.add('killed');
        } else {
            btn.textContent = "☠️ KILL SWITCH";
            btn.classList.remove('killed');
        }
    } catch (e) { }
}

async function toggleKillSwitch() {
    const btn = document.getElementById('kill-switch-btn');
    const currentlyKilled = btn.classList.contains('killed');

    if (!confirm(currentlyKilled ? "Re-arm system for autonomous trading?" : "EMERGENCY STOP: Disarm all autonomous trading?")) return;

    try {
        await fetch(`${API_BASE}/kill-switch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: !currentlyKilled })
        });
        fetchKillStatus();
    } catch (e) {
        alert("Action failed!");
    }
}

document.getElementById('kill-switch-btn').addEventListener('click', toggleKillSwitch);

import React, { useState, useEffect, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { Shield, Activity, Zap, Terminal, AlertTriangle, Play, Pause, Power, DollarSign } from 'lucide-react';

const API_URL = "http://localhost:8000";

const Dashboard = () => {
    const [status, setStatus] = useState(null);
    const [logs, setLogs] = useState([]);
    const [trades, setTrades] = useState([]);
    const [activeTab, setActiveTab] = useState('overview');

    // Polling Effect
    useEffect(() => {
        const fetchData = async () => {
            try {
                // Fetch Status
                const statusRes = await fetch(`${API_URL}/status`);
                if (statusRes.ok) setStatus(await statusRes.json());

                // Fetch Logs
                const logsRes = await fetch(`${API_URL}/logs?lines=20`);
                if (logsRes.ok) setLogs(await logsRes.json());

                // Fetch Trades
                const tradesRes = await fetch(`${API_URL}/trades`);
                if (tradesRes.ok) setTrades(await tradesRes.json());

            } catch (e) {
                console.error("API Error", e);
            }
        };

        const interval = setInterval(fetchData, 2000); // 2s polling
        fetchData();
        return () => clearInterval(interval);
    }, []);

    const sendCommand = async (action) => {
        try {
            if (!confirm(`CONFIRM ACTION: ${action}?`)) return;

            await fetch(`${API_URL}/control`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-AEGIS-KEY': 'aegis_local_dev' }, // Key exposed for demo
                body: JSON.stringify({ action: action, secret: "demo" })
            });
            alert(`Signal SENT: ${action}`);
        } catch (e) {
            alert(`Failed: ${e}`);
        }
    };

    if (!status) return <div className="min-h-screen flex items-center justify-center text-neon-blue animate-pulse">CONNECTING TO AEGIS CORE...</div>;

    return (
        <div className="min-h-screen bg-cyber-black text-gray-300 font-mono p-6">
            {/* Header */}
            <header className="flex justify-between items-center mb-8 border-b border-gray-800 pb-4">
                <div className="flex items-center gap-3">
                    <Shield className="w-8 h-8 text-neon-blue" />
                    <div>
                        <h1 className="text-2xl font-bold text-white tracking-wider">AEGIS <span className="text-neon-blue">SENTINEL</span></h1>
                        <div className="text-xs text-gray-500">AUTONOMOUS TRADING PROTOCOL // PHASE 60</div>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <div className={`px-3 py-1 rounded border ${status.status === 'ACTIVE' ? 'border-neon-green text-neon-green' : 'border-red-500 text-red-500'}`}>
                        {status.status || "OFFLINE"}
                    </div>
                    <div className="text-xs text-gray-500">{new Date().toLocaleTimeString()}</div>
                </div>
            </header>

            {/* Grid Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* Left Col: Stats & Controls */}
                <div className="space-y-6">
                    {/* Main Control Panel */}
                    <div className="bg-cyber-gray p-4 rounded-lg border border-gray-800">
                        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                            <Zap className="w-5 h-5 text-yellow-400" /> COMMAND CENTER
                        </h2>
                        <div className="grid grid-cols-2 gap-3">
                            <button onClick={() => sendCommand('PAUSE')} className="p-3 bg-gray-800 hover:bg-gray-700 rounded border border-gray-600 flex items-center justify-center gap-2">
                                <Pause className="w-4 h-4" /> PAUSE
                            </button>
                            <button onClick={() => sendCommand('RESUME')} className="p-3 bg-gray-800 hover:bg-gray-700 rounded border border-gray-600 flex items-center justify-center gap-2 text-neon-green">
                                <Play className="w-4 h-4" /> RESUME
                            </button>
                            <button onClick={() => sendCommand('PANIC_SELL')} className="col-span-2 p-3 bg-red-900/20 hover:bg-red-900/40 border border-red-500 text-red-500 rounded flex items-center justify-center gap-2 font-bold animate-pulse">
                                <AlertTriangle className="w-5 h-5" /> EMERGENCY LIQUIDATION
                            </button>
                        </div>
                    </div>

                    {/* DNA Stats */}
                    <div className="bg-cyber-gray p-4 rounded-lg border border-gray-800">
                        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                            <Activity className="w-5 h-5 text-neon-pink" /> DNA EVOLUTION
                        </h2>
                        <div className="space-y-2 text-sm">
                            <div className="flex justify-between"><span>Generation:</span> <span className="text-white">Gen-42 (Darwin)</span></div>
                            <div className="flex justify-between"><span>Win Rate:</span> <span className="text-neon-green">68.4%</span></div>
                            <div className="flex justify-between"><span>Sharpe:</span> <span className="text-neon-blue">2.14</span></div>
                            <div className="flex justify-between"><span>Mode:</span> <span className="text-yellow-400">DYNAMIC (Spot/Fut)</span></div>
                        </div>
                    </div>
                </div>

                {/* Center Col: Charts & Activity */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Chart Placeholder */}
                    <div className="bg-cyber-gray p-4 rounded-lg border border-gray-800 h-64">
                        <h2 className="text-sm font-bold text-gray-400 mb-2">EQUITY CURVE (SIMULATED)</h2>
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={[{ n: 1, v: 1000 }, { n: 2, v: 1050 }, { n: 3, v: 1030 }, { n: 4, v: 1100 }, { n: 5, v: 1200 }]}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                <XAxis dataKey="n" hide />
                                <YAxis stroke="#555" />
                                <Tooltip contentStyle={{ backgroundColor: '#1c1c24', border: '1px solid #333' }} />
                                <Line type="monotone" dataKey="v" stroke="#00f3ff" strokeWidth={2} dot={false} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>

                    {/* Live Logs */}
                    <div className="bg-black p-4 rounded-lg border border-gray-800 h-64 overflow-hidden flex flex-col">
                        <h2 className="text-sm font-bold text-gray-400 mb-2 flex items-center gap-2">
                            <Terminal className="w-4 h-4" /> SYSTEM LOGS (LIVE)
                        </h2>
                        <div className="flex-1 overflow-y-auto space-y-1 text-xs font-mono text-green-400/80 p-2">
                            {logs.map((log, i) => (
                                <div key={i} className="border-b border-gray-900 pb-1">{log}</div>
                            ))}
                            {logs.length === 0 && <div className="text-gray-600">Waiting for logs...</div>}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;

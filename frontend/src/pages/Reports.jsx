import { useState, useEffect, useCallback, useRef } from 'react';
import { useApp } from '../contexts/AppContext';
import { getReports, getReport, getAgentStatus } from '../api';
import {
    FileBarChart2,
    Loader2,
    Calendar,
    TrendingUp,
    TrendingDown,
    Minus,
    AlertTriangle,
    Sparkles,
    ChevronRight,
    RefreshCw,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// ─── Polish month names ───
const MONTH_NAMES = [
    'Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj', 'Czerwiec',
    'Lipiec', 'Sierpień', 'Wrzesień', 'Październik', 'Listopad', 'Grudzień',
];

const REPORT_TYPES = [
    { value: 'monthly', label: 'Miesięczny', icon: Calendar },
    { value: 'weekly', label: 'Tygodniowy', icon: TrendingUp },
    { value: 'health', label: 'Zdrowie konta', icon: AlertTriangle },
];

function formatPeriodLabel(label) {
    if (!label) return '';
    if (label.startsWith('week-')) return `Tydzień ${label.slice(5)}`;
    if (label.startsWith('health-')) return `Zdrowie ${label.slice(7)}`;
    const [y, m] = label.split('-');
    const idx = parseInt(m) - 1;
    if (idx >= 0 && idx < 12) return `${MONTH_NAMES[idx]} ${y}`;
    return label;
}

import { markdownComponents } from '../components/MarkdownComponents';

// ─── Structural sections ───

function DeltaIndicator({ value, invertColor = false }) {
    if (value === null || value === undefined) return <span style={{ color: 'rgba(255,255,255,0.3)' }}>—</span>;
    const isPositive = value > 0;
    const isGood = invertColor ? !isPositive : isPositive;
    const color = Math.abs(value) < 1 ? 'rgba(255,255,255,0.4)' : isGood ? '#4ADE80' : '#F87171';
    const Icon = value > 0 ? TrendingUp : value < 0 ? TrendingDown : Minus;
    return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, color, fontSize: 12, fontWeight: 500 }}>
            <Icon size={12} />
            {value > 0 ? '+' : ''}{value}%
        </span>
    );
}

function KpiCard({ label, current, previous, delta, invertColor = false }) {
    return (
        <div className="v2-card" style={{ padding: '14px 16px', flex: '1 1 0' }}>
            <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>
                {label}
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, fontFamily: 'Syne', color: '#F0F0F0' }}>
                {current}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                <DeltaIndicator value={delta} invertColor={invertColor} />
                {previous !== undefined && (
                    <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>
                        vs {previous}
                    </span>
                )}
            </div>
        </div>
    );
}

function MonthComparisonSection({ data }) {
    if (!data || data.note) return null;
    const c = data.current || {};
    const p = data.previous || {};
    const d = data.deltas || {};

    return (
        <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 14, fontWeight: 600, fontFamily: 'Syne', color: '#fff', marginBottom: 10 }}>
                Porownanie miesiac do miesiaca
            </div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', marginBottom: 12 }}>
                {data.period?.label} vs {data.previous_period?.label}
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <KpiCard label="Wydatki" current={`${c.cost_usd} PLN`} previous={`${p.cost_usd}`} delta={d.cost_usd_pct} invertColor />
                <KpiCard label="Klikniecia" current={c.clicks} previous={p.clicks} delta={d.clicks_pct} />
                <KpiCard label="Konwersje" current={c.conversions} previous={p.conversions} delta={d.conversions_pct} />
                <KpiCard label="CPA" current={`${c.cpa} PLN`} previous={`${p.cpa}`} delta={d.cpa_pct} invertColor />
                <KpiCard label="ROAS" current={c.roas} previous={p.roas} delta={d.roas_pct} />
            </div>
        </div>
    );
}

function CampaignDetailSection({ data }) {
    if (!data || !Array.isArray(data) || data.length === 0) return null;
    const hasPrev = data.some(c => c.cost_delta_pct !== undefined);
    const cellStyle = { padding: '6px 8px', borderBottom: '1px solid rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.6)', textAlign: 'right' };
    const headers = ['Kampania', 'Status', 'Budzet/d', 'Wydatki', ...(hasPrev ? ['m/m'] : []), 'Konw.', ...(hasPrev ? ['m/m'] : []), 'CPA', 'ROAS', 'IS%'];
    return (
        <div className="v2-card" style={{ padding: 16, marginBottom: 20, overflowX: 'auto' }}>
            <div style={{ fontSize: 14, fontWeight: 600, fontFamily: 'Syne', color: '#fff', marginBottom: 12 }}>
                Kampanie
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                    <tr>
                        {headers.map(h => (
                            <th key={h} style={{
                                textAlign: h === 'Kampania' ? 'left' : 'right', padding: '6px 8px',
                                borderBottom: '1px solid rgba(255,255,255,0.1)',
                                fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase',
                            }}>{h}</th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {data.map((c, i) => (
                        <tr key={i}>
                            <td style={{ ...cellStyle, color: '#F0F0F0', fontWeight: 500, textAlign: 'left', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.name}</td>
                            <td style={cellStyle}>
                                <span style={{
                                    fontSize: 10, padding: '2px 8px', borderRadius: 999,
                                    background: c.status === 'ENABLED' ? 'rgba(74,222,128,0.12)' : 'rgba(255,255,255,0.06)',
                                    color: c.status === 'ENABLED' ? '#4ADE80' : 'rgba(255,255,255,0.4)',
                                }}>{c.status}</span>
                            </td>
                            <td style={cellStyle}>{c.daily_budget_usd}</td>
                            <td style={{ ...cellStyle, color: '#F0F0F0', fontWeight: 500 }}>{c.cost_usd ?? c.cost_30d_usd}</td>
                            {hasPrev && <td style={cellStyle}><DeltaIndicator value={c.cost_delta_pct} invertColor /></td>}
                            <td style={cellStyle}>{c.conversions ?? c.conversions_30d}</td>
                            {hasPrev && <td style={cellStyle}><DeltaIndicator value={c.conv_delta_pct} /></td>}
                            <td style={cellStyle}>{c.cpa ?? c.cpa_30d}</td>
                            <td style={cellStyle}>{c.roas ?? c.roas_30d}</td>
                            <td style={cellStyle}>{c.impression_share}%</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function ChangeHistorySection({ data }) {
    if (!data || data.total_changes === 0) return null;
    return (
        <div className="v2-card" style={{ padding: 16, marginBottom: 20 }}>
            <div style={{ fontSize: 14, fontWeight: 600, fontFamily: 'Syne', color: '#fff', marginBottom: 12 }}>
                Zmiany na koncie ({data.total_changes})
            </div>
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 14 }}>
                {data.by_operation && Object.entries(data.by_operation).map(([op, cnt]) => (
                    <div key={op} style={{ fontSize: 12 }}>
                        <span style={{ color: 'rgba(255,255,255,0.4)' }}>{op}: </span>
                        <span style={{ color: '#F0F0F0', fontWeight: 500 }}>{cnt}</span>
                    </div>
                ))}
            </div>
            {data.by_resource_type && (
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
                    {Object.entries(data.by_resource_type).map(([type, cnt]) => (
                        <span key={type} style={{
                            fontSize: 11, padding: '3px 10px', borderRadius: 999,
                            background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.6)',
                            border: '1px solid rgba(255,255,255,0.08)',
                        }}>
                            {type}: {cnt}
                        </span>
                    ))}
                </div>
            )}
            {data.notable && data.notable.length > 0 && (
                <div>
                    <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginBottom: 6 }}>
                        Ostatnie zmiany
                    </div>
                    {data.notable.slice(0, 8).map((n, i) => (
                        <div key={i} style={{
                            display: 'flex', gap: 10, alignItems: 'center', padding: '5px 0',
                            borderBottom: '1px solid rgba(255,255,255,0.04)', fontSize: 12,
                        }}>
                            <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: 11, minWidth: 100 }}>{n.date}</span>
                            <span style={{
                                fontSize: 10, padding: '1px 6px', borderRadius: 4,
                                background: n.operation === 'CREATE' ? 'rgba(74,222,128,0.12)' :
                                    n.operation === 'REMOVE' ? 'rgba(248,113,113,0.12)' : 'rgba(79,142,247,0.12)',
                                color: n.operation === 'CREATE' ? '#4ADE80' :
                                    n.operation === 'REMOVE' ? '#F87171' : '#4F8EF7',
                            }}>{n.operation}</span>
                            <span style={{ color: 'rgba(255,255,255,0.5)' }}>{n.type}</span>
                            <span style={{ color: '#F0F0F0' }}>{n.name}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function ChangeImpactSection({ data }) {
    if (!data || !Array.isArray(data) || data.length === 0) return null;
    return (
        <div className="v2-card" style={{ padding: 16, marginBottom: 20 }}>
            <div style={{ fontSize: 14, fontWeight: 600, fontFamily: 'Syne', color: '#fff', marginBottom: 12 }}>
                Wplyw zmian na wyniki
            </div>
            {data.map((item, i) => (
                <div key={i} style={{
                    padding: '10px 0', borderBottom: i < data.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none',
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                        <span style={{
                            fontSize: 10, padding: '2px 8px', borderRadius: 999,
                            background: item.change_type === 'budget_change' ? 'rgba(251,191,36,0.12)' :
                                item.change_type === 'bidding_change' ? 'rgba(123,92,224,0.12)' : 'rgba(79,142,247,0.12)',
                            color: item.change_type === 'budget_change' ? '#FBBF24' :
                                item.change_type === 'bidding_change' ? '#7B5CE0' : '#4F8EF7',
                        }}>
                            {item.change_type === 'budget_change' ? 'Budzet' :
                                item.change_type === 'bidding_change' ? 'Bidding' : 'Status'}
                        </span>
                        <span style={{ fontSize: 12, color: '#F0F0F0', fontWeight: 500 }}>{item.entity_name}</span>
                        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>{item.change_date}</span>
                    </div>
                    <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.6)', marginBottom: 4 }}>
                        Zmienione: {item.changed_fields?.join(', ')}
                    </div>
                    <div style={{ fontSize: 13, color: '#4F8EF7', fontWeight: 500 }}>
                        {item.impact_summary}
                    </div>
                    <div style={{ display: 'flex', gap: 20, marginTop: 6, fontSize: 11 }}>
                        <div>
                            <span style={{ color: 'rgba(255,255,255,0.3)' }}>Przed: </span>
                            <span style={{ color: 'rgba(255,255,255,0.6)' }}>
                                {item.before_7d?.cost_usd} PLN, {item.before_7d?.conversions} konw.
                            </span>
                        </div>
                        <div>
                            <span style={{ color: 'rgba(255,255,255,0.3)' }}>Po: </span>
                            <span style={{ color: 'rgba(255,255,255,0.6)' }}>
                                {item.after_7d?.cost_usd} PLN, {item.after_7d?.conversions} konw.
                            </span>
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
}

function BudgetPacingSection({ data }) {
    if (!data || !data.campaigns || data.campaigns.length === 0) return null;
    return (
        <div className="v2-card" style={{ padding: 16, marginBottom: 20 }}>
            <div style={{ fontSize: 14, fontWeight: 600, fontFamily: 'Syne', color: '#fff', marginBottom: 12 }}>
                Realizacja budzetow
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                {data.campaigns.map((c, i) => {
                    const statusColor = c.status === 'on_track' ? '#4ADE80' :
                        c.status === 'underspend' ? '#FBBF24' : '#F87171';
                    return (
                        <div key={i} style={{
                            flex: '1 1 200px', maxWidth: 280, padding: '10px 14px',
                            background: 'rgba(255,255,255,0.03)', borderRadius: 10,
                            border: '1px solid rgba(255,255,255,0.07)',
                        }}>
                            <div style={{ fontSize: 12, color: '#F0F0F0', fontWeight: 500, marginBottom: 6, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {c.campaign}
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
                                <span style={{ color: 'rgba(255,255,255,0.4)' }}>Wydano</span>
                                <span style={{ color: '#F0F0F0' }}>{c.actual_spend_usd} PLN</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 6 }}>
                                <span style={{ color: 'rgba(255,255,255,0.4)' }}>Oczekiwano</span>
                                <span style={{ color: 'rgba(255,255,255,0.5)' }}>{c.expected_spend_usd} PLN</span>
                            </div>
                            <div style={{
                                height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.08)', overflow: 'hidden',
                            }}>
                                <div style={{
                                    height: '100%', borderRadius: 2, background: statusColor,
                                    width: `${Math.min(c.pacing_pct, 150)}%`, transition: 'width 0.3s',
                                }} />
                            </div>
                            <div style={{ fontSize: 11, color: statusColor, fontWeight: 500, marginTop: 4, textAlign: 'right' }}>
                                {c.pacing_pct}%
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

// ─── Status pill ───
function StatusPill({ status }) {
    const config = {
        completed: { bg: 'rgba(74,222,128,0.12)', color: '#4ADE80', border: 'rgba(74,222,128,0.25)', label: 'Gotowy' },
        generating: { bg: 'rgba(123,92,224,0.12)', color: '#7B5CE0', border: 'rgba(123,92,224,0.25)', label: 'Generowanie...' },
        failed: { bg: 'rgba(248,113,113,0.12)', color: '#F87171', border: 'rgba(248,113,113,0.25)', label: 'Blad' },
    };
    const s = config[status] || config.failed;
    return (
        <span style={{
            fontSize: 10, padding: '2px 10px', borderRadius: 999,
            background: s.bg, color: s.color, border: `1px solid ${s.border}`,
        }}>
            {status === 'generating' && <Loader2 size={10} className="animate-spin" style={{ marginRight: 4, verticalAlign: 'middle' }} />}
            {s.label}
        </span>
    );
}

function TokenUsageBadge({ usage, model }) {
    if (!usage && !model) return null;
    const input = usage?.input_tokens || 0;
    const output = usage?.output_tokens || 0;
    const cacheRead = usage?.cache_read_tokens || 0;
    const total = input + output + cacheRead;
    const cost = usage?.total_cost_usd;
    const durationSec = usage?.duration_ms ? (usage.duration_ms / 1000).toFixed(1) : null;

    return (
        <div style={{
            display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
            padding: '8px 14px', borderRadius: 10,
            background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
            fontSize: 11, color: 'rgba(255,255,255,0.5)',
        }}>
            {model && (
                <span style={{
                    padding: '2px 8px', borderRadius: 999,
                    background: 'rgba(123,92,224,0.12)', color: '#7B5CE0',
                    border: '1px solid rgba(123,92,224,0.25)', fontSize: 10,
                }}>{model}</span>
            )}
            {usage && (
                <>
                    <span>
                        <span style={{ color: 'rgba(255,255,255,0.3)' }}>in: </span>
                        <span style={{ color: '#F0F0F0', fontWeight: 500 }}>{input.toLocaleString()}</span>
                    </span>
                    <span>
                        <span style={{ color: 'rgba(255,255,255,0.3)' }}>out: </span>
                        <span style={{ color: '#F0F0F0', fontWeight: 500 }}>{output.toLocaleString()}</span>
                    </span>
                    {cacheRead > 0 && (
                        <span>
                            <span style={{ color: 'rgba(255,255,255,0.3)' }}>cache: </span>
                            <span style={{ color: '#4F8EF7' }}>{cacheRead.toLocaleString()}</span>
                        </span>
                    )}
                    <span>
                        <span style={{ color: 'rgba(255,255,255,0.3)' }}>total: </span>
                        <span style={{ color: '#F0F0F0', fontWeight: 500 }}>{total.toLocaleString()}</span>
                    </span>
                    {durationSec && (
                        <span style={{ color: 'rgba(255,255,255,0.3)' }}>{durationSec}s</span>
                    )}
                    {cost != null && cost > 0 && (
                        <span style={{ color: '#FBBF24' }}>${cost.toFixed(4)}</span>
                    )}
                </>
            )}
        </div>
    );
}

// ─── Main page ───
export default function Reports() {
    const { selectedClientId, showToast } = useApp();
    const [reports, setReports] = useState([]);
    const [activeReport, setActiveReport] = useState(null);
    const [generating, setGenerating] = useState(false);
    const [streamingText, setStreamingText] = useState('');
    const [streamingData, setStreamingData] = useState(null);
    const [statusMsg, setStatusMsg] = useState('');
    const [error, setError] = useState(null);
    const [agentAvailable, setAgentAvailable] = useState(null);
    const [loadingReport, setLoadingReport] = useState(false);
    const [loadingList, setLoadingList] = useState(false);
    const [progress, setProgress] = useState({ pct: 0, label: '' });
    const [modelName, setModelName] = useState(null);
    const [tokenUsage, setTokenUsage] = useState(null);
    const [reportType, setReportType] = useState('monthly');
    const streamRef = useRef(null);

    // Load a specific report
    const loadReport = useCallback(async (reportId) => {
        setLoadingReport(true);
        try {
            const data = await getReport(reportId);
            setActiveReport(data);
        } catch (err) {
            showToast('Nie udalo sie zaladowac raportu', 'error');
        }
        setLoadingReport(false);
    }, [showToast]);

    // Load report list (and auto-select most recent on first load)
    const loadReports = useCallback(async (autoSelect = false) => {
        if (!selectedClientId) return;
        setLoadingList(true);
        try {
            const data = await getReports(selectedClientId);
            const list = data.reports || [];
            setReports(list);
            // Auto-select most recent completed report if nothing is active
            if (autoSelect && list.length > 0 && !generating) {
                const recent = list.find(r => r.status === 'completed') || list[0];
                if (recent) loadReport(recent.id);
            }
        } catch (err) {
            console.error('Failed to load reports:', err);
        }
        setLoadingList(false);
    }, [selectedClientId, generating, loadReport]);

    useEffect(() => {
        loadReports(true);
    }, [loadReports]);

    // Check Claude availability
    useEffect(() => {
        getAgentStatus()
            .then((data) => setAgentAvailable(data.available))
            .catch(() => setAgentAvailable(false));
    }, []);

    // Generate report via SSE
    const handleGenerate = async () => {
        if (!selectedClientId || generating) return;
        setGenerating(true);
        setStreamingText('');
        setStreamingData(null);
        setStatusMsg('');
        setError(null);
        setActiveReport(null);
        setProgress({ pct: 0, label: 'Rozpoczynam...' });
        setModelName(null);
        setTokenUsage(null);

        try {
            const response = await fetch(`/api/v1/reports/generate?client_id=${selectedClientId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ report_type: reportType }),
            });

            if (!response.ok) {
                if (response.status === 401) {
                    window.dispatchEvent(new CustomEvent('auth:unauthorized'));
                }
                throw new Error(`Blad serwera: ${response.status}`);
            }

            const reader = response.body.getReader();
            streamRef.current = reader;
            const decoder = new TextDecoder();
            let buffer = '';
            let fullContent = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split('\n\n');
                buffer = parts.pop();

                for (const part of parts) {
                    const lines = part.trim().split('\n');
                    let eventType = 'delta';
                    let eventData = '';

                    for (const line of lines) {
                        if (line.startsWith('event: ')) {
                            eventType = line.slice(7).trim();
                        } else if (line.startsWith('data: ')) {
                            eventData = line.slice(6).replace(/\\n/g, '\n');
                        }
                    }

                    if (eventType === 'progress') {
                        try {
                            const p = JSON.parse(eventData);
                            setProgress({ pct: p.pct || 0, label: p.label || '' });
                        } catch {}
                    } else if (eventType === 'model') {
                        setModelName(eventData);
                    } else if (eventType === 'usage') {
                        try {
                            setTokenUsage(JSON.parse(eventData));
                        } catch {}
                    } else if (eventType === 'status') {
                        setStatusMsg(eventData);
                    } else if (eventType === 'data_ready') {
                        try {
                            const parsed = JSON.parse(eventData);
                            setStreamingData(parsed.report_data);
                        } catch {}
                    } else if (eventType === 'delta') {
                        fullContent += eventData;
                        setStreamingText(fullContent);
                    } else if (eventType === 'error') {
                        setError(eventData);
                    } else if (eventType === 'report_id') {
                        // Load completed report
                        const reportId = parseInt(eventData);
                        if (reportId) {
                            await loadReport(reportId);
                            await loadReports();
                        }
                    } else if (eventType === 'done') {
                        // finished
                    }
                }
            }
        } catch (err) {
            setError(err.message);
        }

        setGenerating(false);
        setStatusMsg('');
    };

    if (!selectedClientId) {
        return (
            <div style={{ maxWidth: 1400, margin: '0 auto' }}>
                <div style={{ textAlign: 'center', padding: '80px 20px', color: 'rgba(255,255,255,0.3)' }}>
                    <FileBarChart2 size={40} style={{ marginBottom: 12, opacity: 0.4 }} />
                    <p style={{ fontSize: 14, margin: 0 }}>Wybierz klienta w sidebar</p>
                </div>
            </div>
        );
    }

    return (
        <div style={{ maxWidth: 1400, margin: '0 auto' }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <FileBarChart2 size={22} style={{ color: '#7B5CE0' }} />
                    <h1 style={{ fontSize: 22, fontWeight: 700, fontFamily: 'Syne', color: '#fff', margin: 0 }}>
                        Raporty
                    </h1>
                    {agentAvailable !== null && (
                        <span style={{
                            fontSize: 11, padding: '2px 10px', borderRadius: 999,
                            background: agentAvailable ? 'rgba(74,222,128,0.12)' : 'rgba(248,113,113,0.12)',
                            color: agentAvailable ? '#4ADE80' : '#F87171',
                            border: `1px solid ${agentAvailable ? 'rgba(74,222,128,0.25)' : 'rgba(248,113,113,0.25)'}`,
                        }}>
                            {agentAvailable ? 'Claude dostepny' : 'Claude niedostepny'}
                        </span>
                    )}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {/* Report type pills */}
                    <div style={{ display: 'flex', gap: 4 }}>
                        {REPORT_TYPES.map(rt => {
                            const Icon = rt.icon;
                            const active = reportType === rt.value;
                            return (
                                <button
                                    key={rt.value}
                                    onClick={() => setReportType(rt.value)}
                                    disabled={generating}
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: 5,
                                        padding: '7px 14px', borderRadius: 999, fontSize: 12, fontWeight: 500,
                                        border: `1px solid ${active ? 'rgba(79,142,247,0.5)' : 'rgba(255,255,255,0.1)'}`,
                                        background: active ? 'rgba(79,142,247,0.12)' : 'rgba(255,255,255,0.04)',
                                        color: active ? '#4F8EF7' : 'rgba(255,255,255,0.5)',
                                        cursor: generating ? 'not-allowed' : 'pointer',
                                        transition: 'all 0.15s',
                                    }}
                                >
                                    <Icon size={12} />{rt.label}
                                </button>
                            );
                        })}
                    </div>
                    <button
                        onClick={handleGenerate}
                        disabled={generating}
                        style={{
                            display: 'flex', alignItems: 'center', gap: 8,
                            padding: '10px 20px', borderRadius: 10, border: 'none',
                            background: generating ? 'rgba(123,92,224,0.2)' : 'linear-gradient(135deg, #4F8EF7, #7B5CE0)',
                            color: '#fff', fontSize: 13, fontWeight: 600, cursor: generating ? 'not-allowed' : 'pointer',
                            transition: 'all 0.15s', opacity: generating ? 0.7 : 1,
                        }}
                    >
                        {generating ? (
                            <><Loader2 size={14} className="animate-spin" /> Generuje...</>
                        ) : (
                            <><Sparkles size={14} /> Generuj</>
                        )}
                    </button>
                </div>
            </div>

            <div style={{ display: 'flex', gap: 20 }}>
                {/* Left: Report history */}
                <div style={{ flex: '0 0 260px' }}>
                    <div style={{
                        fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)',
                        textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 10,
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    }}>
                        Zapisane raporty
                        <button onClick={loadReports} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2 }}>
                            <RefreshCw size={11} style={{ color: 'rgba(255,255,255,0.3)' }} />
                        </button>
                    </div>

                    {loadingList && reports.length === 0 && (
                        <div style={{ textAlign: 'center', padding: 20 }}>
                            <Loader2 size={16} className="animate-spin" style={{ color: 'rgba(255,255,255,0.3)' }} />
                        </div>
                    )}

                    {reports.length === 0 && !generating && !loadingList && (
                        <div style={{
                            padding: 20, textAlign: 'center', color: 'rgba(255,255,255,0.3)',
                            fontSize: 12, background: 'rgba(255,255,255,0.02)', borderRadius: 10,
                            border: '1px solid rgba(255,255,255,0.05)',
                        }}>
                            Brak zapisanych raportow
                        </div>
                    )}

                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        {reports.map((r) => {
                            const isActive = activeReport?.id === r.id;
                            return (
                                <button
                                    key={r.id}
                                    onClick={() => loadReport(r.id)}
                                    style={{
                                        display: 'flex', flexDirection: 'column', gap: 4,
                                        padding: '10px 14px', borderRadius: 10, textAlign: 'left',
                                        border: `1px solid ${isActive ? 'rgba(79,142,247,0.4)' : 'rgba(255,255,255,0.07)'}`,
                                        background: isActive ? 'rgba(79,142,247,0.08)' : 'rgba(255,255,255,0.03)',
                                        cursor: 'pointer', transition: 'all 0.15s',
                                    }}
                                    onMouseEnter={(e) => { if (!isActive) { e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; } }}
                                    onMouseLeave={(e) => { if (!isActive) { e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; } }}
                                >
                                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                        <span style={{ fontSize: 13, color: '#F0F0F0', fontWeight: 500 }}>
                                            {formatPeriodLabel(r.period_label)}
                                        </span>
                                        <ChevronRight size={12} style={{ color: 'rgba(255,255,255,0.2)' }} />
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                        {r.report_type && r.report_type !== 'monthly' && (
                                            <span style={{
                                                fontSize: 9, padding: '1px 6px', borderRadius: 999,
                                                background: r.report_type === 'weekly' ? 'rgba(79,142,247,0.12)' : 'rgba(251,191,36,0.12)',
                                                color: r.report_type === 'weekly' ? '#4F8EF7' : '#FBBF24',
                                                border: `1px solid ${r.report_type === 'weekly' ? 'rgba(79,142,247,0.25)' : 'rgba(251,191,36,0.25)'}`,
                                                textTransform: 'uppercase', fontWeight: 600,
                                            }}>
                                                {r.report_type === 'weekly' ? 'tyg.' : 'zdrowie'}
                                            </span>
                                        )}
                                        <StatusPill status={r.status} />
                                        <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)' }}>
                                            {r.created_at ? new Date(r.created_at).toLocaleDateString('pl-PL') : ''}
                                        </span>
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* Main: Report content */}
                <div style={{ flex: 1, minWidth: 0 }}>
                    {/* Generating state */}
                    {generating && (
                        <div>
                            {/* Progress bar */}
                            <div className="v2-card" style={{ padding: '14px 18px', marginBottom: 16 }}>
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                        <Loader2 size={14} className="animate-spin" style={{ color: '#7B5CE0' }} />
                                        <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>{progress.label}</span>
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                        {modelName && (
                                            <span style={{
                                                fontSize: 10, padding: '2px 8px', borderRadius: 999,
                                                background: 'rgba(123,92,224,0.12)', color: '#7B5CE0',
                                                border: '1px solid rgba(123,92,224,0.25)',
                                            }}>{modelName}</span>
                                        )}
                                        <span style={{ fontSize: 13, fontWeight: 600, fontFamily: 'Syne', color: '#F0F0F0' }}>
                                            {progress.pct}%
                                        </span>
                                    </div>
                                </div>
                                <div style={{
                                    height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.08)', overflow: 'hidden',
                                }}>
                                    <div style={{
                                        height: '100%', borderRadius: 2,
                                        background: 'linear-gradient(90deg, #4F8EF7, #7B5CE0)',
                                        width: `${progress.pct}%`,
                                        transition: 'width 0.3s ease',
                                    }} />
                                </div>
                            </div>

                            {/* Show structural data while AI generates */}
                            {streamingData && (
                                <>
                                    <MonthComparisonSection data={streamingData.month_comparison} />
                                    <CampaignDetailSection data={streamingData.campaigns_detail} />
                                    <ChangeHistorySection data={streamingData.change_history} />
                                    <BudgetPacingSection data={streamingData.budget_pacing} />
                                </>
                            )}

                            {/* Streaming AI text */}
                            {streamingText && (
                                <div className="v2-card" style={{ padding: 20 }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                                        <Sparkles size={14} style={{ color: '#7B5CE0' }} />
                                        <span style={{ fontSize: 12, fontWeight: 600, color: '#7B5CE0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                            Analiza AI
                                        </span>
                                    </div>
                                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                                        {streamingText}
                                    </ReactMarkdown>
                                </div>
                            )}

                            {/* Token usage (appears after AI finishes) */}
                            {tokenUsage && (
                                <div style={{ marginTop: 12 }}>
                                    <TokenUsageBadge usage={tokenUsage} model={modelName} />
                                </div>
                            )}
                        </div>
                    )}

                    {/* Error */}
                    {error && !generating && (
                        <div style={{
                            background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.2)',
                            borderRadius: 10, padding: '12px 16px', marginBottom: 16,
                            display: 'flex', alignItems: 'center', gap: 8,
                        }}>
                            <AlertTriangle size={14} style={{ color: '#F87171' }} />
                            <span style={{ fontSize: 13, color: '#F87171' }}>{error}</span>
                        </div>
                    )}

                    {/* Loading specific report */}
                    {loadingReport && (
                        <div style={{ textAlign: 'center', padding: 40 }}>
                            <Loader2 size={24} className="animate-spin" style={{ color: '#4F8EF7' }} />
                        </div>
                    )}

                    {/* Active report view */}
                    {activeReport && !generating && !loadingReport && (
                        <div>
                            {/* Report header */}
                            <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 20, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                                        <Calendar size={14} style={{ color: '#4F8EF7' }} />
                                        <span style={{ fontSize: 18, fontWeight: 700, fontFamily: 'Syne', color: '#fff' }}>
                                            {formatPeriodLabel(activeReport.period_label)}
                                        </span>
                                        <StatusPill status={activeReport.status} />
                                    </div>
                                    <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>
                                        {activeReport.date_from} — {activeReport.date_to}
                                        {activeReport.completed_at && ` · Wygenerowano: ${new Date(activeReport.completed_at).toLocaleString('pl-PL')}`}
                                    </div>
                                </div>
                            </div>

                            {/* Structural sections */}
                            {activeReport.report_data && (
                                <>
                                    <MonthComparisonSection data={activeReport.report_data.month_comparison} />
                                    <CampaignDetailSection data={activeReport.report_data.campaigns_detail} />
                                    <ChangeHistorySection data={activeReport.report_data.change_history} />
                                    <ChangeImpactSection data={activeReport.report_data.change_impact} />
                                    <BudgetPacingSection data={activeReport.report_data.budget_pacing} />
                                </>
                            )}

                            {/* AI Narrative */}
                            {activeReport.ai_narrative && (
                                <div className="v2-card" style={{ padding: 20 }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                                        <Sparkles size={14} style={{ color: '#7B5CE0' }} />
                                        <span style={{ fontSize: 12, fontWeight: 600, color: '#7B5CE0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                            Analiza AI i Rekomendacje
                                        </span>
                                    </div>
                                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                                        {activeReport.ai_narrative}
                                    </ReactMarkdown>
                                </div>
                            )}

                            {/* Token usage from saved report */}
                            {(activeReport.input_tokens || activeReport.model_name) && (
                                <div style={{ marginTop: 12 }}>
                                    <TokenUsageBadge
                                        usage={activeReport.input_tokens ? {
                                            input_tokens: activeReport.input_tokens,
                                            output_tokens: activeReport.output_tokens,
                                            cache_read_tokens: activeReport.cache_read_tokens,
                                            total_cost_usd: activeReport.total_cost_usd,
                                            duration_ms: activeReport.duration_ms,
                                        } : null}
                                        model={activeReport.model_name}
                                    />
                                </div>
                            )}

                            {/* Error message */}
                            {activeReport.error_message && (
                                <div style={{
                                    background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.2)',
                                    borderRadius: 10, padding: '12px 16px', marginTop: 16,
                                }}>
                                    <span style={{ fontSize: 13, color: '#F87171' }}>{activeReport.error_message}</span>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Empty state */}
                    {!generating && !activeReport && !loadingReport && !error && (
                        <div style={{
                            textAlign: 'center', padding: '80px 20px', color: 'rgba(255,255,255,0.3)',
                            background: 'rgba(255,255,255,0.02)', borderRadius: 12,
                            border: '1px solid rgba(255,255,255,0.05)',
                        }}>
                            <FileBarChart2 size={40} style={{ marginBottom: 12, opacity: 0.3 }} />
                            <p style={{ fontSize: 14, margin: '0 0 4px' }}>Wybierz raport z listy lub wygeneruj nowy</p>
                            <p style={{ fontSize: 12, margin: 0 }}>Raport zawiera KPI, porownanie m/m, zmiany i rekomendacje AI</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

import { useState, useEffect } from 'react';
import { useApp } from '../contexts/AppContext';
import api from '../api';
import { getAnomalies, resolveAnomaly } from '../api';
import EmptyState from '../components/EmptyState';
import { Bell, CheckCircle, Loader2, AlertTriangle, TrendingUp, TrendingDown } from 'lucide-react';

const SEVERITY_COLORS = {
    HIGH:   { color: '#F87171', bg: 'rgba(248,113,113,0.1)',  border: 'rgba(248,113,113,0.2)',  label: 'Wysoki'  },
    MEDIUM: { color: '#FBBF24', bg: 'rgba(251,191,36,0.1)',   border: 'rgba(251,191,36,0.2)',   label: 'Średni'  },
    LOW:    { color: '#4F8EF7', bg: 'rgba(79,142,247,0.1)',   border: 'rgba(79,142,247,0.2)',   label: 'Niski'   },
};

const METRICS = [
    { value: 'cost', label: 'Koszt' },
    { value: 'clicks', label: 'Kliknięcia' },
    { value: 'impressions', label: 'Wyświetlenia' },
    { value: 'conversions', label: 'Konwersje' },
    { value: 'ctr', label: 'CTR' },
];

function PillTab({ active, onClick, children }) {
    return (
        <button
            onClick={onClick}
            style={{
                padding: '4px 14px',
                borderRadius: 999,
                fontSize: 12,
                fontWeight: active ? 500 : 400,
                border: `1px solid ${active ? '#4F8EF7' : 'rgba(255,255,255,0.1)'}`,
                background: active ? 'rgba(79,142,247,0.18)' : 'transparent',
                color: active ? 'white' : 'rgba(255,255,255,0.45)',
                cursor: 'pointer',
                transition: 'all 0.15s',
                whiteSpace: 'nowrap',
            }}
        >
            {children}
        </button>
    );
}

function PillButton({ active, onClick, children }) {
    return (
        <button
            onClick={onClick}
            style={{
                padding: '4px 12px',
                borderRadius: 999,
                fontSize: 11,
                fontWeight: 500,
                border: `1px solid ${active ? '#4F8EF7' : 'rgba(255,255,255,0.08)'}`,
                background: active ? 'rgba(79,142,247,0.18)' : 'rgba(255,255,255,0.04)',
                color: active ? 'white' : 'rgba(255,255,255,0.45)',
                cursor: 'pointer',
                transition: 'all 0.15s',
            }}
        >
            {children}
        </button>
    );
}

/* ─── Business Alerts Tab ─── */
function AlertsTab({ selectedClientId, setAlertCount, showToast }) {
    const [tab, setTab] = useState('unresolved');
    const [alerts, setAlerts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [resolving, setResolving] = useState(null);

    const fetchAlerts = async () => {
        if (!selectedClientId) return;
        setLoading(true);
        try {
            const data = await getAnomalies(selectedClientId, tab);
            const list = data.alerts || data || [];
            setAlerts(list);
            if (tab === 'unresolved') setAlertCount(list.length);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAlerts();
    }, [selectedClientId, tab]);

    const handleResolve = async (alertId) => {
        setResolving(alertId);
        try {
            await resolveAnomaly(alertId, selectedClientId);
            showToast('Alert rozwiązany', 'success');
            fetchAlerts();
        } catch (err) {
            showToast('Błąd: ' + err.message, 'error');
        } finally {
            setResolving(null);
        }
    };

    return (
        <>
            {/* Sub-tabs */}
            <div className="flex items-center gap-2" style={{ marginBottom: 16 }}>
                <PillTab active={tab === 'unresolved'} onClick={() => setTab('unresolved')}>
                    Nierozwiązane {tab === 'unresolved' && alerts.length > 0 ? `(${alerts.length})` : ''}
                </PillTab>
                <PillTab active={tab === 'resolved'} onClick={() => setTab('resolved')}>
                    Rozwiązane
                </PillTab>
            </div>

            {loading ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '60px 0' }}>
                    <Loader2 size={28} style={{ color: '#4F8EF7' }} className="animate-spin" />
                </div>
            ) : alerts.length === 0 ? (
                <EmptyState
                    message={tab === 'unresolved' ? 'Brak alertów — wszystko OK!' : 'Brak rozwiązanych alertów'}
                    icon={Bell}
                />
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {alerts.map((alert) => {
                        const sev = SEVERITY_COLORS[alert.severity] || SEVERITY_COLORS.LOW;
                        return (
                            <div key={alert.id} className="v2-card" style={{ padding: '14px 18px' }}>
                                <div className="flex items-start justify-between gap-4">
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                        <div className="flex items-center gap-2" style={{ marginBottom: 6 }}>
                                            <span style={{
                                                fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 999,
                                                background: sev.bg, color: sev.color, border: `1px solid ${sev.border}`,
                                                textTransform: 'uppercase', letterSpacing: '0.05em',
                                            }}>
                                                {sev.label}
                                            </span>
                                            <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                                                {alert.alert_type}
                                            </span>
                                        </div>
                                        <div style={{ fontSize: 13, fontWeight: 500, color: '#F0F0F0', marginBottom: 3 }}>
                                            {alert.title}
                                        </div>
                                        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', lineHeight: 1.5 }}>
                                            {alert.description}
                                        </div>
                                    </div>
                                    {tab === 'unresolved' && (
                                        <button
                                            onClick={() => handleResolve(alert.id)}
                                            disabled={resolving === alert.id}
                                            style={{
                                                display: 'flex', alignItems: 'center', gap: 5,
                                                padding: '5px 12px', borderRadius: 7, fontSize: 12,
                                                background: 'rgba(74,222,128,0.1)',
                                                border: '1px solid rgba(74,222,128,0.25)',
                                                color: '#4ADE80', cursor: 'pointer', flexShrink: 0,
                                                opacity: resolving === alert.id ? 0.5 : 1,
                                            }}
                                        >
                                            {resolving === alert.id
                                                ? <Loader2 size={12} className="animate-spin" />
                                                : <CheckCircle size={12} />
                                            }
                                            Rozwiąż
                                        </button>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </>
    );
}

/* ─── Z-Score Anomaly Detection Tab ─── */
function AnomaliesTab({ selectedClientId }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [metric, setMetric] = useState('cost');
    const [threshold, setThreshold] = useState(2.0);
    const [days, setDays] = useState(90);

    useEffect(() => {
        if (selectedClientId) loadData();
    }, [metric, threshold, days, selectedClientId]);

    async function loadData() {
        setLoading(true);
        setError(null);
        try {
            const result = await api.get('/analytics/anomalies', { params: { metric, threshold, days, client_id: selectedClientId } });
            setData(result);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    return (
        <>
            {/* Controls */}
            <div className="v2-card" style={{ padding: '14px 18px', marginBottom: 16 }}>
                <div className="flex flex-wrap gap-5 items-center">
                    <div>
                        <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Metryka</div>
                        <div className="flex gap-1.5">
                            {METRICS.map(m => (
                                <PillButton key={m.value} active={metric === m.value} onClick={() => setMetric(m.value)}>
                                    {m.label}
                                </PillButton>
                            ))}
                        </div>
                    </div>
                    <div>
                        <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Próg (z-score)</div>
                        <div className="flex gap-1.5">
                            {[1.5, 2.0, 2.5, 3.0].map(t => (
                                <PillButton key={t} active={threshold === t} onClick={() => setThreshold(t)}>
                                    {t}σ
                                </PillButton>
                            ))}
                        </div>
                    </div>
                    <div>
                        <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Okres</div>
                        <div className="flex gap-1.5">
                            {[30, 60, 90].map(d => (
                                <PillButton key={d} active={days === d} onClick={() => setDays(d)}>
                                    {d}d
                                </PillButton>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {loading ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '60px 0' }}>
                    <Loader2 size={28} style={{ color: '#4F8EF7' }} className="animate-spin" />
                </div>
            ) : error ? (
                <div className="v2-card" style={{ padding: 24, textAlign: 'center' }}>
                    <p style={{ color: '#F87171', fontSize: 13, marginBottom: 8 }}>{error}</p>
                    <button onClick={loadData} style={{
                        padding: '5px 14px', borderRadius: 7, fontSize: 12,
                        background: 'rgba(79,142,247,0.15)', border: '1px solid rgba(79,142,247,0.3)',
                        color: '#4F8EF7', cursor: 'pointer',
                    }}>
                        Spróbuj ponownie
                    </button>
                </div>
            ) : (
                <>
                    {/* Stats row */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
                        <div className="v2-card" style={{ padding: '14px 18px', textAlign: 'center' }}>
                            <span style={{ display: 'block', fontSize: 22, fontWeight: 700, color: 'white', fontFamily: 'Syne' }}>
                                {data?.anomalies?.length || 0}
                            </span>
                            <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Anomalie</span>
                        </div>
                        <div className="v2-card" style={{ padding: '14px 18px', textAlign: 'center' }}>
                            <span style={{ display: 'block', fontSize: 22, fontWeight: 700, color: 'white', fontFamily: 'Syne' }}>
                                {data?.mean?.toFixed(1)}
                            </span>
                            <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Średnia</span>
                        </div>
                        <div className="v2-card" style={{ padding: '14px 18px', textAlign: 'center' }}>
                            <span style={{ display: 'block', fontSize: 22, fontWeight: 700, color: 'white', fontFamily: 'Syne' }}>
                                ±{data?.std?.toFixed(1)}
                            </span>
                            <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Odch. std.</span>
                        </div>
                    </div>

                    {/* Anomaly table */}
                    {data?.anomalies?.length > 0 ? (
                        <div className="v2-card" style={{ overflow: 'hidden' }}>
                            <div style={{ overflowX: 'auto' }}>
                                <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
                                    <thead>
                                        <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
                                            <th style={{ textAlign: 'left', padding: '10px 16px', fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Data</th>
                                            <th style={{ textAlign: 'left', padding: '10px 16px', fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Kampania</th>
                                            <th style={{ textAlign: 'right', padding: '10px 16px', fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Wartość</th>
                                            <th style={{ textAlign: 'right', padding: '10px 16px', fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Z-score</th>
                                            <th style={{ textAlign: 'left', padding: '10px 16px', fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Typ</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {data.anomalies.map((a, i) => (
                                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                                <td style={{ padding: '10px 16px', fontFamily: 'monospace', color: 'rgba(255,255,255,0.6)', fontSize: 12 }}>{a.date}</td>
                                                <td style={{ padding: '10px 16px', color: 'rgba(255,255,255,0.5)', fontSize: 12 }}>ID: {a.campaign_id}</td>
                                                <td style={{ padding: '10px 16px', textAlign: 'right', fontFamily: 'monospace', color: 'white', fontWeight: 500, fontSize: 12 }}>{a.value}</td>
                                                <td style={{ padding: '10px 16px', textAlign: 'right' }}>
                                                    <span style={{ fontFamily: 'monospace', fontWeight: 500, fontSize: 12, color: a.z_score > 3 ? '#F87171' : '#FBBF24' }}>
                                                        {a.z_score.toFixed(2)}σ
                                                    </span>
                                                </td>
                                                <td style={{ padding: '10px 16px' }}>
                                                    <span className="flex items-center gap-1" style={{ fontSize: 12, fontWeight: 500, color: a.direction === 'spike' ? '#F87171' : '#4F8EF7' }}>
                                                        {a.direction === 'spike' ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                                                        {a.direction === 'spike' ? 'Skok' : 'Spadek'}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ) : (
                        <div className="v2-card" style={{ padding: '48px 24px', textAlign: 'center' }}>
                            <AlertTriangle size={28} style={{ color: 'rgba(255,255,255,0.15)', margin: '0 auto 10px' }} />
                            <p style={{ color: 'rgba(255,255,255,0.45)', fontSize: 13 }}>Brak anomalii przy progu {threshold}σ</p>
                            <p style={{ color: 'rgba(255,255,255,0.25)', fontSize: 11, marginTop: 4 }}>Spróbuj obniżyć próg lub zwiększyć okres</p>
                        </div>
                    )}
                </>
            )}
        </>
    );
}

/* ─── Main Page ─── */
export default function Alerts() {
    const { selectedClientId, setAlertCount, showToast } = useApp();
    const [mainTab, setMainTab] = useState('alerts');

    if (!selectedClientId) return <EmptyState message="Wybierz klienta" />;

    return (
        <div style={{ maxWidth: 1000 }}>
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Monitoring
                    </h1>
                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                        Alerty biznesowe i wykrywanie anomalii statystycznych
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <PillTab active={mainTab === 'alerts'} onClick={() => setMainTab('alerts')}>
                        <span className="flex items-center gap-1.5">
                            <Bell size={12} />
                            Alerty
                        </span>
                    </PillTab>
                    <PillTab active={mainTab === 'anomalies'} onClick={() => setMainTab('anomalies')}>
                        <span className="flex items-center gap-1.5">
                            <AlertTriangle size={12} />
                            Anomalie (z-score)
                        </span>
                    </PillTab>
                </div>
            </div>

            {mainTab === 'alerts' ? (
                <AlertsTab
                    selectedClientId={selectedClientId}
                    setAlertCount={setAlertCount}
                    showToast={showToast}
                />
            ) : (
                <AnomaliesTab selectedClientId={selectedClientId} />
            )}
        </div>
    );
}

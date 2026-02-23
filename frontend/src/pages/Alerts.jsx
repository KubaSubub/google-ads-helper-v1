import { useState, useEffect } from 'react';
import { useApp } from '../contexts/AppContext';
import { getAnomalies, resolveAnomaly } from '../api';
import EmptyState from '../components/EmptyState';
import { Bell, CheckCircle, Loader2 } from 'lucide-react';

const SEVERITY_COLORS = {
    HIGH:   { color: '#F87171', bg: 'rgba(248,113,113,0.1)',  border: 'rgba(248,113,113,0.2)',  label: 'Wysoki'  },
    MEDIUM: { color: '#FBBF24', bg: 'rgba(251,191,36,0.1)',   border: 'rgba(251,191,36,0.2)',   label: 'Średni'  },
    LOW:    { color: '#4F8EF7', bg: 'rgba(79,142,247,0.1)',   border: 'rgba(79,142,247,0.2)',   label: 'Niski'   },
}

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
    )
}

export default function Alerts() {
    const { selectedClientId, setAlertCount, showToast } = useApp();
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

    if (!selectedClientId) return <EmptyState message="Wybierz klienta" />;

    return (
        <div style={{ maxWidth: 900 }}>
            {/* Header + pill tabs */}
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Alerty
                    </h1>
                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                        Monitoring anomalii i odchyleń
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <PillTab active={tab === 'unresolved'} onClick={() => setTab('unresolved')}>
                        Nierozwiązane {tab === 'unresolved' && alerts.length > 0 ? `(${alerts.length})` : ''}
                    </PillTab>
                    <PillTab active={tab === 'resolved'} onClick={() => setTab('resolved')}>
                        Rozwiązane
                    </PillTab>
                </div>
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
                        const sev = SEVERITY_COLORS[alert.severity] || SEVERITY_COLORS.LOW
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
                        )
                    })}
                </div>
            )}
        </div>
    );
}

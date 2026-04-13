// AnomalyAlertsCard — top 3 unresolved anomalies on the Dashboard
// Closes the workflow gap "specjalista nie widzi CVR spadł 30% w nocy od razu".
import { useState, useEffect } from 'react'
import { AlertTriangle, ChevronRight, ShieldAlert } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { getAnomalies } from '../../../api'
import { useApp } from '../../../contexts/AppContext'
import { C, B, FONT } from '../../../constants/designTokens'

const SEVERITY_CONFIG = {
    HIGH:   { color: C.danger,  label: 'Wysoki', bg: 'rgba(248,113,113,0.10)', border: 'rgba(248,113,113,0.25)' },
    MEDIUM: { color: C.warning, label: 'Średni', bg: 'rgba(251,191,36,0.10)', border: 'rgba(251,191,36,0.25)' },
    LOW:    { color: C.accentBlue, label: 'Niski', bg: 'rgba(79,142,247,0.10)', border: 'rgba(79,142,247,0.25)' },
}

function severityRank(sev) {
    return sev === 'HIGH' ? 0 : sev === 'MEDIUM' ? 1 : 2
}

export default function AnomalyAlertsCard() {
    const { selectedClientId, showToast } = useApp()
    const navigate = useNavigate()
    const [alerts, setAlerts] = useState([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (!selectedClientId) { setAlerts([]); return }
        let cancelled = false
        setLoading(true)
        setError(null)
        getAnomalies(selectedClientId, 'unresolved')
            .then(res => {
                if (cancelled) return
                const list = res?.alerts || []
                setAlerts(list)
            })
            .catch(err => {
                if (cancelled) return
                console.error('[AnomalyAlertsCard]', err)
                setError(err.message || 'Nie udało się załadować alertów')
                showToast?.(`Alerty: ${err.message || 'błąd ładowania'}`, 'error')
            })
            .finally(() => !cancelled && setLoading(false))
        return () => { cancelled = true }
    }, [selectedClientId, showToast])

    // Hide card entirely when everything is healthy
    if (!loading && !error && alerts.length === 0) return null
    if (loading) return null

    if (error) {
        return (
            <div className="v2-card" style={{ padding: '12px 18px', marginBottom: 16, fontSize: 12, color: C.w40 }}>
                <span style={{ color: C.danger, marginRight: 6 }}>⚠</span>
                Alerty — {error}
            </div>
        )
    }

    // Sort by severity, keep top 3
    const top = [...alerts]
        .sort((a, b) => severityRank(a.severity) - severityRank(b.severity))
        .slice(0, 3)
    const highCount = alerts.filter(a => a.severity === 'HIGH').length
    const headerColor = highCount > 0 ? C.danger : C.warning

    return (
        <div
            className="v2-card"
            onClick={() => navigate('/alerts')}
            style={{ padding: '14px 20px', marginBottom: 16, cursor: 'pointer' }}
        >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                {highCount > 0
                    ? <ShieldAlert size={16} style={{ color: C.danger }} />
                    : <AlertTriangle size={16} style={{ color: C.warning }} />}
                <span style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: FONT?.display || 'Syne' }}>
                    {alerts.length === 1
                        ? '1 anomalia do przejrzenia'
                        : `${alerts.length} anomalie do przejrzenia`}
                </span>
                {highCount > 0 && (
                    <span style={{
                        fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 999,
                        background: 'rgba(248,113,113,0.15)', color: C.danger,
                        border: '1px solid rgba(248,113,113,0.3)',
                    }}>
                        {highCount} WYSOKIE
                    </span>
                )}
                <span style={{ marginLeft: 'auto', fontSize: 11, color: C.accentBlue, display: 'flex', alignItems: 'center', gap: 3 }}>
                    Wszystkie <ChevronRight size={11} />
                </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {top.map(a => {
                    const cfg = SEVERITY_CONFIG[a.severity] || SEVERITY_CONFIG.LOW
                    return (
                        <div
                            key={a.id}
                            style={{
                                padding: '8px 12px',
                                borderRadius: 8,
                                background: cfg.bg,
                                border: `1px solid ${cfg.border}`,
                                display: 'flex',
                                alignItems: 'center',
                                gap: 10,
                            }}
                        >
                            <span style={{
                                fontSize: 9, fontWeight: 600, padding: '2px 7px', borderRadius: 999,
                                background: `${cfg.color}22`, color: cfg.color,
                                textTransform: 'uppercase', letterSpacing: '0.05em', flexShrink: 0,
                            }}>
                                {cfg.label}
                            </span>
                            <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{ fontSize: 12, fontWeight: 500, color: C.textPrimary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                    {a.title || a.alert_type?.replace(/_/g, ' ')}
                                </div>
                                {(a.description || a.campaign_name) && (
                                    <div style={{ fontSize: 10, color: C.w40, marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {a.campaign_name && <span>{a.campaign_name}</span>}
                                        {a.campaign_name && a.description && <span> · </span>}
                                        {a.description}
                                    </div>
                                )}
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

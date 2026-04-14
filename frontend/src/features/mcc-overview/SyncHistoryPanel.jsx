import { useState, useEffect } from 'react'
import { X, RefreshCw, CheckCircle, AlertCircle, Clock } from 'lucide-react'
import { getMccSyncHistory } from '../../api'
import { C, B, R, S } from '../../constants/designTokens'

function StatusIcon({ status }) {
    if (status === 'success') return <CheckCircle size={13} style={{ color: C.success }} />
    if (status === 'partial') return <AlertCircle size={13} style={{ color: C.warning }} />
    if (status === 'running') return <RefreshCw size={13} style={{ color: C.accentBlue, animation: 'spin 1s linear infinite' }} />
    return <AlertCircle size={13} style={{ color: C.danger }} />
}

function statusLabel(status) {
    if (status === 'success') return 'Sukces'
    if (status === 'partial') return 'Częściowy'
    if (status === 'running') return 'W trakcie'
    if (status === 'failed') return 'Błąd'
    return status
}

function statusColor(status) {
    if (status === 'success') return C.success
    if (status === 'partial') return C.warning
    if (status === 'running') return C.accentBlue
    return C.danger
}

function fmtDatetime(isoStr) {
    if (!isoStr) return '—'
    const d = new Date(isoStr)
    return (
        `${String(d.getDate()).padStart(2, '0')}.${String(d.getMonth() + 1).padStart(2, '0')}.${d.getFullYear()} ` +
        `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
    )
}

function fmtDuration(s) {
    if (s == null) return '—'
    if (s < 60) return `${s}s`
    const m = Math.floor(s / 60)
    const rem = s % 60
    return rem > 0 ? `${m}m ${rem}s` : `${m}m`
}

export default function SyncHistoryPanel({ clientId, clientName, onClose }) {
    const [history, setHistory] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        let mounted = true
        setLoading(true)
        setError(null)
        getMccSyncHistory(clientId, 5)
            .then(data => { if (mounted) setHistory(data) })
            .catch(() => { if (mounted) setError('Nie udało się załadować historii') })
            .finally(() => { if (mounted) setLoading(false) })
        return () => { mounted = false }
    }, [clientId])

    // Close on Escape
    useEffect(() => {
        const handler = (e) => { if (e.key === 'Escape') onClose() }
        window.addEventListener('keydown', handler)
        return () => window.removeEventListener('keydown', handler)
    }, [onClose])

    return (
        <>
            {/* Backdrop */}
            <div
                onClick={onClose}
                style={{
                    position: 'fixed', inset: 0,
                    background: 'rgba(0,0,0,0.5)',
                    zIndex: 50,
                }}
            />

            {/* Panel */}
            <div style={{
                position: 'fixed', right: 0, top: 0, bottom: 0,
                width: 360,
                background: C.sidebar,
                borderLeft: B.card,
                zIndex: 51,
                display: 'flex', flexDirection: 'column',
                boxShadow: '-8px 0 32px rgba(0,0,0,0.4)',
            }}>
                {/* Header */}
                <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '16px 20px',
                    borderBottom: B.card,
                }}>
                    <div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>Historia synchronizacji</div>
                        <div style={{ fontSize: 11, color: C.w40, marginTop: 2 }}>{clientName}</div>
                    </div>
                    <button
                        onClick={onClose}
                        style={{
                            background: 'none', border: 'none', cursor: 'pointer',
                            color: C.w40, padding: 4, borderRadius: R.sm,
                            display: 'flex', alignItems: 'center',
                        }}
                        title="Zamknij"
                    >
                        <X size={16} />
                    </button>
                </div>

                {/* Content */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px' }}>
                    {loading && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: C.w40, fontSize: 12, padding: '20px 0' }}>
                            <RefreshCw size={13} style={{ animation: 'spin 1s linear infinite' }} />
                            Ładowanie...
                        </div>
                    )}

                    {error && (
                        <div style={{ color: C.danger, fontSize: 12, padding: '12px 0' }}>
                            {error}
                        </div>
                    )}

                    {!loading && !error && history?.length === 0 && (
                        <div style={{ color: C.w30, fontSize: 12, padding: '20px 0', textAlign: 'center' }}>
                            Brak historii syncow
                        </div>
                    )}

                    {!loading && !error && history?.length > 0 && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {history.map((entry) => (
                                <div
                                    key={entry.id}
                                    style={{
                                        background: 'rgba(255,255,255,0.03)',
                                        border: B.card,
                                        borderRadius: R.md,
                                        padding: '10px 12px',
                                    }}
                                >
                                    {/* Status row */}
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                                        <StatusIcon status={entry.status} />
                                        <span style={{ fontSize: 12, fontWeight: 600, color: statusColor(entry.status) }}>
                                            {statusLabel(entry.status)}
                                        </span>
                                        <span style={{ marginLeft: 'auto', fontSize: 11, color: C.w40, display: 'flex', alignItems: 'center', gap: 3 }}>
                                            <Clock size={10} />
                                            {fmtDuration(entry.duration_s)}
                                        </span>
                                    </div>

                                    {/* Timestamp */}
                                    <div style={{ fontSize: 11, color: C.w40, marginBottom: 4 }}>
                                        {fmtDatetime(entry.finished_at || entry.started_at)}
                                    </div>

                                    {/* Counts */}
                                    <div style={{ display: 'flex', gap: 12, fontSize: 11 }}>
                                        <span style={{ color: C.w60 }}>
                                            Zsync: <span style={{ color: C.success }}>{entry.total_synced}</span>
                                        </span>
                                        {entry.total_errors > 0 && (
                                            <span style={{ color: C.w60 }}>
                                                Błędy: <span style={{ color: C.danger }}>{entry.total_errors}</span>
                                            </span>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
            </div>
        </>
    )
}

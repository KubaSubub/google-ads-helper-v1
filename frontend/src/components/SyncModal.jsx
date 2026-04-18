import { useState, useEffect, useRef } from 'react'
import {
    AlertTriangle, CheckCircle2, Clock, Loader2,
    MinusCircle, RefreshCw, X, XCircle,
} from 'lucide-react'
import { useSyncStream } from '../hooks/useSyncStream'
import { C, T, S, R, B } from '../constants/designTokens'

// Two options only per ADR-020:
// - Pełny: full history per phase (mapped to preset=full)
// - Ostatnie N dni: fixed window (mapped to preset=incremental + date_from override)
const DEFAULT_DAYS = 30

const STATUS_ICON = {
    pending:  <Clock size={13} style={{ color: C.w20 }} />,
    running:  <Loader2 size={13} style={{ color: C.accentBlue }} className="animate-spin" />,
    done:     <CheckCircle2 size={13} style={{ color: C.success }} />,
    error:    <XCircle size={13} style={{ color: C.danger }} />,
    skipped:  <MinusCircle size={13} style={{ color: C.w20 }} />,
}

function formatEta(seconds) {
    if (!seconds || seconds <= 0) return ''
    if (seconds < 60) return `~${seconds}s`
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `~${m}m ${s}s`
}

function formatDuration(seconds) {
    if (!seconds) return '0s'
    if (seconds < 60) return `${seconds}s`
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return s > 0 ? `${m}m ${s}s` : `${m}m`
}

function ymd(d) {
    return d.toISOString().slice(0, 10)
}

/**
 * Synchronization modal — per ADR-020.
 *
 * Props:
 * - isOpen: bool
 * - clientIds: number[]   — one or more client ids
 * - clientNames: string[] — parallel array of display names (optional)
 * - onClose: () => void
 *
 * Flow: user picks Pełny / N dni → sequential sync per client via SSE stream.
 */
export default function SyncModal({ isOpen, clientIds = [], clientNames = [], onClose }) {
    const stream = useSyncStream()
    const [mode, setMode] = useState('full')       // 'full' | 'days'
    const [days, setDays] = useState(DEFAULT_DAYS)
    const [queueIndex, setQueueIndex] = useState(0)
    const [queueState, setQueueState] = useState('configure') // configure | running | done
    const [aggregate, setAggregate] = useState({ ok: 0, failed: 0 })
    const cancelledRef = useRef(false)

    useEffect(() => {
        if (!isOpen) return
        stream.reset()
        setMode('full')
        setDays(DEFAULT_DAYS)
        setQueueIndex(0)
        setQueueState('configure')
        setAggregate({ ok: 0, failed: 0 })
        cancelledRef.current = false
    }, [isOpen]) // eslint-disable-line react-hooks/exhaustive-deps

    // Drive the sequential queue: when current client finishes, advance to next.
    useEffect(() => {
        if (queueState !== 'running') return
        if (stream.state !== 'done' && stream.state !== 'error') return

        setAggregate(prev => ({
            ok: prev.ok + (stream.state === 'done' ? 1 : 0),
            failed: prev.failed + (stream.state === 'error' ? 1 : 0),
        }))

        if (cancelledRef.current) {
            setQueueState('done')
            return
        }
        const next = queueIndex + 1
        if (next >= clientIds.length) {
            setQueueState('done')
            return
        }
        setQueueIndex(next)
        const payload = buildSyncPayload()
        stream.startSync(clientIds[next], payload)
    }, [stream.state]) // eslint-disable-line react-hooks/exhaustive-deps

    if (!isOpen || !clientIds.length) return null

    const isBulk = clientIds.length > 1
    const currentName = clientNames[queueIndex] || `Klient #${clientIds[queueIndex]}`

    function buildSyncPayload() {
        if (mode === 'full') return { preset: 'full' }
        // N days: preset=incremental + date_from override (backend honours override
        // in _resolve_dates_for_phase). date_to stays default (yesterday).
        const from = new Date()
        from.setDate(from.getDate() - days)
        const to = new Date()
        to.setDate(to.getDate() - 1)
        return { preset: 'incremental', dateFrom: ymd(from), dateTo: ymd(to) }
    }

    const handleStart = () => {
        if (!clientIds.length) return
        setQueueIndex(0)
        setQueueState('running')
        setAggregate({ ok: 0, failed: 0 })
        stream.startSync(clientIds[0], buildSyncPayload())
    }

    const handleClose = () => {
        if (queueState === 'running') {
            cancelledRef.current = true
            stream.cancel()
        }
        stream.reset()
        onClose?.()
    }

    // ── Configure view ─────────────────────────────────────────────
    if (queueState === 'configure') {
        return (
            <div data-sync-modal style={OVERLAY} onClick={handleClose}>
                <div style={SYNC_MODAL} onClick={e => e.stopPropagation()}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                        <div>
                            <div style={{ fontSize: 16, fontWeight: 700, color: C.textPrimary, fontFamily: 'Syne' }}>Synchronizacja</div>
                            <div style={{ fontSize: 11, color: C.w40, marginTop: 2 }}>
                                {isBulk
                                    ? `${clientIds.length} kont: ${clientNames.slice(0, 3).join(', ')}${clientIds.length > 3 ? '…' : ''}`
                                    : (clientNames[0] || `Klient #${clientIds[0]}`)}
                            </div>
                        </div>
                        <button onClick={handleClose} style={CLOSE_BTN}><X size={16} /></button>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 16 }}>
                        <button
                            onClick={() => setMode('full')}
                            style={optionCardStyle(mode === 'full', C.accentPurple)}
                        >
                            <div style={{ fontSize: 13, fontWeight: 600, color: mode === 'full' ? C.accentPurple : C.textPrimary, marginBottom: 3 }}>
                                Pełny
                            </div>
                            <div style={{ fontSize: 10, color: C.textMuted, lineHeight: 1.4 }}>
                                Cała historia i wszystkie fazy (maksymalny zakres wg limitów API).
                            </div>
                        </button>
                        <button
                            onClick={() => setMode('days')}
                            style={optionCardStyle(mode === 'days', C.accentBlue)}
                        >
                            <div style={{ fontSize: 13, fontWeight: 600, color: mode === 'days' ? C.accentBlue : C.textPrimary, marginBottom: 3 }}>
                                Ostatnie N dni
                            </div>
                            <div style={{ fontSize: 10, color: C.textMuted, lineHeight: 1.4 }}>
                                Wszystkie fazy dla wybranego okresu (do wczoraj włącznie).
                            </div>
                        </button>
                    </div>

                    {mode === 'days' && (
                        <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
                            <label style={{ fontSize: 12, color: C.w60 }}>Liczba dni:</label>
                            <input
                                type="number"
                                min={1}
                                max={1095}
                                value={days}
                                onChange={e => {
                                    const v = parseInt(e.target.value, 10)
                                    if (!Number.isNaN(v) && v > 0 && v <= 1095) setDays(v)
                                }}
                                style={{
                                    width: 80, padding: '6px 10px',
                                    background: C.w04, border: `1px solid ${C.w08}`, borderRadius: 6,
                                    color: C.textPrimary, fontSize: 12,
                                }}
                            />
                            <span style={{ fontSize: 10, color: C.w30 }}>
                                (max 1095 = 3 lata)
                            </span>
                        </div>
                    )}

                    <button onClick={handleStart} style={PRIMARY_BTN}>
                        <RefreshCw size={14} />
                        {isBulk ? `Synchronizuj ${clientIds.length} kont` : 'Synchronizuj'}
                    </button>
                </div>
            </div>
        )
    }

    // ── Progress / Done view ───────────────────────────────────────
    const isDone = queueState === 'done'
    const isError = stream.state === 'error'
    const isSyncing = queueState === 'running' && !isDone

    return (
        <div data-sync-modal style={OVERLAY}>
            <div style={SYNC_MODAL} onClick={e => e.stopPropagation()}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                    <div>
                        <div style={{ fontSize: 16, fontWeight: 700, color: C.textPrimary, fontFamily: 'Syne' }}>
                            {isDone ? 'Synchronizacja zakończona' : 'Synchronizacja...'}
                        </div>
                        <div style={{ fontSize: 11, color: C.w40, marginTop: 2 }}>
                            {isBulk && !isDone
                                ? <>Klient {queueIndex + 1}/{clientIds.length}: <strong>{currentName}</strong></>
                                : currentName}
                            {isSyncing && stream.eta > 0 && (
                                <span style={{ marginLeft: 8, color: C.accentBlue }}>ETA: {formatEta(stream.eta)}</span>
                            )}
                        </div>
                    </div>
                    {isDone && (
                        <button onClick={handleClose} style={CLOSE_BTN}><X size={16} /></button>
                    )}
                </div>

                {/* Current client's progress bar */}
                <div style={{
                    height: 6, borderRadius: 3, background: C.w06,
                    marginBottom: 16, overflow: 'hidden',
                }}>
                    <div style={{
                        height: '100%', borderRadius: 3,
                        background: isError ? C.danger : isDone ? C.success : C.accentBlue,
                        width: `${isDone ? 100 : stream.progress}%`,
                        transition: 'width 0.3s ease',
                    }} />
                </div>

                {/* Bulk: aggregate counter */}
                {isBulk && (
                    <div style={{
                        display: 'flex', gap: 10, marginBottom: 14, fontSize: 11, color: C.w50,
                    }}>
                        <span>
                            <CheckCircle2 size={11} style={{ color: C.success, verticalAlign: 'middle' }} />
                            {' '}OK: {aggregate.ok}
                        </span>
                        <span>
                            <XCircle size={11} style={{ color: C.danger, verticalAlign: 'middle' }} />
                            {' '}Błędów: {aggregate.failed}
                        </span>
                        <span style={{ color: C.w30 }}>
                            Pozostało: {Math.max(0, clientIds.length - queueIndex - (isDone ? 0 : 1))}
                        </span>
                    </div>
                )}

                {/* Error message */}
                {isError && stream.errorMsg && (
                    <div style={{
                        padding: '10px 14px', borderRadius: 8, marginBottom: 14,
                        background: C.dangerBg, border: '1px solid rgba(248,113,113,0.15)',
                        fontSize: 12, color: C.danger,
                    }}>
                        <AlertTriangle size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />
                        {stream.errorMsg}
                    </div>
                )}

                {/* Done summary (last client's result) */}
                {isDone && stream.result && (
                    <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
                        <div style={{
                            flex: 1, padding: '10px 14px', borderRadius: 8,
                            background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.15)',
                        }}>
                            <div style={{ fontSize: 18, fontWeight: 700, color: C.success, fontFamily: 'Syne' }}>
                                {stream.result.total_synced?.toLocaleString('pl-PL') || 0}
                            </div>
                            <div style={{ fontSize: 10, color: C.w40, textTransform: 'uppercase' }}>Obiektów (ostatni)</div>
                        </div>
                        {stream.result.total_errors > 0 && (
                            <div style={{
                                flex: 1, padding: '10px 14px', borderRadius: 8,
                                background: C.dangerBg, border: '1px solid rgba(248,113,113,0.15)',
                            }}>
                                <div style={{ fontSize: 18, fontWeight: 700, color: C.danger, fontFamily: 'Syne' }}>
                                    {stream.result.total_errors}
                                </div>
                                <div style={{ fontSize: 10, color: C.w40, textTransform: 'uppercase' }}>Błędów</div>
                            </div>
                        )}
                        <div style={{
                            flex: 1, padding: '10px 14px', borderRadius: 8,
                            background: C.w03, border: B.card,
                        }}>
                            <div style={{ fontSize: 18, fontWeight: 700, color: C.textPrimary, fontFamily: 'Syne' }}>
                                {formatDuration(stream.result.elapsed_seconds)}
                            </div>
                            <div style={{ fontSize: 10, color: C.w40, textTransform: 'uppercase' }}>Czas</div>
                        </div>
                    </div>
                )}

                {/* Current client's phase list */}
                <div style={{ maxHeight: 340, overflowY: 'auto', marginBottom: 16 }}>
                    {stream.phases.map((p) => (
                        <div key={p.phase} style={{
                            display: 'flex', alignItems: 'center', gap: 8,
                            padding: '6px 8px', borderRadius: 6, marginBottom: 2,
                            background: p.status === 'running' ? 'rgba(79,142,247,0.06)' : 'transparent',
                        }}>
                            {STATUS_ICON[p.status] || STATUS_ICON.pending}
                            <span style={{
                                flex: 1, fontSize: 12,
                                fontWeight: p.status === 'running' ? 500 : 400,
                                color: p.status === 'running' ? C.textPrimary
                                    : p.status === 'done' ? C.w60
                                    : p.status === 'error' ? C.danger
                                    : C.w30,
                            }}>
                                {p.label}
                            </span>
                            {p.status === 'done' && p.count != null && (
                                <span style={{ fontSize: 10, color: C.w25 }}>
                                    {p.count.toLocaleString('pl-PL')}
                                </span>
                            )}
                            {p.status === 'skipped' && (
                                <span style={{ fontSize: 10, color: C.w20, fontStyle: 'italic' }}>
                                    {p.reason || 'pominięto'}
                                </span>
                            )}
                            {p.status === 'error' && (
                                <span style={{ fontSize: 10, color: C.danger }} title={p.error}>
                                    błąd
                                </span>
                            )}
                        </div>
                    ))}
                </div>

                {isSyncing ? (
                    <button onClick={handleClose} style={CANCEL_BTN}>
                        Anuluj
                    </button>
                ) : (
                    <button onClick={handleClose} style={PRIMARY_BTN}>
                        Zamknij
                    </button>
                )}
            </div>
        </div>
    )
}

// ─── Styles ───

function optionCardStyle(active, color) {
    return {
        padding: '12px 14px',
        borderRadius: 10,
        border: `1px solid ${active ? color : C.w08}`,
        background: active ? `${color}15` : C.w03,
        cursor: 'pointer',
        textAlign: 'left',
        transition: 'all 0.15s',
    }
}

const OVERLAY = {
    position: 'fixed', inset: 0, zIndex: 100,
    background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
}

const SYNC_MODAL = {
    background: C.surfaceElevated, border: B.medium,
    borderRadius: 14, padding: '24px 28px', width: 480, maxWidth: '90vw',
    maxHeight: '85vh', overflowY: 'auto',
    boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
}

const CLOSE_BTN = {
    background: 'none', border: 'none', cursor: 'pointer',
    color: C.w30, padding: 4, borderRadius: 6,
}

const PRIMARY_BTN = {
    width: '100%', padding: '11px 0', borderRadius: 8,
    border: 'none', background: C.accentBlue, color: 'white',
    fontSize: 13, fontWeight: 600, cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
    transition: 'opacity 0.15s',
}

const CANCEL_BTN = {
    width: '100%', padding: '11px 0', borderRadius: 8,
    border: B.medium, background: C.w04,
    color: C.w60, fontSize: 13, fontWeight: 500,
    cursor: 'pointer', transition: 'all 0.15s',
}

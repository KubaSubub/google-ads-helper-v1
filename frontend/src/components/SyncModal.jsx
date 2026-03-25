import { useState, useEffect } from 'react'
import {
    AlertTriangle, CheckCircle2, ChevronDown, Clock, Loader2,
    MinusCircle, RefreshCw, X, XCircle,
} from 'lucide-react'
import { useSyncStream } from '../hooks/useSyncStream'
import { getSyncCoverage, getSyncPresets } from '../api'

const PRESET_LIST = [
    { key: 'incremental', color: '#4F8EF7' },
    { key: 'full',        color: '#7B5CE0' },
    { key: 'quick',       color: '#4ADE80' },
    { key: 'metrics_only',color: '#FBBF24' },
]

const STATUS_ICON = {
    pending:  <Clock size={13} style={{ color: 'rgba(255,255,255,0.2)' }} />,
    running:  <Loader2 size={13} style={{ color: '#4F8EF7' }} className="animate-spin" />,
    done:     <CheckCircle2 size={13} style={{ color: '#4ADE80' }} />,
    error:    <XCircle size={13} style={{ color: '#F87171' }} />,
    skipped:  <MinusCircle size={13} style={{ color: 'rgba(255,255,255,0.2)' }} />,
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

// ─── Main Component ───

export default function SyncModal({ isOpen, clientId, clientName, onClose }) {
    const stream = useSyncStream()
    const [presetData, setPresetData] = useState(null)
    const [coverage, setCoverage] = useState(null)
    const [selectedPreset, setSelectedPreset] = useState('incremental')
    const [showAdvanced, setShowAdvanced] = useState(false)

    // Load presets and coverage when modal opens
    useEffect(() => {
        if (!isOpen || !clientId) return
        stream.reset()
        setSelectedPreset('incremental')
        setShowAdvanced(false)
        getSyncPresets().then(setPresetData).catch(() => {})
        getSyncCoverage(clientId).then(setCoverage).catch(() => {})
    }, [isOpen, clientId]) // eslint-disable-line react-hooks/exhaustive-deps

    if (!isOpen) return null

    const handleStart = () => {
        stream.startSync(clientId, { preset: selectedPreset })
    }

    const handleClose = () => {
        if (stream.state === 'syncing') {
            stream.cancel()
        }
        stream.reset()
        onClose()
    }

    const presets = presetData?.presets || {}
    const phasesInfo = presetData?.phases || {}
    const groups = presetData?.groups || {}

    // ─── CONFIGURE VIEW ───
    if (stream.state === 'idle') {
        return (
            <div data-sync-modal style={OVERLAY} onClick={handleClose}>
                <div style={MODAL} onClick={e => e.stopPropagation()}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                        <div>
                            <div style={{ fontSize: 16, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne' }}>Synchronizacja</div>
                            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>
                                {clientName || `Klient #${clientId}`}
                            </div>
                        </div>
                        <button onClick={handleClose} style={CLOSE_BTN}><X size={16} /></button>
                    </div>

                    {/* Presets */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 16 }}>
                        {PRESET_LIST.map(({ key, color }) => {
                            const p = presets[key]
                            if (!p) return null
                            const active = selectedPreset === key
                            return (
                                <button
                                    key={key}
                                    onClick={() => setSelectedPreset(key)}
                                    style={{
                                        padding: '12px 14px',
                                        borderRadius: 10,
                                        border: `1px solid ${active ? color : 'rgba(255,255,255,0.08)'}`,
                                        background: active ? `${color}15` : 'rgba(255,255,255,0.03)',
                                        cursor: 'pointer',
                                        textAlign: 'left',
                                        transition: 'all 0.15s',
                                    }}
                                    className={!active ? 'hover:bg-white/[0.04]' : ''}
                                >
                                    <div style={{ fontSize: 13, fontWeight: 600, color: active ? color : '#F0F0F0', marginBottom: 3 }}>
                                        {p.label}
                                    </div>
                                    <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', lineHeight: 1.4 }}>
                                        {p.description}
                                    </div>
                                </button>
                            )
                        })}
                    </div>

                    {/* Advanced toggle */}
                    <button
                        onClick={() => setShowAdvanced(a => !a)}
                        style={{
                            display: 'flex', alignItems: 'center', gap: 6, width: '100%',
                            padding: '8px 0', background: 'none', border: 'none', cursor: 'pointer',
                            color: 'rgba(255,255,255,0.35)', fontSize: 11,
                        }}
                    >
                        <ChevronDown size={12} style={{ transform: showAdvanced ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }} />
                        Pokaż pokrycie danych
                    </button>

                    {showAdvanced && coverage && (
                        <div style={{ marginBottom: 16 }}>
                            {Object.entries(groups).map(([groupKey, groupLabel]) => {
                                const groupPhases = Object.entries(phasesInfo).filter(([, v]) => v.group === groupKey)
                                if (groupPhases.length === 0) return null
                                return (
                                    <div key={groupKey} style={{ marginBottom: 10 }}>
                                        <div style={{ fontSize: 9, fontWeight: 500, color: 'rgba(255,255,255,0.25)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 4 }}>
                                            {groupLabel}
                                        </div>
                                        {groupPhases.map(([phaseName, phaseInfo]) => {
                                            const cov = coverage[phaseName]
                                            return (
                                                <div key={phaseName} style={{
                                                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                                    padding: '4px 8px', borderRadius: 5, fontSize: 11,
                                                    background: 'rgba(255,255,255,0.02)',
                                                    marginBottom: 2,
                                                }}>
                                                    <span style={{ color: 'rgba(255,255,255,0.5)' }}>{phaseInfo.label}</span>
                                                    <span style={{ color: 'rgba(255,255,255,0.25)', fontSize: 10 }}>
                                                        {cov
                                                            ? cov.data_to
                                                                ? `do ${cov.data_to}`
                                                                : cov.last_sync_at
                                                                    ? `sync ${new Date(cov.last_sync_at).toLocaleDateString('pl-PL')}`
                                                                    : '—'
                                                            : 'brak danych'
                                                        }
                                                        {phaseInfo.max_days && (
                                                            <span style={{ color: 'rgba(255,255,255,0.15)', marginLeft: 6 }}>
                                                                max {phaseInfo.max_days}d
                                                            </span>
                                                        )}
                                                    </span>
                                                </div>
                                            )
                                        })}
                                    </div>
                                )
                            })}
                        </div>
                    )}

                    {/* Start button */}
                    <button onClick={handleStart} style={PRIMARY_BTN}>
                        <RefreshCw size={14} />
                        Synchronizuj
                    </button>
                </div>
            </div>
        )
    }

    // ─── PROGRESS / DONE / ERROR VIEW ───
    const isDone = stream.state === 'done'
    const isError = stream.state === 'error'
    const isSyncing = stream.state === 'syncing'

    return (
        <div data-sync-modal style={OVERLAY}>
            <div style={MODAL} onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                    <div>
                        <div style={{ fontSize: 16, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne' }}>
                            {isDone ? 'Synchronizacja zakończona' : isError ? 'Błąd synchronizacji' : 'Synchronizacja...'}
                        </div>
                        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>
                            {clientName || `Klient #${clientId}`}
                            {isSyncing && stream.eta > 0 && (
                                <span style={{ marginLeft: 8, color: '#4F8EF7' }}>ETA: {formatEta(stream.eta)}</span>
                            )}
                        </div>
                    </div>
                    {isDone || isError ? (
                        <button onClick={handleClose} style={CLOSE_BTN}><X size={16} /></button>
                    ) : null}
                </div>

                {/* Progress bar */}
                <div style={{
                    height: 6, borderRadius: 3,
                    background: 'rgba(255,255,255,0.06)',
                    marginBottom: 16, overflow: 'hidden',
                }}>
                    <div style={{
                        height: '100%', borderRadius: 3,
                        background: isError ? '#F87171' : isDone
                            ? (stream.result?.total_errors > 0 ? '#FBBF24' : '#4ADE80')
                            : '#4F8EF7',
                        width: `${stream.progress}%`,
                        transition: 'width 0.3s ease',
                    }} />
                </div>

                {/* Error message */}
                {isError && stream.errorMsg && (
                    <div style={{
                        padding: '10px 14px', borderRadius: 8, marginBottom: 14,
                        background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.15)',
                        fontSize: 12, color: '#F87171',
                    }}>
                        <AlertTriangle size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />
                        {stream.errorMsg}
                    </div>
                )}

                {/* Done summary */}
                {isDone && stream.result && (
                    <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
                        <div style={{
                            flex: 1, padding: '10px 14px', borderRadius: 8,
                            background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.15)',
                        }}>
                            <div style={{ fontSize: 18, fontWeight: 700, color: '#4ADE80', fontFamily: 'Syne' }}>
                                {stream.result.total_synced?.toLocaleString('pl-PL') || 0}
                            </div>
                            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Obiektów</div>
                        </div>
                        {stream.result.total_errors > 0 && (
                            <div style={{
                                flex: 1, padding: '10px 14px', borderRadius: 8,
                                background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.15)',
                            }}>
                                <div style={{ fontSize: 18, fontWeight: 700, color: '#F87171', fontFamily: 'Syne' }}>
                                    {stream.result.total_errors}
                                </div>
                                <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Błędów</div>
                            </div>
                        )}
                        <div style={{
                            flex: 1, padding: '10px 14px', borderRadius: 8,
                            background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
                        }}>
                            <div style={{ fontSize: 18, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne' }}>
                                {formatDuration(stream.result.elapsed_seconds)}
                            </div>
                            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Czas</div>
                        </div>
                    </div>
                )}

                {/* Phase list */}
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
                                color: p.status === 'running' ? '#F0F0F0'
                                    : p.status === 'done' ? 'rgba(255,255,255,0.6)'
                                    : p.status === 'error' ? '#F87171'
                                    : 'rgba(255,255,255,0.3)',
                            }}>
                                {p.label}
                            </span>
                            {p.status === 'done' && p.count != null && (
                                <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)' }}>
                                    {p.count.toLocaleString('pl-PL')}
                                </span>
                            )}
                            {p.status === 'skipped' && (
                                <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.2)', fontStyle: 'italic' }}>
                                    {p.reason || 'pominięto'}
                                </span>
                            )}
                            {p.status === 'error' && (
                                <span style={{ fontSize: 10, color: '#F87171' }} title={p.error}>
                                    błąd
                                </span>
                            )}
                        </div>
                    ))}
                </div>

                {/* Footer buttons */}
                {isSyncing ? (
                    <button onClick={stream.cancel} style={CANCEL_BTN}>
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

const OVERLAY = {
    position: 'fixed', inset: 0, zIndex: 100,
    background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
}

const MODAL = {
    background: '#1A1D24', border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 14, padding: '24px 28px', width: 480, maxWidth: '90vw',
    maxHeight: '85vh', overflowY: 'auto',
    boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
}

const CLOSE_BTN = {
    background: 'none', border: 'none', cursor: 'pointer',
    color: 'rgba(255,255,255,0.3)', padding: 4, borderRadius: 6,
}

const PRIMARY_BTN = {
    width: '100%', padding: '11px 0', borderRadius: 8,
    border: 'none', background: '#4F8EF7', color: 'white',
    fontSize: 13, fontWeight: 600, cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
    transition: 'opacity 0.15s',
}

const CANCEL_BTN = {
    width: '100%', padding: '11px 0', borderRadius: 8,
    border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.04)',
    color: 'rgba(255,255,255,0.6)', fontSize: 13, fontWeight: 500,
    cursor: 'pointer', transition: 'all 0.15s',
}

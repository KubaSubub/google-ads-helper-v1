// ScriptRunModal — three-phase modal for Quick Script execution
// Phases:
//   1. 'preview'   — show what WOULD happen (dry_run result), offer Execute / Cancel
//   2. 'executing' — loading spinner while real execution runs
//   3. 'result'    — show what ACTUALLY happened + link to Action History
import { useState, useEffect } from 'react'
import {
    XCircle, TrendingUp, Loader2,
    CheckCircle2, AlertTriangle, Eye,
} from 'lucide-react'
import { C, B, FONT } from '../../../constants/designTokens'

// ─── Category metadata (must match backend /recommendations/bulk-apply) ──────
export const CATEGORY_LABELS = {
    clean_waste:     'Wyczyść śmieci',
    pause_burning:   'Pauzuj spalające',
    boost_winners:   'Boost winnerów',
    emergency_brake: 'Hamulec awaryjny',
}

export const CATEGORY_COLORS = {
    clean_waste:     C.danger,
    pause_burning:   C.warning,
    boost_winners:   C.success,
    emergency_brake: C.danger,
}

// ─── Polish pluralization ────────────────────────────────────────────────────
function pluralize(n, one, few, many) {
    if (n === 1) return one
    const mod10 = n % 10, mod100 = n % 100
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few
    return many
}

// ─── Modal shell helpers ─────────────────────────────────────────────────────
function Backdrop({ children, onClick }) {
    return (
        <div
            onClick={onClick}
            style={{
                position: 'fixed', inset: 0, zIndex: 100,
                background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(4px)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                padding: 20,
            }}
        >
            {children}
        </div>
    )
}

function Panel({ children, onClick, wide = false }) {
    return (
        <div
            onClick={onClick}
            style={{
                background: 'rgba(20,22,28,1)', border: B.medium, borderRadius: 14,
                padding: '22px 26px', minWidth: 420,
                maxWidth: wide ? 680 : 560, width: '100%',
                maxHeight: '85vh', overflowY: 'auto',
                boxShadow: '0 20px 60px rgba(0,0,0,0.6)',
            }}
        >
            {children}
        </div>
    )
}

// ─── Preview item card — shows reason, metrics, and selection checkbox ─────
function PreviewItemCard({ item, selected, onToggle }) {
    const priorityColor = item.priority === 'HIGH' ? C.danger
        : item.priority === 'MEDIUM' ? C.warning : C.accentBlue
    const priorityLabel = item.priority === 'HIGH' ? 'Pilne'
        : item.priority === 'MEDIUM' ? 'Średnie' : 'Info'

    const metrics = item.metrics || {}
    const metricRows = []
    if (metrics.clicks != null) metricRows.push(['Kliknięcia', metrics.clicks])
    if (metrics.impressions != null) metricRows.push(['Wyświetlenia', metrics.impressions])
    if (metrics.cost_usd != null) metricRows.push(['Koszt', `${Number(metrics.cost_usd).toFixed(2)} zł`])
    if (metrics.conversions != null) metricRows.push(['Konwersje', Number(metrics.conversions).toFixed(1)])
    if (metrics.ctr != null) metricRows.push(['CTR', `${Number(metrics.ctr).toFixed(2)}%`])
    if (metrics.cpa != null) metricRows.push(['CPA', `${Number(metrics.cpa).toFixed(2)} zł`])
    if (metrics.roas != null) metricRows.push(['ROAS', `${Number(metrics.roas).toFixed(2)}×`])
    if (metrics.quality_score != null) metricRows.push(['QS', `${metrics.quality_score}/10`])

    return (
        <div
            onClick={onToggle}
            style={{
                padding: '12px 14px',
                borderRadius: 10,
                border: `1px solid ${selected ? 'rgba(79,142,247,0.4)' : C.w08}`,
                background: selected ? 'rgba(79,142,247,0.06)' : 'rgba(255,255,255,0.02)',
                cursor: 'pointer',
                transition: 'all 0.12s',
            }}
        >
            {/* Row 1: checkbox + entity name + priority pill */}
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 8 }}>
                <div style={{
                    width: 16, height: 16, borderRadius: 4, flexShrink: 0, marginTop: 1,
                    border: `1.5px solid ${selected ? C.accentBlue : C.w25}`,
                    background: selected ? C.accentBlue : 'transparent',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                    {selected && <CheckCircle2 size={11} style={{ color: '#FFFFFF' }} />}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {item.entity_name || item.summary || `#${item.id}`}
                    </div>
                    {item.campaign_name && (
                        <div style={{ fontSize: 10, color: C.w40, marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            w kampanii: {item.campaign_name}
                        </div>
                    )}
                </div>
                <span style={{
                    fontSize: 9, fontWeight: 600, padding: '2px 8px', borderRadius: 999,
                    background: `${priorityColor}18`, color: priorityColor,
                    border: `1px solid ${priorityColor}35`,
                    flexShrink: 0, textTransform: 'uppercase', letterSpacing: '0.05em',
                }}>
                    {priorityLabel}
                </span>
            </div>

            {/* Row 2: reason — the "why" */}
            {item.reason && (
                <div style={{
                    padding: '8px 10px',
                    borderRadius: 7,
                    background: 'rgba(255,255,255,0.03)',
                    borderLeft: `2px solid ${C.accentBlue}`,
                    marginBottom: metricRows.length > 0 ? 8 : 0,
                    marginLeft: 26,
                }}>
                    <div style={{ fontSize: 9, fontWeight: 600, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 3 }}>
                        Dlaczego
                    </div>
                    <div style={{ fontSize: 11, color: C.w70, lineHeight: 1.45 }}>
                        {item.reason}
                    </div>
                </div>
            )}

            {/* Row 3: metrics chips */}
            {metricRows.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginLeft: 26 }}>
                    {metricRows.map(([label, value]) => (
                        <span key={label} style={{
                            fontSize: 10, padding: '3px 8px', borderRadius: 5,
                            background: 'rgba(255,255,255,0.04)',
                            border: '1px solid rgba(255,255,255,0.06)',
                            color: C.w60,
                            fontFamily: 'monospace',
                        }}>
                            <span style={{ color: C.w30 }}>{label}:</span>{' '}
                            <span style={{ color: C.textPrimary }}>{value}</span>
                        </span>
                    ))}
                    {item.estimated_savings_usd > 0 && (
                        <span style={{
                            fontSize: 10, padding: '3px 8px', borderRadius: 5,
                            background: 'rgba(74,222,128,0.10)',
                            border: '1px solid rgba(74,222,128,0.25)',
                            color: C.success,
                            fontFamily: 'monospace',
                            fontWeight: 600,
                        }}>
                            ↑ oszczędność ~{item.estimated_savings_usd.toFixed(0)} zł
                        </span>
                    )}
                </div>
            )}
        </div>
    )
}

// ─── Main modal component ────────────────────────────────────────────────────
export default function ScriptRunModal({ state, onExecute, onClose, onViewHistory }) {
    const { phase = null, category = null, preview = null, result = null, error = null } = state || {}
    const color = CATEGORY_COLORS[category] || C.accentBlue
    const label = CATEGORY_LABELS[category] || category
    const data = result || preview
    const items = data?.items || []
    const matching = data?.total_matching || 0

    // Per-item selection (preview only) — default ALL selected
    const [selectedIds, setSelectedIds] = useState(() => new Set(items.map(i => i.id)))
    useEffect(() => {
        // Re-seed selection whenever a new preview arrives
        if (phase === 'preview') {
            setSelectedIds(new Set(items.map(i => i.id)))
        }
    }, [phase, preview])

    if (!state) return null

    const toggleSelected = (id) => {
        setSelectedIds(prev => {
            const next = new Set(prev)
            if (next.has(id)) next.delete(id)
            else next.add(id)
            return next
        })
    }
    const toggleAll = () => {
        if (selectedIds.size === items.length) setSelectedIds(new Set())
        else setSelectedIds(new Set(items.map(i => i.id)))
    }

    const selectedItems = items.filter(i => selectedIds.has(i.id))
    const estimatedSavings = (phase === 'preview' ? selectedItems : items)
        .reduce((s, i) => s + (i.estimated_savings_usd || 0), 0)

    // Executing phase: spinner only
    if (phase === 'executing') {
        return (
            <Backdrop onClick={() => { /* block close during execution */ }}>
                <Panel onClick={e => e.stopPropagation()}>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, padding: '30px 10px' }}>
                        <Loader2 size={28} style={{ color }} className="animate-spin" />
                        <div style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary, fontFamily: FONT?.display || 'Syne' }}>
                            {label} — w trakcie…
                        </div>
                        <div style={{ fontSize: 11, color: C.w40, textAlign: 'center', maxWidth: 280 }}>
                            Wysyłamy zmiany do Google Ads. Nie zamykaj tego okna.
                        </div>
                    </div>
                </Panel>
            </Backdrop>
        )
    }

    const isPreview = phase === 'preview'
    const isResult = phase === 'result'
    const hasErrors = isResult && result?.errors?.length > 0
    const appliedCount = result?.applied || 0
    const failedCount = result?.failed || 0

    return (
        <Backdrop onClick={onClose}>
            <Panel wide={isPreview} onClick={e => e.stopPropagation()}>
                {/* Phase banner */}
                {isPreview && (
                    <div style={{
                        padding: '8px 14px', borderRadius: 8, marginBottom: 14,
                        background: 'rgba(79,142,247,0.10)', border: '1px solid rgba(79,142,247,0.25)',
                        display: 'flex', alignItems: 'center', gap: 8,
                    }}>
                        <Eye size={13} style={{ color: C.accentBlue, flexShrink: 0 }} />
                        <span style={{ fontSize: 11, color: C.accentBlue, fontWeight: 600 }}>
                            PODGLĄD — nic jeszcze nie zostało wykonane
                        </span>
                    </div>
                )}
                {isResult && appliedCount > 0 && !hasErrors && (
                    <div style={{
                        padding: '8px 14px', borderRadius: 8, marginBottom: 14,
                        background: 'rgba(74,222,128,0.10)', border: '1px solid rgba(74,222,128,0.25)',
                        display: 'flex', alignItems: 'center', gap: 8,
                    }}>
                        <CheckCircle2 size={13} style={{ color: C.success, flexShrink: 0 }} />
                        <span style={{ fontSize: 11, color: C.success, fontWeight: 600 }}>
                            ZMIANY ZOSTAŁY ZAPISANE W GOOGLE ADS
                        </span>
                    </div>
                )}
                {isResult && (hasErrors || failedCount > 0) && (
                    <div style={{
                        padding: '8px 14px', borderRadius: 8, marginBottom: 14,
                        background: 'rgba(251,191,36,0.10)', border: '1px solid rgba(251,191,36,0.25)',
                        display: 'flex', alignItems: 'center', gap: 8,
                    }}>
                        <AlertTriangle size={13} style={{ color: C.warning, flexShrink: 0 }} />
                        <span style={{ fontSize: 11, color: C.warning, fontWeight: 600 }}>
                            {appliedCount > 0 ? 'CZĘŚCIOWO WYKONANO — sprawdź błędy' : 'NIE UDAŁO SIĘ WYKONAĆ'}
                        </span>
                    </div>
                )}

                {/* Header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                    <div style={{ width: 36, height: 36, borderRadius: 9, background: `${color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        {isResult
                            ? (appliedCount > 0 && !hasErrors ? <CheckCircle2 size={18} style={{ color }} /> : <AlertTriangle size={18} style={{ color: C.warning }} />)
                            : <Eye size={18} style={{ color }} />}
                    </div>
                    <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 15, fontWeight: 700, color: C.textPrimary, fontFamily: FONT?.display || 'Syne' }}>{label}</div>
                        <div style={{ fontSize: 11, color: C.w40, marginTop: 1 }}>
                            {isPreview
                                ? `${matching} ${pluralize(matching, 'rekomendacja do wykonania', 'rekomendacje do wykonania', 'rekomendacji do wykonania')}`
                                : `${appliedCount} ${pluralize(appliedCount, 'wykonana', 'wykonane', 'wykonanych')}${failedCount > 0 ? ` • ${failedCount} ${pluralize(failedCount, 'błąd', 'błędy', 'błędów')}` : ''}`}
                        </div>
                    </div>
                </div>

                {/* Stats for result phase */}
                {isResult && (
                    <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
                        <div style={{ flex: 1, padding: '10px 14px', borderRadius: 8, background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.2)' }}>
                            <div style={{ fontSize: 22, fontWeight: 700, color: C.success, fontFamily: 'Syne' }}>{appliedCount}</div>
                            <div style={{ fontSize: 10, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Wykonane</div>
                        </div>
                        {failedCount > 0 && (
                            <div style={{ flex: 1, padding: '10px 14px', borderRadius: 8, background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)' }}>
                                <div style={{ fontSize: 22, fontWeight: 700, color: C.danger, fontFamily: 'Syne' }}>{failedCount}</div>
                                <div style={{ fontSize: 10, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Błędów</div>
                            </div>
                        )}
                    </div>
                )}

                {/* Estimated savings (preview phase) */}
                {isPreview && estimatedSavings > 0 && (
                    <div style={{ padding: '10px 14px', borderRadius: 8, background: 'rgba(74,222,128,0.06)', border: '1px solid rgba(74,222,128,0.15)', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 10 }}>
                        <TrendingUp size={14} style={{ color: C.success }} />
                        <span style={{ fontSize: 12, color: C.success, fontWeight: 600 }}>
                            Szacowana oszczędność: ~{estimatedSavings.toFixed(0)} zł
                        </span>
                    </div>
                )}

                {/* Preview items — expanded cards with reason and selection */}
                {isPreview && items.length > 0 && (
                    <div style={{ marginBottom: 16 }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                            <div style={{ fontSize: 10, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                                Pozycje do wykonania ({selectedIds.size}/{items.length})
                            </div>
                            <button
                                onClick={toggleAll}
                                style={{ fontSize: 11, color: C.accentBlue, background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                            >
                                {selectedIds.size === items.length ? 'Odznacz wszystkie' : 'Zaznacz wszystkie'}
                            </button>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 380, overflowY: 'auto', paddingRight: 4 }}>
                            {items.map((item) => (
                                <PreviewItemCard
                                    key={item.id}
                                    item={item}
                                    selected={selectedIds.has(item.id)}
                                    onToggle={() => toggleSelected(item.id)}
                                />
                            ))}
                        </div>
                    </div>
                )}

                {/* Result items — compact list with status */}
                {isResult && items.length > 0 && (
                    <div style={{ marginBottom: 16 }}>
                        <div style={{ fontSize: 10, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
                            Szczegóły zmian
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 260, overflowY: 'auto' }}>
                            {items.map((item, i) => {
                                const isSuccess = item.status === 'success'
                                const isFailed = item.status === 'failed'
                                const bg = isSuccess ? 'rgba(74,222,128,0.04)' : isFailed ? 'rgba(248,113,113,0.04)' : 'rgba(255,255,255,0.02)'
                                const border = isSuccess ? 'rgba(74,222,128,0.12)' : isFailed ? 'rgba(248,113,113,0.12)' : 'rgba(255,255,255,0.06)'
                                return (
                                    <div key={item.id || i} style={{ padding: '8px 12px', borderRadius: 7, background: bg, border: `1px solid ${border}`, fontSize: 12, color: C.w70, display: 'flex', alignItems: 'center', gap: 8 }}>
                                        {isSuccess ? <CheckCircle2 size={12} style={{ color: C.success, flexShrink: 0 }} /> : <XCircle size={12} style={{ color: C.danger, flexShrink: 0 }} />}
                                        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                            {item.entity_name || item.summary || `${item.action_type} #${item.id}`}
                                            {item.campaign_name && <span style={{ color: C.w30 }}> · {item.campaign_name}</span>}
                                        </span>
                                        {item.estimated_savings_usd > 0 && (
                                            <span style={{ fontSize: 10, color: C.w40, fontFamily: 'monospace', flexShrink: 0 }}>
                                                ~{item.estimated_savings_usd.toFixed(0)} zł
                                            </span>
                                        )}
                                    </div>
                                )
                            })}
                        </div>
                    </div>
                )}

                {/* Errors */}
                {hasErrors && (
                    <div style={{ marginBottom: 16 }}>
                        <div style={{ fontSize: 10, color: C.danger, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                            Błędy
                        </div>
                        {result.errors.slice(0, 5).map((err, i) => (
                            <div key={i} style={{ padding: '6px 10px', borderRadius: 7, marginBottom: 3, background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', fontSize: 11, color: C.danger }}>{err}</div>
                        ))}
                    </div>
                )}

                {/* Error during execution */}
                {error && (
                    <div style={{ padding: '10px 14px', borderRadius: 8, background: 'rgba(248,113,113,0.10)', border: '1px solid rgba(248,113,113,0.25)', marginBottom: 14, fontSize: 12, color: C.danger }}>
                        {error}
                    </div>
                )}

                {/* Empty preview — all clear */}
                {isPreview && items.length === 0 && (
                    <div style={{
                        padding: '28px 20px',
                        textAlign: 'center',
                        borderRadius: 10,
                        background: 'rgba(74,222,128,0.06)',
                        border: '1px solid rgba(74,222,128,0.15)',
                        marginBottom: 14,
                    }}>
                        <CheckCircle2 size={32} style={{ color: C.success, marginBottom: 10 }} />
                        <div style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary, marginBottom: 6, fontFamily: FONT?.display || 'Syne' }}>
                            Wszystko w porządku
                        </div>
                        <div style={{ fontSize: 12, color: C.w50, lineHeight: 1.5, maxWidth: 360, margin: '0 auto' }}>
                            Brak rekomendacji tej kategorii do wykonania.
                            Nic nie wymaga teraz akcji — zajrzyj tu ponownie jutro
                            albo sprawdź pełną listę w zakładce Rekomendacje.
                        </div>
                    </div>
                )}

                {/* Actions */}
                <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
                    {isPreview && items.length > 0 && (
                        <>
                            <button
                                onClick={onClose}
                                style={{
                                    flex: 1, padding: '12px 0', borderRadius: 8,
                                    border: B.medium, background: C.w04,
                                    color: C.w60, fontSize: 13, fontWeight: 500, cursor: 'pointer',
                                }}
                            >
                                Anuluj
                            </button>
                            <button
                                onClick={() => onExecute(Array.from(selectedIds))}
                                disabled={selectedIds.size === 0}
                                style={{
                                    flex: 1.5, padding: '12px 0', borderRadius: 8,
                                    border: `1px solid ${selectedIds.size === 0 ? C.w08 : color}`,
                                    background: selectedIds.size === 0 ? C.w04 : `${color}22`,
                                    color: selectedIds.size === 0 ? C.w30 : color,
                                    fontSize: 13, fontWeight: 600,
                                    cursor: selectedIds.size === 0 ? 'not-allowed' : 'pointer',
                                }}
                            >
                                {category === 'clean_waste' && (selectedIds.size > 0
                                    ? `Wyklucz ${selectedIds.size} ${pluralize(selectedIds.size, 'frazę', 'frazy', 'fraz')}`
                                    : 'Wyklucz zaznaczone')}
                                {category === 'pause_burning' && (selectedIds.size > 0
                                    ? `Wstrzymaj ${selectedIds.size} ${pluralize(selectedIds.size, 'słowo', 'słowa', 'słów')}`
                                    : 'Wstrzymaj zaznaczone')}
                                {category === 'boost_winners' && (selectedIds.size > 0
                                    ? `Zwiększ budżet (${selectedIds.size})`
                                    : 'Zwiększ budżet')}
                                {category === 'emergency_brake' && (selectedIds.size > 0
                                    ? `Zastosuj (${selectedIds.size})`
                                    : 'Zastosuj zaznaczone')}
                                {!['clean_waste', 'pause_burning', 'boost_winners', 'emergency_brake'].includes(category) &&
                                    'Wykonaj na koncie'}
                            </button>
                        </>
                    )}
                    {isPreview && items.length === 0 && (
                        <button
                            onClick={onClose}
                            style={{
                                flex: 1, padding: '12px 0', borderRadius: 8,
                                border: B.medium, background: C.w04,
                                color: C.w60, fontSize: 13, fontWeight: 500, cursor: 'pointer',
                            }}
                        >
                            Zamknij
                        </button>
                    )}
                    {isResult && (
                        <>
                            <button
                                onClick={onViewHistory}
                                style={{
                                    flex: 1, padding: '12px 0', borderRadius: 8,
                                    border: `1px solid ${C.accentBlue}40`, background: 'rgba(79,142,247,0.10)',
                                    color: C.accentBlue, fontSize: 13, fontWeight: 500, cursor: 'pointer',
                                }}
                            >
                                Zobacz w historii
                            </button>
                            <button
                                onClick={onClose}
                                style={{
                                    flex: 1, padding: '12px 0', borderRadius: 8,
                                    border: B.medium, background: C.w04,
                                    color: C.w60, fontSize: 13, fontWeight: 500, cursor: 'pointer',
                                }}
                            >
                                Zamknij
                            </button>
                        </>
                    )}
                </div>
            </Panel>
        </Backdrop>
    )
}

import { useState, useEffect, useMemo, useCallback } from 'react'
import { LineChart, Line, ResponsiveContainer, XAxis, Tooltip, CartesianGrid } from 'recharts'
import {
    ChevronRight, ChevronUp, ChevronDown,
    XCircle, Pause, TrendingUp, Shield, Loader2,
    CheckCircle2, Clock, AlertTriangle, Eye,
} from 'lucide-react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
    getDashboardKPIs, getCampaigns, getCampaignsSummary,
    getHealthScore, getRecommendations,
    getBudgetPacing, getDeviceBreakdown, getGeoBreakdown,
    getWastedSpend, getImpressionShare,
    getQualityScoreAudit,
} from '../../api'
import api from '../../api'
import { useApp } from '../../contexts/AppContext'
import { useFilter } from '../../contexts/FilterContext'
import TrendExplorer from '../../components/TrendExplorer'
import WoWChart from '../../components/WoWChart'
import EmptyState from '../../components/EmptyState'
import HealthScoreCard from './components/HealthScoreCard'
import MiniKpiGrid from './components/MiniKpiGrid'
import QsHealthWidget from './components/QsHealthWidget'
import TopActions from './components/TopActions'
import CampaignMiniRanking from './components/CampaignMiniRanking'
import DayOfWeekWidget from './components/DayOfWeekWidget'

import { C, T, B, TOOLTIP_STYLE, TRANSITION, FONT } from '../../constants/designTokens'

// ─── Quick Scripts API ───────────────────────────────────────────────────────
const getBulkRecommendations = (clientId, category, dryRun = true, itemIds = null) =>
    api.post('/recommendations/bulk-apply', {
        client_id: clientId,
        category,
        dry_run: dryRun,
        ...(itemIds && itemIds.length ? { item_ids: itemIds } : {}),
    })

// ─── Quick Scripts helpers ───────────────────────────────────────────────────
function pluralize(n, one, few, many) {
    if (n === 1) return one
    const mod10 = n % 10, mod100 = n % 100
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few
    return many
}

const CATEGORY_LABELS = {
    clean_waste:     'Wyczyść śmieci',
    pause_burning:   'Pauzuj spalające',
    boost_winners:   'Boost winnerów',
    emergency_brake: 'Hamulec awaryjny',
}
const CATEGORY_COLORS = {
    clean_waste:     C.danger,
    pause_burning:   C.warning,
    boost_winners:   C.success,
    emergency_brake: C.danger,
}

const CARD = { background: C.w03, border: B.card, borderRadius: 12 }

// ─── Script result modal ─────────────────────────────────────────────────────
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

/**
 * ScriptRunModal — three-phase modal for quick script execution.
 *
 * Phases:
 *   1. 'preview'   — show what WOULD happen (dry_run result), offer Execute / Cancel
 *   2. 'executing' — loading spinner while real execution runs
 *   3. 'result'    — show what ACTUALLY happened + link to Action History
 */
function ScriptRunModal({ state, onExecute, onClose, onViewHistory }) {
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

// ─── Quick script button ─────────────────────────────────────────────────────
function QuickScript({ icon: Icon, label, description, color, onClick, loading: scriptLoading, count }) {
    const hasItems = count > 0
    return (
        <button
            onClick={onClick}
            disabled={scriptLoading}
            style={{
                ...CARD,
                padding: '14px 16px',
                textAlign: 'left',
                cursor: scriptLoading ? 'wait' : 'pointer',
                opacity: scriptLoading ? 0.5 : 1,
                transition: TRANSITION.fast,
                flex: '1 1 200px',
                minWidth: 180,
                borderColor: hasItems ? `${color}30` : C.w07,
            }}
            className="hover:bg-white/[0.04]"
        >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <div style={{ width: 28, height: 28, borderRadius: 7, background: `${color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {scriptLoading ? <Loader2 size={13} style={{ color }} className="animate-spin" /> : <Icon size={13} style={{ color }} />}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: C.textPrimary }}>{label}</div>
                    <span style={{
                        fontSize: 10,
                        fontWeight: 600,
                        color: hasItems ? color : C.success,
                    }}>
                        {hasItems
                            ? `${count} do wykonania`
                            : '✓ brak do wykonania'}
                    </span>
                </div>
            </div>
            <div style={{ fontSize: 11, color: C.w40, lineHeight: 1.4 }}>{description}</div>
        </button>
    )
}

// ─── Main Dashboard ──────────────────────────────────────────────────────────
export default function DashboardPage() {
    const { selectedClientId, showToast } = useApp()
    const { filters, dateParams, days } = useFilter()
    const navigate = useNavigate()
    const location = useLocation()
    const fromMCC = location.state?.fromMCC

    // Dashboard always restricts to ENABLED campaigns; status/name filters are ignored here
    const campaignParams = useMemo(() => {
        const p = { campaign_status: 'ENABLED' }
        if (filters.campaignType !== 'ALL') p.campaign_type = filters.campaignType
        return p
    }, [filters.campaignType])
    const allParams = useMemo(() => ({ ...dateParams, ...campaignParams }), [dateParams, campaignParams])

    const [kpis, setKpis]                       = useState(null)
    const [campaigns, setCampaigns]             = useState([])
    const [healthScore, setHealthScore]         = useState(null)
    const [recommendations, setRecs]            = useState([])
    const [budgetPacing, setBudgetPacing]       = useState(null)
    const [deviceData, setDeviceData]           = useState(null)
    const [geoData, setGeoData]                 = useState(null)
    const [wastedSpend, setWastedSpend]         = useState(null)
    const [campaignMetrics, setCampaignMetrics] = useState(null)
    const [impressionShare, setImpressionShare] = useState(null)
    const [qsAudit, setQsAudit]                = useState(null)

    // Quick Scripts state
    const [scriptCounts, setScriptCounts]       = useState({})
    const [scriptLoading, setScriptLoading]     = useState({})
    const [scriptsExpanded, setScriptsExpanded] = useState(null)
    // modalState shape: { phase: 'preview'|'executing'|'result', category, preview?, result?, error? }
    const [modalState, setModalState]           = useState(null)

    // Budget Pacing expanded state
    const [pacingExpanded, setPacingExpanded] = useState(false)

    const [expandedDevice, setExpandedDevice] = useState(null)
    const [geoSortBy, setGeoSortBy] = useState('cost_usd')
    const [geoSortDir, setGeoSortDir] = useState('desc')

    const [loading, setLoading]             = useState(false)
    const [healthLoading, setHealthLoading] = useState(false)
    const [error, setError]                 = useState(null)

    useEffect(() => {
        if (!selectedClientId) return
        let cancelled = false

        setLoading(true)
        setHealthLoading(true)
        setError(null)

        // Primary (blocking) — needed for page skeleton
        Promise.all([
            getDashboardKPIs(selectedClientId, allParams),
            getCampaigns(selectedClientId, campaignParams),
        ])
            .then(([kpiData, campData]) => {
                if (cancelled) return
                setKpis(kpiData)
                setCampaigns(campData?.items || [])
            })
            .catch(err => !cancelled && setError(err.message))
            .finally(() => !cancelled && setLoading(false))

        // Secondary — each endpoint updates its own state independently so a slow
        // endpoint (e.g. recommendations generation) does not block faster widgets.
        const safe = (promise, onResolve) => {
            promise
                .then(data => !cancelled && onResolve(data))
                .catch(err => { console.error('[Dashboard secondary]', err); !cancelled && onResolve(null) })
        }

        safe(
            getHealthScore(selectedClientId, allParams),
            (hs) => { setHealthScore(hs); setHealthLoading(false) },
        )
        safe(
            getRecommendations(selectedClientId, { status: 'pending', ...dateParams }),
            (recs) => setRecs(recs?.recommendations || recs?.items || []),
        )
        safe(getBudgetPacing(selectedClientId, campaignParams), setBudgetPacing)
        safe(getDeviceBreakdown(selectedClientId, allParams), setDeviceData)
        safe(getGeoBreakdown(selectedClientId, allParams), setGeoData)
        safe(getWastedSpend(selectedClientId, allParams), setWastedSpend)
        safe(
            getCampaignsSummary(selectedClientId, allParams),
            (cm) => setCampaignMetrics(cm?.campaigns || null),
        )
        safe(getImpressionShare(selectedClientId, allParams), setImpressionShare)
        safe(getQualityScoreAudit(selectedClientId, dateParams), setQsAudit)

        return () => { cancelled = true }
    }, [selectedClientId, allParams, campaignParams, dateParams])

    // Quick Scripts — reload whenever underlying recommendations change (tied to filter cycle)
    const loadScriptCounts = useCallback(async () => {
        if (!selectedClientId) return
        const categories = ['clean_waste', 'pause_burning', 'boost_winners', 'emergency_brake']
        const counts = {}
        for (const cat of categories) {
            try {
                const res = await getBulkRecommendations(selectedClientId, cat, true)
                counts[cat] = res.total_matching || 0
            } catch { counts[cat] = 0 }
        }
        setScriptCounts(counts)
        const total = Object.values(counts).reduce((a, b) => a + b, 0)
        if (total > 0) setScriptsExpanded(prev => prev === null ? true : prev)
    }, [selectedClientId])

    // Re-run when filter-driven data reload finishes (recommendations are filter-scoped)
    useEffect(() => { loadScriptCounts() }, [loadScriptCounts, recommendations])

    // Step 1: open preview — fetch dry_run result and show confirmation modal
    const openScriptPreview = async (category) => {
        setScriptLoading(prev => ({ ...prev, [category]: true }))
        try {
            const preview = await getBulkRecommendations(selectedClientId, category, true)
            setModalState({ phase: 'preview', category, preview })
        } catch (err) {
            showToast?.(`Nie udało się pobrać podglądu: ${err.message}`, 'error')
        } finally {
            setScriptLoading(prev => ({ ...prev, [category]: false }))
        }
    }

    // Step 2: execute — after user confirms in preview modal
    // `itemIds` narrows execution to just the rows the user left checked.
    const executeScript = async (itemIds = null) => {
        if (!modalState || modalState.phase !== 'preview') return
        const { category } = modalState
        setModalState({ phase: 'executing', category, preview: modalState.preview })
        try {
            const result = await getBulkRecommendations(selectedClientId, category, false, itemIds)
            setModalState({ phase: 'result', category, result })
            loadScriptCounts()
        } catch (err) {
            setModalState({
                phase: 'result',
                category,
                result: { applied: 0, failed: 0, errors: [err.message], items: [] },
                error: err.message,
            })
        }
    }

    // Dashboard shows only enabled campaigns; sidebar pill filters by type
    const filteredCampaigns = useMemo(() => campaigns.filter(c => {
        if (c.status !== 'ENABLED') return false
        if (filters.campaignType !== 'ALL' && c.campaign_type !== filters.campaignType) return false
        return true
    }), [campaigns, filters.campaignType])
    const filteredCampaignIds = useMemo(
        () => filteredCampaigns.map(c => c.id),
        [filteredCampaigns]
    )

    if (!selectedClientId) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                <EmptyState message="Wybierz klienta w sidebarze, aby zobaczyć dane" />
            </div>
        )
    }

    const { current, change_pct } = kpis || {}

    return (
        <div style={{ maxWidth: 1400, margin: '0 auto', padding: '0 4px' }}>

            {/* ── Header ─────────────────────────────────────────────────── */}
            {fromMCC && (
                <button
                    onClick={() => navigate('/mcc-overview')}
                    style={{
                        display: 'inline-flex', alignItems: 'center', gap: 4,
                        background: 'none', border: 'none', color: C.accentBlue,
                        fontSize: 12, cursor: 'pointer', padding: 0, marginBottom: 8,
                    }}
                >
                    &larr; Wszystkie konta
                </button>
            )}
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 24 }}>
                <div>
                    <h1 style={{ ...T.pageTitle }}>
                        Pulpit
                    </h1>
                    <p style={{ ...T.pageSubtitle }}>
                        {typeof filters.period === 'number'
                            ? `Ostatnie ${filters.period} dni`
                            : `${filters.dateFrom} — ${filters.dateTo}`
                        }
                    </p>
                </div>
            </div>

            {error && (
                <div style={{ background: C.dangerBg, border: B.danger, borderRadius: 8, padding: '10px 16px', marginBottom: 20, fontSize: 13, color: C.danger }}>
                    Błąd ładowania danych: {error}
                </div>
            )}

            {/* ── Health Score + KPI row ─────────────────────────────────── */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 16, marginBottom: 16 }}>
                <HealthScoreCard
                    score={healthScore?.score}
                    issues={healthScore?.issues}
                    loading={healthLoading}
                    dataAvailable={healthScore?.data_available}
                    breakdown={healthScore?.breakdown}
                    onClick={() => navigate('/alerts')}
                />

                <MiniKpiGrid
                    current={current}
                    change_pct={change_pct}
                    wastedSpend={wastedSpend}
                />
            </div>

            {/* ── QS Health + Top Actions (compact side-by-side) ────────── */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                <QsHealthWidget qsAudit={qsAudit} compact />
                <TopActions recommendations={recommendations} compact />
            </div>

            {/* ── Quick Scripts ─────────────────────────────────────────── */}
            <div style={{ marginBottom: 16 }}>
                <div
                    onClick={() => setScriptsExpanded(prev => !prev)}
                    style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, userSelect: 'none', marginBottom: scriptsExpanded ? 10 : 0 }}
                >
                    <span style={{ fontSize: 11, fontWeight: 600, color: C.w50, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                        Szybkie skrypty
                    </span>
                    {Object.values(scriptCounts).reduce((a, b) => a + b, 0) > 0 && (
                        <span style={{ fontSize: 10, fontWeight: 600, color: C.accentBlue, background: 'rgba(79,142,247,0.12)', padding: '1px 8px', borderRadius: 999 }}>
                            {Object.values(scriptCounts).reduce((a, b) => a + b, 0)} do wykonania
                        </span>
                    )}
                    <ChevronDown size={12} style={{ color: C.w25, transform: scriptsExpanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
                </div>
                {scriptsExpanded && (
                    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                        <QuickScript icon={XCircle} label="Wyczyść śmieci" description="Dodaj negatywy dla nieistotnych fraz"
                            color={C.danger} count={scriptCounts.clean_waste || 0}
                            loading={scriptLoading.clean_waste} onClick={() => openScriptPreview('clean_waste')} />
                        <QuickScript icon={Pause} label="Pauzuj spalające" description="Wstrzymaj słowa bez konwersji z wys. kosztem"
                            color={C.warning} count={scriptCounts.pause_burning || 0}
                            loading={scriptLoading.pause_burning} onClick={() => openScriptPreview('pause_burning')} />
                        <QuickScript icon={TrendingUp} label="Boost winnerów" description="Zwiększ budżet kampanii z dobrym CPA i niskim IS"
                            color={C.success} count={scriptCounts.boost_winners || 0}
                            loading={scriptLoading.boost_winners} onClick={() => openScriptPreview('boost_winners')} />
                        <QuickScript icon={Shield} label="Hamulec awaryjny" description="Obniż stawki i pauzuj przy ekstremalnym CPA"
                            color={C.danger} count={scriptCounts.emergency_brake || 0}
                            loading={scriptLoading.emergency_brake} onClick={() => openScriptPreview('emergency_brake')} />
                    </div>
                )}
            </div>

            {/* ── Trend Explorer ────────────────────────────────────────── */}
            <div style={{ marginBottom: 16 }}>
                <TrendExplorer campaignIds={filteredCampaignIds} />
            </div>

            {/* ── WoW Comparison ────────────────────────────────────────── */}
            <WoWChart />

            {/* ── Day of Week Performance ─────────────────────────────── */}
            <DayOfWeekWidget />

            {/* ── Campaign Mini-Ranking ───────────────────────────────── */}
            <CampaignMiniRanking campaigns={filteredCampaigns} campaignMetrics={campaignMetrics} />

            {/* ── Budget Pacing (compact + expandable) ──────────────────── */}
            {budgetPacing?.campaigns?.length > 0 && (() => {
                const camps = budgetPacing.campaigns
                const onTrack   = camps.filter(c => c.status === 'on_track').length
                const overspend = camps.filter(c => c.status === 'overspend').length
                const underspend = camps.filter(c => c.status === 'underspend').length
                const totalActual   = camps.reduce((s, c) => s + (c.actual_spend_usd ?? 0), 0)
                const totalExpected = camps.reduce((s, c) => s + (c.expected_spend_usd ?? 0), 0)
                const totalPct = totalExpected > 0 ? (totalActual / totalExpected * 100) : 0
                const barColor = totalPct > 115 ? C.danger : totalPct < 80 ? C.warning : C.success
                const barPct = Math.min(totalPct, 150)

                const statusLabel = (s) => s === 'on_track' ? 'Na torze' : s === 'overspend' ? 'Przekroczenie' : s === 'underspend' ? 'Niedostateczne' : '—'
                const statusColor = (s) => s === 'on_track' ? C.success : s === 'overspend' ? C.danger : s === 'underspend' ? C.warning : C.w30

                const sortedCamps = [...camps].sort((a, b) => {
                    // Sort: overspend first, then underspend, then on_track — most urgent at top
                    const order = { overspend: 0, underspend: 1, on_track: 2, no_data: 3 }
                    return (order[a.status] ?? 9) - (order[b.status] ?? 9)
                })

                return (
                    <div className="v2-card" style={{ marginBottom: 16, overflow: 'hidden' }}>
                        {/* Header row — clickable to expand */}
                        <div
                            onClick={() => setPacingExpanded(e => !e)}
                            style={{ padding: '14px 20px', cursor: 'pointer', userSelect: 'none' }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10, flexWrap: 'wrap' }}>
                                <span style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne' }}>
                                    Pacing budżetu ({budgetPacing.days_elapsed}/{budgetPacing.days_in_month} dni)
                                </span>
                                <div style={{ display: 'flex', gap: 10, marginLeft: 'auto', fontSize: 11 }}>
                                    <span style={{ color: C.success }}>● {onTrack} na torze</span>
                                    {overspend > 0 && <span style={{ color: C.danger }}>● {overspend} przekroczenie</span>}
                                    {underspend > 0 && <span style={{ color: C.warning }}>● {underspend} niedostateczne</span>}
                                </div>
                                <ChevronDown size={14} style={{ color: C.w40, transform: pacingExpanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                <div style={{ flex: 1, height: 8, borderRadius: 4, background: C.w06, overflow: 'hidden', position: 'relative' }}>
                                    <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${(barPct / 150 * 100).toFixed(0)}%`, background: barColor, transition: 'width 0.3s' }} />
                                    <div style={{ position: 'absolute', left: `${(100 / 150 * 100).toFixed(0)}%`, top: -2, bottom: -2, width: 1, background: 'rgba(255,255,255,0.25)' }} />
                                </div>
                                <span style={{ fontSize: 12, fontFamily: 'monospace', color: barColor, fontWeight: 600, minWidth: 50, textAlign: 'right' }}>
                                    {totalPct.toFixed(0)}%
                                </span>
                                <span style={{ fontSize: 11, color: C.w40, fontFamily: 'monospace' }}>
                                    {totalActual.toLocaleString('pl-PL', { maximumFractionDigits: 0 })} / {totalExpected.toLocaleString('pl-PL', { maximumFractionDigits: 0 })} zł
                                </span>
                            </div>
                        </div>

                        {/* Expandable campaigns list */}
                        {pacingExpanded && (
                            <div style={{ borderTop: B.subtle, padding: '8px 0 12px' }}>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 90px 90px 110px 90px', gap: 12, padding: '6px 20px', fontSize: 9, fontWeight: 500, color: C.w30, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                                    <span>Kampania</span>
                                    <span style={{ textAlign: 'right' }}>Budżet/mies.</span>
                                    <span style={{ textAlign: 'right' }}>Wydano</span>
                                    <span style={{ textAlign: 'right' }}>Pacing</span>
                                    <span style={{ textAlign: 'right' }}>Status</span>
                                </div>
                                {sortedCamps.map(c => {
                                    const campPct = Math.min(c.pacing_pct ?? 0, 150)
                                    const campColor = statusColor(c.status)
                                    return (
                                        <div
                                            key={c.campaign_id}
                                            onClick={() => navigate(`/campaigns?campaign_id=${c.campaign_id}`)}
                                            style={{
                                                display: 'grid',
                                                gridTemplateColumns: '1fr 90px 90px 110px 90px',
                                                gap: 12,
                                                padding: '8px 20px',
                                                alignItems: 'center',
                                                cursor: 'pointer',
                                                fontSize: 12,
                                                borderTop: `1px solid ${C.w04}`,
                                                transition: 'background 0.12s',
                                            }}
                                            onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.025)'}
                                            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                                        >
                                            <span style={{ color: C.textPrimary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                {c.campaign_name}
                                            </span>
                                            <span style={{ textAlign: 'right', fontFamily: 'monospace', color: C.w60 }}>
                                                {(c.monthly_budget_usd ?? 0).toLocaleString('pl-PL', { maximumFractionDigits: 0 })} zł
                                            </span>
                                            <span style={{ textAlign: 'right', fontFamily: 'monospace', color: C.w60 }}>
                                                {(c.actual_spend_usd ?? 0).toLocaleString('pl-PL', { maximumFractionDigits: 0 })} zł
                                            </span>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'flex-end' }}>
                                                <div style={{ flex: 1, maxWidth: 60, height: 4, borderRadius: 2, background: C.w06, overflow: 'hidden', position: 'relative' }}>
                                                    <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${(campPct / 150 * 100).toFixed(0)}%`, background: campColor }} />
                                                </div>
                                                <span style={{ fontFamily: 'monospace', color: campColor, fontWeight: 600, minWidth: 36, textAlign: 'right' }}>
                                                    {(c.pacing_pct ?? 0).toFixed(0)}%
                                                </span>
                                            </div>
                                            <span style={{ textAlign: 'right', fontSize: 10, color: campColor, fontWeight: 500 }}>
                                                {statusLabel(c.status)}
                                            </span>
                                        </div>
                                    )
                                })}
                            </div>
                        )}
                    </div>
                )
            })()}

            {/* ── PMax Channel Split removed — use /pmax ────────────────── */}
            {false && (
                <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 16 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                        <span style={{ ...T.sectionTitle }}>
                            PMax — rozkład kanałów
                        </span>
                        <span onClick={() => navigate('/audit-center')} style={{ fontSize: 11, color: C.accentBlue, cursor: 'pointer' }}>
                            Szczegóły →
                        </span>
                    </div>
                    {(() => {
                        const CHANNEL_LABELS = {
                            SEARCH: 'Wyszukiwarka', DISPLAY: 'Sieć reklamowa', VIDEO: 'YouTube',
                            SHOPPING: 'Zakupy', DISCOVER: 'Discover', CROSS_NETWORK: 'Cross-network',
                        }
                        const channels = pmaxChannels.channels
                        const imbalance = channels.find(c => c.cost_share_pct > 60 && c.conv_share_pct < 30)
                        return (
                            <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr', gap: 16, alignItems: 'center' }}>
                                <div style={{ width: 140, height: 140 }}>
                                    <ResponsiveContainer width="100%" height="100%">
                                        <PieChart>
                                            <Pie
                                                data={channels}
                                                dataKey="cost_share_pct"
                                                nameKey="network_type"
                                                cx="50%" cy="50%"
                                                innerRadius={36} outerRadius={60}
                                                strokeWidth={0}
                                            >
                                                {channels.map((ch, i) => (
                                                    <Cell key={i} fill={CHANNEL_COLORS[ch.network_type] || '#64748B'} />
                                                ))}
                                            </Pie>
                                            <Tooltip
                                                contentStyle={{ ...TOOLTIP_STYLE, fontSize: 11, padding: '6px 10px' }}
                                                formatter={(v, name) => [`${v}%`, name]}
                                            />
                                        </PieChart>
                                    </ResponsiveContainer>
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                                    {channels.map(ch => {
                                        const color = CHANNEL_COLORS[ch.network_type] || '#64748B'
                                        const isAlert = ch.cost_share_pct > 60 && ch.conv_share_pct < 30
                                        return (
                                            <div key={ch.network_type} className="flex items-center justify-between">
                                                <div className="flex items-center gap-2">
                                                    <div style={{ width: 8, height: 8, borderRadius: 2, background: color, flexShrink: 0 }} />
                                                    <span style={{ fontSize: 12, color: C.textPrimary }}>{CHANNEL_LABELS[ch.network_type] || ch.network_type}</span>
                                                </div>
                                                <div className="flex items-center gap-3" style={{ fontSize: 11 }}>
                                                    <span style={{ color: C.w50 }}>{(ch.cost_micros / 1e6).toFixed(0)} zł</span>
                                                    <span style={{ color: C.textMuted, minWidth: 40, textAlign: 'right' }}>{ch.cost_share_pct}%</span>
                                                    <span style={{ color: isAlert ? C.danger : C.textMuted, minWidth: 50, textAlign: 'right', fontWeight: isAlert ? 600 : 400 }}>
                                                        {ch.conv_share_pct}% conv
                                                    </span>
                                                </div>
                                            </div>
                                        )
                                    })}
                                    {imbalance && (
                                        <div style={{ marginTop: 4, padding: '6px 10px', borderRadius: 8, background: C.dangerBg, border: '1px solid rgba(248,113,113,0.2)', fontSize: 11, color: C.danger }}>
                                            ⚠ {imbalance.network_type}: {imbalance.cost_share_pct}% kosztów, tylko {imbalance.conv_share_pct}% konwersji
                                        </div>
                                    )}
                                </div>
                            </div>
                        )
                    })()}
                </div>
            )}

            {/* ── Device + Geo Breakdown ────────────────────────────────── */}
            {(deviceData?.devices?.length > 0 || geoData?.cities?.length > 0) && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                    {/* Device breakdown */}
                    {deviceData?.devices?.length > 0 && (
                        <div className="v2-card" style={{ padding: '16px 20px' }}>
                            <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, marginBottom: 12, fontFamily: 'Syne' }}>
                                Urządzenia
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                {deviceData.devices.map(d => {
                                    const color = d.device === 'MOBILE' ? C.accentBlue : d.device === 'DESKTOP' ? C.accentPurple : C.warning
                                    const isExpanded = expandedDevice === d.device
                                    const hasTrend = d.trend && d.trend.length >= 2
                                    return (
                                        <div key={d.device}>
                                            <div
                                                className="flex items-center justify-between"
                                                style={{ marginBottom: 4, cursor: hasTrend ? 'pointer' : 'default' }}
                                                onClick={() => hasTrend && setExpandedDevice(isExpanded ? null : d.device)}
                                            >
                                                <div className="flex items-center gap-1.5">
                                                    {hasTrend && (
                                                        <ChevronRight
                                                            size={12}
                                                            style={{
                                                                color: C.w30,
                                                                transform: isExpanded ? 'rotate(90deg)' : 'none',
                                                                transition: 'transform 0.15s',
                                                            }}
                                                        />
                                                    )}
                                                    <span style={{ fontSize: 12, fontWeight: 500, color: C.textPrimary }}>{{ MOBILE: 'Telefony', DESKTOP: 'Komputery', TABLET: 'Tablety' }[d.device] || d.device}</span>
                                                </div>
                                                <span style={{ fontSize: 11, color: C.w40 }}>{d.share_clicks_pct}% kliknięć</span>
                                            </div>
                                            <div style={{ height: 4, borderRadius: 2, background: C.w06 }}>
                                                <div style={{ height: '100%', borderRadius: 2, background: color, width: `${d.share_clicks_pct}%`, transition: 'width 0.3s' }} />
                                            </div>
                                            <div className="flex items-center justify-between" style={{ marginTop: 4, fontSize: 10, color: C.textMuted }}>
                                                <span>CTR {d.ctr}% · CPC {d.cpc.toFixed(2)} zł</span>
                                                <span>ROAS {d.roas}×</span>
                                            </div>

                                            {/* Expanded device trend */}
                                            {isExpanded && hasTrend && (
                                                <div style={{
                                                    marginTop: 8,
                                                    padding: '12px 14px',
                                                    background: 'rgba(255,255,255,0.02)',
                                                    border: B.subtle,
                                                    borderRadius: 8,
                                                }}>
                                                    <div style={{ display: 'flex', gap: 16, marginBottom: 8 }}>
                                                        {[
                                                            { label: 'Kliknięcia', key: 'clicks', color: C.accentBlue },
                                                            { label: 'Koszt', key: 'cost', color: C.warning },
                                                            { label: 'Konwersje', key: 'conversions', color: C.success },
                                                        ].map(m => {
                                                            const values = d.trend.map(t => t[m.key])
                                                            const avg = values.reduce((a, b) => a + b, 0) / values.length
                                                            return (
                                                                <div key={m.key} style={{ fontSize: 10, color: C.w40 }}>
                                                                    <span style={{ color: m.color, fontWeight: 600 }}>●</span>{' '}
                                                                    {m.label}: <span style={{ color: C.textPrimary }}>
                                                                        {m.key === 'cost' ? `${avg.toFixed(2)} zł` : avg.toFixed(1)}
                                                                    </span>
                                                                    <span style={{ color: C.w25 }}> avg/d</span>
                                                                </div>
                                                            )
                                                        })}
                                                    </div>
                                                    <ResponsiveContainer width="100%" height={100}>
                                                        <LineChart data={d.trend} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                                                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                                                            <XAxis
                                                                dataKey="date"
                                                                tickFormatter={v => { const dt = new Date(v); return `${dt.getDate()}.${(dt.getMonth()+1).toString().padStart(2,'0')}` }}
                                                                tick={{ fontSize: 9, fill: C.w20 }}
                                                                axisLine={false} tickLine={false}
                                                                interval="preserveStartEnd"
                                                            />
                                                            <Tooltip
                                                                contentStyle={{
                                                                    background: C.surfaceElevated,
                                                                    border: B.hover,
                                                                    borderRadius: 8,
                                                                    fontSize: 11,
                                                                }}
                                                                labelFormatter={v => { const dt = new Date(v); return `${dt.getDate()}.${(dt.getMonth()+1).toString().padStart(2,'0')}` }}
                                                            />
                                                            <Line type="monotone" dataKey="clicks" stroke="#4F8EF7" strokeWidth={1.5} dot={false} name="Kliknięcia" />
                                                            <Line type="monotone" dataKey="cost" stroke="#FBBF24" strokeWidth={1.5} dot={false} name="Koszt (zł)" />
                                                            <Line type="monotone" dataKey="conversions" stroke="#4ADE80" strokeWidth={1.5} dot={false} name="Konwersje" />
                                                        </LineChart>
                                                    </ResponsiveContainer>
                                                </div>
                                            )}
                                        </div>
                                    )
                                })}
                            </div>
                        </div>
                    )}

                    {/* Geo breakdown */}
                    {geoData?.cities?.length > 0 && (
                        <div className="v2-card" style={{ padding: '16px 20px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                                <span style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne' }}>
                                    Top miasta
                                </span>
                            </div>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr>
                                        {[
                                            { label: 'Miasto', key: 'city' },
                                            { label: 'Kliknięcia', key: 'clicks' },
                                            { label: 'Koszt', key: 'cost_usd' },
                                            { label: '% kosztu', key: 'share_cost_pct' },
                                            { label: 'ROAS', key: 'roas' },
                                        ].map(h => {
                                            const isSorted = geoSortBy === h.key
                                            return (
                                                <th
                                                    key={h.label}
                                                    onClick={() => {
                                                        if (geoSortBy === h.key) setGeoSortDir(d => d === 'desc' ? 'asc' : 'desc')
                                                        else { setGeoSortBy(h.key); setGeoSortDir('desc') }
                                                    }}
                                                    style={{
                                                        padding: '4px 6px', fontSize: 10, fontWeight: 500,
                                                        color: isSorted ? C.accentBlue : C.textMuted, textTransform: 'uppercase',
                                                        letterSpacing: '0.08em', textAlign: h.key === 'city' ? 'left' : 'right',
                                                        cursor: 'pointer', userSelect: 'none',
                                                    }}
                                                >
                                                    {h.label}
                                                    {isSorted && (geoSortDir === 'desc'
                                                        ? <ChevronDown size={9} style={{ marginLeft: 2, verticalAlign: 'middle' }} />
                                                        : <ChevronUp size={9} style={{ marginLeft: 2, verticalAlign: 'middle' }} />
                                                    )}
                                                </th>
                                            )
                                        })}
                                    </tr>
                                </thead>
                                <tbody>
                                    {[...geoData.cities].sort((a, b) => {
                                        const vA = geoSortBy === 'city' ? (a.city || '') : (a[geoSortBy] ?? 0)
                                        const vB = geoSortBy === 'city' ? (b.city || '') : (b[geoSortBy] ?? 0)
                                        if (typeof vA === 'string') return geoSortDir === 'desc' ? vB.localeCompare(vA) : vA.localeCompare(vB)
                                        return geoSortDir === 'desc' ? vB - vA : vA - vB
                                    }).slice(0, 8).map(c => (
                                        <tr key={c.city} style={{ borderTop: `1px solid ${C.w04}` }}>
                                            <td style={{ padding: '6px', fontSize: 12, color: C.textPrimary }}>{c.city}</td>
                                            <td style={{ padding: '6px', fontSize: 12, fontFamily: 'monospace', color: C.w60, textAlign: 'right' }}>{c.clicks}</td>
                                            <td style={{ padding: '6px', fontSize: 12, fontFamily: 'monospace', color: C.w60, textAlign: 'right' }}>{c.cost_usd?.toFixed(0) ?? '—'} zł</td>
                                            <td style={{ padding: '6px', fontSize: 12, fontFamily: 'monospace', color: C.w40, textAlign: 'right' }}>{c.share_cost_pct != null ? `${c.share_cost_pct}%` : '—'}</td>
                                            <td style={{ padding: '6px', fontSize: 12, fontFamily: 'monospace', textAlign: 'right', color: (c.roas ?? 0) >= 3 ? C.success : (c.roas ?? 0) >= 1 ? C.warning : C.danger }}>{c.roas?.toFixed(2) ?? '—'}×</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}

            {/* ── Impression Share (Search campaigns) ───────────────────── */}
            {impressionShare?.summary && Object.keys(impressionShare.summary).length > 0 && (
                <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 16 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                        <span style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne' }}>
                            Udział w wyświetleniach (Search)
                        </span>
                        <span style={{ fontSize: 10, color: C.w30, textTransform: 'uppercase' }}>
                            Avg. za okres
                        </span>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                        {[
                            { label: 'Impr. Share', key: 'impression_share', good: 0.5 },
                            { label: 'Lost (Budget)', key: 'budget_lost_is', invert: true, bad: 0.2 },
                            { label: 'Lost (Rank)', key: 'rank_lost_is', invert: true, bad: 0.3 },
                        ].map(m => {
                            const val = impressionShare.summary[m.key]
                            if (val == null) return null
                            const pct = (val * 100).toFixed(1)
                            const color = m.invert
                                ? (val > (m.bad || 0.3) ? C.danger : val > 0.1 ? C.warning : C.success)
                                : (val > (m.good || 0.5) ? C.success : val > 0.3 ? C.warning : C.danger)
                            return (
                                <div key={m.key}>
                                    <div style={{ fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                                        {m.label}
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, marginBottom: 4 }}>
                                        <span style={{ fontSize: 20, fontWeight: 700, color, fontFamily: 'Syne' }}>
                                            {pct}
                                        </span>
                                        <span style={{ fontSize: 12, color: C.w40 }}>%</span>
                                    </div>
                                    <div style={{ height: 4, borderRadius: 2, background: C.w06 }}>
                                        <div style={{ height: '100%', borderRadius: 2, background: color, width: `${Math.min(parseFloat(pct), 100)}%`, transition: 'width 0.3s' }} />
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>
            )}

            {/* Quick script preview / execute / result modal */}
            {modalState && (
                <ScriptRunModal
                    state={modalState}
                    onExecute={executeScript}
                    onClose={() => setModalState(null)}
                    onViewHistory={() => { setModalState(null); navigate('/action-history') }}
                />
            )}

        </div>
    )
}

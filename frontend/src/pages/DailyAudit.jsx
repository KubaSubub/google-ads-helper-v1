import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    AlertTriangle, Ban, CheckCircle2, ChevronDown, ChevronRight, Clock,
    DollarSign, Loader2, Pause, RefreshCw,
    Search, Shield, ShieldAlert, TrendingDown,
    TrendingUp, XCircle,
} from 'lucide-react'
import { useApp } from '../contexts/AppContext'
import EmptyState from '../components/EmptyState'
import { BudgetPacingModule, KpiCard as KpiChip } from '../components/modules'
import { C, T, S, R, B, PILL, TOOLTIP_STYLE, SEVERITY, TRANSITION, FONT } from '../constants/designTokens'
import api from '../api'

// ─── API calls ───
const getDailyAudit = (clientId) => api.get('/daily-audit/', { params: { client_id: clientId } })
const getBulkRecommendations = (clientId, category, dryRun = true) =>
    api.post('/recommendations/bulk-apply', { client_id: clientId, category, dry_run: dryRun })

// ─── Styles ───
const CARD = {
    background: C.w03,
    border: B.card,
    borderRadius: R.card,
}
const SECTION_TITLE = {
    ...T.caption, letterSpacing: '0.1em', marginBottom: 12,
}
const SEVERITY_COLOR = { high: C.danger, medium: C.warning, low: C.accentBlue }

// ─── Polish pluralization helper ───
function pluralize(n, one, few, many) {
    if (n === 1) return one
    const mod10 = n % 10
    const mod100 = n % 100
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few
    return many
}

// KpiChip imported from components/modules (aliased as KpiChip, uses size="sm")

// ─── Category labels ───
const CATEGORY_LABELS = {
    clean_waste: 'Wyczyść śmieci',
    pause_burning: 'Pauzuj spalające',
    boost_winners: 'Boost winnerów',
    emergency_brake: 'Hamulec awaryjny',
}
const CATEGORY_COLORS = {
    clean_waste: C.danger,
    pause_burning: C.warning,
    boost_winners: C.success,
    emergency_brake: C.danger,
}

// ─── Script result modal ───
function ScriptResultModal({ result, category, onClose }) {
    if (!result) return null
    const color = CATEGORY_COLORS[category] || C.accentBlue
    const label = CATEGORY_LABELS[category] || category
    const hasErrors = result.errors && result.errors.length > 0

    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 100,
            background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
        }} onClick={onClose}>
            <div style={{
                background: C.surfaceElevated, border: B.medium,
                borderRadius: R.modal, padding: '24px 28px', minWidth: 380, maxWidth: 520,
                maxHeight: '80vh', overflowY: 'auto',
                boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
            }} onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
                    <div style={{
                        width: 36, height: 36, borderRadius: 9,
                        background: `${color}15`, display: 'flex',
                        alignItems: 'center', justifyContent: 'center',
                    }}>
                        {result.applied > 0 && result.failed === 0
                            ? <CheckCircle2 size={18} style={{ color }} />
                            : hasErrors
                                ? <AlertTriangle size={18} style={{ color: C.warning }} />
                                : <CheckCircle2 size={18} style={{ color }} />
                        }
                    </div>
                    <div>
                        <div style={{ fontSize: 15, fontWeight: 700, color: C.textPrimary, fontFamily: FONT.display }}>{label}</div>
                        <div style={{ fontSize: 11, color: C.w40, marginTop: 1 }}>
                            Zakończono • {result.total_matching || 0} {pluralize(result.total_matching || 0, 'rekomendacja', 'rekomendacje', 'rekomendacji')}
                            {result.total_skipped > 0 && (
                                <span style={{ color: C.w25 }}> • {result.total_skipped} pominiętych</span>
                            )}
                        </div>
                    </div>
                </div>

                {/* Stats */}
                <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
                    <div style={{
                        flex: 1, padding: '10px 14px', borderRadius: R.md,
                        background: C.successBg, border: B.success,
                    }}>
                        <div style={{ fontSize: 20, fontWeight: 700, color: C.success, fontFamily: FONT.display }}>{result.applied || 0}</div>
                        <div style={{ ...T.caption }}>Wykonane</div>
                    </div>
                    {result.failed > 0 && (
                        <div style={{
                            flex: 1, padding: '10px 14px', borderRadius: R.md,
                            background: C.dangerBg, border: B.danger,
                        }}>
                            <div style={{ fontSize: 20, fontWeight: 700, color: C.danger, fontFamily: FONT.display }}>{result.failed}</div>
                            <div style={{ ...T.caption }}>Błędów</div>
                        </div>
                    )}
                </div>

                {/* Items list */}
                {result.items && result.items.length > 0 && (
                    <div style={{ marginBottom: 16 }}>
                        <div style={{ ...T.caption, color: C.textDim, marginBottom: 8 }}>
                            {result.dry_run ? 'Do wykonania' : 'Szczegóły zmian'}
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 220, overflowY: 'auto' }}>
                            {result.items.map((item, i) => {
                                const isSuccess = item.status === 'success'
                                const isFailed = item.status === 'failed'
                                const iconColor = isSuccess ? C.success : isFailed ? C.danger : C.w25
                                return (
                                    <div key={item.id || i} style={{
                                        padding: '8px 12px', borderRadius: 7,
                                        background: isSuccess ? 'rgba(74,222,128,0.04)' : isFailed ? 'rgba(248,113,113,0.04)' : C.w03,
                                        border: `1px solid ${isSuccess ? 'rgba(74,222,128,0.12)' : isFailed ? 'rgba(248,113,113,0.12)' : C.w06}`,
                                        fontSize: 12, color: C.w70,
                                        display: 'flex', alignItems: 'center', gap: 8,
                                    }}>
                                        {isSuccess
                                            ? <CheckCircle2 size={12} style={{ color: iconColor, flexShrink: 0 }} />
                                            : isFailed
                                                ? <XCircle size={12} style={{ color: iconColor, flexShrink: 0 }} />
                                                : <Clock size={12} style={{ color: iconColor, flexShrink: 0 }} />
                                        }
                                        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                            {item.summary || `${item.action_type} #${item.id}`}
                                        </span>
                                        {item.estimated_savings_usd > 0 && (
                                            <span style={{ fontSize: 10, color: isSuccess ? C.success : C.textDim, fontWeight: 500, flexShrink: 0 }}>
                                                ~${item.estimated_savings_usd.toFixed(2)}
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
                        <div style={{ ...T.caption, color: C.textDim, marginBottom: 8 }}>
                            Błędy
                        </div>
                        {result.errors.map((err, i) => (
                            <div key={i} style={{
                                padding: '6px 10px', borderRadius: R.sm, marginBottom: 3,
                                background: C.dangerBg, border: `1px solid ${C.dangerBorder}`,
                                fontSize: 11, color: C.danger,
                            }}>
                                {err}
                            </div>
                        ))}
                    </div>
                )}

                {/* Close button */}
                <button onClick={onClose} style={{
                    width: '100%', padding: '10px 0', borderRadius: R.md,
                    border: B.medium, background: C.w04,
                    color: C.w60, fontSize: 12, fontWeight: 500,
                    cursor: 'pointer', transition: TRANSITION.fast,
                }} className="hover:bg-white/[0.06]">
                    Zamknij
                </button>
            </div>
        </div>
    )
}

// ─── Quick script button ───
function QuickScript({ icon: Icon, label, description, color, onClick, loading: scriptLoading, count }) {
    return (
        <button onClick={onClick} disabled={scriptLoading || count === 0} style={{
            ...CARD, padding: '14px 16px', textAlign: 'left', cursor: count === 0 ? 'default' : 'pointer',
            opacity: count === 0 ? 0.4 : 1, transition: TRANSITION.fast, flex: '1 1 200px', minWidth: 180,
            borderColor: count > 0 ? `${color}30` : C.w07,
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <div style={{ width: 28, height: 28, borderRadius: 7, background: `${color}15`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {scriptLoading ? <Loader2 size={13} style={{ color }} className="animate-spin" /> : <Icon size={13} style={{ color }} />}
                </div>
                <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: C.textPrimary }}>{label}</div>
                    {count > 0 && <span style={{ fontSize: 10, color, fontWeight: 600 }}>{count} do wykonania</span>}
                </div>
            </div>
            <div style={{ fontSize: 11, color: C.w40, lineHeight: 1.4 }}>{description}</div>
        </button>
    )
}

// ─── Main component ───
export default function DailyAudit() {
    const { selectedClientId, showToast } = useApp()
    const navigate = useNavigate()
    const [audit, setAudit] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [scriptCounts, setScriptCounts] = useState({})
    const [scriptLoading, setScriptLoading] = useState({})
    const [scriptResults, setScriptResults] = useState({})
    const [scriptsExpanded, setScriptsExpanded] = useState(null) // null = auto, true/false = manual
    const [resultModal, setResultModal] = useState(null) // { category, result }

    const loadAudit = useCallback(async () => {
        if (!selectedClientId) return
        setLoading(true); setError(null)
        try {
            const res = await getDailyAudit(selectedClientId)
            setAudit(res)
        } catch (err) { setError(err.message) }
        finally { setLoading(false) }
    }, [selectedClientId])

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

    useEffect(() => { loadAudit(); loadScriptCounts() }, [loadAudit, loadScriptCounts])

    const runScript = async (category) => {
        setScriptLoading(prev => ({ ...prev, [category]: true }))
        try {
            const res = await getBulkRecommendations(selectedClientId, category, false)
            setScriptResults(prev => ({ ...prev, [category]: res }))
            setResultModal({ category, result: res })
            loadAudit()
            loadScriptCounts()
        } catch (err) { showToast(`Błąd: ${err.message}`, 'error') }
        finally { setScriptLoading(prev => ({ ...prev, [category]: false })) }
    }

    if (!selectedClientId) return <EmptyState message="Wybierz klienta w sidebarze" />

    if (loading) return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 400 }}>
            <Loader2 size={32} style={{ color: C.accentBlue }} className="animate-spin" />
        </div>
    )

    if (error) return (
        <div style={{ textAlign: 'center', padding: 48 }}>
            <AlertTriangle size={32} style={{ color: C.danger, margin: '0 auto 12px' }} />
            <div style={{ fontSize: 13, color: C.w50, marginBottom: 12 }}>{error}</div>
            <button onClick={loadAudit} style={{ padding: '6px 16px', borderRadius: 7, background: C.accentBlue, color: 'white', border: 'none', cursor: 'pointer', fontSize: 12 }}>
                Ponów
            </button>
        </div>
    )

    const d = audit || {}
    const kpi = d.kpi_snapshot || {}
    const health = d.health_summary || {}
    const anomalies = d.anomalies_24h || []
    const disapproved = d.disapproved_ads || []
    const budgetCapped = d.budget_capped_performers || []
    const searchTerms = d.search_terms_needing_action || []
    const recs = d.pending_recommendations || {}
    const periodDays = kpi.period_days || 3

    // All alerts combined for banner
    const allAlerts = [
        ...anomalies.map(a => ({ ...a, kind: 'anomaly' })),
        ...disapproved.map(a => ({ ...a, kind: 'disapproved', severity: 'high' })),
        ...budgetCapped.map(a => ({ ...a, kind: 'budget_capped', severity: 'medium' })),
    ]
    const hasHighSeverity = allAlerts.some(a => a.severity === 'high')

    // Severity counts for status badge
    const criticalCount = anomalies.filter(a => a.severity === 'high').length + disapproved.length
    const warningCount = anomalies.filter(a => a.severity === 'medium').length + budgetCapped.length
    const overallStatus = criticalCount > 0 ? 'critical' : warningCount > 0 ? 'warning' : 'ok'

    // Total script actions available
    const totalScriptActions = Object.values(scriptCounts).reduce((a, b) => a + b, 0)

    return (
        <div style={{ maxWidth: 1400 }}>
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 20 }}>
                <div>
                    <h1 style={T.pageTitle}>
                        Poranny Przegląd
                    </h1>
                    <p style={T.pageSubtitle}>
                        Ostatnie {periodDays} dni &middot; {health.total_active_campaigns || 0} {pluralize(health.total_active_campaigns || 0, 'kampania', 'kampanie', 'kampanii')} &middot; {health.total_enabled_keywords || 0} słów kluczowych
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    {/* Status badge */}
                    <div style={{
                        display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 999,
                        background: overallStatus === 'critical' ? 'rgba(248,113,113,0.12)' : overallStatus === 'warning' ? 'rgba(251,191,36,0.12)' : 'rgba(74,222,128,0.12)',
                        border: `1px solid ${overallStatus === 'critical' ? 'rgba(248,113,113,0.3)' : overallStatus === 'warning' ? C.warningBorder : C.successBorder}`,
                    }}>
                        {overallStatus === 'critical' ? <ShieldAlert size={13} style={{ color: C.danger }} /> :
                         overallStatus === 'warning' ? <AlertTriangle size={13} style={{ color: C.warning }} /> :
                         <CheckCircle2 size={13} style={{ color: C.success }} />}
                        <span style={{ fontSize: 12, fontWeight: 600, color: overallStatus === 'critical' ? C.danger : overallStatus === 'warning' ? C.warning : C.success }}>
                            {overallStatus === 'critical'
                                ? `${criticalCount} ${pluralize(criticalCount, 'krytyczny', 'krytyczne', 'krytycznych')}`
                                : overallStatus === 'warning'
                                ? `${warningCount} ${pluralize(warningCount, 'ostrzeżenie', 'ostrzeżenia', 'ostrzeżeń')}`
                                : 'Wszystko OK'}
                        </span>
                    </div>
                    <button onClick={() => { loadAudit(); loadScriptCounts() }} style={{
                        padding: '6px 14px', borderRadius: 7, fontSize: 12, fontWeight: 500,
                        background: C.w04, border: B.medium,
                        color: C.w60, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
                    }}>
                        <RefreshCw size={12} />Odśwież
                    </button>
                </div>
            </div>

            {/* Alert banner — only when alerts exist */}
            {allAlerts.length > 0 && (
                <div style={{
                    background: hasHighSeverity ? 'rgba(248,113,113,0.10)' : 'rgba(251,191,36,0.10)',
                    border: `1px solid ${hasHighSeverity ? 'rgba(248,113,113,0.25)' : 'rgba(251,191,36,0.25)'}`,
                    borderRadius: 10, padding: '10px 16px', marginBottom: 16,
                    display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
                }}>
                    {hasHighSeverity
                        ? <ShieldAlert size={14} style={{ color: C.danger, flexShrink: 0 }} />
                        : <AlertTriangle size={14} style={{ color: C.warning, flexShrink: 0 }} />}
                    <span style={{ fontSize: 12, fontWeight: 600, color: hasHighSeverity ? C.danger : C.warning }}>
                        {allAlerts.length} {pluralize(allAlerts.length, 'alert wymaga', 'alerty wymagają', 'alertów wymaga')} uwagi
                    </span>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', flex: 1 }}>
                        {allAlerts.slice(0, 4).map((a, i) => (
                            <span key={i} style={{
                                fontSize: 11, color: C.w50, padding: '2px 8px',
                                background: C.w04, borderRadius: 6,
                                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 220,
                            }}>
                                {a.kind === 'anomaly' && (a.alert_type?.replace(/_/g, ' ') || a.message)}
                                {a.kind === 'disapproved' && `Odrzucona: ${a.headline_1 || 'reklama'}`}
                                {a.kind === 'budget_capped' && `Budżet: ${a.campaign_name}`}
                            </span>
                        ))}
                        {allAlerts.length > 4 && (
                            <span style={{ fontSize: 11, color: C.w30 }}>+{allAlerts.length - 4} więcej</span>
                        )}
                    </div>
                    <button onClick={() => navigate('/alerts')} style={{
                        padding: '4px 10px', borderRadius: 6, fontSize: 10, fontWeight: 500,
                        background: C.w06, border: B.medium,
                        color: C.w50, cursor: 'pointer', flexShrink: 0,
                        display: 'flex', alignItems: 'center', gap: 3,
                    }}>
                        Szczegóły <ChevronRight size={10} />
                    </button>
                </div>
            )}

            {/* ROW 1: KPIs (no Health Score — it's on Dashboard) */}
            {(!kpi.current_spend && !kpi.current_clicks && !kpi.current_conversions) ? (
                <div style={{ ...CARD, padding: '20px 24px', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
                    <Clock size={18} style={{ color: C.w25, flexShrink: 0 }} />
                    <div>
                        <div style={{ fontSize: 13, color: C.w50 }}>
                            Brak danych za ostatnie {periodDays} dni
                        </div>
                        <div style={{ fontSize: 11, color: C.w25, marginTop: 2 }}>
                            Dane pojawią się po synchronizacji z aktywnym kontem Google Ads
                        </div>
                    </div>
                </div>
            ) : (
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
                    <KpiChip label="Wydatki" current={kpi.current_spend} previous={kpi.previous_spend} suffix=" zł" size="sm" />
                    <KpiChip label="Kliknięcia" current={kpi.current_clicks} previous={kpi.previous_clicks} size="sm" />
                    <KpiChip label="Konwersje" current={kpi.current_conversions} previous={kpi.previous_conversions} size="sm" />
                </div>
            )}

            {/* ROW 2: Quick Optimization Scripts — collapsed by default */}
            <div style={{ marginBottom: 16 }}>
                <div
                    onClick={() => setScriptsExpanded(prev => !prev)}
                    style={{ ...SECTION_TITLE, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, userSelect: 'none' }}
                >
                    <span>Szybkie skrypty optymalizacji</span>
                    {totalScriptActions > 0 && (
                        <span style={{ fontSize: 10, fontWeight: 600, color: C.accentBlue, background: 'rgba(79,142,247,0.12)', padding: '1px 6px', borderRadius: 999 }}>
                            {totalScriptActions}
                        </span>
                    )}
                    <span style={{ fontSize: 10, color: C.w20, fontStyle: 'italic' }}>(zaawansowane)</span>
                    <ChevronDown size={12} style={{
                        color: C.w25,
                        transform: scriptsExpanded ? 'rotate(180deg)' : 'none',
                        transition: 'transform 0.2s',
                    }} />
                </div>
                {scriptsExpanded && (
                    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                        <QuickScript icon={XCircle} label="Wyczyść śmieci" description="Dodaj negatywy dla nieistotnych fraz wyszukiwania"
                            color="#F87171" count={scriptCounts.clean_waste || 0}
                            loading={scriptLoading.clean_waste} onClick={() => runScript('clean_waste')} />
                        <QuickScript icon={Pause} label="Pauzuj spalające" description="Wstrzymaj słowa kluczowe bez konwersji z wysokim kosztem"
                            color="#FBBF24" count={scriptCounts.pause_burning || 0}
                            loading={scriptLoading.pause_burning} onClick={() => runScript('pause_burning')} />
                        <QuickScript icon={TrendingUp} label="Boost winnerów" description="Zwiększ budżet kampanii z dobrym CPA i niskim IS"
                            color="#4ADE80" count={scriptCounts.boost_winners || 0}
                            loading={scriptLoading.boost_winners} onClick={() => runScript('boost_winners')} />
                        <QuickScript icon={Shield} label="Hamulec awaryjny" description="Obniż stawki i pauzuj przy ekstremalnym CPA"
                            color="#EF4444" count={scriptCounts.emergency_brake || 0}
                            loading={scriptLoading.emergency_brake} onClick={() => runScript('emergency_brake')} />
                    </div>
                )}
            </div>

            {/* ROW 3: Two columns — Search terms + Recommendations */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 14, marginBottom: 16 }}>
                {/* Search terms needing action */}
                <div style={{ ...CARD, padding: '16px 20px' }}>
                    <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
                        <div style={SECTION_TITLE}>Frazy do przejrzenia ({searchTerms.length})</div>
                        <button onClick={() => navigate('/search-terms')} style={{
                            fontSize: 10, color: C.accentBlue, background: 'none', border: 'none', cursor: 'pointer',
                            display: 'flex', alignItems: 'center', gap: 3,
                        }}>
                            Wszystkie <ChevronRight size={10} />
                        </button>
                    </div>
                    {searchTerms.length === 0 ? (
                        <div style={{ padding: '24px 0', textAlign: 'center', fontSize: 12, color: C.w30 }}>
                            Brak fraz wymagających akcji
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            {searchTerms.slice(0, 10).map((t, i) => (
                                <div key={i} style={{
                                    display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0',
                                    borderBottom: i < Math.min(searchTerms.length, 10) - 1 ? `1px solid ${C.w04}` : 'none',
                                }}>
                                    <Search size={10} style={{ color: C.w20, flexShrink: 0 }} />
                                    <span style={{ fontSize: 12, color: C.textPrimary, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {t.term || t.text}
                                    </span>
                                    <span style={{ fontSize: 10, color: C.textMuted, fontFamily: 'monospace', flexShrink: 0 }}>
                                        {t.clicks} klik | {t.cost_usd?.toFixed(2)} zł
                                    </span>
                                </div>
                            ))}
                            {searchTerms.length > 10 && (
                                <div style={{ fontSize: 11, color: C.w30, textAlign: 'center', paddingTop: 6 }}>
                                    +{searchTerms.length - 10} więcej
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Pending recommendations — grouped by rule type */}
                <div style={{ ...CARD, padding: '16px 20px' }}>
                    <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
                        <div style={SECTION_TITLE}>Oczekujące rekomendacje ({recs.total_pending || 0})</div>
                        <button onClick={() => navigate('/recommendations')} style={{
                            fontSize: 10, color: C.accentBlue, background: 'none', border: 'none', cursor: 'pointer',
                            display: 'flex', alignItems: 'center', gap: 3,
                        }}>
                            Wszystkie <ChevronRight size={10} />
                        </button>
                    </div>
                    {(recs.groups || []).length === 0 ? (
                        <div style={{ padding: '24px 0', textAlign: 'center', fontSize: 12, color: C.w30 }}>
                            Brak oczekujących rekomendacji
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {(recs.groups || []).map((g, gi) => {
                                const prioColor = g.max_priority === 'HIGH' ? C.danger : g.max_priority === 'MEDIUM' ? C.warning : C.accentBlue
                                return (
                                    <div key={gi} style={{
                                        background: 'rgba(255,255,255,0.02)', border: B.subtle,
                                        borderRadius: 8, padding: '10px 12px',
                                    }}>
                                        {/* Group header */}
                                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: g.items?.length ? 8 : 0 }}>
                                            <span style={{ fontSize: 12, fontWeight: 600, color: C.textPrimary }}>{g.label}</span>
                                            <span style={{
                                                fontSize: 9, fontWeight: 600, padding: '2px 7px', borderRadius: 999,
                                                background: `${prioColor}18`, color: prioColor,
                                            }}>
                                                {g.count} {g.max_priority}
                                            </span>
                                        </div>
                                        {/* Top items */}
                                        {(g.items || []).map((item, ii) => (
                                            <div key={ii} style={{
                                                display: 'flex', alignItems: 'center', gap: 6,
                                                padding: '3px 6px', fontSize: 11,
                                            }}>
                                                <span style={{ color: C.w20 }}>&bull;</span>
                                                <span style={{ color: C.textPrimary, fontWeight: 500 }}>{item.entity_name}</span>
                                                {item.metric && (
                                                    <span style={{ color: item.metric.includes('0 konw') ? C.danger : C.success, fontSize: 10 }}>
                                                        {item.metric}
                                                    </span>
                                                )}
                                                {item.detail && (
                                                    <span style={{ color: C.w25, fontSize: 10 }}>{item.detail}</span>
                                                )}
                                            </div>
                                        ))}
                                        {g.count > 3 && (
                                            <div style={{ fontSize: 10, color: C.w20, fontStyle: 'italic', padding: '2px 6px' }}>
                                                +{g.count - 3} więcej...
                                            </div>
                                        )}
                                    </div>
                                )
                            })}
                        </div>
                    )}
                </div>
            </div>

            {/* ROW 4: Budget pacing overview (yesterday's data) */}
            <BudgetPacingModule
                campaigns={d.budget_pacing}
                variant="table"
                showLegend
            />

            {resultModal && (
                <ScriptResultModal
                    result={resultModal.result}
                    category={resultModal.category}
                    onClose={() => setResultModal(null)}
                />
            )}
        </div>
    )
}

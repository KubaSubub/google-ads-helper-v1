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
import api from '../api'

// ─── API calls ───
const getDailyAudit = (clientId) => api.get('/daily-audit/', { params: { client_id: clientId } })
const getBulkRecommendations = (clientId, category, dryRun = true) =>
    api.post('/recommendations/bulk-apply', { client_id: clientId, category, dry_run: dryRun })

// ─── Styles ───
const CARD = {
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: 12,
}
const SECTION_TITLE = {
    fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)',
    textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12,
}
const SEVERITY_COLOR = { high: '#F87171', medium: '#FBBF24', low: '#4F8EF7' }

// ─── Polish pluralization helper ───
function pluralize(n, one, few, many) {
    if (n === 1) return one
    const mod10 = n % 10
    const mod100 = n % 100
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few
    return many
}

// ─── KPI chip ───
function KpiChip({ label, current, previous, prefix = '', suffix = '' }) {
    const pct = previous > 0 ? ((current - previous) / previous * 100) : 0
    const isUp = pct > 0
    return (
        <div style={{ ...CARD, padding: '12px 16px', flex: '1 1 140px', minWidth: 120 }}>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>{label}</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1 }}>
                {prefix}{typeof current === 'number' ? current.toLocaleString('pl-PL', { maximumFractionDigits: 2 }) : '—'}{suffix}
            </div>
            {previous != null && previous > 0 && (
                <div style={{ fontSize: 10, marginTop: 4, display: 'flex', alignItems: 'center', gap: 3,
                    color: isUp ? '#4ADE80' : pct < 0 ? '#F87171' : 'rgba(255,255,255,0.25)' }}>
                    {isUp ? <TrendingUp size={10} /> : pct < 0 ? <TrendingDown size={10} /> : null}
                    <span>{Math.abs(pct).toFixed(1)}% vs poprz. okres</span>
                </div>
            )}
        </div>
    )
}

// ─── Category labels ───
const CATEGORY_LABELS = {
    clean_waste: 'Wyczyść śmieci',
    pause_burning: 'Pauzuj spalające',
    boost_winners: 'Boost winnerów',
    emergency_brake: 'Hamulec awaryjny',
}
const CATEGORY_COLORS = {
    clean_waste: '#F87171',
    pause_burning: '#FBBF24',
    boost_winners: '#4ADE80',
    emergency_brake: '#F87171',
}

// ─── Script result modal ───
function ScriptResultModal({ result, category, onClose }) {
    if (!result) return null
    const color = CATEGORY_COLORS[category] || '#4F8EF7'
    const label = CATEGORY_LABELS[category] || category
    const hasErrors = result.errors && result.errors.length > 0

    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 100,
            background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
        }} onClick={onClose}>
            <div style={{
                background: '#1A1D24', border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 14, padding: '24px 28px', minWidth: 380, maxWidth: 520,
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
                                ? <AlertTriangle size={18} style={{ color: '#FBBF24' }} />
                                : <CheckCircle2 size={18} style={{ color }} />
                        }
                    </div>
                    <div>
                        <div style={{ fontSize: 15, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne' }}>{label}</div>
                        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 1 }}>
                            Zakończono • {result.total_matching || 0} {pluralize(result.total_matching || 0, 'rekomendacja', 'rekomendacje', 'rekomendacji')}
                            {result.total_skipped > 0 && (
                                <span style={{ color: 'rgba(255,255,255,0.25)' }}> • {result.total_skipped} pominiętych</span>
                            )}
                        </div>
                    </div>
                </div>

                {/* Stats */}
                <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
                    <div style={{
                        flex: 1, padding: '10px 14px', borderRadius: 8,
                        background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.15)',
                    }}>
                        <div style={{ fontSize: 20, fontWeight: 700, color: '#4ADE80', fontFamily: 'Syne' }}>{result.applied || 0}</div>
                        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Wykonane</div>
                    </div>
                    {result.failed > 0 && (
                        <div style={{
                            flex: 1, padding: '10px 14px', borderRadius: 8,
                            background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.15)',
                        }}>
                            <div style={{ fontSize: 20, fontWeight: 700, color: '#F87171', fontFamily: 'Syne' }}>{result.failed}</div>
                            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Błędów</div>
                        </div>
                    )}
                </div>

                {/* Items list */}
                {result.items && result.items.length > 0 && (
                    <div style={{ marginBottom: 16 }}>
                        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
                            {result.dry_run ? 'Do wykonania' : 'Szczegóły zmian'}
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 220, overflowY: 'auto' }}>
                            {result.items.map((item, i) => {
                                const isSuccess = item.status === 'success'
                                const isFailed = item.status === 'failed'
                                const iconColor = isSuccess ? '#4ADE80' : isFailed ? '#F87171' : 'rgba(255,255,255,0.25)'
                                return (
                                    <div key={item.id || i} style={{
                                        padding: '8px 12px', borderRadius: 7,
                                        background: isSuccess ? 'rgba(74,222,128,0.04)' : isFailed ? 'rgba(248,113,113,0.04)' : 'rgba(255,255,255,0.03)',
                                        border: `1px solid ${isSuccess ? 'rgba(74,222,128,0.12)' : isFailed ? 'rgba(248,113,113,0.12)' : 'rgba(255,255,255,0.06)'}`,
                                        fontSize: 12, color: 'rgba(255,255,255,0.7)',
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
                                            <span style={{ fontSize: 10, color: isSuccess ? '#4ADE80' : 'rgba(255,255,255,0.3)', fontWeight: 500, flexShrink: 0 }}>
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
                        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
                            Błędy
                        </div>
                        {result.errors.map((err, i) => (
                            <div key={i} style={{
                                padding: '6px 10px', borderRadius: 6, marginBottom: 3,
                                background: 'rgba(248,113,113,0.06)', border: '1px solid rgba(248,113,113,0.1)',
                                fontSize: 11, color: '#F87171',
                            }}>
                                {err}
                            </div>
                        ))}
                    </div>
                )}

                {/* Close button */}
                <button onClick={onClose} style={{
                    width: '100%', padding: '10px 0', borderRadius: 8,
                    border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.04)',
                    color: 'rgba(255,255,255,0.6)', fontSize: 12, fontWeight: 500,
                    cursor: 'pointer', transition: 'all 0.15s',
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
            opacity: count === 0 ? 0.4 : 1, transition: 'all 0.15s', flex: '1 1 200px', minWidth: 180,
            borderColor: count > 0 ? `${color}30` : 'rgba(255,255,255,0.07)',
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <div style={{ width: 28, height: 28, borderRadius: 7, background: `${color}15`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {scriptLoading ? <Loader2 size={13} style={{ color }} className="animate-spin" /> : <Icon size={13} style={{ color }} />}
                </div>
                <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#F0F0F0' }}>{label}</div>
                    {count > 0 && <span style={{ fontSize: 10, color, fontWeight: 600 }}>{count} do wykonania</span>}
                </div>
            </div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', lineHeight: 1.4 }}>{description}</div>
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
            <Loader2 size={32} style={{ color: '#4F8EF7' }} className="animate-spin" />
        </div>
    )

    if (error) return (
        <div style={{ textAlign: 'center', padding: 48 }}>
            <AlertTriangle size={32} style={{ color: '#F87171', margin: '0 auto 12px' }} />
            <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.5)', marginBottom: 12 }}>{error}</div>
            <button onClick={loadAudit} style={{ padding: '6px 16px', borderRadius: 7, background: '#4F8EF7', color: 'white', border: 'none', cursor: 'pointer', fontSize: 12 }}>
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
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Poranny Przegląd
                    </h1>
                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                        Ostatnie {periodDays} dni &middot; {health.total_active_campaigns || 0} {pluralize(health.total_active_campaigns || 0, 'kampania', 'kampanie', 'kampanii')} &middot; {health.total_enabled_keywords || 0} słów kluczowych
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    {/* Status badge */}
                    <div style={{
                        display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 999,
                        background: overallStatus === 'critical' ? 'rgba(248,113,113,0.12)' : overallStatus === 'warning' ? 'rgba(251,191,36,0.12)' : 'rgba(74,222,128,0.12)',
                        border: `1px solid ${overallStatus === 'critical' ? 'rgba(248,113,113,0.3)' : overallStatus === 'warning' ? 'rgba(251,191,36,0.3)' : 'rgba(74,222,128,0.3)'}`,
                    }}>
                        {overallStatus === 'critical' ? <ShieldAlert size={13} style={{ color: '#F87171' }} /> :
                         overallStatus === 'warning' ? <AlertTriangle size={13} style={{ color: '#FBBF24' }} /> :
                         <CheckCircle2 size={13} style={{ color: '#4ADE80' }} />}
                        <span style={{ fontSize: 12, fontWeight: 600, color: overallStatus === 'critical' ? '#F87171' : overallStatus === 'warning' ? '#FBBF24' : '#4ADE80' }}>
                            {overallStatus === 'critical'
                                ? `${criticalCount} ${pluralize(criticalCount, 'krytyczny', 'krytyczne', 'krytycznych')}`
                                : overallStatus === 'warning'
                                ? `${warningCount} ${pluralize(warningCount, 'ostrzeżenie', 'ostrzeżenia', 'ostrzeżeń')}`
                                : 'Wszystko OK'}
                        </span>
                    </div>
                    <button onClick={() => { loadAudit(); loadScriptCounts() }} style={{
                        padding: '6px 14px', borderRadius: 7, fontSize: 12, fontWeight: 500,
                        background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)',
                        color: 'rgba(255,255,255,0.6)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
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
                        ? <ShieldAlert size={14} style={{ color: '#F87171', flexShrink: 0 }} />
                        : <AlertTriangle size={14} style={{ color: '#FBBF24', flexShrink: 0 }} />}
                    <span style={{ fontSize: 12, fontWeight: 600, color: hasHighSeverity ? '#F87171' : '#FBBF24' }}>
                        {allAlerts.length} {pluralize(allAlerts.length, 'alert wymaga', 'alerty wymagają', 'alertów wymaga')} uwagi
                    </span>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', flex: 1 }}>
                        {allAlerts.slice(0, 4).map((a, i) => (
                            <span key={i} style={{
                                fontSize: 11, color: 'rgba(255,255,255,0.5)', padding: '2px 8px',
                                background: 'rgba(255,255,255,0.04)', borderRadius: 6,
                                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 220,
                            }}>
                                {a.kind === 'anomaly' && (a.alert_type?.replace(/_/g, ' ') || a.message)}
                                {a.kind === 'disapproved' && `Odrzucona: ${a.headline_1 || 'reklama'}`}
                                {a.kind === 'budget_capped' && `Budżet: ${a.campaign_name}`}
                            </span>
                        ))}
                        {allAlerts.length > 4 && (
                            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>+{allAlerts.length - 4} więcej</span>
                        )}
                    </div>
                    <button onClick={() => navigate('/alerts')} style={{
                        padding: '4px 10px', borderRadius: 6, fontSize: 10, fontWeight: 500,
                        background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
                        color: 'rgba(255,255,255,0.5)', cursor: 'pointer', flexShrink: 0,
                        display: 'flex', alignItems: 'center', gap: 3,
                    }}>
                        Szczegóły <ChevronRight size={10} />
                    </button>
                </div>
            )}

            {/* ROW 1: KPIs (no Health Score — it's on Dashboard) */}
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
                <KpiChip label="Wydatki" current={kpi.current_spend} previous={kpi.previous_spend} suffix=" zł" />
                <KpiChip label="Kliknięcia" current={kpi.current_clicks} previous={kpi.previous_clicks} />
                <KpiChip label="Konwersje" current={kpi.current_conversions} previous={kpi.previous_conversions} />
            </div>

            {/* ROW 2: Quick Optimization Scripts — collapsed by default */}
            <div style={{ marginBottom: 16 }}>
                <div
                    onClick={() => setScriptsExpanded(prev => !prev)}
                    style={{ ...SECTION_TITLE, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, userSelect: 'none' }}
                >
                    <span>Szybkie skrypty optymalizacji</span>
                    {totalScriptActions > 0 && (
                        <span style={{ fontSize: 10, fontWeight: 600, color: '#4F8EF7', background: 'rgba(79,142,247,0.12)', padding: '1px 6px', borderRadius: 999 }}>
                            {totalScriptActions}
                        </span>
                    )}
                    <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.2)', fontStyle: 'italic' }}>(zaawansowane)</span>
                    <ChevronDown size={12} style={{
                        color: 'rgba(255,255,255,0.25)',
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
                            fontSize: 10, color: '#4F8EF7', background: 'none', border: 'none', cursor: 'pointer',
                            display: 'flex', alignItems: 'center', gap: 3,
                        }}>
                            Wszystkie <ChevronRight size={10} />
                        </button>
                    </div>
                    {searchTerms.length === 0 ? (
                        <div style={{ padding: '24px 0', textAlign: 'center', fontSize: 12, color: 'rgba(255,255,255,0.3)' }}>
                            Brak fraz wymagających akcji
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            {searchTerms.slice(0, 10).map((t, i) => (
                                <div key={i} style={{
                                    display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0',
                                    borderBottom: i < Math.min(searchTerms.length, 10) - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                                }}>
                                    <Search size={10} style={{ color: 'rgba(255,255,255,0.2)', flexShrink: 0 }} />
                                    <span style={{ fontSize: 12, color: '#F0F0F0', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {t.term || t.text}
                                    </span>
                                    <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', fontFamily: 'monospace', flexShrink: 0 }}>
                                        {t.clicks} klik | {t.cost_usd?.toFixed(2)} zł
                                    </span>
                                </div>
                            ))}
                            {searchTerms.length > 10 && (
                                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', textAlign: 'center', paddingTop: 6 }}>
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
                            fontSize: 10, color: '#4F8EF7', background: 'none', border: 'none', cursor: 'pointer',
                            display: 'flex', alignItems: 'center', gap: 3,
                        }}>
                            Wszystkie <ChevronRight size={10} />
                        </button>
                    </div>
                    {(recs.groups || []).length === 0 ? (
                        <div style={{ padding: '24px 0', textAlign: 'center', fontSize: 12, color: 'rgba(255,255,255,0.3)' }}>
                            Brak oczekujących rekomendacji
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {(recs.groups || []).map((g, gi) => {
                                const prioColor = g.max_priority === 'HIGH' ? '#F87171' : g.max_priority === 'MEDIUM' ? '#FBBF24' : '#4F8EF7'
                                return (
                                    <div key={gi} style={{
                                        background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)',
                                        borderRadius: 8, padding: '10px 12px',
                                    }}>
                                        {/* Group header */}
                                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: g.items?.length ? 8 : 0 }}>
                                            <span style={{ fontSize: 12, fontWeight: 600, color: '#F0F0F0' }}>{g.label}</span>
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
                                                <span style={{ color: 'rgba(255,255,255,0.2)' }}>&bull;</span>
                                                <span style={{ color: '#F0F0F0', fontWeight: 500 }}>{item.entity_name}</span>
                                                {item.metric && (
                                                    <span style={{ color: item.metric.includes('0 konw') ? '#F87171' : '#4ADE80', fontSize: 10 }}>
                                                        {item.metric}
                                                    </span>
                                                )}
                                                {item.detail && (
                                                    <span style={{ color: 'rgba(255,255,255,0.25)', fontSize: 10 }}>{item.detail}</span>
                                                )}
                                            </div>
                                        ))}
                                        {g.count > 3 && (
                                            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.2)', fontStyle: 'italic', padding: '2px 6px' }}>
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
            {(d.budget_pacing || []).length > 0 && (
                <div style={{ marginBottom: 16 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, ...SECTION_TITLE }}>
                        <span>Pacing budżetu kampanii</span>
                        {d.budget_pacing[0]?.reference_date && (
                            <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.2)', fontStyle: 'italic', textTransform: 'none', letterSpacing: 0 }}>
                                (dane z {d.budget_pacing[0].reference_date})
                            </span>
                        )}
                    </div>
                    <div className="v2-card" style={{ overflow: 'hidden' }}>
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                                        {['Kampania', 'Budżet dzienny', 'Wydane', 'Pacing', 'Status'].map(h => (
                                            <th key={h} style={{
                                                padding: '8px 12px', fontSize: 10, fontWeight: 500,
                                                color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase',
                                                letterSpacing: '0.08em', textAlign: 'left',
                                            }}>{h}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {(d.budget_pacing || []).map((c, i) => {
                                        const pct = c.pacing_pct || 0
                                        // Red = underspending (<50%), Yellow = moderate (50-80%), Green = on track (80%+), Red again if overspend (>120%)
                                        const barColor = pct > 120 ? '#F87171' : pct >= 80 ? '#4ADE80' : pct >= 50 ? '#FBBF24' : '#F87171'
                                        // Build LIMITED tooltip
                                        const limitedParts = []
                                        if (c.budget_lost_is > 0) limitedParts.push(`IS utracone: ${c.budget_lost_is}%`)
                                        if (c.budget_lost_top_is > 0) limitedParts.push(`Top IS utracone: ${c.budget_lost_top_is}%`)
                                        if (c.budget_lost_abs_top_is > 0) limitedParts.push(`Abs Top IS utracone: ${c.budget_lost_abs_top_is}%`)
                                        const limitedTooltip = limitedParts.join(' | ')
                                        return (
                                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                                <td style={{ padding: '8px 12px', fontSize: 12, color: '#F0F0F0', fontWeight: 500, maxWidth: 250 }}>
                                                    <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.campaign_name}</span>
                                                </td>
                                                <td style={{ padding: '8px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.6)' }}>
                                                    {c.daily_budget?.toFixed(2)} zł
                                                </td>
                                                <td style={{ padding: '8px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.6)' }}>
                                                    {(c.spent ?? c.spent_today)?.toFixed(2)} zł
                                                </td>
                                                <td style={{ padding: '8px 12px', width: 160 }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                                        <div style={{ flex: 1, height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.06)' }}>
                                                            <div style={{ width: `${Math.min(pct, 100)}%`, height: '100%', borderRadius: 2, background: barColor, transition: 'width 0.3s' }} />
                                                        </div>
                                                        <span style={{ fontSize: 10, color: barColor, fontWeight: 600, minWidth: 32, textAlign: 'right' }}>{pct.toFixed(0)}%</span>
                                                    </div>
                                                </td>
                                                <td style={{ padding: '8px 12px' }}>
                                                    {c.is_limited && (
                                                        <span style={{
                                                            fontSize: 9, fontWeight: 600, padding: '2px 6px', borderRadius: 999,
                                                            background: 'rgba(251,191,36,0.12)', color: '#FBBF24',
                                                            border: '1px solid rgba(251,191,36,0.25)',
                                                        }}>
                                                            LIMITED
                                                        </span>
                                                    )}
                                                </td>
                                            </tr>
                                        )
                                    })}
                                </tbody>
                            </table>
                        </div>
                        {/* Legend */}
                        <div style={{
                            padding: '8px 12px', borderTop: '1px solid rgba(255,255,255,0.04)',
                            display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center',
                        }}>
                            {[
                                { color: '#F87171', label: '< 50% — niedostateczne wydawanie' },
                                { color: '#FBBF24', label: '50–80% — umiarkowane' },
                                { color: '#4ADE80', label: '80–120% — zgodnie z planem' },
                                { color: '#F87171', label: '> 120% — przekroczenie budżetu' },
                            ].map((item, i) => (
                                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                                    <div style={{ width: 8, height: 8, borderRadius: 2, background: item.color, flexShrink: 0 }} />
                                    <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)' }}>{item.label}</span>
                                </div>
                            ))}
                            <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                                <span style={{ fontSize: 9, fontWeight: 600, padding: '1px 4px', borderRadius: 3, background: 'rgba(251,191,36,0.12)', color: '#FBBF24' }}>LIMITED</span>
                                <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)' }}>— kampania traci IS z powodu budżetu (najedź aby zobaczyć szczegóły)</span>
                            </div>
                        </div>
                    </div>
                </div>
            )}

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

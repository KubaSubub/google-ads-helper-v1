import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    AlertTriangle, Ban, CheckCircle2, ChevronRight, Clock,
    DollarSign, Flame, Loader2, Pause, RefreshCw,
    Search, Shield, ShieldAlert, Target, TrendingDown,
    TrendingUp, Zap, XCircle, Sparkles, Play, Eye,
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

// ─── Health gauge (inline) ───
function MiniGauge({ score }) {
    const color = score > 70 ? '#4ADE80' : score > 40 ? '#FBBF24' : '#F87171'
    const r = 22, circ = 2 * Math.PI * r, off = circ * (1 - score / 100)
    return (
        <div style={{ position: 'relative', width: 52, height: 52, flexShrink: 0 }}>
            <svg width="52" height="52" viewBox="0 0 52 52">
                <circle cx="26" cy="26" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="4" />
                <circle cx="26" cy="26" r={r} fill="none" stroke={color} strokeWidth="4"
                    strokeDasharray={circ} strokeDashoffset={off} strokeLinecap="round"
                    transform="rotate(-90 26 26)" style={{ transition: 'stroke-dashoffset 0.6s ease' }} />
            </svg>
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <span style={{ fontSize: 15, fontWeight: 700, color, fontFamily: 'Syne' }}>{score}</span>
            </div>
        </div>
    )
}

// ─── KPI chip ───
function KpiChip({ label, today, yesterday, prefix = '', suffix = '' }) {
    const pct = yesterday > 0 ? ((today - yesterday) / yesterday * 100) : 0
    const isUp = pct > 0
    return (
        <div style={{ ...CARD, padding: '12px 16px', flex: '1 1 140px', minWidth: 120 }}>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>{label}</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1 }}>
                {prefix}{typeof today === 'number' ? today.toLocaleString('pl-PL', { maximumFractionDigits: 2 }) : '—'}{suffix}
            </div>
            {yesterday != null && (
                <div style={{ fontSize: 10, marginTop: 4, display: 'flex', alignItems: 'center', gap: 3,
                    color: isUp ? '#4ADE80' : pct < 0 ? '#F87171' : 'rgba(255,255,255,0.25)' }}>
                    {isUp ? <TrendingUp size={10} /> : pct < 0 ? <TrendingDown size={10} /> : null}
                    <span>{Math.abs(pct).toFixed(1)}% vs wczoraj</span>
                </div>
            )}
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
    }, [selectedClientId])

    useEffect(() => { loadAudit(); loadScriptCounts() }, [loadAudit, loadScriptCounts])

    const runScript = async (category) => {
        setScriptLoading(prev => ({ ...prev, [category]: true }))
        try {
            const res = await getBulkRecommendations(selectedClientId, category, false)
            setScriptResults(prev => ({ ...prev, [category]: res }))
            showToast(`Wykonano: ${res.applied || 0} akcji, ${res.failed || 0} bledow`, res.failed > 0 ? 'warning' : 'success')
            loadAudit()
            loadScriptCounts()
        } catch (err) { showToast(`Blad: ${err.message}`, 'error') }
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
                Ponow
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

    // Severity counts
    const criticalCount = anomalies.filter(a => a.severity === 'high').length + disapproved.length
    const warningCount = anomalies.filter(a => a.severity === 'medium').length + budgetCapped.length
    const overallStatus = criticalCount > 0 ? 'critical' : warningCount > 0 ? 'warning' : 'ok'

    return (
        <div style={{ maxWidth: 1400 }}>
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 20 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Codzienny Audyt
                    </h1>
                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                        Wszystko co musisz sprawdzic kazdego ranka
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
                            {overallStatus === 'critical' ? `${criticalCount} krytycznych` : overallStatus === 'warning' ? `${warningCount} ostrzezen` : 'Wszystko OK'}
                        </span>
                    </div>
                    <button onClick={() => { loadAudit(); loadScriptCounts() }} style={{
                        padding: '6px 14px', borderRadius: 7, fontSize: 12, fontWeight: 500,
                        background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)',
                        color: 'rgba(255,255,255,0.6)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
                    }}>
                        <RefreshCw size={12} />Odswiez
                    </button>
                </div>
            </div>

            {/* ROW 1: KPIs + Health */}
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
                <KpiChip label="Wydatki" today={kpi.today_spend} yesterday={kpi.yesterday_spend} suffix=" zl" />
                <KpiChip label="Klikniecia" today={kpi.today_clicks} yesterday={kpi.yesterday_clicks} />
                <KpiChip label="Konwersje" today={kpi.today_conversions} yesterday={kpi.yesterday_conversions} />
                <div style={{ ...CARD, padding: '12px 16px', flex: '1 1 200px', minWidth: 180, display: 'flex', alignItems: 'center', gap: 14 }}>
                    <MiniGauge score={health.health_score || 0} />
                    <div>
                        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>Health Score</div>
                        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)' }}>
                            {health.total_active_campaigns || 0} kampanii | {health.total_enabled_keywords || 0} slow kluczowych
                        </div>
                    </div>
                </div>
            </div>

            {/* ROW 2: Alerts section */}
            {(anomalies.length > 0 || disapproved.length > 0 || budgetCapped.length > 0) && (
                <div style={{ marginBottom: 16 }}>
                    <div style={SECTION_TITLE}>Alerty wymagajace uwagi</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        {/* Anomalies */}
                        {anomalies.map((a, i) => (
                            <div key={`anom-${i}`} style={{
                                ...CARD, padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 10,
                                borderColor: SEVERITY_COLOR[a.severity] + '30',
                            }}>
                                <div style={{ width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
                                    background: SEVERITY_COLOR[a.severity], boxShadow: `0 0 6px ${SEVERITY_COLOR[a.severity]}` }} />
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <span style={{ fontSize: 12, fontWeight: 500, color: '#F0F0F0' }}>{a.alert_type?.replace(/_/g, ' ')}</span>
                                    {a.campaign_name && <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', marginLeft: 8 }}>{a.campaign_name}</span>}
                                </div>
                                <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', flexShrink: 0 }}>{a.message || ''}</span>
                                <button onClick={() => navigate('/alerts')} style={{ padding: '3px 8px', borderRadius: 5, fontSize: 10, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.4)', cursor: 'pointer' }}>
                                    <ChevronRight size={10} />
                                </button>
                            </div>
                        ))}

                        {/* Disapproved ads */}
                        {disapproved.map((ad, i) => (
                            <div key={`dis-${i}`} style={{
                                ...CARD, padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 10,
                                borderColor: 'rgba(248,113,113,0.3)',
                            }}>
                                <Ban size={13} style={{ color: '#F87171', flexShrink: 0 }} />
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <span style={{ fontSize: 12, fontWeight: 500, color: '#F87171' }}>Odrzucona reklama</span>
                                    <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', marginLeft: 8 }}>{ad.headline_1 || 'Bez naglowka'}</span>
                                </div>
                                <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)' }}>{ad.campaign_name}</span>
                                <span style={{
                                    fontSize: 9, fontWeight: 600, padding: '2px 6px', borderRadius: 999,
                                    background: ad.approval_status === 'DISAPPROVED' ? 'rgba(248,113,113,0.15)' : 'rgba(251,191,36,0.15)',
                                    color: ad.approval_status === 'DISAPPROVED' ? '#F87171' : '#FBBF24',
                                }}>{ad.approval_status}</span>
                            </div>
                        ))}

                        {/* Budget capped performers */}
                        {budgetCapped.map((c, i) => (
                            <div key={`bc-${i}`} style={{
                                ...CARD, padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 10,
                                borderColor: 'rgba(251,191,36,0.3)',
                            }}>
                                <DollarSign size={13} style={{ color: '#FBBF24', flexShrink: 0 }} />
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <span style={{ fontSize: 12, fontWeight: 500, color: '#FBBF24' }}>Ograniczona budzetem</span>
                                    <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', marginLeft: 8 }}>{c.campaign_name}</span>
                                </div>
                                <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>
                                    CPA: {(c.cpa_usd || c.cpa || 0).toFixed(2)} zl (sr. konta: {(c.account_avg_cpa_usd || c.account_avg_cpa || 0).toFixed(2)} zl)
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* ROW 3: Quick Optimization Scripts */}
            <div style={{ marginBottom: 16 }}>
                <div style={SECTION_TITLE}>Szybkie skrypty optymalizacji</div>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                    <QuickScript icon={XCircle} label="Wyczysc smieci" description="Dodaj negatywy dla nieistotnych fraz wyszukiwania"
                        color="#F87171" count={scriptCounts.clean_waste || 0}
                        loading={scriptLoading.clean_waste} onClick={() => runScript('clean_waste')} />
                    <QuickScript icon={Pause} label="Pauzuj spalajace" description="Wstrzymaj slowa kluczowe bez konwersji z wysokim kosztem"
                        color="#FBBF24" count={scriptCounts.pause_burning || 0}
                        loading={scriptLoading.pause_burning} onClick={() => runScript('pause_burning')} />
                    <QuickScript icon={TrendingUp} label="Boost winnerow" description="Zwieksz budzet kampanii z dobrym CPA i niskim IS"
                        color="#4ADE80" count={scriptCounts.boost_winners || 0}
                        loading={scriptLoading.boost_winners} onClick={() => runScript('boost_winners')} />
                    <QuickScript icon={Shield} label="Hamulec awaryjny" description="Obniż stawki i pauzuj przy ekstremalnym CPA"
                        color="#EF4444" count={scriptCounts.emergency_brake || 0}
                        loading={scriptLoading.emergency_brake} onClick={() => runScript('emergency_brake')} />
                </div>
            </div>

            {/* ROW 4: Two columns — Search terms + Recommendations */}
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
                            Brak fraz wymagajacych akcji
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
                                        {t.clicks} klik | {t.cost_usd?.toFixed(2)} zl
                                    </span>
                                </div>
                            ))}
                            {searchTerms.length > 10 && (
                                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', textAlign: 'center', paddingTop: 6 }}>
                                    +{searchTerms.length - 10} wiecej
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Pending recommendations */}
                <div style={{ ...CARD, padding: '16px 20px' }}>
                    <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
                        <div style={SECTION_TITLE}>Oczekujace rekomendacje ({recs.total_pending || recs.total || 0})</div>
                        <button onClick={() => navigate('/recommendations')} style={{
                            fontSize: 10, color: '#4F8EF7', background: 'none', border: 'none', cursor: 'pointer',
                            display: 'flex', alignItems: 'center', gap: 3,
                        }}>
                            Wszystkie <ChevronRight size={10} />
                        </button>
                    </div>
                    {(recs.top_5 || recs.top || []).length === 0 ? (
                        <div style={{ padding: '24px 0', textAlign: 'center', fontSize: 12, color: 'rgba(255,255,255,0.3)' }}>
                            Brak oczekujacych rekomendacji
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            {(recs.top_5 || recs.top || []).map((r, i) => {
                                const priorityColor = r.priority === 'HIGH' ? '#F87171' : r.priority === 'MEDIUM' ? '#FBBF24' : '#4F8EF7'
                                return (
                                    <div key={i} style={{
                                        display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0',
                                        borderBottom: i < (recs.top_5 || recs.top || []).length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                                    }}>
                                        <span style={{
                                            fontSize: 8, fontWeight: 700, padding: '2px 5px', borderRadius: 3,
                                            background: `${priorityColor}15`, color: priorityColor,
                                        }}>
                                            {r.priority?.[0]}
                                        </span>
                                        <span style={{ fontSize: 12, color: '#F0F0F0', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                            {(r.action_type || r.type || '')?.replace(/_/g, ' ')}
                                        </span>
                                        <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', flexShrink: 0 }}>
                                            {r.campaign_name || ''}
                                        </span>
                                    </div>
                                )
                            })}
                        </div>
                    )}
                </div>
            </div>

            {/* ROW 5: Budget pacing overview */}
            {(d.budget_pacing || []).length > 0 && (
                <div style={{ marginBottom: 16 }}>
                    <div style={SECTION_TITLE}>Budget pacing kampanii</div>
                    <div className="v2-card" style={{ overflow: 'hidden' }}>
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                                        {['Kampania', 'Budzet dzienny', 'Wydane dzis', 'Pacing', 'Status'].map(h => (
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
                                        const barColor = pct > 100 ? '#F87171' : pct > 80 ? '#FBBF24' : '#4ADE80'
                                        return (
                                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                                <td style={{ padding: '8px 12px', fontSize: 12, color: '#F0F0F0', fontWeight: 500, maxWidth: 250 }}>
                                                    <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.campaign_name}</span>
                                                </td>
                                                <td style={{ padding: '8px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.6)' }}>
                                                    {c.daily_budget?.toFixed(2)} zl
                                                </td>
                                                <td style={{ padding: '8px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.6)' }}>
                                                    {c.spent_today?.toFixed(2)} zl
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
                                                        <span style={{ fontSize: 9, fontWeight: 600, padding: '2px 6px', borderRadius: 999, background: 'rgba(251,191,36,0.12)', color: '#FBBF24', border: '1px solid rgba(251,191,36,0.25)' }}>
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
                    </div>
                </div>
            )}
        </div>
    )
}

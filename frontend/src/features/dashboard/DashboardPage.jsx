import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { LineChart, Line, ResponsiveContainer, XAxis, Tooltip, CartesianGrid } from 'recharts'
import {
    ChevronRight, ChevronUp, ChevronDown,
    XCircle, Pause, TrendingUp, Shield, Loader2,
} from 'lucide-react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
    getDashboardKPIs, getCampaigns, getCampaignsSummary,
    getHealthScore, getRecommendations,
    getBudgetPacing, getDeviceBreakdown, getGeoBreakdown,
    getWastedSpend, getImpressionShare,
    getQualityScoreAudit,
    getScriptsCatalog, getScriptsCounts, dryRunScript,
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
import ScriptRunModal from './components/ScriptRunModal'
import BudgetPacingCard from './components/BudgetPacingCard'
import AnomalyAlertsCard from './components/AnomalyAlertsCard'

import { C, T, B, TOOLTIP_STYLE, TRANSITION } from '../../constants/designTokens'

// ─── Quick Scripts API ───────────────────────────────────────────────────────
const getBulkRecommendations = (clientId, category, dryRun = true, itemIds = null) =>
    api.post('/recommendations/bulk-apply', {
        client_id: clientId,
        category,
        dry_run: dryRun,
        ...(itemIds && itemIds.length ? { item_ids: itemIds } : {}),
    })

const CARD = { background: C.w03, border: B.card, borderRadius: 12 }

// Debounce a value so rapid filter-preset clicks don't trigger a request per tick.
// Kept short (100 ms) so the UX still feels snappy but thunderings herds collapse.
function useDebouncedValue(value, delay = 100) {
    const [debounced, setDebounced] = useState(value)
    useEffect(() => {
        const t = setTimeout(() => setDebounced(value), delay)
        return () => clearTimeout(t)
    }, [value, delay])
    return debounced
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
    const campaignParamsRaw = useMemo(() => {
        const p = { campaign_status: 'ENABLED' }
        if (filters.campaignType !== 'ALL') p.campaign_type = filters.campaignType
        return p
    }, [filters.campaignType])
    const allParamsRaw = useMemo(() => ({ ...dateParams, ...campaignParamsRaw }), [dateParams, campaignParamsRaw])

    // Debounce the fan-out triggers so rapid filter-preset clicks collapse into one batch.
    // 100 ms is short enough that user-initiated single clicks still feel instant.
    const campaignParams = useDebouncedValue(campaignParamsRaw, 100)
    const allParams = useDebouncedValue(allParamsRaw, 100)
    const debouncedDateParams = useDebouncedValue(dateParams, 100)

    // In-flight request dedup: two effects or a double render within the debounce
    // window shouldn't fire identical requests. Keys are endpoint + serialized params.
    const inFlightRef = useRef(new Map())
    const dedup = useCallback((key, factory) => {
        const m = inFlightRef.current
        if (m.has(key)) return m.get(key)
        const p = Promise.resolve().then(factory).finally(() => m.delete(key))
        m.set(key, p)
        return p
    }, [])

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

    // Quick Scripts state (legacy — kept to not break rest of the file; UI gone)
    const [scriptCounts, setScriptCounts]       = useState({})
    const [scriptLoading, setScriptLoading]     = useState({})
    const [scriptsExpanded, setScriptsExpanded] = useState(null)
    const [modalState, setModalState]           = useState(null)

    // New: totals for /scripts badge
    const [scriptsTotals, setScriptsTotals] = useState({ total: 0, savings: 0 })

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

        const paramsKey = JSON.stringify(allParams)
        const campKey = JSON.stringify(campaignParams)
        const dateKey = JSON.stringify(debouncedDateParams)
        const k = (ep, suffix) => `${ep}|client=${selectedClientId}|${suffix}`

        // Primary (blocking) — needed for page skeleton
        Promise.all([
            dedup(k('dashboard-kpis', paramsKey), () => getDashboardKPIs(selectedClientId, allParams)),
            dedup(k('campaigns', campKey), () => getCampaigns(selectedClientId, campaignParams)),
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
            dedup(k('health-score', paramsKey), () => getHealthScore(selectedClientId, allParams)),
            (hs) => { setHealthScore(hs); setHealthLoading(false) },
        )
        safe(
            dedup(k('recommendations', dateKey), () => getRecommendations(selectedClientId, { status: 'pending', ...debouncedDateParams })),
            (recs) => setRecs(recs?.recommendations || recs?.items || []),
        )
        safe(dedup(k('budget-pacing', campKey), () => getBudgetPacing(selectedClientId, campaignParams)), setBudgetPacing)
        safe(dedup(k('device', paramsKey), () => getDeviceBreakdown(selectedClientId, allParams)), setDeviceData)
        safe(dedup(k('geo', paramsKey), () => getGeoBreakdown(selectedClientId, allParams)), setGeoData)
        safe(dedup(k('wasted', paramsKey), () => getWastedSpend(selectedClientId, allParams)), setWastedSpend)
        safe(
            dedup(k('campaigns-summary', paramsKey), () => getCampaignsSummary(selectedClientId, allParams)),
            (cm) => setCampaignMetrics(cm?.campaigns || null),
        )
        safe(dedup(k('impression-share', paramsKey), () => getImpressionShare(selectedClientId, allParams)), setImpressionShare)
        safe(dedup(k('qs-audit', dateKey), () => getQualityScoreAudit(selectedClientId, debouncedDateParams)), setQsAudit)

        return () => { cancelled = true }
    }, [selectedClientId, allParams, campaignParams, debouncedDateParams, dedup])

    // Scripts totals — fetch from /scripts (new date-aware engine). The legacy
    // `recommendations` feed is no longer used for the Quick Scripts slot.
    // One bulk counts request — backend runs dry-run for every registered
    // script and aggregates the totals. Backend caches the result for 60s
    // so dashboard refreshes are instant.
    useEffect(() => {
        if (!selectedClientId) return
        let cancelled = false
        getScriptsCounts({
            client_id: selectedClientId,
            date_from: debouncedDateParams.date_from,
            date_to: debouncedDateParams.date_to,
        })
            .then(res => {
                if (cancelled) return
                const counts = res?.counts || {}
                let total = 0
                let savings = 0
                Object.values(counts).forEach(c => {
                    total += c?.total || 0
                    savings += c?.savings || 0
                })
                setScriptsTotals({ total, savings })
            })
            .catch(() => !cancelled && setScriptsTotals({ total: 0, savings: 0 }))
        return () => { cancelled = true }
    }, [selectedClientId, debouncedDateParams])

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
            // Re-fetch recommendations — applied recs flip from 'pending' so script counts update
            getRecommendations(selectedClientId, { status: 'pending', ...dateParams })
                .then(recs => setRecs(recs?.recommendations || recs?.items || []))
                .catch(() => {})
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

            {/* ── Anomaly alerts (hides itself when no issues) ──────────── */}
            <AnomalyAlertsCard />

            {/* ── QS Health + Top Actions (compact side-by-side) ────────── */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                <QsHealthWidget qsAudit={qsAudit} compact />
                <TopActions recommendations={recommendations} compact />
            </div>

            {/* ── Scripts badge — link do /scripts ──────────────────────── */}
            <div
                onClick={() => navigate('/scripts')}
                style={{
                    marginBottom: 16,
                    padding: '14px 20px',
                    borderRadius: 12,
                    border: scriptsTotals.total > 0
                        ? '1px solid rgba(79,142,247,0.35)'
                        : '1px solid rgba(255,255,255,0.07)',
                    background: scriptsTotals.total > 0
                        ? 'rgba(79,142,247,0.06)'
                        : 'rgba(255,255,255,0.02)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 14,
                    transition: TRANSITION.fast,
                }}
                className="hover:bg-white/[0.04]"
            >
                <div style={{
                    width: 32, height: 32, borderRadius: 8,
                    background: scriptsTotals.total > 0 ? 'rgba(79,142,247,0.15)' : 'rgba(255,255,255,0.04)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                    <Shield size={15} style={{ color: scriptsTotals.total > 0 ? C.accentBlue : C.w40 }} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, marginBottom: 2 }}>
                        Skrypty optymalizacji
                    </div>
                    <div style={{ fontSize: 11, color: C.w40 }}>
                        {scriptsTotals.total > 0 ? (
                            <>
                                <strong style={{ color: C.accentBlue }}>{scriptsTotals.total} czeka</strong>
                                {scriptsTotals.savings > 0 && (
                                    <> · ~<strong>{Math.round(scriptsTotals.savings)} zł</strong> potencjalnej oszczędności</>
                                )}
                            </>
                        ) : (
                            'Brak akcji do wykonania dla wybranego okresu'
                        )}
                    </div>
                </div>
                <ChevronRight size={14} style={{ color: C.w30 }} />
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

            {/* ── Budget Pacing (compact + expandable + projection) ─────── */}
            <BudgetPacingCard data={budgetPacing} />

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

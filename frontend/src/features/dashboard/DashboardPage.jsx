import { useState, useEffect, useMemo, useCallback } from 'react'
import { LineChart, Line, ResponsiveContainer, XAxis, Tooltip, CartesianGrid, PieChart, Pie, Cell } from 'recharts'
import {
    ChevronRight, ChevronUp, ChevronDown,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import {
    getDashboardKPIs, getCampaigns, getCampaignsSummary,
    getHealthScore, getCampaignTrends, getRecommendations,
    getBudgetPacing, getDeviceBreakdown, getGeoBreakdown,
    getWastedSpend, getImpressionShare, getActionHistory,
    getQualityScoreAudit, getPmaxChannels,
} from '../../api'
import { useApp } from '../../contexts/AppContext'
import { useFilter } from '../../contexts/FilterContext'
import InsightsFeed from '../../components/InsightsFeed'
import TrendExplorer from '../../components/TrendExplorer'
import WoWChart from '../../components/WoWChart'
import EmptyState from '../../components/EmptyState'
import HealthScoreCard from './components/HealthScoreCard'
import MiniKpiGrid from './components/MiniKpiGrid'
import QsHealthWidget from './components/QsHealthWidget'

// ─── Campaign type labels ────────────────────────────────────────────────────
const TYPE_LABELS = {
    SEARCH: 'Search',
    PERFORMANCE_MAX: 'PMax',
    DISPLAY: 'Display',
    SHOPPING: 'Shopping',
    VIDEO: 'Video',
    SMART: 'Smart',
}

// ─── Status helpers ──────────────────────────────────────────────────────────
const STATUS_CONFIG = {
    ENABLED:  { dot: '#4ADE80', label: 'Aktywna'     },
    PAUSED:   { dot: '#FBBF24', label: 'Wstrzymana'  },
    REMOVED:  { dot: '#F87171', label: 'Usunięta'    },
}

// ─── Sparkline ───────────────────────────────────────────────────────────────
function Sparkline({ data, direction }) {
    if (!data || data.length < 2) {
        return <span style={{ color: 'rgba(255,255,255,0.15)', fontSize: 11 }}>—</span>
    }
    // Cost trend: up = bad (spending more), down = good (saving)
    const color = direction === 'up' ? '#F87171' : direction === 'down' ? '#4ADE80' : '#4F8EF7'
    // Backend returns flat array [12.5, 14.2, ...] — Recharts needs [{v: 12.5}, ...]
    const chartData = Array.isArray(data) && typeof data[0] === 'number'
        ? data.map(v => ({ v }))
        : data
    return (
        <LineChart width={72} height={24} data={chartData}>
            <Tooltip
                contentStyle={{ background: '#1a1d24', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 6, fontSize: 10, padding: '4px 8px' }}
                formatter={v => [`${typeof v === 'number' ? v.toLocaleString('pl-PL', { maximumFractionDigits: 1 }) : v}`, null]}
                labelFormatter={() => ''}
            />
            <Line type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} dot={false} />
        </LineChart>
    )
}

// ─── Main Dashboard ──────────────────────────────────────────────────────────
export default function DashboardPage() {
    const { selectedClientId } = useApp()
    const { filters, allParams, campaignParams, days } = useFilter()
    const navigate = useNavigate()

    const [kpis, setKpis]                   = useState(null)
    const [campaigns, setCampaigns]         = useState([])
    const [healthScore, setHealthScore]     = useState(null)
    const [campaignTrends, setCampaignTrends] = useState(null)
    const [recommendations, setRecs]        = useState([])
    const [budgetPacing, setBudgetPacing]   = useState(null)
    const [deviceData, setDeviceData]       = useState(null)
    const [geoData, setGeoData]             = useState(null)
    const [wastedSpend, setWastedSpend]     = useState(null)
    const [campaignMetrics, setCampaignMetrics] = useState(null)
    const [impressionShare, setImpressionShare] = useState(null)
    const [recentActions, setRecentActions] = useState([])
    const [qsAudit, setQsAudit]           = useState(null)
    const [pmaxChannels, setPmaxChannels] = useState(null)

    const [expandedDevice, setExpandedDevice] = useState(null)
    const [sortBy, setSortBy] = useState('cost_usd')
    const [sortDir, setSortDir] = useState('desc')
    const [geoSortBy, setGeoSortBy] = useState('cost_usd')
    const [geoSortDir, setGeoSortDir] = useState('desc')

    const [loading, setLoading]             = useState(false)
    const [healthLoading, setHealthLoading] = useState(false)
    const [error, setError]                 = useState(null)

    const loadData = useCallback(async () => {
        if (!selectedClientId) return
        setLoading(true)
        setHealthLoading(true)
        setError(null)

        try {
            const [kpiData, campData] = await Promise.all([
                getDashboardKPIs(selectedClientId, allParams),
                getCampaigns(selectedClientId),
            ])
            setKpis(kpiData)
            setCampaigns(campData?.items || [])
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }

        // Secondary data — non-blocking
        const _catch = (p) => p.catch(err => { console.error('[Dashboard secondary]', err); return null })
        return Promise.all([
            _catch(getHealthScore(selectedClientId, allParams)),
            _catch(getCampaignTrends(selectedClientId, undefined, allParams)),
            getRecommendations(selectedClientId, { status: 'pending' }).catch(err => { console.error('[Dashboard recs]', err); return { recommendations: [] } }),
            _catch(getBudgetPacing(selectedClientId, campaignParams)),
            _catch(getDeviceBreakdown(selectedClientId, allParams)),
            _catch(getGeoBreakdown(selectedClientId, allParams)),
            _catch(getWastedSpend(selectedClientId, allParams)),
            _catch(getCampaignsSummary(selectedClientId, allParams)),
            _catch(getImpressionShare(selectedClientId, allParams)),
            _catch(getActionHistory(selectedClientId, { limit: 5 })),
            _catch(getQualityScoreAudit(selectedClientId)),
            _catch(getPmaxChannels(selectedClientId, allParams)),
        ])
    }, [selectedClientId, allParams, campaignParams])

    useEffect(() => {
        let cancelled = false
        const promise = loadData()
        if (promise) {
            promise.then(results => {
                if (cancelled || !results) return
                const [hs, ct, recs, bp, dev, geo, ws, cm, is_, actionsData, qsData, pmaxCh] = results
                setHealthScore(hs)
                setCampaignTrends(ct)
                setRecs(recs?.recommendations || recs?.items || [])
                setBudgetPacing(bp)
                setDeviceData(dev)
                setGeoData(geo)
                setWastedSpend(ws)
                setCampaignMetrics(cm?.campaigns || null)
                setImpressionShare(is_)
                setRecentActions(actionsData?.actions || [])
                setQsAudit(qsData)
                setPmaxChannels(pmaxCh)
                setHealthLoading(false)
            })
        }
        return () => { cancelled = true }
    }, [loadData])

    // In-memory filtering + sorting for campaign table
    const filteredCampaigns = useMemo(() => {
        let result = campaigns.filter(c => {
            if (filters.campaignType !== 'ALL' && c.campaign_type !== filters.campaignType) return false
            if (filters.status !== 'ALL' && c.status !== filters.status) return false
            if (filters.campaignName && !c.name?.toLowerCase().includes(filters.campaignName.toLowerCase())) return false
            if (filters.campaignLabel !== 'ALL' && !(c.labels || []).includes(filters.campaignLabel)) return false
            return true
        })
        if (sortBy && campaignMetrics) {
            result = [...result].sort((a, b) => {
                const mA = campaignMetrics[String(a.id)]
                const mB = campaignMetrics[String(b.id)]
                const getCpaVal = (m) => m && m.conversions > 0 ? m.cost_usd / m.conversions : 0
                const vA = sortBy === 'budget_usd' ? (a.budget_usd ?? 0) : sortBy === 'cpa' ? getCpaVal(mA) : (mA?.[sortBy] ?? 0)
                const vB = sortBy === 'budget_usd' ? (b.budget_usd ?? 0) : sortBy === 'cpa' ? getCpaVal(mB) : (mB?.[sortBy] ?? 0)
                return sortDir === 'desc' ? vB - vA : vA - vB
            })
        }
        return result
    }, [campaigns, filters.campaignType, filters.status, filters.campaignName, filters.campaignLabel, campaignMetrics, sortBy, sortDir])
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
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Pulpit
                    </h1>
                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                        {typeof filters.period === 'number'
                            ? `Ostatnie ${filters.period} dni`
                            : `${filters.dateFrom} — ${filters.dateTo}`
                        }
                    </p>
                </div>
                <span onClick={() => navigate('/daily-audit')} style={{ fontSize: 11, color: '#4F8EF7', cursor: 'pointer' }}>
                    Poranny przegląd →
                </span>
            </div>

            {error && (
                <div style={{ background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.2)', borderRadius: 8, padding: '10px 16px', marginBottom: 20, fontSize: 13, color: '#F87171' }}>
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
                    onClick={null}
                />

                <MiniKpiGrid
                    current={current}
                    change_pct={change_pct}
                    wastedSpend={wastedSpend}
                />
            </div>

            {/* ── QS Health Widget ───────────────────────────────────────── */}
            <QsHealthWidget qsAudit={qsAudit} />

            {/* ── Insights Feed ─────────────────────────────────────────── */}
            <div style={{ marginBottom: 16 }}>
                <InsightsFeed
                    kpis={kpis}
                    campaigns={campaigns}
                    recommendations={recommendations}
                />
            </div>

            {/* ── Trend Explorer ────────────────────────────────────────── */}
            <div style={{ marginBottom: 16 }}>
                <TrendExplorer campaignIds={filteredCampaignIds} />
            </div>

            {/* ── WoW Comparison ────────────────────────────────────────── */}
            <WoWChart />

            {/* ── Campaign Table ────────────────────────────────────────── */}
            <div className="v2-card" style={{ overflow: 'hidden', marginBottom: 16 }}>
                <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.07)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                        Kampanie
                    </span>
                    <div className="flex items-center gap-3">
                        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>
                            {filteredCampaigns.length} z {campaigns.length}
                        </span>
                        <span onClick={() => navigate('/campaigns')} style={{ fontSize: 11, color: '#4F8EF7', cursor: 'pointer' }}>
                            Wszystkie →
                        </span>
                    </div>
                </div>

                {loading ? (
                    <div style={{ padding: '40px 20px', textAlign: 'center', fontSize: 12, color: 'rgba(255,255,255,0.3)' }}>
                        Ładowanie kampanii…
                    </div>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                                    {[
                                        { label: 'Nazwa', key: null },
                                        { label: 'Status', key: null },
                                        { label: 'Typ', key: null },
                                        { label: 'Budżet/dzień', key: 'budget_usd', right: true },
                                        { label: 'Koszt', key: 'cost_usd', right: true },
                                        { label: 'Konwersje', key: 'conversions', right: true },
                                        { label: 'ROAS', key: 'roas', right: true },
                                        { label: 'CPA', key: 'cpa', right: true },
                                        { label: 'IS', key: 'impression_share', right: true },
                                        { label: `Trend (${days}d)`, key: null },
                                        { label: 'Strategia', key: null },
                                    ].map(h => {
                                        const isSorted = h.key && sortBy === h.key
                                        return (
                                            <th
                                                key={h.label}
                                                onClick={h.key ? () => {
                                                    if (sortBy === h.key) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
                                                    else { setSortBy(h.key); setSortDir('desc') }
                                                } : undefined}
                                                style={{
                                                    padding: '10px 16px',
                                                    textAlign: h.right ? 'right' : 'left',
                                                    fontSize: 10, fontWeight: 500,
                                                    color: isSorted ? '#4F8EF7' : 'rgba(255,255,255,0.35)',
                                                    textTransform: 'uppercase',
                                                    letterSpacing: '0.08em',
                                                    whiteSpace: 'nowrap',
                                                    cursor: h.key ? 'pointer' : 'default',
                                                    userSelect: 'none',
                                                }}
                                            >
                                                {h.label}
                                                {isSorted && (sortDir === 'desc'
                                                    ? <ChevronDown size={10} style={{ marginLeft: 2, verticalAlign: 'middle' }} />
                                                    : <ChevronUp size={10} style={{ marginLeft: 2, verticalAlign: 'middle' }} />
                                                )}
                                            </th>
                                        )
                                    })}
                                </tr>
                            </thead>
                            <tbody>
                                {filteredCampaigns.length === 0 ? (
                                    <tr>
                                        <td colSpan={11} style={{ padding: '32px 16px', textAlign: 'center', fontSize: 12, color: 'rgba(255,255,255,0.3)' }}>
                                            Brak kampanii dla wybranych filtrów
                                        </td>
                                    </tr>
                                ) : filteredCampaigns.map(c => {
                                    const statusCfg = STATUS_CONFIG[c.status] || { dot: '#666', label: c.status }
                                    const trendData = campaignTrends?.campaigns?.[String(c.id)]
                                    const metrics = campaignMetrics?.[String(c.id)]
                                    return (
                                        <tr
                                            key={c.id}
                                            style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.12s', cursor: 'pointer' }}
                                            onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.025)'}
                                            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                                            onClick={() => navigate(`/campaigns?campaign_id=${c.id}`)}
                                        >
                                            <td style={{ padding: '11px 16px', fontSize: 13, fontWeight: 500, color: '#F0F0F0', maxWidth: 260 }}>
                                                <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                    {c.name}
                                                </span>
                                            </td>
                                            <td style={{ padding: '11px 16px', whiteSpace: 'nowrap' }}>
                                                <span className="flex items-center gap-1.5" style={{ fontSize: 12 }}>
                                                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: statusCfg.dot, flexShrink: 0 }} />
                                                    <span style={{ color: statusCfg.dot }}>{statusCfg.label}</span>
                                                </span>
                                            </td>
                                            <td style={{ padding: '11px 16px', fontSize: 12, color: 'rgba(255,255,255,0.5)', whiteSpace: 'nowrap' }}>
                                                {TYPE_LABELS[c.campaign_type] ?? c.campaign_type}
                                            </td>
                                            <td style={{ padding: '11px 16px', textAlign: 'right', fontSize: 13, fontFamily: 'DM Mono, monospace', color: 'rgba(255,255,255,0.7)', whiteSpace: 'nowrap' }}>
                                                {c.budget_usd != null ? `${c.budget_usd.toFixed(0)} zł` : '—'}
                                            </td>
                                            <td style={{ padding: '11px 16px', textAlign: 'right', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.6)', whiteSpace: 'nowrap' }}>
                                                {metrics ? `${metrics.cost_usd.toLocaleString('pl-PL', { maximumFractionDigits: 0 })} zł` : '—'}
                                            </td>
                                            <td style={{ padding: '11px 16px', textAlign: 'right', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.6)', whiteSpace: 'nowrap' }}>
                                                {metrics ? metrics.conversions.toFixed(1) : '—'}
                                            </td>
                                            <td style={{ padding: '11px 16px', textAlign: 'right', fontSize: 12, fontFamily: 'monospace', whiteSpace: 'nowrap', color: metrics ? ((metrics.roas >= 3) ? '#4ADE80' : (metrics.roas >= 1) ? '#FBBF24' : '#F87171') : 'rgba(255,255,255,0.3)' }}>
                                                {metrics ? `${metrics.roas.toFixed(2)}×` : '—'}
                                            </td>
                                            <td style={{ padding: '11px 16px', textAlign: 'right', fontSize: 12, fontFamily: 'monospace', whiteSpace: 'nowrap', color: 'rgba(255,255,255,0.6)' }}>
                                                {metrics && metrics.conversions > 0 ? `${(metrics.cost_usd / metrics.conversions).toFixed(0)} zł` : '—'}
                                            </td>
                                            <td style={{ padding: '11px 16px', textAlign: 'right', fontSize: 12, fontFamily: 'monospace', whiteSpace: 'nowrap', color: metrics?.impression_share != null ? (metrics.impression_share > 0.5 ? '#4ADE80' : metrics.impression_share > 0.3 ? '#FBBF24' : '#F87171') : 'rgba(255,255,255,0.3)' }}>
                                                {metrics?.impression_share != null ? `${(metrics.impression_share * 100).toFixed(0)}%` : '—'}
                                            </td>
                                            <td style={{ padding: '11px 16px' }}>
                                                <div className="flex items-center gap-2">
                                                    <Sparkline data={trendData?.cost_trend} direction={trendData?.direction} />
                                                </div>
                                            </td>
                                            <td style={{ padding: '11px 16px', fontSize: 11, color: 'rgba(255,255,255,0.4)', whiteSpace: 'nowrap', maxWidth: 180 }}>
                                                <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis' }} title={c.bidding_strategy ?? ''}>
                                                    {c.bidding_strategy ?? '—'}
                                                </span>
                                            </td>
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* ── Budget Pacing ─────────────────────────────────────────── */}
            {budgetPacing?.campaigns?.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                        <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                            Pacing budżetu ({budgetPacing.month})
                        </span>
                        <span onClick={() => navigate('/campaigns')} style={{ fontSize: 11, color: '#4F8EF7', cursor: 'pointer' }}>
                            Wszystkie →
                        </span>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
                        {budgetPacing.campaigns.map(c => {
                            const color = c.status === 'overspend' ? '#F87171' : c.status === 'underspend' ? '#FBBF24' : '#4ADE80'
                            const bg = c.status === 'overspend' ? 'rgba(248,113,113,0.08)' : c.status === 'underspend' ? 'rgba(251,191,36,0.08)' : 'rgba(74,222,128,0.08)'
                            const label = c.status === 'overspend' ? 'Przekroczenie' : c.status === 'underspend' ? 'Niedostateczne' : 'Na torze'
                            const progressPct = Math.min(c.pacing_pct, 150)
                            return (
                                <div key={c.campaign_id} className="v2-card" style={{ padding: '12px 14px' }}>
                                    <div className="flex items-center justify-between" style={{ marginBottom: 6 }}>
                                        <span style={{ fontSize: 12, fontWeight: 500, color: '#F0F0F0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 180 }}>
                                            {c.campaign_name}
                                        </span>
                                        <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 999, background: bg, color, border: `1px solid ${color}30` }}>
                                            {label}
                                        </span>
                                    </div>
                                    {/* Progress bar */}
                                    <div style={{ height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.06)', marginBottom: 6 }}>
                                        <div style={{ height: '100%', borderRadius: 2, background: color, width: `${Math.min(progressPct, 100)}%`, transition: 'width 0.3s' }} />
                                    </div>
                                    <div className="flex items-center justify-between" style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>
                                        <span>{c.actual_spend_usd?.toFixed(0) ?? '—'} / {c.expected_spend_usd?.toFixed(0) ?? '—'} zł</span>
                                        <span style={{ color }}>{c.pacing_pct}%</span>
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>
            )}

            {/* ── PMax Channel Split ────────────────────────────────────── */}
            {pmaxChannels?.channels?.length > 0 && (
                <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 16 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                        <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                            PMax — rozkład kanałów
                        </span>
                        <span onClick={() => navigate('/audit-center')} style={{ fontSize: 11, color: '#4F8EF7', cursor: 'pointer' }}>
                            Szczegóły →
                        </span>
                    </div>
                    {(() => {
                        const CHANNEL_COLORS = {
                            SEARCH: '#4F8EF7', DISPLAY: '#7B5CE0', VIDEO: '#FBBF24',
                            SHOPPING: '#4ADE80', DISCOVER: '#F472B6', CROSS_NETWORK: '#94A3B8',
                        }
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
                                                contentStyle={{ background: '#1a1d24', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 6, fontSize: 11, padding: '6px 10px' }}
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
                                                    <span style={{ fontSize: 12, color: '#F0F0F0' }}>{CHANNEL_LABELS[ch.network_type] || ch.network_type}</span>
                                                </div>
                                                <div className="flex items-center gap-3" style={{ fontSize: 11 }}>
                                                    <span style={{ color: 'rgba(255,255,255,0.5)' }}>{(ch.cost_micros / 1e6).toFixed(0)} zł</span>
                                                    <span style={{ color: 'rgba(255,255,255,0.35)', minWidth: 40, textAlign: 'right' }}>{ch.cost_share_pct}%</span>
                                                    <span style={{ color: isAlert ? '#F87171' : 'rgba(255,255,255,0.35)', minWidth: 50, textAlign: 'right', fontWeight: isAlert ? 600 : 400 }}>
                                                        {ch.conv_share_pct}% conv
                                                    </span>
                                                </div>
                                            </div>
                                        )
                                    })}
                                    {imbalance && (
                                        <div style={{ marginTop: 4, padding: '6px 10px', borderRadius: 8, background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', fontSize: 11, color: '#F87171' }}>
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
                            <div style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', marginBottom: 12, fontFamily: 'Syne' }}>
                                Urządzenia
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                {deviceData.devices.map(d => {
                                    const color = d.device === 'MOBILE' ? '#4F8EF7' : d.device === 'DESKTOP' ? '#7B5CE0' : '#FBBF24'
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
                                                                color: 'rgba(255,255,255,0.3)',
                                                                transform: isExpanded ? 'rotate(90deg)' : 'none',
                                                                transition: 'transform 0.15s',
                                                            }}
                                                        />
                                                    )}
                                                    <span style={{ fontSize: 12, fontWeight: 500, color: '#F0F0F0' }}>{{ MOBILE: 'Telefony', DESKTOP: 'Komputery', TABLET: 'Tablety' }[d.device] || d.device}</span>
                                                </div>
                                                <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>{d.share_clicks_pct}% kliknięć</span>
                                            </div>
                                            <div style={{ height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.06)' }}>
                                                <div style={{ height: '100%', borderRadius: 2, background: color, width: `${d.share_clicks_pct}%`, transition: 'width 0.3s' }} />
                                            </div>
                                            <div className="flex items-center justify-between" style={{ marginTop: 4, fontSize: 10, color: 'rgba(255,255,255,0.35)' }}>
                                                <span>CTR {d.ctr}% · CPC {d.cpc.toFixed(2)} zł</span>
                                                <span>ROAS {d.roas}×</span>
                                            </div>

                                            {/* Expanded device trend */}
                                            {isExpanded && hasTrend && (
                                                <div style={{
                                                    marginTop: 8,
                                                    padding: '12px 14px',
                                                    background: 'rgba(255,255,255,0.02)',
                                                    border: '1px solid rgba(255,255,255,0.06)',
                                                    borderRadius: 8,
                                                }}>
                                                    <div style={{ display: 'flex', gap: 16, marginBottom: 8 }}>
                                                        {[
                                                            { label: 'Kliknięcia', key: 'clicks', color: '#4F8EF7' },
                                                            { label: 'Koszt', key: 'cost', color: '#FBBF24' },
                                                            { label: 'Konwersje', key: 'conversions', color: '#4ADE80' },
                                                        ].map(m => {
                                                            const values = d.trend.map(t => t[m.key])
                                                            const avg = values.reduce((a, b) => a + b, 0) / values.length
                                                            return (
                                                                <div key={m.key} style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>
                                                                    <span style={{ color: m.color, fontWeight: 600 }}>●</span>{' '}
                                                                    {m.label}: <span style={{ color: '#F0F0F0' }}>
                                                                        {m.key === 'cost' ? `${avg.toFixed(2)} zł` : avg.toFixed(1)}
                                                                    </span>
                                                                    <span style={{ color: 'rgba(255,255,255,0.25)' }}> avg/d</span>
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
                                                                tick={{ fontSize: 9, fill: 'rgba(255,255,255,0.2)' }}
                                                                axisLine={false} tickLine={false}
                                                                interval="preserveStartEnd"
                                                            />
                                                            <Tooltip
                                                                contentStyle={{
                                                                    background: '#1a1d24',
                                                                    border: '1px solid rgba(255,255,255,0.12)',
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
                                <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
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
                                                        color: isSorted ? '#4F8EF7' : 'rgba(255,255,255,0.35)', textTransform: 'uppercase',
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
                                        <tr key={c.city} style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}>
                                            <td style={{ padding: '6px', fontSize: 12, color: '#F0F0F0' }}>{c.city}</td>
                                            <td style={{ padding: '6px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.6)', textAlign: 'right' }}>{c.clicks}</td>
                                            <td style={{ padding: '6px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.6)', textAlign: 'right' }}>{c.cost_usd?.toFixed(0) ?? '—'} zł</td>
                                            <td style={{ padding: '6px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.4)', textAlign: 'right' }}>{c.share_cost_pct != null ? `${c.share_cost_pct}%` : '—'}</td>
                                            <td style={{ padding: '6px', fontSize: 12, fontFamily: 'monospace', textAlign: 'right', color: (c.roas ?? 0) >= 3 ? '#4ADE80' : (c.roas ?? 0) >= 1 ? '#FBBF24' : '#F87171' }}>{c.roas?.toFixed(2) ?? '—'}×</td>
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
                        <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                            Udział w wyświetleniach (Search)
                        </span>
                        <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase' }}>
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
                                ? (val > (m.bad || 0.3) ? '#F87171' : val > 0.1 ? '#FBBF24' : '#4ADE80')
                                : (val > (m.good || 0.5) ? '#4ADE80' : val > 0.3 ? '#FBBF24' : '#F87171')
                            return (
                                <div key={m.key}>
                                    <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                                        {m.label}
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, marginBottom: 4 }}>
                                        <span style={{ fontSize: 20, fontWeight: 700, color, fontFamily: 'Syne' }}>
                                            {pct}
                                        </span>
                                        <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>%</span>
                                    </div>
                                    <div style={{ height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.06)' }}>
                                        <div style={{ height: '100%', borderRadius: 2, background: color, width: `${Math.min(parseFloat(pct), 100)}%`, transition: 'width 0.3s' }} />
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>
            )}

            {/* ── Recent actions widget ─────────────────────────────────── */}
            {recentActions.length > 0 && (
                <div className="v2-card" style={{ padding: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                        <h3 style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', margin: 0 }}>Ostatnie akcje</h3>
                        <button
                            onClick={() => navigate('/action-history')}
                            style={{ fontSize: 11, color: '#4F8EF7', background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 3 }}
                        >
                            Wszystkie <ChevronRight size={12} />
                        </button>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        {recentActions.slice(0, 5).map((a, i) => (
                            <div key={a.id || i} style={{
                                display: 'flex', alignItems: 'center', gap: 10,
                                padding: '6px 10px', borderRadius: 8,
                                background: 'rgba(255,255,255,0.02)',
                                border: '1px solid rgba(255,255,255,0.04)',
                                fontSize: 12,
                            }}>
                                <span style={{
                                    fontSize: 10, fontWeight: 600,
                                    color: a.status === 'SUCCESS' ? '#4ADE80' : a.status === 'REVERTED' ? 'rgba(255,255,255,0.35)' : '#F87171',
                                }}>{a.status}</span>
                                <span style={{ color: 'rgba(255,255,255,0.7)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                    {a.entity_name || a.action_type}
                                </span>
                                <span style={{ color: 'rgba(255,255,255,0.25)', fontSize: 11, flexShrink: 0 }}>
                                    {a.executed_at ? new Date(a.executed_at).toLocaleDateString('pl-PL') : ''}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

        </div>
    )
}

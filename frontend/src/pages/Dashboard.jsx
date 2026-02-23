import { useState, useEffect, useMemo, useCallback } from 'react'
import { LineChart, Line } from 'recharts'
import {
    MousePointerClick, DollarSign, Target, BarChart3,
    TrendingUp, TrendingDown,
} from 'lucide-react'
import {
    getDashboardKPIs, getCampaigns,
    getHealthScore, getCampaignTrends, getRecommendations,
} from '../api'
import { useApp } from '../contexts/AppContext'
import { useFilter } from '../contexts/FilterContext'
import FilterBar from '../components/FilterBar'
import InsightsFeed from '../components/InsightsFeed'
import TrendExplorer from '../components/TrendExplorer'
import EmptyState from '../components/EmptyState'

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

// ─── Health Score card ───────────────────────────────────────────────────────
function HealthScoreCard({ score, issues, loading }) {
    const radius = 34
    const circumference = 2 * Math.PI * radius
    const safeScore = typeof score === 'number' ? score : 0
    const offset = circumference * (1 - safeScore / 100)
    const color = safeScore > 70 ? '#4ADE80' : safeScore > 40 ? '#FBBF24' : '#F87171'

    return (
        <div className="v2-card" style={{ padding: '20px 24px', height: '100%', display: 'flex', flexDirection: 'column' }}>
            <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 14 }}>
                Health Score
            </div>

            {loading ? (
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.2)', fontSize: 12 }}>
                    Ładowanie…
                </div>
            ) : (
                <div className="flex items-center gap-5">
                    {/* Circular gauge */}
                    <div style={{ position: 'relative', width: 76, height: 76, flexShrink: 0 }}>
                        <svg width="76" height="76" viewBox="0 0 76 76">
                            <circle cx="38" cy="38" r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
                            <circle
                                cx="38" cy="38" r={radius} fill="none"
                                stroke={color} strokeWidth="6"
                                strokeDasharray={circumference}
                                strokeDashoffset={offset}
                                strokeLinecap="round"
                                transform="rotate(-90 38 38)"
                                style={{ transition: 'stroke-dashoffset 0.6s ease' }}
                            />
                        </svg>
                        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <span style={{ fontSize: 22, fontWeight: 700, color, fontFamily: 'Syne', lineHeight: 1 }}>
                                {safeScore}
                            </span>
                        </div>
                    </div>

                    {/* Issues list */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                        {(issues || []).length === 0 ? (
                            <div style={{ fontSize: 12, color: '#4ADE80', lineHeight: 1.5 }}>
                                Wszystko działa poprawnie
                            </div>
                        ) : (
                            (issues || []).slice(0, 3).map((issue, i) => (
                                <div key={i} style={{ display: 'flex', gap: 6, alignItems: 'flex-start', marginBottom: 5 }}>
                                    <span style={{
                                        fontSize: 6, marginTop: 4, flexShrink: 0,
                                        color: issue.severity === 'high' ? '#F87171' : '#FBBF24',
                                    }}>●</span>
                                    <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', lineHeight: 1.45 }}>
                                        {issue.message}
                                    </span>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}

// ─── Mini KPI card ───────────────────────────────────────────────────────────
function MiniKPI({ title, value, change, suffix = '', prefix = '', icon: Icon, iconColor = '#4F8EF7' }) {
    const isUp = change > 0
    const isDown = change < 0
    const display = typeof value === 'number'
        ? value.toLocaleString('pl-PL', { maximumFractionDigits: 2 })
        : (value ?? '—')

    return (
        <div className="v2-card" style={{ padding: '14px 18px' }}>
            <div className="flex items-center justify-between mb-2">
                <span style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                    {title}
                </span>
                {Icon && (
                    <div style={{ width: 26, height: 26, borderRadius: 6, background: `${iconColor}15`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <Icon size={13} style={{ color: iconColor }} />
                    </div>
                )}
            </div>
            <div style={{ fontSize: 21, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1, marginBottom: 6 }}>
                {prefix}{display}{suffix}
            </div>
            {change !== undefined && change !== null && (
                <div style={{ fontSize: 11, display: 'flex', alignItems: 'center', gap: 3, color: isUp ? '#4ADE80' : isDown ? '#F87171' : 'rgba(255,255,255,0.3)' }}>
                    {isUp ? <TrendingUp size={11} /> : isDown ? <TrendingDown size={11} /> : null}
                    <span>{Math.abs(change).toFixed(1)}%</span>
                    <span style={{ color: 'rgba(255,255,255,0.25)' }}>vs poprz.</span>
                </div>
            )}
        </div>
    )
}

// ─── Sparkline ───────────────────────────────────────────────────────────────
function Sparkline({ data, direction }) {
    if (!data || data.length < 2) {
        return <span style={{ color: 'rgba(255,255,255,0.15)', fontSize: 11 }}>—</span>
    }
    const color = direction === 'up' ? '#4ADE80' : direction === 'down' ? '#F87171' : '#4F8EF7'
    return (
        <LineChart width={72} height={24} data={data}>
            <Line type="monotone" dataKey="cost" stroke={color} strokeWidth={1.5} dot={false} />
        </LineChart>
    )
}

// ─── Main Dashboard ──────────────────────────────────────────────────────────
export default function Dashboard() {
    const { selectedClientId } = useApp()
    const { filters } = useFilter()

    const [kpis, setKpis]                   = useState(null)
    const [campaigns, setCampaigns]         = useState([])
    const [healthScore, setHealthScore]     = useState(null)
    const [campaignTrends, setCampaignTrends] = useState(null)
    const [recommendations, setRecs]        = useState([])

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
                getDashboardKPIs(selectedClientId, filters.period),
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
        Promise.all([
            getHealthScore(selectedClientId).catch(() => null),
            getCampaignTrends(selectedClientId, 7).catch(() => null),
            getRecommendations(selectedClientId).catch(() => ({ recommendations: [] })),
        ]).then(([hs, ct, recs]) => {
            setHealthScore(hs)
            setCampaignTrends(ct)
            setRecs(recs?.recommendations || recs?.items || [])
            setHealthLoading(false)
        })
    }, [selectedClientId, filters.period])

    useEffect(() => { loadData() }, [loadData])

    // In-memory filtering for campaign table
    const filteredCampaigns = useMemo(() => {
        return campaigns.filter(c => {
            if (filters.campaignType !== 'ALL' && c.campaign_type !== filters.campaignType) return false
            if (filters.status !== 'ALL' && c.status !== filters.status) return false
            return true
        })
    }, [campaigns, filters.campaignType, filters.status])

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
                        Ostatnie {filters.period} dni
                    </p>
                </div>
                <FilterBar />
            </div>

            {error && (
                <div style={{ background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.2)', borderRadius: 8, padding: '10px 16px', marginBottom: 20, fontSize: 13, color: '#F87171' }}>
                    Błąd ładowania danych: {error}
                </div>
            )}

            {/* ── Health Score + KPI row ──────────────────────────────────── */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 16, marginBottom: 16 }}>
                {/* Health score */}
                <HealthScoreCard
                    score={healthScore?.score}
                    issues={healthScore?.issues}
                    loading={healthLoading}
                />

                {/* 4 KPI mini cards */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                    <MiniKPI
                        title="Kliknięcia"
                        value={current?.clicks}
                        change={change_pct?.clicks}
                        icon={MousePointerClick}
                        iconColor="#4F8EF7"
                    />
                    <MiniKPI
                        title="Koszt"
                        value={current?.cost_usd}
                        change={change_pct?.cost_usd}
                        suffix=" zł"
                        icon={DollarSign}
                        iconColor="#7B5CE0"
                    />
                    <MiniKPI
                        title="Konwersje"
                        value={current?.conversions}
                        change={change_pct?.conversions}
                        icon={Target}
                        iconColor="#4ADE80"
                    />
                    <MiniKPI
                        title="ROAS"
                        value={current?.roas}
                        change={change_pct?.roas}
                        suffix="×"
                        icon={BarChart3}
                        iconColor="#FBBF24"
                    />
                </div>
            </div>

            {/* ── Insights Feed ───────────────────────────────────────────── */}
            <div style={{ marginBottom: 16 }}>
                <InsightsFeed
                    kpis={kpis}
                    campaigns={campaigns}
                    recommendations={recommendations}
                />
            </div>

            {/* ── Trend Explorer ──────────────────────────────────────────── */}
            <div style={{ marginBottom: 16 }}>
                <TrendExplorer />
            </div>

            {/* ── Campaign Table ──────────────────────────────────────────── */}
            <div className="v2-card" style={{ overflow: 'hidden' }}>
                <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.07)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                        Kampanie
                    </span>
                    <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>
                        {filteredCampaigns.length} z {campaigns.length}
                    </span>
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
                                    {['Nazwa', 'Status', 'Typ', 'Budżet/dzień', 'Trend (7d)', 'Strategia'].map(h => (
                                        <th key={h} style={{
                                            padding: '10px 16px',
                                            textAlign: h === 'Budżet/dzień' ? 'right' : 'left',
                                            fontSize: 10, fontWeight: 500,
                                            color: 'rgba(255,255,255,0.35)',
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.08em',
                                            whiteSpace: 'nowrap',
                                        }}>{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {filteredCampaigns.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} style={{ padding: '32px 16px', textAlign: 'center', fontSize: 12, color: 'rgba(255,255,255,0.3)' }}>
                                            Brak kampanii dla wybranych filtrów
                                        </td>
                                    </tr>
                                ) : filteredCampaigns.map(c => {
                                    const statusCfg = STATUS_CONFIG[c.status] || { dot: '#666', label: c.status }
                                    const trendData = campaignTrends?.campaigns?.[String(c.id)]
                                    return (
                                        <tr
                                            key={c.id}
                                            style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.12s' }}
                                            onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.025)'}
                                            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
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
                                            <td style={{ padding: '11px 16px' }}>
                                                <div className="flex items-center gap-2">
                                                    <Sparkline data={trendData?.cost_trend} direction={trendData?.direction} />
                                                </div>
                                            </td>
                                            <td style={{ padding: '11px 16px', fontSize: 11, color: 'rgba(255,255,255,0.4)', whiteSpace: 'nowrap', maxWidth: 180 }}>
                                                <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis' }}>
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
        </div>
    )
}

import { useState, useEffect, useMemo, useCallback } from 'react'
import { LineChart, Line, ResponsiveContainer, XAxis, Tooltip, CartesianGrid } from 'recharts'
import {
    MousePointerClick, DollarSign, Target, BarChart3,
    TrendingUp, TrendingDown, ChevronRight,
} from 'lucide-react'
import {
    getDashboardKPIs, getCampaigns,
    getHealthScore, getCampaignTrends, getRecommendations,
    getBudgetPacing, getDeviceBreakdown, getGeoBreakdown,
} from '../api'
import { useApp } from '../contexts/AppContext'
import { useFilter } from '../contexts/FilterContext'
import InsightsFeed from '../components/InsightsFeed'
import TrendExplorer from '../components/TrendExplorer'
import EmptyState from '../components/EmptyState'

// â”€â”€â”€ Campaign type labels â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const TYPE_LABELS = {
    SEARCH: 'Search',
    PERFORMANCE_MAX: 'PMax',
    DISPLAY: 'Display',
    SHOPPING: 'Shopping',
    VIDEO: 'Video',
    SMART: 'Smart',
}

// â”€â”€â”€ Status helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const STATUS_CONFIG = {
    ENABLED:  { dot: '#4ADE80', label: 'Aktywna'     },
    PAUSED:   { dot: '#FBBF24', label: 'Wstrzymana'  },
    REMOVED:  { dot: '#F87171', label: 'Usunięta'    },
}

// â”€â”€â”€ Health Score card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function HealthScoreCard({ score, issues, loading, dataAvailable }) {
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
            ) : dataAvailable === false ? (
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', marginBottom: 8 }}>
                            Brak danych
                        </div>
                        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', lineHeight: 1.4 }}>
                            Synchronizuj konto aby zebrać dane
                        </div>
                    </div>
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
                                    }}>â—Ź</span>
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

// â”€â”€â”€ Mini KPI card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function MiniKPI({ title, tooltip, value, change, suffix = '', prefix = '', icon: Icon, iconColor = '#4F8EF7' }) {
    const isUp = change > 0
    const isDown = change < 0
    const display = typeof value === 'number'
        ? value.toLocaleString('pl-PL', { maximumFractionDigits: 2 })
        : (value ?? '—')

    return (
        <div className="v2-card" style={{ padding: '14px 18px' }}>
            <div className="flex items-center justify-between mb-2">
                <span style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.1em' }} title={tooltip || undefined}>
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

// â”€â”€â”€ Sparkline â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
            <Line type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} dot={false} />
        </LineChart>
    )
}

// â”€â”€â”€ Main Dashboard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export default function Dashboard() {
    const { selectedClientId } = useApp()
    const { filters, allParams, campaignParams, days } = useFilter()

    const [kpis, setKpis]                   = useState(null)
    const [campaigns, setCampaigns]         = useState([])
    const [healthScore, setHealthScore]     = useState(null)
    const [campaignTrends, setCampaignTrends] = useState(null)
    const [recommendations, setRecs]        = useState([])
    const [budgetPacing, setBudgetPacing]   = useState(null)
    const [deviceData, setDeviceData]       = useState(null)
    const [geoData, setGeoData]             = useState(null)

    const [expandedDevice, setExpandedDevice] = useState(null)

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
        ])
    }, [selectedClientId, allParams, campaignParams])

    useEffect(() => {
        let cancelled = false
        const promise = loadData()
        if (promise) {
            promise.then(results => {
                if (cancelled || !results) return
                const [hs, ct, recs, bp, dev, geo] = results
                setHealthScore(hs)
                setCampaignTrends(ct)
                setRecs(recs?.recommendations || recs?.items || [])
                setBudgetPacing(bp)
                setDeviceData(dev)
                setGeoData(geo)
                setHealthLoading(false)
            })
        }
        return () => { cancelled = true }
    }, [loadData])

    // In-memory filtering for campaign table
    const filteredCampaigns = useMemo(() => {
        return campaigns.filter(c => {
            if (filters.campaignType !== 'ALL' && c.campaign_type !== filters.campaignType) return false
            if (filters.status !== 'ALL' && c.status !== filters.status) return false
            if (filters.campaignName && !c.name?.toLowerCase().includes(filters.campaignName.toLowerCase())) return false
            if (filters.campaignLabel !== 'ALL' && !(c.labels || []).includes(filters.campaignLabel)) return false
            return true
        })
    }, [campaigns, filters.campaignType, filters.status, filters.campaignName, filters.campaignLabel])
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

            {/* â”€â”€ Header â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
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
            </div>

            {error && (
                <div style={{ background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.2)', borderRadius: 8, padding: '10px 16px', marginBottom: 20, fontSize: 13, color: '#F87171' }}>
                    Błąd ładowania danych: {error}
                </div>
            )}

            {/* â”€â”€ Health Score + KPI row â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 16, marginBottom: 16 }}>
                {/* Health score */}
                <HealthScoreCard
                    score={healthScore?.score}
                    issues={healthScore?.issues}
                    loading={healthLoading}
                    dataAvailable={healthScore?.data_available}
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
                        tooltip="Return On Ad Spend — przychód na każdą wydaną złotówkę"
                        value={current?.roas}
                        change={change_pct?.roas}
                        suffix="×"
                        icon={BarChart3}
                        iconColor="#FBBF24"
                    />
                </div>
            </div>

            {/* â”€â”€ Insights Feed â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
            <div style={{ marginBottom: 16 }}>
                <InsightsFeed
                    kpis={kpis}
                    campaigns={campaigns}
                    recommendations={recommendations}
                />
            </div>

            {/* â”€â”€ Trend Explorer â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
            <div style={{ marginBottom: 16 }}>
                <TrendExplorer campaignIds={filteredCampaignIds} />
            </div>

            {/* â”€â”€ Budget Pacing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
            {budgetPacing?.campaigns?.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', marginBottom: 8, fontFamily: 'Syne' }}>
                        Pacing budżetu ({budgetPacing.month})
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

            {/* â”€â”€ Device + Geo Breakdown â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
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
                                                    <span style={{ fontSize: 12, fontWeight: 500, color: '#F0F0F0' }}>{d.device}</span>
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
                            <div style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', marginBottom: 12, fontFamily: 'Syne' }}>
                                Top miasta
                            </div>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr>
                                        {['Miasto', 'Kliknięcia', 'Koszt', 'ROAS'].map(h => (
                                            <th key={h} style={{
                                                padding: '4px 6px', fontSize: 10, fontWeight: 500,
                                                color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase',
                                                letterSpacing: '0.08em', textAlign: h === 'Miasto' ? 'left' : 'right',
                                            }}>{h}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {geoData.cities.slice(0, 8).map(c => (
                                        <tr key={c.city} style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}>
                                            <td style={{ padding: '6px', fontSize: 12, color: '#F0F0F0' }}>{c.city}</td>
                                            <td style={{ padding: '6px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.6)', textAlign: 'right' }}>{c.clicks}</td>
                                            <td style={{ padding: '6px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.6)', textAlign: 'right' }}>{c.cost_usd?.toFixed(0) ?? '—'} zł</td>
                                            <td style={{ padding: '6px', fontSize: 12, fontFamily: 'monospace', textAlign: 'right', color: (c.roas ?? 0) >= 3 ? '#4ADE80' : (c.roas ?? 0) >= 1 ? '#FBBF24' : '#F87171' }}>{c.roas?.toFixed(2) ?? '—'}×</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}

            {/* â”€â”€ Campaign Table â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
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
                                    {['Nazwa', 'Status', 'Typ', 'Budżet/dzień', `Trend (${days}d)`, 'Strategia'].map(h => (
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

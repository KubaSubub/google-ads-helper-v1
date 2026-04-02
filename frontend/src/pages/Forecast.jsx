import { useState, useEffect } from 'react'
import {
    ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts'
import { TrendingUp, TrendingDown, Activity, AlertCircle, Calendar, Loader2, ArrowRight } from 'lucide-react'
import { getForecast, getCampaigns } from '../api'
import { useApp } from '../contexts/AppContext'
import { useFilter } from '../contexts/FilterContext'
import { useNavigateTo } from '../hooks/useNavigateTo'
import EmptyState from '../components/EmptyState'
import DarkSelect from '../components/DarkSelect'
import { C, T, S, R, B, PILL, MODAL, TOOLTIP_STYLE, SEVERITY, TRANSITION, FONT } from '../constants/designTokens'

const HORIZON_OPTIONS = [7, 14, 30]

function PillButton({ active, onClick, children }) {
    return (
        <button
            onClick={onClick}
            style={{
                padding: '4px 12px',
                borderRadius: 999,
                fontSize: 11,
                fontWeight: 500,
                border: `1px solid ${active ? C.accentBlue : C.w08}`,
                background: active ? C.accentBlueBg : C.w04,
                color: active ? 'white' : C.textPlaceholder,
                cursor: 'pointer',
                transition: 'all 0.15s',
            }}
        >
            {children}
        </button>
    )
}

const METRIC_OPTIONS = [
    { value: 'cost', label: 'Koszt' },
    { value: 'clicks', label: 'Kliknięcia' },
    { value: 'conversions', label: 'Konwersje' },
    { value: 'ctr', label: 'CTR' },
]

export default function Forecast() {
    const { selectedClientId } = useApp()
    const { days } = useFilter()
    const navigateTo = useNavigateTo()
    const [campaigns, setCampaigns] = useState([])
    const [selectedCampaign, setSelectedCampaign] = useState(null)
    const [metric, setMetric] = useState('cost')
    const [forecastDays, setForecastDays] = useState(() => {
        // Sync initial value from global FilterContext, clamped to available options
        const closest = HORIZON_OPTIONS.reduce((prev, curr) =>
            Math.abs(curr - days) < Math.abs(prev - days) ? curr : prev
        )
        return closest
    })
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [retryCount, setRetryCount] = useState(0)
    const [campaignRetry, setCampaignRetry] = useState(0)

    // Sync forecastDays when global FilterContext changes
    useEffect(() => {
        const closest = HORIZON_OPTIONS.reduce((prev, curr) =>
            Math.abs(curr - days) < Math.abs(prev - days) ? curr : prev
        )
        setForecastDays(closest)
    }, [days])

    useEffect(() => {
        if (!selectedClientId) return
        let cancelled = false
        async function loadCampaigns() {
            try {
                const res = await getCampaigns(selectedClientId)
                if (cancelled) return
                const items = res?.items || []
                setCampaigns(items)
                if (items.length > 0) setSelectedCampaign(items[0].id)
            } catch (err) {
                if (!cancelled) setError(err.message)
            }
        }
        loadCampaigns()
        return () => { cancelled = true }
    }, [selectedClientId, campaignRetry])

    useEffect(() => {
        if (!selectedCampaign) return
        let cancelled = false
        async function load() {
            setLoading(true)
            setError(null)
            try {
                const res = await getForecast(selectedCampaign, metric, forecastDays)
                if (cancelled) return
                setData(res)
            } catch (err) {
                if (!cancelled) setError(err.message)
            } finally {
                if (!cancelled) setLoading(false)
            }
        }
        load()
        return () => { cancelled = true }
    }, [selectedCampaign, metric, forecastDays, retryCount])

    if (!selectedClientId) return <EmptyState message="Wybierz klienta" />

    if (!selectedCampaign && !error) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '60px 0' }}>
                <Loader2 size={28} style={{ color: C.accentBlue }} className="animate-spin" />
            </div>
        )
    }

    const chartData = data ? [
        ...data.historical.map(d => ({ date: d.date, historical: d.value, predicted: null, ci_lower: null, ci_upper: null })),
        ...data.forecast.map(d => ({ date: d.date, historical: null, predicted: d.predicted, ci_lower: d.ci_lower, ci_upper: d.ci_upper }))
    ] : []

    const trendColor = data?.trend?.direction === 'up' ? C.success
        : data?.trend?.direction === 'down' ? C.danger : C.accentBlue

    const confidenceLabel = data?.model?.confidence === 'high' ? { color: C.success, bg: 'rgba(74,222,128,0.12)', border: 'rgba(74,222,128,0.25)' }
        : data?.model?.confidence === 'medium' ? { color: C.warning, bg: 'rgba(251,191,36,0.12)', border: 'rgba(251,191,36,0.25)' }
        : { color: C.danger, bg: 'rgba(248,113,113,0.12)', border: 'rgba(248,113,113,0.25)' }

    return (
        <div style={{ maxWidth: 1200 }}>
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: C.textPrimary, fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Prognozowanie
                    </h1>
                    <p style={{ fontSize: 12, color: C.textMuted, marginTop: 3 }}>
                        Predykcja wyników na najbliższe {forecastDays} dni (model liniowy)
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex gap-1.5">
                        {HORIZON_OPTIONS.map(d => (
                            <PillButton key={d} active={forecastDays === d} onClick={() => setForecastDays(d)}>
                                {d}d
                            </PillButton>
                        ))}
                    </div>
                    <DarkSelect
                        value={selectedCampaign}
                        onChange={(v) => setSelectedCampaign(Number(v))}
                        options={campaigns.map(c => ({ value: c.id, label: c.name }))}
                        placeholder="Kampania..."
                        style={{ minWidth: 200 }}
                    />
                    {selectedCampaign && (
                        <span onClick={() => navigateTo('campaigns')} style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 11, color: C.accentBlue, cursor: 'pointer', whiteSpace: 'nowrap' }}>
                            Kampanie <ArrowRight size={12} />
                        </span>
                    )}

                    <div className="flex gap-1.5">
                        {METRIC_OPTIONS.map(m => (
                            <PillButton key={m.value} active={metric === m.value} onClick={() => setMetric(m.value)}>
                                {m.label}
                            </PillButton>
                        ))}
                    </div>
                </div>
            </div>

            {loading && (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '60px 0' }}>
                    <Loader2 size={28} style={{ color: C.accentBlue }} className="animate-spin" />
                </div>
            )}

            {error && (
                <div className="v2-card" style={{ padding: 24, textAlign: 'center' }}>
                    <p style={{ color: C.danger, fontSize: 13, marginBottom: 8 }}>{error}</p>
                    <button onClick={() => {
                        setError(null)
                        if (!selectedCampaign) {
                            // Campaigns failed to load — re-trigger campaigns fetch
                            setCampaignRetry(c => c + 1)
                        } else {
                            // Forecast failed — re-trigger forecast fetch
                            setRetryCount(c => c + 1)
                        }
                    }} style={{
                        padding: '5px 14px', borderRadius: 7, fontSize: 12,
                        background: C.infoBg, border: '1px solid rgba(79,142,247,0.3)',
                        color: C.accentBlue, cursor: 'pointer',
                    }}>
                        Spróbuj ponownie
                    </button>
                </div>
            )}

            {data && !loading && (
                <>
                    {/* KPI Cards */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
                        <div className="v2-card" style={{ padding: '16px 18px' }}>
                            <div className="flex items-center gap-2" style={{ marginBottom: 6 }}>
                                <Activity size={14} style={{ color: C.w40 }} />
                                <span style={{ fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Trend ({forecastDays} dni)</span>
                            </div>
                            <div className="flex items-center gap-2">
                                {data.trend.direction === 'up' && <TrendingUp size={18} style={{ color: C.success }} />}
                                {data.trend.direction === 'down' && <TrendingDown size={18} style={{ color: C.danger }} />}
                                {data.trend.direction === 'stable' && <Activity size={18} style={{ color: C.accentBlue }} />}
                                <span style={{ fontSize: 22, fontWeight: 700, fontFamily: 'Syne', color: trendColor }}>
                                    {data.trend.change_pct > 0 ? '+' : ''}{data.trend.change_pct}%
                                </span>
                            </div>
                            <p style={{ fontSize: 10, color: C.w30, marginTop: 4 }}>vs ostatnie {forecastDays} dni</p>
                        </div>

                        <div className="v2-card" style={{ padding: '16px 18px' }}>
                            <div className="flex items-center gap-2" style={{ marginBottom: 6 }}>
                                <Calendar size={14} style={{ color: C.w40 }} />
                                <span style={{ fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Prognoza (Średnia)</span>
                            </div>
                            <p style={{ fontSize: 22, fontWeight: 700, fontFamily: 'Syne', color: 'white' }}>{data.trend.forecast_avg.toFixed(2)}</p>
                            <p style={{ fontSize: 10, color: C.w30, marginTop: 4 }}>przewidywana dzienna wartość</p>
                        </div>

                        <div className="v2-card" style={{ padding: '16px 18px' }}>
                            <div className="flex items-center gap-2" style={{ marginBottom: 6 }}>
                                <AlertCircle size={14} style={{ color: C.w40 }} />
                                <span style={{ fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Pewność modelu (R²)</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span style={{ fontSize: 22, fontWeight: 700, fontFamily: 'Syne', color: 'white' }}>{data.model.r_squared.toFixed(2)}</span>
                                <span style={{
                                    fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 999,
                                    background: confidenceLabel.bg, color: confidenceLabel.color,
                                    border: `1px solid ${confidenceLabel.border}`,
                                    textTransform: 'uppercase',
                                }}>
                                    {data.model.confidence}
                                </span>
                            </div>
                        </div>

                        <div className="v2-card" style={{ padding: '16px 18px' }}>
                            <div className="flex items-center gap-2" style={{ marginBottom: 6 }}>
                                <Activity size={14} style={{ color: C.w40 }} />
                                <span style={{ fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Slope (Wzrost/Dzień)</span>
                            </div>
                            <p style={{ fontSize: 22, fontWeight: 700, fontFamily: 'Syne', color: 'white' }}>{data.model.slope_per_day.toFixed(2)}</p>
                            <p style={{ fontSize: 10, color: C.w30, marginTop: 4 }}>jednostek dziennie</p>
                        </div>
                    </div>

                    {/* Chart */}
                    <div className="v2-card" style={{ padding: '20px 24px', height: 380 }}>
                        <h3 style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary, marginBottom: 16, fontFamily: 'DM Sans' }}>
                            Wykres historyczny + prognoza
                        </h3>
                        <ResponsiveContainer width="100%" height="90%">
                            <ComposedChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                                <XAxis
                                    dataKey="date"
                                    stroke="rgba(255,255,255,0.15)"
                                    tick={{ fill: C.textMuted, fontSize: 10 }}
                                    tickFormatter={d => d.slice(5)}
                                />
                                <YAxis
                                    stroke="rgba(255,255,255,0.15)"
                                    tick={{ fill: C.textMuted, fontSize: 10 }}
                                />
                                <Tooltip
                                    contentStyle={{
                                        background: C.surfaceElevated,
                                        border: B.medium,
                                        borderRadius: 8,
                                        color: C.textPrimary,
                                        fontSize: 12,
                                    }}
                                    itemStyle={{ color: C.textPrimary }}
                                    formatter={(value, name) => {
                                        if (name === 'ci_upper' || name === 'ci_lower') return [null, null]
                                        return [typeof value === 'number' ? value.toFixed(2) : value, name]
                                    }}
                                />
                                {/* Confidence interval band */}
                                <Area
                                    type="monotone"
                                    dataKey="ci_upper"
                                    stroke="none"
                                    fill="rgba(74,222,128,0.08)"
                                    name="ci_upper"
                                    legendType="none"
                                />
                                <Area
                                    type="monotone"
                                    dataKey="ci_lower"
                                    stroke="none"
                                    fill="#0D0F14"
                                    name="ci_lower"
                                    legendType="none"
                                />
                                <Line
                                    type="monotone"
                                    dataKey="historical"
                                    stroke="#4F8EF7"
                                    strokeWidth={2}
                                    dot={false}
                                    activeDot={{ r: 5, fill: C.accentBlue }}
                                    name="Dane historyczne"
                                />
                                <Line
                                    type="monotone"
                                    dataKey="predicted"
                                    stroke="#4ADE80"
                                    strokeWidth={2}
                                    strokeDasharray="5 5"
                                    dot={{ r: 3, fill: C.success }}
                                    name="Prognoza"
                                />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </div>
                </>
            )}
        </div>
    )
}

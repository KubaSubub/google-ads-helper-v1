import { useState, useEffect, useCallback } from 'react'
import {
    ComposedChart, Line, XAxis, YAxis, Tooltip, Legend,
    ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { Plus, X, TrendingUp } from 'lucide-react'
import { getCorrelationMatrix, getTrends } from '../api'
import { useFilter } from '../contexts/FilterContext'
import { useApp } from '../contexts/AppContext'

const METRIC_COLORS = ['#4F8EF7', '#7B5CE0', '#4ADE80', '#FBBF24', '#F87171']

const METRIC_OPTIONS = [
    { key: 'cost', label: 'Koszt (zł)', unit: 'PLN' },
    { key: 'clicks', label: 'Kliknięcia', unit: '' },
    { key: 'impressions', label: 'Wyświetlenia', unit: '' },
    { key: 'conversions', label: 'Konwersje', unit: '' },
    { key: 'ctr', label: 'CTR (%)', unit: '%', tooltip: 'Click-Through Rate — stosunek kliknięć do wyświetleń' },
    { key: 'cpc', label: 'CPC (avg)', unit: 'PLN', tooltip: 'Cost Per Click — średni koszt kliknięcia' },
    { key: 'roas', label: 'ROAS', unit: '', tooltip: 'Return On Ad Spend — przychód na wydaną złotówkę' },
    { key: 'cpa', label: 'CPA', unit: 'PLN', tooltip: 'Cost Per Acquisition — koszt pozyskania konwersji' },
    { key: 'cvr', label: 'CVR (%)', unit: '%', tooltip: 'Conversion Rate — procent kliknięć zakończonych konwersją' },
]

const CORRELATION_METRIC_MAP = {
    cost: 'cost_micros',
    clicks: 'clicks',
    impressions: 'impressions',
    conversions: 'conversions',
    ctr: 'ctr',
    cpc: 'avg_cpc_micros',
    roas: 'roas',
    cvr: 'conversion_rate',
}

// Pearson correlation coefficient
function pearsonCorrelation(x, y) {
    const n = x.length
    if (n < 2) return null
    const meanX = x.reduce((a, b) => a + b, 0) / n
    const meanY = y.reduce((a, b) => a + b, 0) / n
    const num = x.reduce((sum, xi, i) => sum + (xi - meanX) * (y[i] - meanY), 0)
    const denX = Math.sqrt(x.reduce((sum, xi) => sum + (xi - meanX) ** 2, 0))
    const denY = Math.sqrt(y.reduce((sum, yi) => sum + (yi - meanY) ** 2, 0))
    if (denX === 0 || denY === 0) return null
    return num / (denX * denY)
}

function getCorrelationLabel(r) {
    if (r === null) return null
    const abs = Math.abs(r)
    const sign = r > 0 ? '+' : ''
    if (abs > 0.7) return `${sign}${r.toFixed(2)} ${r > 0 ? '↑ silna' : '↓ silna ujemna'}`
    if (abs > 0.4) return `${sign}${r.toFixed(2)} → umiarkowana`
    return `${r.toFixed(2)} ≈ brak korelacji`
}

function formatDate(dateStr) {
    const d = new Date(dateStr)
    return `${d.getDate()}.${(d.getMonth() + 1).toString().padStart(2, '0')}`
}

// Determine if two metrics need dual Y-axis (different units)
function needsDualAxis(metrics) {
    const pct = ['ctr', 'cvr']
    const money = ['cost', 'cpc', 'cpa']
    const hasPct = metrics.some(m => pct.includes(m))
    const hasMoney = metrics.some(m => money.includes(m))
    const hasCount = metrics.some(m => !pct.includes(m) && !money.includes(m))
    return (hasPct && (hasMoney || hasCount)) || (hasMoney && hasCount)
}

const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null
    return (
        <div style={{
            background: '#1a1d24',
            border: '1px solid rgba(255,255,255,0.12)',
            borderRadius: 8,
            padding: '10px 14px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
            fontSize: 12,
        }}>
            <div style={{ color: 'rgba(255,255,255,0.5)', marginBottom: 6 }}>{label}</div>
            {payload.map((p, i) => (
                <div key={i} style={{ color: p.color, marginBottom: 2 }}>
                    {p.name}: <strong>{p.value?.toLocaleString?.() ?? p.value}</strong>
                </div>
            ))}
        </div>
    )
}

export default function TrendExplorer({ campaignIds = [] }) {
    const { selectedClientId } = useApp()
    const { filters, days } = useFilter()
    const [activeMetrics, setActiveMetrics] = useState(['cost', 'clicks'])
    const [showDropdown, setShowDropdown] = useState(false)
    const [data, setData] = useState([])
    const [loading, setLoading] = useState(false)
    const [isMock, setIsMock] = useState(false)
    const [correlationLabel, setCorrelationLabel] = useState(null)

    const fetchData = useCallback(async () => {
        if (!selectedClientId) return
        setLoading(true)
        try {
            const result = await getTrends(selectedClientId, {
                metrics: activeMetrics.join(','),
                days: days,
                campaign_type: filters.campaignType,
                status: filters.status,
            })
            setData(result.data || [])
            setIsMock(result.is_mock || false)
        } catch (e) {
            console.error('TrendExplorer fetch error:', e)
            setData([])
        } finally {
            setLoading(false)
        }
    }, [selectedClientId, activeMetrics, days, filters.campaignType, filters.status])

    useEffect(() => { fetchData() }, [fetchData])

    const addMetric = (key) => {
        if (activeMetrics.length >= 5 || activeMetrics.includes(key)) return
        setActiveMetrics(prev => [...prev, key])
        setShowDropdown(false)
    }

    const removeMetric = (key) => {
        if (activeMetrics.length <= 1) return
        setActiveMetrics(prev => prev.filter(m => m !== key))
    }

    const localCorrelationLabel = useCallback(() => {
        if (activeMetrics.length < 2 || data.length < 3) return null
        const x = data.map(d => d[activeMetrics[0]] ?? 0)
        const y = data.map(d => d[activeMetrics[1]] ?? 0)
        const r = pearsonCorrelation(x, y)
        return getCorrelationLabel(r)
    }, [activeMetrics, data])

    useEffect(() => {
        let cancelled = false

        const fetchCorrelation = async () => {
            if (activeMetrics.length < 2 || data.length < 3) {
                if (!cancelled) setCorrelationLabel(null)
                return
            }

            const mappedA = CORRELATION_METRIC_MAP[activeMetrics[0]]
            const mappedB = CORRELATION_METRIC_MAP[activeMetrics[1]]
            const fallback = localCorrelationLabel()

            if (!mappedA || !mappedB || campaignIds.length === 0) {
                if (!cancelled) setCorrelationLabel(fallback)
                return
            }

            try {
                const response = await getCorrelationMatrix({
                    campaign_ids: campaignIds,
                    metrics: [mappedA, mappedB],
                    date_from: filters.dateFrom || undefined,
                    date_to: filters.dateTo || undefined,
                })
                const r = response?.matrix?.[mappedA]?.[mappedB]
                if (!cancelled) {
                    setCorrelationLabel(typeof r === 'number' ? getCorrelationLabel(r) : fallback)
                }
            } catch (e) {
                if (!cancelled) setCorrelationLabel(fallback)
            }
        }

        fetchCorrelation()
        return () => { cancelled = true }
    }, [activeMetrics, campaignIds, data, filters.dateFrom, filters.dateTo, localCorrelationLabel])
    const dual = needsDualAxis(activeMetrics)
    const pctMetrics = ['ctr', 'cvr']

    const availableToAdd = METRIC_OPTIONS.filter(m => !activeMetrics.includes(m.key))

    return (
        <div className="v2-card" style={{ padding: '20px 24px' }}>
            {/* Header */}
            <div className="flex items-center justify-between mb-4" style={{ flexWrap: 'wrap', gap: 12 }}>
                <div className="flex items-center gap-2">
                    <TrendingUp size={16} style={{ color: '#4F8EF7' }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                        Trend Explorer
                    </span>
                </div>

                <div className="flex items-center gap-3 flex-wrap">
                    {/* Active metric pills */}
                    {activeMetrics.map((key, idx) => {
                        const opt = METRIC_OPTIONS.find(m => m.key === key)
                        return (
                            <div
                                key={key}
                                className="flex items-center gap-1.5"
                                style={{
                                    background: `${METRIC_COLORS[idx]}20`,
                                    border: `1px solid ${METRIC_COLORS[idx]}40`,
                                    borderRadius: 999,
                                    padding: '3px 10px 3px 12px',
                                    fontSize: 12,
                                    color: METRIC_COLORS[idx],
                                }}
                            >
                                <span title={opt?.tooltip || undefined}>{opt?.label ?? key}</span>
                                {activeMetrics.length > 1 && (
                                    <button
                                        onClick={() => removeMetric(key)}
                                        style={{ color: 'rgba(255,255,255,0.4)', lineHeight: 1 }}
                                        className="hover:text-white/70"
                                    >
                                        <X size={12} />
                                    </button>
                                )}
                            </div>
                        )
                    })}

                    {/* Add metric button */}
                    {activeMetrics.length < 5 && availableToAdd.length > 0 && (
                        <div style={{ position: 'relative' }}>
                            <button
                                onClick={() => setShowDropdown(v => !v)}
                                style={{
                                    display: 'flex', alignItems: 'center', gap: 5,
                                    background: 'rgba(255,255,255,0.04)',
                                    border: '1px solid rgba(255,255,255,0.1)',
                                    borderRadius: 999,
                                    padding: '3px 12px',
                                    fontSize: 12,
                                    color: 'rgba(255,255,255,0.5)',
                                    cursor: 'pointer',
                                }}
                                className="hover:border-white/20 hover:text-white/70"
                            >
                                <Plus size={12} />
                                Dodaj metrykę
                            </button>
                            {showDropdown && (
                                <div
                                    style={{
                                        position: 'absolute', top: '100%', right: 0, marginTop: 6,
                                        background: '#1a1d24',
                                        border: '1px solid rgba(255,255,255,0.12)',
                                        borderRadius: 8,
                                        boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
                                        zIndex: 50,
                                        minWidth: 160,
                                        overflow: 'hidden',
                                    }}
                                >
                                    {availableToAdd.map(opt => (
                                        <button
                                            key={opt.key}
                                            onClick={() => addMetric(opt.key)}
                                            style={{
                                                display: 'block', width: '100%',
                                                textAlign: 'left',
                                                padding: '8px 14px',
                                                fontSize: 12,
                                                color: 'rgba(255,255,255,0.7)',
                                                cursor: 'pointer',
                                                background: 'transparent',
                                                border: 'none',
                                            }}
                                            className="hover:bg-white/5 hover:text-white"
                                        >
                                            {opt.label}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Correlation badge */}
                    {correlationLabel && (
                        <div style={{
                            fontSize: 11,
                            color: 'rgba(255,255,255,0.4)',
                            paddingLeft: 8,
                            borderLeft: '1px solid rgba(255,255,255,0.08)',
                        }}>
                            Kor. <span style={{ color: '#FBBF24' }}>{correlationLabel}</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Mock data warning banner */}
            {isMock && !loading && (
                <div style={{
                    background: 'rgba(251, 191, 36, 0.1)',
                    border: '1px solid #FBBF24',
                    borderRadius: 6,
                    padding: '10px 14px',
                    marginBottom: 12,
                    fontSize: 12,
                    color: '#FBBF24',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                }}>
                    <span>⚠️</span>
                    <span>Brak rzeczywistych danych — synchronizuj konto aby zebrać dane metryk</span>
                </div>
            )}

            {/* Chart */}
            {loading ? (
                <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>
                    Ładowanie danych…
                </div>
            ) : data.length === 0 ? (
                <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>
                    Brak danych dla wybranych filtrów
                </div>
            ) : (
                <ResponsiveContainer width="100%" height={220}>
                    <ComposedChart data={data} margin={{ top: 4, right: dual ? 40 : 8, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis
                            dataKey="date"
                            tickFormatter={formatDate}
                            tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.3)' }}
                            axisLine={false}
                            tickLine={false}
                        />
                        <YAxis
                            yAxisId="left"
                            tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.3)' }}
                            axisLine={false}
                            tickLine={false}
                            width={40}
                        />
                        {dual && (
                            <YAxis
                                yAxisId="right"
                                orientation="right"
                                tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.3)' }}
                                axisLine={false}
                                tickLine={false}
                                width={40}
                            />
                        )}
                        <Tooltip content={<CustomTooltip />} />
                        {activeMetrics.map((key, idx) => {
                            const opt = METRIC_OPTIONS.find(m => m.key === key)
                            const yAxis = dual && idx > 0 && pctMetrics.includes(key) ? 'right' : 'left'
                            return (
                                <Line
                                    key={key}
                                    yAxisId={yAxis}
                                    type="monotone"
                                    dataKey={key}
                                    name={opt?.label ?? key}
                                    stroke={METRIC_COLORS[idx]}
                                    strokeWidth={1.8}
                                    dot={false}
                                    activeDot={{ r: 4, fill: METRIC_COLORS[idx] }}
                                />
                            )
                        })}
                    </ComposedChart>
                </ResponsiveContainer>
            )}
        </div>
    )
}

import { useState, useEffect, useCallback } from 'react'
import {
    ComposedChart, Line, XAxis, YAxis, Tooltip, Legend,
    ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { Plus, X, TrendingUp } from 'lucide-react'
import { getCorrelationMatrix, getTrends } from '../api'
import { useFilter } from '../contexts/FilterContext'
import { useApp } from '../contexts/AppContext'
import { C, T, S, R, B, PILL, MODAL, TOOLTIP_STYLE, SEVERITY, TRANSITION, FONT } from '../constants/designTokens'

const METRIC_COLORS = [C.accentBlue, C.accentPurple, C.success, C.warning, C.danger]

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

function getCorrelationLabel(r) {
    if (r === null || r === undefined) return null
    const abs = Math.abs(r)
    const sign = r > 0 ? '+' : ''
    if (abs > 0.7) {
        return r > 0
            ? `${sign}${r.toFixed(2)} ↑ silna dodatnia`
            : `${r.toFixed(2)} ↓ silna ujemna`
    }
    if (abs > 0.4) {
        return r > 0
            ? `${sign}${r.toFixed(2)} → umiarkowana dodatnia`
            : `${r.toFixed(2)} → umiarkowana ujemna`
    }
    return `${r.toFixed(2)} ≈ słaba / brak`
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
            background: C.surfaceElevated,
            border: B.hover,
            borderRadius: 8,
            padding: '10px 14px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
            fontSize: 12,
        }}>
            <div style={{ color: C.w50, marginBottom: 6 }}>{label}</div>
            {payload.map((p, i) => (
                <div key={i} style={{ color: p.color, marginBottom: 2 }}>
                    {p.name}: <strong>{p.value?.toLocaleString?.('pl-PL') ?? p.value}</strong>
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
    const [correlationData, setCorrelationData] = useState(null) // { best: {pairLabel,label,r}, pairs: [{a,b,r,label}...] }
    const [showCorrelationPopup, setShowCorrelationPopup] = useState(false)

    const fetchData = useCallback(async () => {
        if (!selectedClientId) return
        setLoading(true)
        try {
            const params = {
                metrics: activeMetrics.join(','),
                date_from: filters.dateFrom,
                date_to: filters.dateTo,
            }
            if (filters.campaignType !== 'ALL') params.campaign_type = filters.campaignType
            if (filters.status !== 'ALL') params.status = filters.status
            const result = await getTrends(selectedClientId, params)
            setData(result.data || [])
            setIsMock(result.is_mock || false)
        } catch (e) {
            console.error('TrendExplorer fetch error:', e)
            setData([])
        } finally {
            setLoading(false)
        }
    }, [selectedClientId, activeMetrics, filters.dateFrom, filters.dateTo, filters.campaignType, filters.status])

    useEffect(() => { fetchData() }, [fetchData])

    // Close popups on outside click
    useEffect(() => {
        if (!showCorrelationPopup && !showDropdown) return
        const handler = (e) => {
            if (!e.target.closest('[data-correlation-popup]') && !e.target.closest('[data-metric-dropdown]')) {
                setShowCorrelationPopup(false)
                setShowDropdown(false)
            }
        }
        document.addEventListener('mousedown', handler)
        return () => document.removeEventListener('mousedown', handler)
    }, [showCorrelationPopup, showDropdown])

    const addMetric = (key) => {
        if (activeMetrics.length >= 5 || activeMetrics.includes(key)) return
        setActiveMetrics(prev => [...prev, key])
        setShowDropdown(false)
    }

    const removeMetric = (key) => {
        if (activeMetrics.length <= 1) return
        setActiveMetrics(prev => prev.filter(m => m !== key))
    }

    useEffect(() => {
        let cancelled = false

        const fetchCorrelation = async () => {
            if (activeMetrics.length < 2 || data.length < 3) {
                if (!cancelled) setCorrelationData(null)
                return
            }

            // Map all active metrics to backend names
            const mapped = activeMetrics
                .map(k => ({ key: k, backend: CORRELATION_METRIC_MAP[k] }))
                .filter(m => m.backend)
            if (mapped.length < 2) {
                if (!cancelled) setCorrelationData(null)
                return
            }

            try {
                const response = await getCorrelationMatrix({
                    campaign_ids: campaignIds,
                    metrics: mapped.map(m => m.backend),
                    date_from: filters.dateFrom || undefined,
                    date_to: filters.dateTo || undefined,
                })
                if (cancelled) return

                // Build all correlation pairs
                const pairs = []
                let bestIdx = 0
                for (let i = 0; i < mapped.length; i++) {
                    for (let j = i + 1; j < mapped.length; j++) {
                        const r = response?.matrix?.[mapped[i].backend]?.[mapped[j].backend]
                        if (typeof r === 'number') {
                            const labelA = METRIC_OPTIONS.find(m => m.key === mapped[i].key)?.label ?? mapped[i].key
                            const labelB = METRIC_OPTIONS.find(m => m.key === mapped[j].key)?.label ?? mapped[j].key
                            pairs.push({ a: labelA, b: labelB, r, label: getCorrelationLabel(r) })
                            if (Math.abs(r) > Math.abs(pairs[bestIdx].r)) bestIdx = pairs.length - 1
                        }
                    }
                }

                if (pairs.length > 0) {
                    const best = pairs[bestIdx]
                    setCorrelationData({
                        best: { pairLabel: `${best.a} vs ${best.b}`, label: best.label, r: best.r },
                        pairs: pairs.sort((a, b) => Math.abs(b.r) - Math.abs(a.r)),
                    })
                } else {
                    setCorrelationData(null)
                }
            } catch (e) {
                if (!cancelled) setCorrelationData(null)
            }
        }

        fetchCorrelation()
        return () => { cancelled = true }
    }, [activeMetrics, campaignIds, data, filters.dateFrom, filters.dateTo])
    const dual = needsDualAxis(activeMetrics)
    const pctMetrics = ['ctr', 'cvr']

    const availableToAdd = METRIC_OPTIONS.filter(m => !activeMetrics.includes(m.key))

    return (
        <div className="v2-card" style={{ padding: '20px 24px' }}>
            {/* Header */}
            <div className="flex items-center justify-between mb-4" style={{ flexWrap: 'wrap', gap: 12 }}>
                <div className="flex items-center gap-2">
                    <TrendingUp size={16} style={{ color: C.accentBlue }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne' }}>
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
                                        style={{ color: C.w40, lineHeight: 1 }}
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
                        <div style={{ position: 'relative' }} data-metric-dropdown>
                            <button
                                onClick={() => setShowDropdown(v => !v)}
                                style={{
                                    display: 'flex', alignItems: 'center', gap: 5,
                                    background: C.w04,
                                    border: B.medium,
                                    borderRadius: 999,
                                    padding: '3px 12px',
                                    fontSize: 12,
                                    color: C.w50,
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
                                        background: C.surfaceElevated,
                                        border: B.hover,
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
                                                color: C.w70,
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

                    {/* Correlation badge — click to show full matrix */}
                    {correlationData && (
                        <div style={{ position: 'relative' }} data-correlation-popup>
                            <button
                                onClick={() => setShowCorrelationPopup(v => !v)}
                                style={{
                                    fontSize: 11,
                                    color: C.w40,
                                    paddingLeft: 8,
                                    background: 'none',
                                    border: 'none',
                                    borderLeft: `1px solid ${C.w08}`,
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 4,
                                }}
                                className="hover:text-white/60"
                            >
                                <span style={{ color: C.w30 }}>
                                    Kor.
                                </span>
                                <span style={{
                                    color: Math.abs(correlationData.best.r) > 0.7 ? C.success
                                         : Math.abs(correlationData.best.r) > 0.4 ? C.warning
                                         : C.textMuted,
                                }}>
                                    {correlationData.best.r > 0 ? '+' : ''}{correlationData.best.r.toFixed(2)}
                                </span>
                                {correlationData.pairs.length > 1 && (
                                    <span style={{ fontSize: 9, color: C.w25 }}>
                                        ({correlationData.pairs.length} par)
                                    </span>
                                )}
                            </button>

                            {showCorrelationPopup && (
                                <div
                                    style={{
                                        position: 'absolute',
                                        top: '100%',
                                        right: 0,
                                        marginTop: 6,
                                        background: C.surfaceElevated,
                                        border: B.hover,
                                        borderRadius: 8,
                                        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
                                        zIndex: 50,
                                        minWidth: 280,
                                        padding: '12px 0',
                                    }}
                                >
                                    <div style={{
                                        padding: '0 14px 8px',
                                        fontSize: 11,
                                        fontWeight: 600,
                                        color: C.w50,
                                        borderBottom: B.subtle,
                                        marginBottom: 4,
                                    }}>
                                        Macierz korelacji (Pearson)
                                    </div>
                                    {correlationData.pairs.map((pair, i) => {
                                        const absR = Math.abs(pair.r)
                                        const rColor = absR > 0.7 ? C.success
                                                      : absR > 0.4 ? C.warning
                                                      : C.textMuted
                                        return (
                                            <div
                                                key={i}
                                                style={{
                                                    display: 'flex',
                                                    justifyContent: 'space-between',
                                                    alignItems: 'center',
                                                    padding: '6px 14px',
                                                    fontSize: 11,
                                                }}
                                            >
                                                <span style={{ color: C.w60, flex: 1 }}>
                                                    {pair.a} <span style={{ color: C.w20 }}>vs</span> {pair.b}
                                                </span>
                                                <span style={{ color: rColor, fontWeight: 600, marginLeft: 12, whiteSpace: 'nowrap' }}>
                                                    {pair.r > 0 ? '+' : ''}{pair.r.toFixed(2)}
                                                </span>
                                            </div>
                                        )
                                    })}
                                </div>
                            )}
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
                    color: C.warning,
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
                <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', color: C.w30, fontSize: 12 }}>
                    Ładowanie danych…
                </div>
            ) : data.length === 0 ? (
                <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', color: C.w30, fontSize: 12 }}>
                    Brak danych dla wybranych filtrów
                </div>
            ) : (
                <ResponsiveContainer width="100%" height={220}>
                    <ComposedChart data={data} margin={{ top: 4, right: dual ? 40 : 8, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis
                            dataKey="date"
                            tickFormatter={formatDate}
                            tick={{ fontSize: 10, fill: C.w30 }}
                            axisLine={false}
                            tickLine={false}
                        />
                        <YAxis
                            yAxisId="left"
                            tick={{ fontSize: 10, fill: C.w30 }}
                            axisLine={false}
                            tickLine={false}
                            width={40}
                        />
                        {dual && (
                            <YAxis
                                yAxisId="right"
                                orientation="right"
                                tick={{ fontSize: 10, fill: C.w30 }}
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

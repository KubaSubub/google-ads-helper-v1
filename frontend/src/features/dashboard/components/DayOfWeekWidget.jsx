// DayOfWeekWidget — heatmap-style day-of-week performance with bid suggestions
import { useState, useEffect, useMemo } from 'react'
import { Calendar, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react'
import { getDayparting, getDaypartingDowSuggestions } from '../../../api'
import { useApp } from '../../../contexts/AppContext'
import { useFilter } from '../../../contexts/FilterContext'

const METRICS = [
    { key: 'clicks', label: 'Klikniecia' },
    { key: 'conversions', label: 'Konwersje' },
    { key: 'conversion_value_amount', label: 'Wartosc konwersji', isCurrency: true },
    { key: 'aov', label: 'AOV', isCurrency: true },
    { key: 'cpa', label: 'CPA', isCurrency: true, invert: true },
    { key: 'roas', label: 'ROAS', suffix: 'x' },
    { key: 'cvr', label: 'CVR', suffix: '%' },
    { key: 'cpc', label: 'CPC', isCurrency: true, invert: true },
]

const MIN_OBSERVATIONS_FOR_SIGNIFICANCE = 4

// 5-level gradient: deep red -> orange -> amber -> lime -> green
function heatColor(value, min, max, invert) {
    if (max === min) return 'rgba(255,255,255,0.06)'
    const ratio = (value - min) / (max - min)
    const t = invert ? 1 - ratio : ratio
    if (t >= 0.80) return 'rgba(74,222,128,0.22)'
    if (t >= 0.60) return 'rgba(163,230,53,0.18)'
    if (t >= 0.40) return 'rgba(251,191,36,0.15)'
    if (t >= 0.20) return 'rgba(251,146,60,0.13)'
    return 'rgba(248,113,113,0.15)'
}

function textColor(value, min, max, invert) {
    if (max === min) return 'rgba(255,255,255,0.5)'
    const ratio = (value - min) / (max - min)
    const t = invert ? 1 - ratio : ratio
    if (t >= 0.80) return '#4ADE80'
    if (t >= 0.60) return '#A3E635'
    if (t >= 0.40) return '#FBBF24'
    if (t >= 0.20) return '#FB923C'
    return '#F87171'
}

function borderColor(value, min, max, invert) {
    if (max === min) return 'rgba(255,255,255,0.04)'
    const ratio = (value - min) / (max - min)
    const t = invert ? 1 - ratio : ratio
    if (t >= 0.80) return 'rgba(74,222,128,0.35)'
    if (t >= 0.60) return 'rgba(163,230,53,0.30)'
    if (t >= 0.40) return 'rgba(251,191,36,0.25)'
    if (t >= 0.20) return 'rgba(251,146,60,0.22)'
    return 'rgba(248,113,113,0.30)'
}

function formatVal(val, def, currency) {
    if (val == null) return '—'
    if (typeof val !== 'number') return String(val)
    const formatted = val.toLocaleString('pl-PL', { maximumFractionDigits: 1 })
    if (def.isCurrency) return `${formatted} ${currency}`
    if (def.suffix) return `${formatted}${def.suffix}`
    return formatted
}

function buildPrevParams(allParams) {
    // Build previous-period params by shifting the date window backwards
    const prev = { ...allParams }
    const dateFrom = allParams.date_from
    const dateTo = allParams.date_to
    if (dateFrom && dateTo) {
        const from = new Date(dateFrom)
        const to = new Date(dateTo)
        const span = (to - from) / (1000 * 60 * 60 * 24) + 1
        const prevTo = new Date(from)
        prevTo.setDate(prevTo.getDate() - 1)
        const prevFrom = new Date(prevTo)
        prevFrom.setDate(prevFrom.getDate() - (span - 1))
        prev.date_from = prevFrom.toISOString().slice(0, 10)
        prev.date_to = prevTo.toISOString().slice(0, 10)
    } else if (allParams.days) {
        prev.days = allParams.days
        // Fall back: backend will treat days as a fresh window; we still
        // surface the comparison label even if dates aren't shifted.
    }
    return prev
}

function Skeleton() {
    return (
        <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 16 }}>
            <div style={{ height: 14, width: 120, background: 'rgba(255,255,255,0.05)', borderRadius: 4, marginBottom: 14 }} />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 8 }}>
                {Array.from({ length: 7 }).map((_, i) => (
                    <div key={i} style={{ height: 76, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: 10 }} />
                ))}
            </div>
        </div>
    )
}

export default function DayOfWeekWidget() {
    const { selectedClientId, showToast } = useApp()
    const { allParams, days: filterDays } = useFilter()
    const [data, setData] = useState(null)
    const [prevData, setPrevData] = useState(null)
    const [suggestions, setSuggestions] = useState(null)
    const [metric, setMetric] = useState('clicks')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (!selectedClientId) return
        let cancelled = false
        setLoading(true)
        setError(null)
        const prevParams = buildPrevParams(allParams)
        Promise.all([
            getDayparting(selectedClientId, allParams),
            getDayparting(selectedClientId, prevParams).catch(() => null),
            getDaypartingDowSuggestions(selectedClientId, { ...allParams, days: Math.max(14, Math.min(90, filterDays || 30)) }).catch(() => null),
        ])
            .then(([d, prev, sug]) => {
                if (cancelled) return
                setData(d)
                setPrevData(prev)
                setSuggestions(sug)
                setLoading(false)
            })
            .catch(err => {
                if (cancelled) return
                console.error('[DayOfWeekWidget]', err)
                setData(null)
                setLoading(false)
                setError(err.message || 'Nie udało się załadować danych dnia tygodnia')
                showToast?.(`Dzień tygodnia: ${err.message || 'błąd ładowania'}`, 'error')
            })
        return () => { cancelled = true }
    }, [selectedClientId, allParams, filterDays, showToast])

    const view = useMemo(() => {
        if (!data?.days?.length) return null
        const days = data.days
        const metricDef = METRICS.find(m => m.key === metric) || METRICS[0]
        const values = days.map(d => d[metric] ?? 0)
        const min = Math.min(...values)
        const max = Math.max(...values)
        const median = [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)]

        const significantBest = (idx) => {
            const obs = days[idx].observations || 0
            const v = values[idx]
            return obs >= MIN_OBSERVATIONS_FOR_SIGNIFICANCE && median > 0 && (metricDef.invert ? v <= median * 0.83 : v >= median * 1.2)
        }
        const significantWorst = (idx) => {
            const obs = days[idx].observations || 0
            const v = values[idx]
            return obs >= MIN_OBSERVATIONS_FOR_SIGNIFICANCE && median > 0 && (metricDef.invert ? v >= median * 1.2 : v <= median * 0.83)
        }

        let bestIdx = -1
        let worstIdx = -1
        const sortable = values.map((v, i) => ({ v, i, obs: days[i].observations || 0 }))
            .filter(x => x.obs >= MIN_OBSERVATIONS_FOR_SIGNIFICANCE)
        if (sortable.length) {
            const sorted = [...sortable].sort((a, b) => a.v - b.v)
            const high = sorted[sorted.length - 1].i
            const low = sorted[0].i
            bestIdx = metricDef.invert ? low : high
            worstIdx = metricDef.invert ? high : low
            if (!significantBest(bestIdx)) bestIdx = -1
            if (!significantWorst(worstIdx)) worstIdx = -1
        }
        return { days, metricDef, values, min, max, bestIdx, worstIdx, median }
    }, [data, metric])

    if (loading && !data) return <Skeleton />

    if (error && !data) {
        return (
            <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 16, fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>
                <span style={{ color: '#F87171', marginRight: 6 }}>⚠</span>
                Dzień tygodnia — {error}
            </div>
        )
    }

    if (!view) return null

    const { days, metricDef, values, min, max, bestIdx, worstIdx } = view
    const currency = data.currency || 'PLN'
    const periodDays = data.period_days || 30
    const obsPerDay = Math.floor(periodDays / 7)
    const lowSampleWarning = obsPerDay < MIN_OBSERVATIONS_FOR_SIGNIFICANCE
    const ctMode = data.campaign_type_used || 'ALL'
    const sugList = suggestions?.suggestions || []

    return (
        <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 16 }}>
            <div className="flex items-center justify-between" style={{ marginBottom: 14 }}>
                <div className="flex items-center gap-2">
                    <Calendar size={14} style={{ color: '#7B5CE0' }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                        Dzien tygodnia
                    </span>
                    <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', marginLeft: 4 }}>
                        {periodDays}d · {obsPerDay} obs/dz · {ctMode === 'ALL' ? 'wszystkie typy' : ctMode}
                    </span>
                    {lowSampleWarning && (
                        <span title="Mała próbka — best/worst może być szumem"
                              style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: 10, color: '#FBBF24' }}>
                            <AlertTriangle size={10} /> mało danych
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-1" style={{ flexWrap: 'wrap' }}>
                    {METRICS.map(m => (
                        <button
                            key={m.key}
                            onClick={() => setMetric(m.key)}
                            style={{
                                padding: '3px 10px', borderRadius: 999, fontSize: 10, cursor: 'pointer',
                                border: metric === m.key ? '1px solid rgba(79,142,247,0.4)' : '1px solid rgba(255,255,255,0.06)',
                                background: metric === m.key ? 'rgba(79,142,247,0.1)' : 'transparent',
                                color: metric === m.key ? '#4F8EF7' : 'rgba(255,255,255,0.4)',
                            }}
                        >
                            {m.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Heatmap grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 8 }}>
                {days.map((d, i) => {
                    const val = d[metric] ?? 0
                    const isBest = i === bestIdx
                    const isWorst = i === worstIdx
                    const ringColor = isBest ? 'rgba(74,222,128,0.55)' : isWorst ? 'rgba(248,113,113,0.55)' : null
                    const avgVal = d[`avg_${metric}`]
                    const prevDay = prevData?.days?.find(p => p.day_of_week === d.day_of_week)
                    const prevVal = prevDay ? prevDay[metric] : null
                    const deltaPct = (prevVal && prevVal !== 0)
                        ? ((val - prevVal) / Math.abs(prevVal)) * 100
                        : null
                    const positive = metricDef.invert ? (deltaPct != null && deltaPct < 0) : (deltaPct != null && deltaPct > 0)

                    return (
                        <div
                            key={d.day_name}
                            title={d.dates ? `Dni: ${d.dates.join(', ')}` : `${d.observations || 0} obserwacji`}
                            style={{
                                padding: '12px 8px', borderRadius: 10, textAlign: 'center',
                                background: heatColor(val, min, max, metricDef.invert),
                                border: `1px solid ${borderColor(val, min, max, metricDef.invert)}`,
                                boxShadow: ringColor ? `0 0 0 2px ${ringColor}` : 'none',
                                position: 'relative',
                            }}
                        >
                            <div style={{ fontSize: 10, fontWeight: 600, color: 'rgba(255,255,255,0.4)', marginBottom: 6, textTransform: 'uppercase' }}>
                                {d.day_name}
                            </div>
                            <div style={{
                                fontSize: 16, fontWeight: 700, fontFamily: 'Syne',
                                color: textColor(val, min, max, metricDef.invert),
                            }}>
                                {formatVal(val, metricDef, currency)}
                            </div>
                            <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.25)', marginTop: 4 }}>
                                avg: {avgVal != null ? formatVal(avgVal, metricDef, currency) : '—'}
                            </div>
                            {deltaPct != null && Math.abs(deltaPct) >= 1 && (
                                <div style={{
                                    fontSize: 9, marginTop: 2,
                                    color: positive ? '#4ADE80' : '#F87171',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2,
                                }}>
                                    {positive ? <TrendingUp size={9} /> : <TrendingDown size={9} />}
                                    {deltaPct > 0 ? '+' : ''}{deltaPct.toFixed(0)}% PoP
                                </div>
                            )}
                            {d.dates && d.dates.length > 0 && (
                                <div style={{ fontSize: 8, color: 'rgba(255,255,255,0.18)', marginTop: 2 }}>
                                    {d.dates.length === 1 ? d.dates[0] : `${d.dates.length}×`}
                                </div>
                            )}
                            {(isBest || isWorst) && (
                                <div style={{
                                    position: 'absolute', top: 4, right: 6, fontSize: 8,
                                    color: isBest ? '#4ADE80' : '#F87171', fontWeight: 700,
                                }}>
                                    {isBest ? 'NAJLEPSZY' : 'NAJGORSZY'}
                                </div>
                            )}
                        </div>
                    )
                })}
            </div>

            {/* Legend */}
            <div className="flex items-center gap-4" style={{ marginTop: 8, fontSize: 10, color: 'rgba(255,255,255,0.35)' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ width: 8, height: 8, borderRadius: 2, boxShadow: '0 0 0 2px rgba(74,222,128,0.55)' }} />
                    Najlepszy dzień
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ width: 8, height: 8, borderRadius: 2, boxShadow: '0 0 0 2px rgba(248,113,113,0.55)' }} />
                    Najgorszy dzień
                </span>
                <span style={{ marginLeft: 'auto', fontSize: 9, color: 'rgba(255,255,255,0.3)' }}>
                    Highlighted gdy {'>='} {MIN_OBSERVATIONS_FOR_SIGNIFICANCE} obs i odchylenie {'>='} 20%
                </span>
            </div>

            {/* Bid-schedule suggestions */}
            {sugList.length > 0 && (
                <div style={{ marginTop: 14, padding: '12px 14px', background: 'rgba(79,142,247,0.05)', border: '1px solid rgba(79,142,247,0.2)', borderRadius: 10 }}>
                    <div style={{ fontSize: 11, fontWeight: 600, color: '#4F8EF7', marginBottom: 8, fontFamily: 'Syne' }}>
                        Rekomendacje bid-schedule (per dzień)
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        {sugList.map((s) => {
                            const isInc = s.suggestion_type === 'INCREASE'
                            const isDec = s.suggestion_type === 'DECREASE'
                            const color = isInc ? '#4ADE80' : isDec ? '#F87171' : '#FBBF24'
                            return (
                                <div key={s.day_of_week} style={{
                                    display: 'flex', alignItems: 'center', gap: 10,
                                    padding: '6px 10px', background: 'rgba(255,255,255,0.02)',
                                    borderLeft: `2px solid ${color}`, borderRadius: 4, fontSize: 11,
                                }}>
                                    <span style={{ fontWeight: 700, fontFamily: 'Syne', color, minWidth: 24 }}>{s.day_name}</span>
                                    {s.bid_adjustment_pct != null && (
                                        <span style={{ fontWeight: 600, color, minWidth: 36 }}>
                                            {s.bid_adjustment_pct > 0 ? '+' : ''}{s.bid_adjustment_pct}%
                                        </span>
                                    )}
                                    <span style={{ color: 'rgba(255,255,255,0.65)', flex: 1 }}>{s.reason}</span>
                                    <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase' }}>{s.confidence}</span>
                                </div>
                            )
                        })}
                    </div>
                </div>
            )}
        </div>
    )
}

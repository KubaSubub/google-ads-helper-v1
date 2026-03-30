// DayOfWeekWidget — heatmap-style day-of-week performance
import { useState, useEffect } from 'react'
import { Calendar } from 'lucide-react'
import { getDayparting } from '../../../api'
import { useApp } from '../../../contexts/AppContext'
import { useFilter } from '../../../contexts/FilterContext'

const METRICS = [
    { key: 'clicks', label: 'Klikniecia' },
    { key: 'conversions', label: 'Konwersje' },
    { key: 'cpa', label: 'CPA', suffix: ' zl', invert: true },
    { key: 'roas', label: 'ROAS', suffix: 'x' },
    { key: 'cvr', label: 'CVR', suffix: '%' },
    { key: 'cpc', label: 'CPC', suffix: ' zl', invert: true },
]

function heatColor(value, min, max, invert) {
    if (max === min) return 'rgba(255,255,255,0.06)'
    const ratio = (value - min) / (max - min)
    const t = invert ? 1 - ratio : ratio
    // green for good, red for bad
    if (t > 0.66) return 'rgba(74,222,128,0.15)'
    if (t > 0.33) return 'rgba(251,191,36,0.1)'
    return 'rgba(248,113,113,0.1)'
}

function textColor(value, min, max, invert) {
    if (max === min) return 'rgba(255,255,255,0.5)'
    const ratio = (value - min) / (max - min)
    const t = invert ? 1 - ratio : ratio
    if (t > 0.66) return '#4ADE80'
    if (t > 0.33) return '#FBBF24'
    return '#F87171'
}

export default function DayOfWeekWidget() {
    const { selectedClientId } = useApp()
    const { allParams } = useFilter()
    const [data, setData] = useState(null)
    const [metric, setMetric] = useState('clicks')

    useEffect(() => {
        if (!selectedClientId) return
        getDayparting(selectedClientId, allParams)
            .then(setData)
            .catch(() => setData(null))
    }, [selectedClientId, allParams])

    if (!data?.days?.length) return null

    const days = data.days
    const metricDef = METRICS.find(m => m.key === metric) || METRICS[0]
    const values = days.map(d => d[metric] ?? 0)
    const min = Math.min(...values)
    const max = Math.max(...values)

    // Find best and worst day
    const bestIdx = values.indexOf(Math.max(...values))
    const worstIdx = values.indexOf(Math.min(...values))

    return (
        <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 16 }}>
            <div className="flex items-center justify-between" style={{ marginBottom: 14 }}>
                <div className="flex items-center gap-2">
                    <Calendar size={14} style={{ color: '#7B5CE0' }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                        Dzien tygodnia
                    </span>
                </div>
                <div className="flex items-center gap-1">
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
                    const isBest = i === bestIdx && !metricDef.invert
                    const isWorst = i === worstIdx && !metricDef.invert
                    const isBestInv = i === worstIdx && metricDef.invert
                    const isWorstInv = i === bestIdx && metricDef.invert
                    const highlight = isBest || isBestInv

                    return (
                        <div
                            key={d.day_name}
                            style={{
                                padding: '12px 8px', borderRadius: 10, textAlign: 'center',
                                background: heatColor(val, min, max, metricDef.invert),
                                border: highlight
                                    ? '1px solid rgba(74,222,128,0.3)'
                                    : (isWorst || isWorstInv)
                                        ? '1px solid rgba(248,113,113,0.2)'
                                        : '1px solid rgba(255,255,255,0.04)',
                            }}
                        >
                            <div style={{ fontSize: 10, fontWeight: 600, color: 'rgba(255,255,255,0.4)', marginBottom: 6, textTransform: 'uppercase' }}>
                                {d.day_name}
                            </div>
                            <div style={{
                                fontSize: 16, fontWeight: 700, fontFamily: 'Syne',
                                color: textColor(val, min, max, metricDef.invert),
                            }}>
                                {typeof val === 'number' ? val.toLocaleString('pl-PL', { maximumFractionDigits: 1 }) : val}
                                {metricDef.suffix && <span style={{ fontSize: 10 }}>{metricDef.suffix}</span>}
                            </div>
                            <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.25)', marginTop: 4 }}>
                                avg: {d[`avg_${metric}`] != null
                                    ? (typeof d[`avg_${metric}`] === 'number'
                                        ? d[`avg_${metric}`].toLocaleString('pl-PL', { maximumFractionDigits: 1 })
                                        : d[`avg_${metric}`])
                                    : '—'
                                }
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

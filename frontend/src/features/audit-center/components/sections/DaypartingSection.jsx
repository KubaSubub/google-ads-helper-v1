import { useState } from 'react'

const METRICS = [
    { key: 'clicks', label: 'Klikniecia' },
    { key: 'conversions', label: 'Konwersje' },
    { key: 'conversion_value_amount', label: 'Wartosc konw.', isCurrency: true },
    { key: 'aov', label: 'AOV', isCurrency: true },
    { key: 'cpa', label: 'CPA', isCurrency: true, invert: true },
    { key: 'roas', label: 'ROAS', suffix: 'x' },
]

function heatColor(t) {
    if (t >= 0.80) return 'rgba(74,222,128,0.20)'
    if (t >= 0.60) return 'rgba(163,230,53,0.16)'
    if (t >= 0.40) return 'rgba(251,191,36,0.13)'
    if (t >= 0.20) return 'rgba(251,146,60,0.11)'
    return 'rgba(248,113,113,0.13)'
}
function borderColor(t) {
    if (t >= 0.80) return 'rgba(74,222,128,0.30)'
    if (t >= 0.60) return 'rgba(163,230,53,0.25)'
    if (t >= 0.40) return 'rgba(251,191,36,0.22)'
    if (t >= 0.20) return 'rgba(251,146,60,0.20)'
    return 'rgba(248,113,113,0.25)'
}
function textColor(t) {
    if (t >= 0.80) return '#4ADE80'
    if (t >= 0.60) return '#A3E635'
    if (t >= 0.40) return '#FBBF24'
    if (t >= 0.20) return '#FB923C'
    return '#F87171'
}

function formatVal(val, def, currency) {
    if (val == null) return '—'
    if (typeof val !== 'number') return String(val)
    const f = val.toLocaleString('pl-PL', { maximumFractionDigits: 1 })
    if (def.isCurrency) return `${f} ${currency}`
    if (def.suffix) return `${f}${def.suffix}`
    return f
}

export default function DaypartingSection({ data }) {
    const [metric, setMetric] = useState('clicks')
    if (!data?.days?.length) return null

    const def = METRICS.find(m => m.key === metric) || METRICS[0]
    const currency = data.currency || 'PLN'
    const values = data.days.map(d => d[metric] ?? 0)
    const min = Math.min(...values)
    const max = Math.max(...values)

    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div className="flex items-center gap-1" style={{ marginBottom: 10, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', marginRight: 6 }}>
                    {data.period_days || 0}d · {data.campaign_type_used === 'ALL' ? 'wszystkie typy' : (data.campaign_type_used || 'ALL')}
                </span>
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

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 8 }}>
                {data.days.map(d => {
                    const val = d[metric] ?? 0
                    const ratio = max === min ? 0.5 : (val - min) / (max - min)
                    const t = def.invert ? 1 - ratio : ratio
                    return (
                        <div key={d.day_of_week} style={{
                            padding: 10, borderRadius: 8, textAlign: 'center',
                            background: heatColor(t),
                            border: `1px solid ${borderColor(t)}`,
                        }}>
                            <div style={{ fontSize: 11, fontWeight: 600, color: '#F0F0F0', marginBottom: 6 }}>
                                {d.day_name}
                            </div>
                            <div style={{ fontSize: 16, fontWeight: 700, fontFamily: 'Syne', color: textColor(t) }}>
                                {formatVal(val, def, currency)}
                            </div>
                            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', marginTop: 4 }}>
                                {d.observations || 0} obs
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

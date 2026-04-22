// 7×24 (day-of-week × hour-of-day) heatmap for bid-schedule planning.
import { useState, useMemo } from 'react'

const METRICS = [
    { key: 'cost', label: 'Koszt', isCurrency: true },
    { key: 'clicks', label: 'Klikniecia' },
    { key: 'conversions', label: 'Konwersje' },
    { key: 'cpa', label: 'CPA', isCurrency: true, invert: true },
    { key: 'roas', label: 'ROAS', suffix: 'x' },
    { key: 'cvr', label: 'CVR', suffix: '%' },
]

const DAY_NAMES = ['Pn', 'Wt', 'Sr', 'Cz', 'Pt', 'Sb', 'Nd']

function heatColor(t) {
    if (t == null) return 'rgba(255,255,255,0.02)'
    if (t >= 0.80) return 'rgba(74,222,128,0.30)'
    if (t >= 0.60) return 'rgba(163,230,53,0.22)'
    if (t >= 0.40) return 'rgba(251,191,36,0.18)'
    if (t >= 0.20) return 'rgba(251,146,60,0.16)'
    return 'rgba(248,113,113,0.18)'
}

function fmt(val, def, currency) {
    if (val == null) return '—'
    if (typeof val !== 'number') return String(val)
    const f = val.toLocaleString('pl-PL', { maximumFractionDigits: 1 })
    if (def.isCurrency) return `${f} ${currency}`
    if (def.suffix) return `${f}${def.suffix}`
    return f
}

export default function DowHourHeatmapSection({ data }) {
    const [metric, setMetric] = useState('cost')
    if (!data?.cells?.length) return null

    const def = METRICS.find(m => m.key === metric) || METRICS[0]
    const currency = data.currency || 'PLN'

    const { grid, min, max } = useMemo(() => {
        const g = {}
        for (const c of data.cells) {
            g[`${c.day_of_week}_${c.hour}`] = c
        }
        const vals = data.cells.map(c => c[metric]).filter(v => v != null && v !== 0)
        const min = vals.length ? Math.min(...vals) : 0
        const max = vals.length ? Math.max(...vals) : 0
        return { grid: g, min, max }
    }, [data, metric])

    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div className="flex items-center justify-between" style={{ marginBottom: 10, flexWrap: 'wrap', gap: 6 }}>
                <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>
                    Ostatnie {data.window_days || 30}d · 7×24 (dzień × godzina) ·
                    {data.overall_cpa ? ` baseline CPA ${data.overall_cpa.toFixed(2)} ${currency}` : ''}
                </span>
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

            <div style={{ overflowX: 'auto' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '32px repeat(24, minmax(28px, 1fr))', gap: 2, minWidth: 760 }}>
                    {/* Header row */}
                    <div />
                    {Array.from({ length: 24 }).map((_, h) => (
                        <div key={`h${h}`} style={{ fontSize: 9, color: 'rgba(255,255,255,0.35)', textAlign: 'center', padding: '2px 0' }}>
                            {h}
                        </div>
                    ))}

                    {/* Day rows */}
                    {DAY_NAMES.map((dayName, dow) => (
                        <div key={`row${dow}`} style={{ display: 'contents' }}>
                            <div style={{ fontSize: 10, fontWeight: 600, color: 'rgba(255,255,255,0.55)', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', paddingRight: 6 }}>
                                {dayName}
                            </div>
                            {Array.from({ length: 24 }).map((_, h) => {
                                const cell = grid[`${dow}_${h}`]
                                const val = cell?.[metric]
                                let t = null
                                if (val != null && max !== min) {
                                    const ratio = (val - min) / (max - min)
                                    t = def.invert ? 1 - ratio : ratio
                                }
                                return (
                                    <div
                                        key={`c${dow}_${h}`}
                                        title={cell ? `${dayName} ${h}:00 · ${def.label}: ${fmt(val, def, currency)} · clicks ${cell.clicks}, conv ${cell.conversions}` : ''}
                                        style={{
                                            height: 22,
                                            background: heatColor(t),
                                            border: '1px solid rgba(255,255,255,0.04)',
                                            borderRadius: 3,
                                            cursor: cell ? 'help' : 'default',
                                        }}
                                    />
                                )
                            })}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}

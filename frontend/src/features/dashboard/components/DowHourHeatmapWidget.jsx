// DowHourHeatmapWidget — 7x24 (day-of-week x hour-of-day) matrix for Dashboard.
import { useState, useEffect, useMemo } from 'react'
import { Grid3x3 } from 'lucide-react'
import { getDaypartingHeatmap } from '../../../api'
import { useApp } from '../../../contexts/AppContext'
import { useFilter } from '../../../contexts/FilterContext'

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

function Skeleton() {
    return (
        <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 16 }}>
            <div style={{ height: 14, width: 160, background: 'rgba(255,255,255,0.05)', borderRadius: 4, marginBottom: 14 }} />
            <div style={{ display: 'grid', gridTemplateColumns: '32px repeat(24, 1fr)', gap: 2 }}>
                {Array.from({ length: 7 * 25 }).map((_, i) => (
                    <div key={i} style={{ height: 20, background: 'rgba(255,255,255,0.03)', borderRadius: 3 }} />
                ))}
            </div>
        </div>
    )
}

export default function DowHourHeatmapWidget() {
    const { selectedClientId, showToast } = useApp()
    const { allParams, days: periodDays } = useFilter()
    const [data, setData] = useState(null)
    const [metric, setMetric] = useState('cost')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (!selectedClientId) return
        let cancelled = false
        setLoading(true)
        setError(null)
        getDaypartingHeatmap(selectedClientId, { ...allParams, days: Math.max(14, Math.min(90, periodDays || 30)) })
            .then(d => { if (!cancelled) { setData(d); setLoading(false) } })
            .catch(err => {
                if (cancelled) return
                console.error('[DowHourHeatmapWidget]', err)
                setData(null); setLoading(false)
                setError(err.message || 'Nie udalo sie zaladowac macierzy 7x24')
                showToast?.(`Heatmapa 7x24: ${err.message || 'blad'}`, 'error')
            })
        return () => { cancelled = true }
    }, [selectedClientId, allParams, periodDays, showToast])

    const { grid, min, max } = useMemo(() => {
        if (!data?.cells?.length) return { grid: {}, min: 0, max: 0 }
        const g = {}
        for (const c of data.cells) g[`${c.day_of_week}_${c.hour}`] = c
        const vals = data.cells.map(c => c[metric]).filter(v => v != null && v !== 0)
        return {
            grid: g,
            min: vals.length ? Math.min(...vals) : 0,
            max: vals.length ? Math.max(...vals) : 0,
        }
    }, [data, metric])

    if (loading && !data) return <Skeleton />
    if (error && !data) {
        return (
            <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 16, fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>
                <span style={{ color: '#F87171', marginRight: 6 }}>⚠</span>
                Heatmapa 7x24 — {error}
            </div>
        )
    }
    // Cells are always materialized 7x24, but may all be null when the hourly
    // segment hasn't been synced. Show an explicit empty state instead of null.
    const hasAnyData = data?.cells?.length && data.cells.some(c => (c.clicks || 0) > 0 || (c.conversions || 0) > 0)
    if (!data?.cells?.length || !hasAnyData) {
        return (
            <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 16 }}>
                <div className="flex items-center gap-2" style={{ marginBottom: 8 }}>
                    <Grid3x3 size={14} style={{ color: '#7B5CE0' }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                        Heatmapa 7×24 (dzien × godzina)
                    </span>
                </div>
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>
                    Brak danych godzinowych dla tego konta. Uruchom sync segmentu godzinowego, aby zobaczyć macierz 7×24.
                </div>
            </div>
        )
    }

    const def = METRICS.find(m => m.key === metric) || METRICS[0]
    const currency = data.currency || 'PLN'

    return (
        <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 16 }}>
            <div className="flex items-center justify-between" style={{ marginBottom: 14, flexWrap: 'wrap', gap: 6 }}>
                <div className="flex items-center gap-2">
                    <Grid3x3 size={14} style={{ color: '#7B5CE0' }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                        Heatmapa 7×24 (dzien × godzina)
                    </span>
                    <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', marginLeft: 4 }}>
                        Ostatnie {data.window_days || 30}d
                        {data.overall_cpa ? ` · baseline CPA ${data.overall_cpa.toFixed(2)} ${currency}` : ''}
                    </span>
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

            <div style={{ overflowX: 'auto' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '32px repeat(24, minmax(24px, 1fr))', gap: 2, minWidth: 720 }}>
                    <div />
                    {Array.from({ length: 24 }).map((_, h) => (
                        <div key={`h${h}`} style={{ fontSize: 9, color: 'rgba(255,255,255,0.35)', textAlign: 'center', padding: '2px 0' }}>
                            {h}
                        </div>
                    ))}

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
                                        title={cell ? `${dayName} ${h}:00 · ${def.label}: ${fmt(val, def, currency)} · klik ${cell.clicks} · konw ${cell.conversions}` : `${dayName} ${h}:00 · brak danych`}
                                        style={{
                                            height: 20,
                                            background: heatColor(t),
                                            border: '1px solid rgba(255,255,255,0.04)',
                                            borderRadius: 3,
                                            cursor: cell && (cell.clicks || 0) > 0 ? 'help' : 'default',
                                        }}
                                    />
                                )
                            })}
                        </div>
                    ))}
                </div>
            </div>

            <div className="flex items-center gap-3" style={{ marginTop: 8, fontSize: 9, color: 'rgba(255,255,255,0.3)' }}>
                <span>Intensywnosc: slabe</span>
                {[0.15, 0.3, 0.5, 0.7, 0.9].map((t, i) => (
                    <span key={i} style={{ width: 18, height: 10, background: heatColor(t), border: '1px solid rgba(255,255,255,0.08)', borderRadius: 2 }} />
                ))}
                <span>dobre</span>
                <span style={{ marginLeft: 'auto' }}>Najedz kursorem na komorke aby zobaczyc szczegoly</span>
            </div>
        </div>
    )
}

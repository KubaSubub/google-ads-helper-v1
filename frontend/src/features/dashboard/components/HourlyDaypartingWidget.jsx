// HourlyDaypartingWidget — 24-hour performance bars for Dashboard.
import { useState, useEffect } from 'react'
import { Clock } from 'lucide-react'
import { getHourlyDayparting } from '../../../api'
import { useApp } from '../../../contexts/AppContext'
import { useFilter } from '../../../contexts/FilterContext'

const METRICS = [
    { key: 'conversions', label: 'Konwersje' },
    { key: 'clicks', label: 'Klikniecia' },
    { key: 'cost_usd', label: 'Koszt', isCurrency: true },
    { key: 'cpa', label: 'CPA', isCurrency: true, invert: true },
    { key: 'roas', label: 'ROAS', suffix: 'x' },
]

function formatVal(val, def, currency) {
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
            <div style={{ height: 14, width: 140, background: 'rgba(255,255,255,0.05)', borderRadius: 4, marginBottom: 14 }} />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(24, 1fr)', gap: 3 }}>
                {Array.from({ length: 24 }).map((_, i) => (
                    <div key={i} style={{ height: 56, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: 6 }} />
                ))}
            </div>
        </div>
    )
}

export default function HourlyDaypartingWidget() {
    const { selectedClientId, showToast } = useApp()
    const { allParams } = useFilter()
    const [data, setData] = useState(null)
    const [metric, setMetric] = useState('conversions')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (!selectedClientId) return
        let cancelled = false
        setLoading(true)
        setError(null)
        getHourlyDayparting(selectedClientId, allParams)
            .then(d => { if (!cancelled) { setData(d); setLoading(false) } })
            .catch(err => {
                if (cancelled) return
                console.error('[HourlyDaypartingWidget]', err)
                setData(null); setLoading(false)
                setError(err.message || 'Nie udalo sie zaladowac danych godzinowych')
                showToast?.(`Godziny: ${err.message || 'blad'}`, 'error')
            })
        return () => { cancelled = true }
    }, [selectedClientId, allParams, showToast])

    if (loading && !data) return <Skeleton />
    if (error && !data) {
        return (
            <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 16, fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>
                <span style={{ color: '#F87171', marginRight: 6 }}>⚠</span>
                Godziny — {error}
            </div>
        )
    }
    // Widget shows even when hours array is empty or all zeros — the empty state
    // tells the user the hourly segment hasn't been synced yet (fail-silent was
    // making the widget vanish with no explanation).
    const hasAnyData = data?.hours?.length && data.hours.some(h => (h.clicks || 0) > 0 || (h.conversions || 0) > 0)
    if (!data?.hours?.length || !hasAnyData) {
        return (
            <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 16 }}>
                <div className="flex items-center gap-2" style={{ marginBottom: 8 }}>
                    <Clock size={14} style={{ color: '#4F8EF7' }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                        Godziny (0-23)
                    </span>
                </div>
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>
                    Brak danych godzinowych dla tego konta. Uruchom sync segmentu godzinowego, aby zobaczyć rozkład 24h.
                </div>
            </div>
        )
    }

    const def = METRICS.find(m => m.key === metric) || METRICS[0]
    const currency = data.currency || 'PLN'
    const ctMode = data.campaign_type_used || 'ALL'
    const vals = data.hours.map(h => {
        const v = h[metric]
        return v == null ? 0 : v
    })
    const min = Math.min(...vals)
    const max = Math.max(...vals)

    const bestIdx = vals.indexOf(def.invert ? min : max)
    const worstIdx = vals.indexOf(def.invert ? max : min)

    return (
        <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 16 }}>
            <div className="flex items-center justify-between" style={{ marginBottom: 14, flexWrap: 'wrap', gap: 6 }}>
                <div className="flex items-center gap-2">
                    <Clock size={14} style={{ color: '#4F8EF7' }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                        Godziny (0-23)
                    </span>
                    <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', marginLeft: 4 }}>
                        best: {bestIdx}:00 · worst: {worstIdx}:00 · {ctMode === 'ALL' ? 'wszystkie typy' : ctMode}
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

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(24, 1fr)', gap: 3 }}>
                {data.hours.map((h, i) => {
                    const val = vals[i]
                    const ratio = max === min ? 0.5 : (val - min) / (max - min)
                    const t = def.invert ? 1 - ratio : ratio
                    const isBiz = h.hour >= 9 && h.hour <= 18
                    const isBest = i === bestIdx && val > 0
                    const isWorst = i === worstIdx && val > 0
                    const bg = `rgba(${t >= 0.5 ? '74,222,128' : '248,113,113'},${0.08 + Math.abs(t - 0.5) * 2 * 0.35})`
                    return (
                        <div
                            key={h.hour}
                            title={`${h.hour_label || `${h.hour}:00`}: ${def.label} ${formatVal(val, def, currency)} · klik ${h.clicks} · konw ${h.conversions?.toFixed?.(1) ?? 0}`}
                            style={{
                                height: 56, borderRadius: 6,
                                background: bg,
                                border: `1px solid ${isBiz ? 'rgba(79,142,247,0.18)' : 'rgba(255,255,255,0.05)'}`,
                                boxShadow: isBest ? '0 0 0 2px rgba(74,222,128,0.55)' : isWorst ? '0 0 0 2px rgba(248,113,113,0.55)' : 'none',
                                display: 'flex', flexDirection: 'column',
                                alignItems: 'center', justifyContent: 'flex-end',
                                paddingBottom: 4, position: 'relative',
                            }}
                        >
                            {val > 0 && (
                                <span style={{ fontSize: 8, color: t >= 0.5 ? '#4ADE80' : '#F87171', fontWeight: 600, marginBottom: 1 }}>
                                    {typeof val === 'number' ? val.toLocaleString('pl-PL', { maximumFractionDigits: 0 }) : val}
                                </span>
                            )}
                            <span style={{ fontSize: 8, color: 'rgba(255,255,255,0.4)' }}>{h.hour}</span>
                        </div>
                    )
                })}
            </div>

            <div className="flex items-center gap-3" style={{ marginTop: 8, fontSize: 9, color: 'rgba(255,255,255,0.3)' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ width: 8, height: 8, borderRadius: 2, boxShadow: '0 0 0 2px rgba(74,222,128,0.55)' }} /> Najlepsza godzina
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ width: 8, height: 8, borderRadius: 2, boxShadow: '0 0 0 2px rgba(248,113,113,0.55)' }} /> Najgorsza
                </span>
                <span style={{ marginLeft: 'auto' }}>
                    Ramka niebieska = godziny biznesowe 9-18
                </span>
            </div>
        </div>
    )
}

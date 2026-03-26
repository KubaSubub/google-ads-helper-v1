import { useState, useEffect, useCallback } from 'react'
import {
    ComposedChart, Line, XAxis, YAxis, Tooltip,
    ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'
import { getWoWComparison } from '../api'
import { useApp } from '../contexts/AppContext'
import { useFilter } from '../contexts/FilterContext'

const METRIC_OPTIONS = [
    { key: 'cost', label: 'Koszt (zł)' },
    { key: 'clicks', label: 'Kliknięcia' },
    { key: 'conversions', label: 'Konwersje' },
    { key: 'ctr', label: 'CTR (%)' },
    { key: 'roas', label: 'ROAS' },
    { key: 'cpa', label: 'CPA (zł)' },
    { key: 'impressions', label: 'Wyświetlenia' },
]

export default function WoWChart() {
    const { selectedClientId } = useApp()
    const { allParams, days } = useFilter()
    const [metric, setMetric] = useState('cost')
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(false)

    const load = useCallback(async () => {
        if (!selectedClientId) return
        setLoading(true)
        try {
            const resp = await getWoWComparison(selectedClientId, {
                ...allParams,
                metric,
                days: Math.min(days || 7, 30),
            })
            setData(resp)
        } catch (err) {
            console.error('[WoWChart]', err)
            setData(null)
        } finally {
            setLoading(false)
        }
    }, [selectedClientId, allParams, metric, days])

    useEffect(() => { load() }, [load])

    if (!data && !loading) return null

    // Merge current and previous into single array aligned by day_index
    const maxDays = data?.period_days || 7
    const merged = []
    for (let i = 0; i < maxDays; i++) {
        const cur = data?.current?.find(d => d.day_index === i)
        const prev = data?.previous?.find(d => d.day_index === i)
        const curDate = cur?.date
        const prevDate = prev?.date
        const formatDate = (s) => {
            if (!s) return null
            const d = new Date(s)
            return `${d.getDate()}.${(d.getMonth() + 1).toString().padStart(2, '0')}`
        }
        merged.push({
            day: formatDate(curDate) || formatDate(prevDate) || `D${i + 1}`,
            current: cur?.value ?? null,
            previous: prev?.value ?? null,
        })
    }

    const metricLabel = METRIC_OPTIONS.find(m => m.key === metric)?.label || metric

    return (
        <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                    Porównanie okresów
                </span>
                <div className="flex items-center gap-2">
                    {data?.current_range && (
                        <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)' }}>
                            {data.current_range[0].slice(5)} — {data.current_range[1].slice(5)}
                            {' vs '}
                            {data.previous_range[0].slice(5)} — {data.previous_range[1].slice(5)}
                        </span>
                    )}
                    <select
                        value={metric}
                        onChange={e => setMetric(e.target.value)}
                        style={{
                            background: 'rgba(255,255,255,0.06)',
                            border: '1px solid rgba(255,255,255,0.1)',
                            borderRadius: 6,
                            padding: '4px 8px',
                            fontSize: 11,
                            color: '#F0F0F0',
                            cursor: 'pointer',
                        }}
                    >
                        {METRIC_OPTIONS.map(m => (
                            <option key={m.key} value={m.key}>{m.label}</option>
                        ))}
                    </select>
                </div>
            </div>

            {loading ? (
                <div style={{ height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, color: 'rgba(255,255,255,0.2)' }}>
                    Ładowanie…
                </div>
            ) : merged.length === 0 ? (
                <div style={{ height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, color: 'rgba(255,255,255,0.3)' }}>
                    Brak danych do porównania
                </div>
            ) : (
                <ResponsiveContainer width="100%" height={180}>
                    <ComposedChart data={merged} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                        <XAxis
                            dataKey="day"
                            tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.35)' }}
                            axisLine={false}
                            tickLine={false}
                        />
                        <YAxis
                            tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.25)' }}
                            axisLine={false}
                            tickLine={false}
                            width={45}
                        />
                        <Tooltip
                            contentStyle={{
                                background: '#1a1d24',
                                border: '1px solid rgba(255,255,255,0.12)',
                                borderRadius: 8,
                                fontSize: 11,
                            }}
                            formatter={(value, name) => [
                                value != null ? value.toLocaleString('pl-PL', { maximumFractionDigits: 2 }) : '—',
                                name === 'current' ? 'Bieżący okres' : 'Poprzedni okres',
                            ]}
                        />
                        <Legend
                            formatter={value => (
                                <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.5)' }}>
                                    {value === 'current' ? `Bieżący (${metricLabel})` : `Poprzedni (${metricLabel})`}
                                </span>
                            )}
                        />
                        <Line
                            type="monotone"
                            dataKey="previous"
                            stroke="rgba(255,255,255,0.25)"
                            strokeWidth={1.5}
                            strokeDasharray="5 3"
                            dot={false}
                            connectNulls
                        />
                        <Line
                            type="monotone"
                            dataKey="current"
                            stroke="#4F8EF7"
                            strokeWidth={2}
                            dot={{ r: 3, fill: '#4F8EF7', strokeWidth: 0 }}
                            connectNulls
                        />
                    </ComposedChart>
                </ResponsiveContainer>
            )}
        </div>
    )
}

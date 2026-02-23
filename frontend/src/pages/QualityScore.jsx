import { useState, useEffect, useCallback } from 'react'
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts'
import { AlertTriangle, CheckCircle, HelpCircle, ArrowRight, RefreshCw, Loader2 } from 'lucide-react'
import { getQualityScoreAudit } from '../api'
import { useApp } from '../contexts/AppContext'
import EmptyState from '../components/EmptyState'

const QS_COLORS = { low: '#F87171', mid: '#FBBF24', high: '#4ADE80' }

function getQSColor(score) {
    if (score <= 3) return QS_COLORS.low
    if (score <= 6) return QS_COLORS.mid
    return QS_COLORS.high
}

export default function QualityScore() {
    const { selectedClientId } = useApp()
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    const loadData = useCallback(async () => {
        if (!selectedClientId) return
        setLoading(true)
        setError(null)
        try {
            const res = await getQualityScoreAudit(selectedClientId)
            setData(res)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }, [selectedClientId])

    useEffect(() => { loadData() }, [loadData])

    if (!selectedClientId) return <EmptyState message="Wybierz klienta w sidebarze" />

    if (error) {
        return (
            <div style={{ maxWidth: 1200, padding: '40px 0', textAlign: 'center' }}>
                <div style={{ fontSize: 14, color: '#F87171', marginBottom: 12 }}>Błąd: {error}</div>
                <button onClick={loadData} style={{ padding: '6px 16px', borderRadius: 7, fontSize: 12, background: '#4F8EF7', color: 'white', border: 'none', cursor: 'pointer' }}>
                    Spróbuj ponownie
                </button>
            </div>
        )
    }

    if (loading || !data) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '60px 0' }}>
                <Loader2 size={28} style={{ color: '#4F8EF7' }} className="animate-spin" />
            </div>
        )
    }

    const chartData = Array.from({ length: 10 }, (_, i) => {
        const score = i + 1
        return {
            score: score.toString(),
            count: data.qs_distribution?.[`qs_${score}`] || 0,
            color: getQSColor(score),
        }
    })

    const highQSCount = chartData.filter(d => parseInt(d.score) >= 8).reduce((a, c) => a + c.count, 0)

    return (
        <div style={{ maxWidth: 1200 }}>
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 20 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Audyt Quality Score
                    </h1>
                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                        Analiza {data.total_keywords} słów kluczowych
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '5px 12px', borderRadius: 7, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>
                        <HelpCircle size={12} />
                        Cel: średni QS powyżej 7.0
                    </div>
                    <button
                        onClick={loadData}
                        style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '5px 12px', borderRadius: 7, fontSize: 12, background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.6)', cursor: 'pointer' }}
                        className="hover:border-white/20 hover:text-white/80"
                    >
                        <RefreshCw size={12} /> Odśwież
                    </button>
                </div>
            </div>

            {/* Summary row */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 20 }}>
                <div className="v2-card" style={{ padding: '14px 18px', borderLeft: '3px solid #4F8EF7' }}>
                    <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                        Średni QS
                    </div>
                    <span style={{ fontSize: 26, fontWeight: 700, color: getQSColor(data.average_qs), fontFamily: 'Syne' }}>
                        {data.average_qs.toFixed(1)}
                    </span>
                    <span style={{ fontSize: 13, color: 'rgba(255,255,255,0.3)', marginLeft: 4 }}>/10</span>
                </div>
                <div className="v2-card" style={{ padding: '14px 18px', borderLeft: '3px solid #F87171' }}>
                    <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                        Niski QS (&lt;{data.qs_threshold})
                    </div>
                    <span style={{ fontSize: 26, fontWeight: 700, color: '#F87171', fontFamily: 'Syne' }}>
                        {data.low_qs_count}
                    </span>
                    <span style={{ fontSize: 11, color: 'rgba(248,113,113,0.5)', marginLeft: 6 }}>wymaga uwagi</span>
                </div>
                <div className="v2-card" style={{ padding: '14px 18px', borderLeft: '3px solid #4ADE80' }}>
                    <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                        Wysoki QS (8-10)
                    </div>
                    <span style={{ fontSize: 26, fontWeight: 700, color: '#4ADE80', fontFamily: 'Syne' }}>
                        {highQSCount}
                    </span>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 16 }}>
                {/* Chart */}
                <div className="v2-card" style={{ padding: '18px' }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne', marginBottom: 16 }}>
                        Rozkład QS
                    </div>
                    <div style={{ height: 220 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={chartData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                                <XAxis
                                    dataKey="score"
                                    tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }}
                                    axisLine={false} tickLine={false}
                                />
                                <YAxis
                                    tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }}
                                    axisLine={false} tickLine={false}
                                    allowDecimals={false} width={24}
                                />
                                <Tooltip
                                    cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                                    contentStyle={{
                                        backgroundColor: '#1a1d24',
                                        borderColor: 'rgba(255,255,255,0.12)',
                                        borderRadius: '8px',
                                        color: '#F0F0F0',
                                        fontSize: 12,
                                    }}
                                />
                                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                                    {chartData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="flex justify-between" style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', marginTop: 8, padding: '0 4px' }}>
                        <span style={{ color: '#F87171' }}>Niski (1-3)</span>
                        <span style={{ color: '#FBBF24' }}>Średni (4-6)</span>
                        <span style={{ color: '#4ADE80' }}>Wysoki (7-10)</span>
                    </div>
                </div>

                {/* Issues table */}
                <div className="v2-card" style={{ overflow: 'hidden' }}>
                    <div style={{ padding: '14px 18px', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                            Słowa wymagające optymalizacji
                        </div>
                        <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', marginTop: 2 }}>
                            Wynik jakości poniżej {data.qs_threshold} — popraw je, aby obniżyć CPC.
                        </p>
                    </div>

                    {data.low_qs_keywords.length === 0 ? (
                        <div style={{ padding: '40px', textAlign: 'center' }}>
                            <CheckCircle size={32} style={{ color: '#4ADE80', margin: '0 auto 10px' }} />
                            <div style={{ fontSize: 14, fontWeight: 500, color: '#F0F0F0', marginBottom: 4 }}>Brak problemów!</div>
                            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>Wszystkie aktywne słowa mają QS ≥ {data.qs_threshold}.</div>
                        </div>
                    ) : (
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                                        {['Słowo kluczowe', 'QS', 'Diagnostyka', 'Rekomendacja'].map(h => (
                                            <th key={h} style={{
                                                padding: '10px 14px', textAlign: h === 'QS' ? 'center' : 'left',
                                                fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)',
                                                textTransform: 'uppercase', letterSpacing: '0.08em',
                                            }}>{h}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.low_qs_keywords.map((item, i) => (
                                        <tr key={i}
                                            style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.12s' }}
                                            onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.025)'}
                                            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                                        >
                                            <td style={{ padding: '12px 14px' }}>
                                                <div style={{ fontSize: 13, fontWeight: 500, color: '#F0F0F0' }}>{item.keyword}</div>
                                                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', marginTop: 2 }}>{item.campaign}</div>
                                            </td>
                                            <td style={{ padding: '12px 14px', textAlign: 'center' }}>
                                                <span style={{
                                                    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                                                    width: 30, height: 30, borderRadius: 8, fontWeight: 700, fontSize: 13,
                                                    background: `${getQSColor(item.quality_score)}15`,
                                                    color: getQSColor(item.quality_score),
                                                }}>
                                                    {item.quality_score}
                                                </span>
                                            </td>
                                            <td style={{ padding: '12px 14px' }}>
                                                {item.issues?.length > 0 ? (
                                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                                                        {item.issues.map((issue, idx) => (
                                                            <div key={idx} className="flex items-start gap-1.5" style={{ fontSize: 11, color: 'rgba(248,113,113,0.7)' }}>
                                                                <AlertTriangle size={10} style={{ marginTop: 2, flexShrink: 0 }} />
                                                                <span>{issue}</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.2)', fontStyle: 'italic' }}>Brak wyraźnych problemów</span>
                                                )}
                                            </td>
                                            <td style={{ padding: '12px 14px' }}>
                                                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 6, fontSize: 11, color: 'rgba(255,255,255,0.55)', background: 'rgba(255,255,255,0.03)', padding: '6px 10px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.06)' }}>
                                                    <ArrowRight size={10} style={{ color: '#4F8EF7', marginTop: 2, flexShrink: 0 }} />
                                                    {item.recommendation}
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

import { useState, useEffect } from 'react'
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts'
import { AlertTriangle, CheckCircle, HelpCircle, ArrowRight } from 'lucide-react'
import { LoadingSpinner, ErrorMessage, PageHeader } from '../components/UI'
import { getQualityScoreAudit } from '../api'

export default function QualityScore() {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        loadData()
    }, [])

    async function loadData() {
        setLoading(true)
        try {
            const res = await getQualityScoreAudit(1) // Hardcoded client_id=1
            setData(res)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    if (error) return <ErrorMessage message={error} onRetry={loadData} />
    if (loading) return <LoadingSpinner />

    // Prepare chart data
    const chartData = Array.from({ length: 10 }, (_, i) => {
        const score = i + 1
        return {
            score: score.toString(),
            count: data.qs_distribution[`qs_${score}`] || 0,
            color: score <= 4 ? '#ef4444' : score <= 7 ? '#eab308' : '#22c55e'
        }
    })

    return (
        <div className="max-w-[1400px] mx-auto space-y-6">
            <PageHeader
                title="Audyt Wyniku Jakości (Quality Score)"
                subtitle={`Analiza ${data.total_keywords} słów kluczowych`}
            >
                <div className="flex items-center gap-2 text-sm text-surface-200/60 bg-surface-700/30 px-3 py-1.5 rounded-lg border border-surface-700/50">
                    <HelpCircle size={14} />
                    <span>Cel: Utrzymaj średni QS powyżej 7.0</span>
                </div>
            </PageHeader>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="glass p-5 rounded-xl border-l-4 border-l-brand-500">
                    <p className="text-sm text-surface-200/60 font-medium">Średni Wynik Jakości</p>
                    <p className="text-3xl font-bold text-white mt-1">{data.average_qs.toFixed(1)}/10</p>
                </div>
                <div className="glass p-5 rounded-xl border-l-4 border-l-red-500">
                    <p className="text-sm text-surface-200/60 font-medium">Słowa z niskim QS (&lt;{data.qs_threshold})</p>
                    <div className="flex items-baseline gap-2 mt-1">
                        <p className="text-3xl font-bold text-red-400">{data.low_qs_count}</p>
                        <span className="text-xs text-red-400/60">wymagają uwagi</span>
                    </div>
                </div>
                <div className="glass p-5 rounded-xl border-l-4 border-l-green-500">
                    <p className="text-sm text-surface-200/60 font-medium">Słowa z wysokim QS (8-10)</p>
                    <div className="flex items-baseline gap-2 mt-1">
                        <p className="text-3xl font-bold text-green-400">
                            {chartData.filter(d => parseInt(d.score) >= 8).reduce((acc, curr) => acc + curr.count, 0)}
                        </p>
                        <span className="text-xs text-green-400/60">świetna robota!</span>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Chart Section */}
                <div className="lg:col-span-1 glass p-6 rounded-xl">
                    <h3 className="text-lg font-semibold text-white mb-6">Rozkład Wyniku Jakości</h3>
                    <div className="h-64 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={chartData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.5} vertical={false} />
                                <XAxis
                                    dataKey="score"
                                    stroke="#9ca3af"
                                    tick={{ fill: '#9ca3af', fontSize: 12 }}
                                    axisLine={false}
                                    tickLine={false}
                                />
                                <YAxis
                                    stroke="#9ca3af"
                                    tick={{ fill: '#9ca3af', fontSize: 12 }}
                                    axisLine={false}
                                    tickLine={false}
                                    allowDecimals={false}
                                />
                                <Tooltip
                                    cursor={{ fill: '#374151', opacity: 0.2 }}
                                    contentStyle={{
                                        backgroundColor: '#1f2937',
                                        borderColor: '#374151',
                                        borderRadius: '8px',
                                        color: '#f3f4f6'
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
                    <div className="mt-4 flex justify-between text-xs text-surface-200/40 px-2">
                        <span>Niski (1-4)</span>
                        <span>Średni (5-7)</span>
                        <span>Wysoki (8-10)</span>
                    </div>
                </div>

                {/* Issues Table */}
                <div className="lg:col-span-2 glass rounded-xl overflow-hidden">
                    <div className="p-6 border-b border-surface-700/40">
                        <h3 className="text-lg font-semibold text-white">Słowa wymagające optymalizacji</h3>
                        <p className="text-sm text-surface-200/60 mt-1">
                            Te słowa mają wynik jakości poniżej {data.qs_threshold}. Popraw je, aby obniżyć CPC.
                        </p>
                    </div>

                    {data.low_qs_keywords.length === 0 ? (
                        <div className="p-12 text-center">
                            <CheckCircle className="mx-auto h-12 w-12 text-green-500/50 mb-3" />
                            <h3 className="text-lg font-medium text-white">Brak problemów z Quality Score!</h3>
                            <p className="text-surface-200/60 mt-1">Wszystkie aktywne słowa kluczowe mają wynik {data.qs_threshold} lub wyższy.</p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead className="bg-surface-800/50">
                                    <tr>
                                        <th className="text-left py-3 px-4 font-medium text-surface-200/40 uppercase text-xs">Słowo kluczowe</th>
                                        <th className="text-center py-3 px-4 font-medium text-surface-200/40 uppercase text-xs">QS</th>
                                        <th className="text-left py-3 px-4 font-medium text-surface-200/40 uppercase text-xs">Diagnostyka</th>
                                        <th className="text-left py-3 px-4 font-medium text-surface-200/40 uppercase text-xs">Rekomendacja</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-surface-700/20">
                                    {data.low_qs_keywords.map((item, i) => (
                                        <tr key={i} className="hover:bg-surface-700/20 transition-colors">
                                            <td className="py-4 px-4">
                                                <div className="font-medium text-white">{item.keyword}</div>
                                                <div className="text-xs text-surface-200/50 mt-0.5">{item.campaign}</div>
                                            </td>
                                            <td className="py-4 px-4 text-center">
                                                <span className={`inline-flex items-center justify-center w-8 h-8 rounded-lg font-bold ${item.quality_score <= 3 ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'
                                                    }`}>
                                                    {item.quality_score}
                                                </span>
                                            </td>
                                            <td className="py-4 px-4">
                                                {item.issues.length > 0 ? (
                                                    <div className="space-y-1">
                                                        {item.issues.map((issue, idx) => (
                                                            <div key={idx} className="flex items-start gap-1.5 text-xs text-red-300/80">
                                                                <AlertTriangle size={12} className="mt-0.5 shrink-0" />
                                                                <span>{issue}</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <span className="text-xs text-surface-200/30 italic">Brak wyraźnych problemów</span>
                                                )}
                                            </td>
                                            <td className="py-4 px-4">
                                                <div className="flex items-start gap-2 text-xs text-surface-200/70 bg-surface-700/30 p-2 rounded border border-surface-700/50">
                                                    <ArrowRight size={12} className="mt-0.5 text-brand-400 shrink-0" />
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

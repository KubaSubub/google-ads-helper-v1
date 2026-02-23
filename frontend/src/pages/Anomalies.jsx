import { useState, useEffect } from 'react'
import { LoadingSpinner, ErrorMessage, PageHeader, Badge } from '../components/UI'
import { getAnomaliesDetection as getAnomalies } from '../api'
import { useApp } from '../contexts/AppContext'
import EmptyState from '../components/EmptyState'
import { AlertTriangle, TrendingUp, TrendingDown } from 'lucide-react'

const METRICS = [
    { value: 'cost', label: 'Koszt' },
    { value: 'clicks', label: 'Kliknięcia' },
    { value: 'impressions', label: 'Wyświetlenia' },
    { value: 'conversions', label: 'Konwersje' },
    { value: 'ctr', label: 'CTR' },
]

export default function Anomalies() {
    const { selectedClientId } = useApp()
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [metric, setMetric] = useState('cost')
    const [threshold, setThreshold] = useState(2.0)
    const [days, setDays] = useState(90)

    useEffect(() => {
        if (selectedClientId) loadData()
    }, [metric, threshold, days, selectedClientId])

    async function loadData() {
        setLoading(true)
        setError(null)
        try {
            const result = await getAnomalies({ metric, threshold, days, client_id: selectedClientId })
            setData(result)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    if (!selectedClientId) return <EmptyState message="Wybierz klienta w sidebarze" />

    return (
        <div className="max-w-[1200px] mx-auto">
            <PageHeader
                title="Wykrywanie anomalii"
                subtitle="Automatyczne wykrywanie nietypowych zmian w metrykach (z-score)"
            />

            {/* Controls */}
            <div className="glass rounded-xl p-4 mb-6 flex flex-wrap gap-4 items-center animate-fade-in">
                <div>
                    <label className="block text-[10px] text-surface-200/40 uppercase tracking-wider mb-1">Metryka</label>
                    <div className="flex gap-1.5">
                        {METRICS.map(m => (
                            <button
                                key={m.value}
                                onClick={() => setMetric(m.value)}
                                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${metric === m.value
                                        ? 'bg-brand-600 text-white'
                                        : 'bg-surface-700/40 text-surface-200/50 hover:text-surface-200'
                                    }`}
                            >
                                {m.label}
                            </button>
                        ))}
                    </div>
                </div>

                <div>
                    <label className="block text-[10px] text-surface-200/40 uppercase tracking-wider mb-1">Próg (z-score)</label>
                    <div className="flex gap-1.5">
                        {[1.5, 2.0, 2.5, 3.0].map(t => (
                            <button
                                key={t}
                                onClick={() => setThreshold(t)}
                                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${threshold === t
                                        ? 'bg-brand-600 text-white'
                                        : 'bg-surface-700/40 text-surface-200/50 hover:text-surface-200'
                                    }`}
                            >
                                {t}σ
                            </button>
                        ))}
                    </div>
                </div>

                <div>
                    <label className="block text-[10px] text-surface-200/40 uppercase tracking-wider mb-1">Okres</label>
                    <div className="flex gap-1.5">
                        {[30, 60, 90].map(d => (
                            <button
                                key={d}
                                onClick={() => setDays(d)}
                                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${days === d
                                        ? 'bg-brand-600 text-white'
                                        : 'bg-surface-700/40 text-surface-200/50 hover:text-surface-200'
                                    }`}
                            >
                                {d}d
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {loading ? (
                <LoadingSpinner />
            ) : error ? (
                <ErrorMessage message={error} onRetry={loadData} />
            ) : (
                <>
                    {/* Stats */}
                    <div className="grid grid-cols-3 gap-4 mb-6 stagger-children">
                        <div className="glass rounded-xl p-4 text-center">
                            <span className="block text-2xl font-bold text-white">{data?.anomalies?.length || 0}</span>
                            <span className="text-xs text-surface-200/40">Anomalie</span>
                        </div>
                        <div className="glass rounded-xl p-4 text-center">
                            <span className="block text-2xl font-bold text-white font-mono">{data?.mean?.toFixed(1)}</span>
                            <span className="text-xs text-surface-200/40">Średnia</span>
                        </div>
                        <div className="glass rounded-xl p-4 text-center">
                            <span className="block text-2xl font-bold text-white font-mono">±{data?.std?.toFixed(1)}</span>
                            <span className="text-xs text-surface-200/40">Odch. std.</span>
                        </div>
                    </div>

                    {/* Anomaly list */}
                    {data?.anomalies?.length > 0 ? (
                        <div className="glass rounded-xl overflow-hidden animate-fade-in">
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b border-surface-700/40">
                                            <th className="text-left py-3 px-4 text-xs font-medium text-surface-200/40 uppercase tracking-wider">Data</th>
                                            <th className="text-left py-3 px-4 text-xs font-medium text-surface-200/40 uppercase tracking-wider">Kampania</th>
                                            <th className="text-right py-3 px-4 text-xs font-medium text-surface-200/40 uppercase tracking-wider">Wartość</th>
                                            <th className="text-right py-3 px-4 text-xs font-medium text-surface-200/40 uppercase tracking-wider">Z-score</th>
                                            <th className="text-left py-3 px-4 text-xs font-medium text-surface-200/40 uppercase tracking-wider">Typ</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-surface-700/20">
                                        {data.anomalies.map((a, i) => (
                                            <tr key={i} className="hover:bg-surface-700/20 transition-colors">
                                                <td className="py-3 px-4 font-mono text-surface-200/80">{a.date}</td>
                                                <td className="py-3 px-4 text-surface-200/60">ID: {a.campaign_id}</td>
                                                <td className="py-3 px-4 text-right font-mono text-white font-medium">{a.value}</td>
                                                <td className="py-3 px-4 text-right">
                                                    <span className={`font-mono font-medium ${a.z_score > 3 ? 'text-red-400' : 'text-yellow-400'}`}>
                                                        {a.z_score.toFixed(2)}σ
                                                    </span>
                                                </td>
                                                <td className="py-3 px-4">
                                                    <span className={`inline-flex items-center gap-1 text-xs font-medium ${a.direction === 'spike' ? 'text-red-400' : 'text-blue-400'
                                                        }`}>
                                                        {a.direction === 'spike' ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                                                        {a.direction === 'spike' ? 'Skok' : 'Spadek'}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ) : (
                        <div className="glass rounded-xl p-12 text-center animate-fade-in">
                            <AlertTriangle size={32} className="text-surface-200/20 mx-auto mb-3" />
                            <p className="text-surface-200/50 text-sm">Brak anomalii przy progu {threshold}σ</p>
                            <p className="text-surface-200/30 text-xs mt-1">Spróbuj obniżyć próg lub zwiększyć okres</p>
                        </div>
                    )}
                </>
            )}
        </div>
    )
}

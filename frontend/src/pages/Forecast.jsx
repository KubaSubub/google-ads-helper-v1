import { useState, useEffect } from 'react'
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceArea
} from 'recharts'
import { TrendingUp, TrendingDown, Activity, AlertCircle, Calendar } from 'lucide-react'
import { LoadingSpinner, ErrorMessage, PageHeader } from '../components/UI'
import { getForecast, getCampaigns } from '../api'
import { useApp } from '../contexts/AppContext'

export default function Forecast() {
    const { selectedClientId } = useApp()
    const [campaigns, setCampaigns] = useState([])
    const [selectedCampaign, setSelectedCampaign] = useState(null)
    const [metric, setMetric] = useState('cost')
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (selectedClientId) loadCampaigns()
    }, [selectedClientId])

    useEffect(() => {
        if (selectedCampaign) {
            loadForecast()
        }
    }, [selectedCampaign, metric])

    async function loadCampaigns() {
        try {
            const res = await getCampaigns(selectedClientId)
            setCampaigns(res.items)
            if (res.items.length > 0) {
                setSelectedCampaign(res.items[0].id)
            }
        } catch (err) {
            console.error("Failed to load campaigns", err)
        }
    }

    async function loadForecast() {
        setLoading(true)
        setError(null)
        try {
            const res = await getForecast(selectedCampaign, metric, 7)
            setData(res)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    if (!selectedCampaign) return <LoadingSpinner />

    // Combine historical and forecast data for chart
    const chartData = data ? [
        ...data.historical.map(d => ({ date: d.date, historical: d.value, predicted: null })),
        ...data.forecast.map(d => ({ date: d.date, historical: null, predicted: d.predicted }))
    ] : []

    return (
        <div className="max-w-[1400px] mx-auto space-y-6">
            <PageHeader
                title="Prognozowanie"
                subtitle="Predykcja wyników na najbliższe 7 dni (model liniowy)"
            >
                <div className="flex gap-4">
                    <select
                        value={selectedCampaign}
                        onChange={e => setSelectedCampaign(Number(e.target.value))}
                        className="bg-surface-700/40 border border-surface-700/60 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-brand-500"
                    >
                        {campaigns.map(c => (
                            <option key={c.id} value={c.id}>{c.name}</option>
                        ))}
                    </select>

                    <select
                        value={metric}
                        onChange={e => setMetric(e.target.value)}
                        className="bg-surface-700/40 border border-surface-700/60 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-brand-500"
                    >
                        <option value="cost">Koszt</option>
                        <option value="clicks">Kliknięcia</option>
                        <option value="conversions">Konwersje</option>
                        <option value="ctr">CTR</option>
                    </select>
                </div>
            </PageHeader>

            {loading && <LoadingSpinner />}
            {error && <ErrorMessage message={error} onRetry={loadForecast} />}

            {data && !loading && (
                <>
                    {/* KPI Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div className="glass p-5 rounded-xl">
                            <div className="flex items-center gap-2 text-surface-200/60 mb-1">
                                <Activity size={16} />
                                <span className="text-xs font-medium uppercase">Trend (7 dni)</span>
                            </div>
                            <div className="flex items-center gap-2">
                                {data.trend.direction === 'up' && <TrendingUp className="text-green-400" />}
                                {data.trend.direction === 'down' && <TrendingDown className="text-red-400" />}
                                {data.trend.direction === 'stable' && <Activity className="text-blue-400" />}
                                <span className={`text-2xl font-bold ${data.trend.direction === 'up' ? 'text-green-400' :
                                        data.trend.direction === 'down' ? 'text-red-400' : 'text-blue-400'
                                    }`}>
                                    {data.trend.change_pct > 0 ? '+' : ''}{data.trend.change_pct}%
                                </span>
                            </div>
                            <p className="text-xs text-surface-200/40 mt-1">vs ostatnie 7 dni</p>
                        </div>

                        <div className="glass p-5 rounded-xl">
                            <div className="flex items-center gap-2 text-surface-200/60 mb-1">
                                <Calendar size={16} />
                                <span className="text-xs font-medium uppercase">Prognoza (Średnia)</span>
                            </div>
                            <p className="text-2xl font-bold text-white">{data.trend.forecast_avg.toFixed(2)}</p>
                            <p className="text-xs text-surface-200/40 mt-1">przewidywana dzienna wartość</p>
                        </div>

                        <div className="glass p-5 rounded-xl">
                            <div className="flex items-center gap-2 text-surface-200/60 mb-1">
                                <AlertCircle size={16} />
                                <span className="text-xs font-medium uppercase">Pewność modelu (R²)</span>
                            </div>
                            <p className="text-2xl font-bold text-white">{data.model.r_squared.toFixed(2)}</p>
                            <span className={`text-xs px-2 py-0.5 rounded ${data.model.confidence === 'high' ? 'bg-green-500/20 text-green-400' :
                                    data.model.confidence === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                                        'bg-red-500/20 text-red-400'
                                }`}>
                                {data.model.confidence.toUpperCase()}
                            </span>
                        </div>

                        <div className="glass p-5 rounded-xl">
                            <div className="flex items-center gap-2 text-surface-200/60 mb-1">
                                <Activity size={16} />
                                <span className="text-xs font-medium uppercase">Slope (Wzrost/Dzień)</span>
                            </div>
                            <p className="text-2xl font-bold text-white">{data.model.slope_per_day.toFixed(2)}</p>
                            <p className="text-xs text-surface-200/40 mt-1">jednostek dziennie</p>
                        </div>
                    </div>

                    {/* Chart */}
                    <div className="glass p-6 rounded-xl h-96">
                        <h3 className="text-lg font-semibold text-white mb-4">Wykres Historyczny + Prognoza</h3>
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                                <XAxis
                                    dataKey="date"
                                    stroke="#9ca3af"
                                    tick={{ fill: '#9ca3af', fontSize: 10 }}
                                    tickFormatter={d => d.slice(5)} // Show MM-DD
                                />
                                <YAxis
                                    stroke="#9ca3af"
                                    tick={{ fill: '#9ca3af', fontSize: 10 }}
                                />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#f3f4f6' }}
                                    itemStyle={{ color: '#f3f4f6' }}
                                />
                                {/* Historical Line */}
                                <Line
                                    type="monotone"
                                    dataKey="historical"
                                    stroke="#3b82f6"
                                    strokeWidth={2}
                                    dot={false}
                                    activeDot={{ r: 6 }}
                                    name="Dane historyczne"
                                />
                                {/* Forecast Line (Dashed) */}
                                <Line
                                    type="monotone"
                                    dataKey="predicted"
                                    stroke="#22c55e"
                                    strokeWidth={2}
                                    strokeDasharray="5 5"
                                    dot={{ r: 3 }}
                                    name="Prognoza"
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </>
            )}
        </div>
    )
}

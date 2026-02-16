import { useState, useEffect } from 'react'
import {
    MousePointerClick,
    Eye,
    DollarSign,
    Target,
    TrendingUp,
    BarChart3,
} from 'lucide-react'
import KPICard from '../components/KPICard'
import { MetricsAreaChart, CampaignBarChart } from '../components/Charts'
import { LoadingSpinner, ErrorMessage, PageHeader } from '../components/UI'
import { getDashboardKPIs, getCampaigns, getCampaignMetrics } from '../api'

export default function Dashboard() {
    const [kpis, setKpis] = useState(null)
    const [campaigns, setCampaigns] = useState([])
    const [chartData, setChartData] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [days, setDays] = useState(30)

    const clientId = 1 // Demo client

    useEffect(() => {
        loadData()
    }, [days])

    async function loadData() {
        setLoading(true)
        setError(null)
        try {
            const [kpiData, campData] = await Promise.all([
                getDashboardKPIs(clientId, days),
                getCampaigns(clientId),
            ])
            setKpis(kpiData)
            setCampaigns(campData.items || [])

            // Load metrics for the first active campaign for the chart
            const activeCampaigns = (campData.items || []).filter(c => c.status === 'ENABLED')
            if (activeCampaigns.length > 0) {
                const metrics = await getCampaignMetrics(activeCampaigns[0].id)
                setChartData(
                    metrics.map(m => ({
                        date: m.date.slice(5), // MM-DD
                        cost: m.cost,
                        clicks: m.clicks,
                        conversions: m.conversions,
                        ctr: m.ctr,
                    }))
                )
            }
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    if (loading) return <LoadingSpinner />
    if (error) return <ErrorMessage message={error} onRetry={loadData} />

    const { current, change_pct } = kpis || {}

    // Campaign summary for bar chart
    const campaignChartData = campaigns
        .filter(c => c.status === 'ENABLED')
        .map(c => ({
            name: c.name.length > 18 ? c.name.slice(0, 18) + '…' : c.name,
            cost: c.budget_amount * days, // approximate
            clicks: Math.round(c.budget_amount * 10), // approximate from budget
        }))

    return (
        <div className="max-w-[1400px] mx-auto">
            <PageHeader
                title="Dashboard"
                subtitle={`Demo Meble Sp. z o.o. • Ostatnie ${days} dni`}
            >
                <div className="flex gap-2">
                    {[7, 14, 30, 90].map(d => (
                        <button
                            key={d}
                            onClick={() => setDays(d)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${days === d
                                    ? 'bg-brand-600 text-white'
                                    : 'bg-surface-700/40 text-surface-200/50 hover:text-surface-200 hover:bg-surface-700/60'
                                }`}
                        >
                            {d}d
                        </button>
                    ))}
                </div>
            </PageHeader>

            {/* KPI Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8 stagger-children">
                <KPICard
                    title="Kliknięcia"
                    value={current?.clicks}
                    change={change_pct?.clicks}
                    icon={MousePointerClick}
                />
                <KPICard
                    title="Wyświetlenia"
                    value={current?.impressions}
                    change={change_pct?.impressions}
                    icon={Eye}
                />
                <KPICard
                    title="Koszt"
                    value={current?.cost}
                    change={change_pct?.cost}
                    suffix=" zł"
                    icon={DollarSign}
                />
                <KPICard
                    title="Konwersje"
                    value={current?.conversions}
                    change={change_pct?.conversions}
                    icon={Target}
                />
                <KPICard
                    title="CTR"
                    value={current?.ctr}
                    change={change_pct?.ctr}
                    suffix="%"
                    icon={TrendingUp}
                />
                <KPICard
                    title="ROAS"
                    value={current?.roas}
                    change={change_pct?.roas}
                    icon={BarChart3}
                />
            </div>

            {/* Charts Row */}
            <div className="grid lg:grid-cols-2 gap-6 mb-8">
                <MetricsAreaChart
                    data={chartData}
                    dataKey="cost"
                    title="Koszt kampanii (dziennie)"
                    color="#6366f1"
                />
                <MetricsAreaChart
                    data={chartData}
                    dataKey="clicks"
                    title="Kliknięcia (dziennie)"
                    color="#22d3ee"
                />
            </div>

            {/* Campaigns Table */}
            <div className="glass rounded-xl p-5 animate-fade-in">
                <h3 className="text-sm font-semibold text-surface-200/70 mb-4">Kampanie</h3>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-surface-700/40">
                                <th className="text-left py-3 px-3 text-xs font-medium text-surface-200/40 uppercase tracking-wider">Nazwa</th>
                                <th className="text-left py-3 px-3 text-xs font-medium text-surface-200/40 uppercase tracking-wider">Status</th>
                                <th className="text-left py-3 px-3 text-xs font-medium text-surface-200/40 uppercase tracking-wider">Typ</th>
                                <th className="text-right py-3 px-3 text-xs font-medium text-surface-200/40 uppercase tracking-wider">Budżet/dzień</th>
                                <th className="text-left py-3 px-3 text-xs font-medium text-surface-200/40 uppercase tracking-wider">Strategia</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-surface-700/20">
                            {campaigns.map(c => (
                                <tr key={c.id} className="hover:bg-surface-700/20 transition-colors cursor-pointer">
                                    <td className="py-3 px-3 font-medium text-white">{c.name}</td>
                                    <td className="py-3 px-3">
                                        <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${c.status === 'ENABLED' ? 'text-green-400' : c.status === 'PAUSED' ? 'text-yellow-400' : 'text-red-400'
                                            }`}>
                                            <span className={`w-1.5 h-1.5 rounded-full ${c.status === 'ENABLED' ? 'bg-green-400' : c.status === 'PAUSED' ? 'bg-yellow-400' : 'bg-red-400'
                                                }`} />
                                            {c.status === 'ENABLED' ? 'Aktywna' : c.status === 'PAUSED' ? 'Wstrzymana' : c.status}
                                        </span>
                                    </td>
                                    <td className="py-3 px-3 text-surface-200/60">{c.campaign_type}</td>
                                    <td className="py-3 px-3 text-right font-mono text-surface-200/80">{c.budget_amount?.toFixed(0)} zł</td>
                                    <td className="py-3 px-3 text-surface-200/60 text-xs">{c.bidding_strategy}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    )
}

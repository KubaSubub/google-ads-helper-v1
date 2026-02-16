import { useState, useEffect } from 'react'
import { MetricsAreaChart } from '../components/Charts'
import { LoadingSpinner, ErrorMessage, PageHeader, StatusBadge } from '../components/UI'
import KPICard from '../components/KPICard'
import { getCampaigns, getCampaignKPIs, getCampaignMetrics } from '../api'
import { MousePointerClick, DollarSign, Target, TrendingUp } from 'lucide-react'

export default function Campaigns() {
    const [campaigns, setCampaigns] = useState([])
    const [selected, setSelected] = useState(null)
    const [kpis, setKpis] = useState(null)
    const [metrics, setMetrics] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        loadCampaigns()
    }, [])

    async function loadCampaigns() {
        setLoading(true)
        try {
            const data = await getCampaigns(1)
            setCampaigns(data.items || [])
            if (data.items?.length > 0) {
                selectCampaign(data.items[0])
            }
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    async function selectCampaign(campaign) {
        setSelected(campaign)
        try {
            const [kpiData, metricData] = await Promise.all([
                getCampaignKPIs(campaign.id),
                getCampaignMetrics(campaign.id),
            ])
            setKpis(kpiData)
            setMetrics(
                metricData.map(m => ({
                    date: m.date.slice(5),
                    cost: m.cost,
                    clicks: m.clicks,
                    conversions: m.conversions,
                }))
            )
        } catch (err) {
            console.error('Failed to load campaign details:', err)
        }
    }

    if (loading) return <LoadingSpinner />
    if (error) return <ErrorMessage message={error} onRetry={loadCampaigns} />

    return (
        <div className="max-w-[1400px] mx-auto">
            <PageHeader title="Kampanie" subtitle={`${campaigns.length} kampanii`} />

            <div className="grid lg:grid-cols-3 gap-6">
                {/* Campaign List */}
                <div className="lg:col-span-1 glass rounded-xl p-4 max-h-[calc(100vh-160px)] overflow-y-auto">
                    <div className="space-y-2">
                        {campaigns.map(c => (
                            <button
                                key={c.id}
                                onClick={() => selectCampaign(c)}
                                className={`w-full text-left px-4 py-3 rounded-lg transition-all ${selected?.id === c.id
                                        ? 'bg-brand-600/20 border border-brand-500/30'
                                        : 'hover:bg-surface-700/40 border border-transparent'
                                    }`}
                            >
                                <div className="flex items-center justify-between mb-1">
                                    <span className="text-sm font-medium text-white truncate">{c.name}</span>
                                    <StatusBadge status={c.status} />
                                </div>
                                <div className="flex items-center gap-3 text-xs text-surface-200/40">
                                    <span>{c.campaign_type}</span>
                                    <span>•</span>
                                    <span>{c.budget_amount?.toFixed(0)} zł/dzień</span>
                                </div>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Campaign Detail */}
                <div className="lg:col-span-2 space-y-6">
                    {selected && kpis && (
                        <>
                            <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 stagger-children">
                                <KPICard
                                    title="Kliknięcia"
                                    value={kpis.current.clicks}
                                    change={kpis.change_pct.clicks}
                                    icon={MousePointerClick}
                                />
                                <KPICard
                                    title="Koszt"
                                    value={kpis.current.cost}
                                    change={kpis.change_pct.cost}
                                    suffix=" zł"
                                    icon={DollarSign}
                                />
                                <KPICard
                                    title="Konwersje"
                                    value={kpis.current.conversions}
                                    change={kpis.change_pct.conversions}
                                    icon={Target}
                                />
                                <KPICard
                                    title="CTR"
                                    value={kpis.current.ctr}
                                    change={kpis.change_pct.ctr}
                                    suffix="%"
                                    icon={TrendingUp}
                                />
                            </div>

                            <MetricsAreaChart
                                data={metrics}
                                dataKey="cost"
                                title={`${selected.name} — Koszt dzienny`}
                                color="#6366f1"
                            />
                            <MetricsAreaChart
                                data={metrics}
                                dataKey="clicks"
                                title={`${selected.name} — Kliknięcia`}
                                color="#22d3ee"
                            />
                        </>
                    )}
                </div>
            </div>
        </div>
    )
}

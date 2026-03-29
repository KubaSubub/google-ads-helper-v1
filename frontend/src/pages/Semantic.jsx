import { useState, useEffect } from 'react'
import { LoadingSpinner, ErrorMessage, PageHeader, Badge } from '../components/UI'
import { getSemanticClusters, addNegativeKeyword } from '../api'
import { useApp } from '../contexts/AppContext'
import { useFilter } from '../contexts/FilterContext'
import { Brain, ChevronDown, ChevronUp, AlertCircle, TrendingUp, MousePointer2, DollarSign, Layers, Search, Ban, Loader2, CheckSquare, Square, X } from 'lucide-react'
import clsx from 'clsx'

export default function Semantic() {
    const { selectedClientId, showToast } = useApp()
    const { days } = useFilter()
    const [clusters, setClusters] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [expandedId, setExpandedId] = useState(null)
    const [minCost, setMinCost] = useState(0)
    const [searchTerm, setSearchTerm] = useState('')
    const [addingNegatives, setAddingNegatives] = useState(null)
    const [selectedWaste, setSelectedWaste] = useState(new Set())
    const [bulkExcluding, setBulkExcluding] = useState(false)

    function toggleWasteSelect(clusterId, e) {
        e.stopPropagation()
        setSelectedWaste(prev => {
            const next = new Set(prev)
            if (next.has(clusterId)) next.delete(clusterId)
            else next.add(clusterId)
            return next
        })
    }

    async function handleBulkExcludeSelected() {
        const wasteClusters = clusters.filter(c => selectedWaste.has(c.id))
        const allItems = wasteClusters.flatMap(c => c.items)
        if (allItems.length === 0) return
        setBulkExcluding(true)
        let added = 0
        let failed = 0
        for (const item of allItems) {
            try {
                await addNegativeKeyword({
                    client_id: selectedClientId,
                    text: item.text,
                    match_type: 'EXACT',
                    scope: 'CAMPAIGN',
                })
                added++
            } catch { failed++ }
        }
        setBulkExcluding(false)
        setSelectedWaste(new Set())
        if (failed > 0) {
            showToast(`Dodano ${added} negatywów, ${failed} błędów`, 'error')
        } else {
            showToast(`Dodano ${added} negatywów z ${wasteClusters.length} klastrów`, 'success')
        }
    }

    async function handleBulkNegative(cluster) {
        if (!confirm(`Dodać ${cluster.items.length} fraz z klastra "${cluster.name}" jako negatywy EXACT?`)) return
        setAddingNegatives(cluster.id)
        let added = 0
        let failed = 0
        for (const item of cluster.items) {
            try {
                await addNegativeKeyword({
                    client_id: selectedClientId,
                    text: item.text,
                    match_type: 'EXACT',
                    scope: 'CAMPAIGN',
                })
                added++
            } catch { failed++ }
        }
        setAddingNegatives(null)
        if (failed > 0) {
            showToast(`Dodano ${added} negatywów, ${failed} błędów`, 'error')
        } else {
            showToast(`Dodano ${added} negatywów z klastra "${cluster.name}"`, 'success')
        }
    }

    useEffect(() => {
        if (selectedClientId) loadData()
    }, [selectedClientId, days])

    async function loadData() {
        setLoading(true)
        try {
            const data = await getSemanticClusters({ client_id: selectedClientId, days, top_n: 500 })
            setClusters(data)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    const toggleExpand = (id) => {
        setExpandedId(expandedId === id ? null : id)
    }

    if (loading) return (
        <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
            <LoadingSpinner />
            <p className="text-surface-200/50 text-sm animate-pulse">Analizowanie semantyczne wyrażeń...</p>
            <p className="text-surface-200/30 text-xs">(Pierwsze uruchomienie może potrwać chwilę)</p>
        </div>
    )

    if (error) return <ErrorMessage message={error} onRetry={loadData} />

    const totalTerms = clusters.reduce((acc, c) => acc + c.metrics.term_count, 0)
    const totalCost = clusters.reduce((acc, c) => acc + c.metrics.cost, 0)

    return (
        <div className="max-w-[1200px] mx-auto pb-12">
            <PageHeader
                title="Klastry Semantyczne"
                subtitle={`Zgrupowano ${totalTerms} wyrażeń w ${clusters.length} klastrów tematycznych`}
            >
                <div className="flex items-center gap-2 bg-surface-700/40 p-1 rounded-lg">
                    <span className="text-xs text-surface-200/50 px-2">Filtr kosztu:</span>
                    {[0, 10, 50, 100].map(v => (
                        <button
                            key={v}
                            onClick={() => setMinCost(v)}
                            className={clsx(
                                "px-3 py-1 rounded text-xs font-medium transition-all",
                                minCost === v ? "bg-brand-600 text-white" : "hover:bg-surface-600/50 text-surface-200/70"
                            )}
                        >
                            {v === 0 ? 'Wszystkie' : `> ${v} zł`}
                        </button>
                    ))}
                </div>

                <div className="flex items-center gap-2 bg-surface-700/40 p-1 rounded-lg">
                    <Search size={14} className="text-surface-200/40 ml-2" />
                    <input
                        type="text"
                        placeholder="Szukaj w klastrach..."
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                        className="bg-transparent border-none text-xs text-white placeholder-surface-200/40 outline-none w-40"
                    />
                </div>
            </PageHeader>

            <div className="grid gap-4">
                {clusters
                    .filter(c => c.metrics.cost >= minCost)
                    .filter(c => !searchTerm || c.name.toLowerCase().includes(searchTerm.toLowerCase()) || c.items.some(item => item.text.toLowerCase().includes(searchTerm.toLowerCase())))
                    .map((cluster) => (
                        <div
                            key={cluster.id}
                            className={clsx(
                                "group glass rounded-xl overflow-hidden transition-all duration-300 border border-surface-700/40",
                                expandedId === cluster.id ? "ring-1 ring-brand-500/30" : "hover:bg-surface-700/10"
                            )}
                        >
                            {/* Header */}
                            <div
                                onClick={() => toggleExpand(cluster.id)}
                                className="p-5 flex items-center justify-between cursor-pointer select-none"
                            >
                                <div className="flex items-center gap-4">
                                    {cluster.is_waste && (
                                        <button
                                            onClick={(e) => toggleWasteSelect(cluster.id, e)}
                                            className="flex-shrink-0 text-surface-200/50 hover:text-red-400 transition-colors"
                                            title={selectedWaste.has(cluster.id) ? 'Odznacz klaster' : 'Zaznacz klaster do wykluczenia'}
                                        >
                                            {selectedWaste.has(cluster.id)
                                                ? <CheckSquare size={18} className="text-red-400" />
                                                : <Square size={18} />
                                            }
                                        </button>
                                    )}
                                    <div className={clsx(
                                        "w-10 h-10 rounded-lg flex items-center justify-center transition-colors",
                                        cluster.is_waste ? "bg-red-500/10 text-red-400" : "bg-brand-500/10 text-brand-400"
                                    )}>
                                        {cluster.is_waste ? <AlertCircle size={20} /> : <Layers size={20} />}
                                    </div>
                                    <div>
                                        <h3 className="text-base font-semibold text-white group-hover:text-brand-300 transition-colors">
                                            {cluster.name}
                                        </h3>
                                        <div className="flex items-center gap-3 text-xs text-surface-200/50 mt-1">
                                            <span>{cluster.metrics.term_count} wyrażeń</span>
                                            <span>•</span>
                                            <span className="flex items-center gap-1">
                                                <MousePointer2 size={10} />
                                                {cluster.metrics.clicks}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-6">
                                    {cluster.is_waste && (
                                        <>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); handleBulkNegative(cluster) }}
                                                disabled={addingNegatives === cluster.id}
                                                className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium transition-all bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20"
                                                style={{ cursor: addingNegatives === cluster.id ? 'wait' : 'pointer', opacity: addingNegatives === cluster.id ? 0.5 : 1 }}
                                            >
                                                {addingNegatives === cluster.id ? <Loader2 size={12} className="animate-spin" /> : <Ban size={12} />}
                                                Dodaj jako negatywy
                                            </button>
                                            <Badge variant="danger" className="hidden sm:flex">Potencjalna strata</Badge>
                                        </>
                                    )}

                                    <div className="text-right">
                                        <div className="text-sm font-mono text-white font-medium">
                                            {cluster.metrics.cost.toFixed(2)} zł
                                        </div>
                                        <div className="text-[10px] text-surface-200/40 uppercase tracking-wider">Koszt</div>
                                    </div>

                                    <div className="text-right w-20">
                                        <div className={clsx(
                                            "text-sm font-mono font-medium",
                                            cluster.metrics.conversions > 0 ? "text-green-400" : "text-surface-200/30"
                                        )}>
                                            {cluster.metrics.conversions.toFixed(1)}
                                        </div>
                                        <div className="text-[10px] text-surface-200/40 uppercase tracking-wider">Conv.</div>
                                    </div>

                                    {expandedId === cluster.id ? <ChevronUp size={20} className="text-surface-200/40" /> : <ChevronDown size={20} className="text-surface-200/40" />}
                                </div>
                            </div>

                            {/* Details */}
                            {expandedId === cluster.id && (
                                <div className="border-t border-surface-700/40 bg-surface-800/20 p-5 animate-fade-in-down">
                                    <div className="flex flex-wrap gap-2">
                                        {cluster.items.map((item, idx) => (
                                            <div
                                                key={idx}
                                                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-700/40 border border-surface-700/60 text-xs text-surface-200 hover:border-brand-500/30 transition-colors cursor-default"
                                                title={`Koszt: ${item.cost.toFixed(2)} zł | Kliknięcia: ${item.clicks}`}
                                            >
                                                {item.text}
                                                {item.cost > 0 && <span className="text-surface-200/40 ml-1">| {item.cost.toFixed(0)}zł</span>}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}

                {clusters.length === 0 && !loading && (
                    <div className="text-center py-20 text-surface-200/40">
                        Brak danych do analizy.
                    </div>
                )}
            </div>

            {/* Floating action bar for selected waste clusters */}
            {selectedWaste.size > 0 && (
                <div
                    className="sticky bottom-0 left-0 right-0 z-50 mt-4"
                    style={{ marginLeft: '-1rem', marginRight: '-1rem' }}
                >
                    <div className="mx-auto max-w-[1200px] px-4">
                        <div className="flex items-center justify-between gap-4 px-5 py-3 rounded-xl border border-red-500/20 bg-surface-800/95 backdrop-blur-md shadow-lg shadow-black/30">
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center">
                                    <Ban size={16} className="text-red-400" />
                                </div>
                                <div>
                                    <span className="text-sm font-medium text-white">
                                        {selectedWaste.size} {selectedWaste.size === 1 ? 'klaster' : selectedWaste.size < 5 ? 'klastry' : 'klastrów'}
                                    </span>
                                    <span className="text-xs text-surface-200/50 ml-2">
                                        ({clusters.filter(c => selectedWaste.has(c.id)).reduce((sum, c) => sum + c.items.length, 0)} fraz)
                                    </span>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => setSelectedWaste(new Set())}
                                    className="flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-medium transition-all border border-surface-600/50 text-surface-200/70 hover:bg-surface-700/50 hover:text-white"
                                >
                                    <X size={12} />
                                    Odznacz
                                </button>
                                <button
                                    onClick={handleBulkExcludeSelected}
                                    disabled={bulkExcluding}
                                    className="flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-medium transition-all bg-red-500/15 text-red-400 border border-red-500/30 hover:bg-red-500/25 hover:text-red-300"
                                    style={{ cursor: bulkExcluding ? 'wait' : 'pointer', opacity: bulkExcluding ? 0.6 : 1 }}
                                >
                                    {bulkExcluding ? <Loader2 size={12} className="animate-spin" /> : <Ban size={12} />}
                                    Wyklucz wszystkie
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

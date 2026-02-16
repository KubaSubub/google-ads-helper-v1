import { useState, useEffect } from 'react'
import {
    AlertTriangle,
    TrendingUp,
    TrendingDown,
    PauseCircle,
    PlusCircle,
    MinusCircle,
    ArrowRightLeft,
    CheckCircle2,
    XCircle,
    Loader2,
    Filter,
    Zap,
    Play
} from 'lucide-react'
import { LoadingSpinner, ErrorMessage, PageHeader } from '../components/UI'
import { getRecommendations, applyRecommendation } from '../api'

const TYPE_CONFIG = {
    PAUSE_KEYWORD: { icon: PauseCircle, color: 'text-red-400', bg: 'bg-red-500/10', label: 'Pause Keyword' },
    INCREASE_BID: { icon: TrendingUp, color: 'text-green-400', bg: 'bg-green-500/10', label: 'Increase Bid' },
    DECREASE_BID: { icon: TrendingDown, color: 'text-orange-400', bg: 'bg-orange-500/10', label: 'Decrease Bid' },
    ADD_KEYWORD: { icon: PlusCircle, color: 'text-blue-400', bg: 'bg-blue-500/10', label: 'Add Keyword' },
    ADD_NEGATIVE: { icon: MinusCircle, color: 'text-rose-400', bg: 'bg-rose-500/10', label: 'Add Negative' },
    PAUSE_AD: { icon: PauseCircle, color: 'text-yellow-400', bg: 'bg-yellow-500/10', label: 'Pause Ad' },
    REALLOCATE_BUDGET: { icon: ArrowRightLeft, color: 'text-purple-400', bg: 'bg-purple-500/10', label: 'Reallocate Budget' },
}

const PRIORITY_CONFIG = {
    HIGH: { color: 'text-red-400', bg: 'bg-red-500/20', border: 'border-red-500/30', label: '🔴 HIGH' },
    MEDIUM: { color: 'text-yellow-400', bg: 'bg-yellow-500/20', border: 'border-yellow-500/30', label: '🟡 MEDIUM' },
    LOW: { color: 'text-gray-400', bg: 'bg-gray-500/20', border: 'border-gray-500/30', label: '⚪ LOW' },
}

function RecommendationCard({ rec, onApply, isApplying }) {
    const typeConf = TYPE_CONFIG[rec.type] || TYPE_CONFIG.PAUSE_KEYWORD
    const prioConf = PRIORITY_CONFIG[rec.priority] || PRIORITY_CONFIG.LOW
    const Icon = typeConf.icon

    return (
        <div className={`bg-gray-800/50 border ${prioConf.border} rounded-xl p-5 hover:bg-gray-800/70 transition-all group`}>
            <div className="flex items-start gap-4">
                <div className={`p-2.5 rounded-lg ${typeConf.bg} shrink-0`}>
                    <Icon className={`w-5 h-5 ${typeConf.color}`} />
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${prioConf.bg} ${prioConf.color}`}>
                            {prioConf.label}
                        </span>
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${typeConf.bg} ${typeConf.color}`}>
                            {typeConf.label}
                        </span>
                    </div>
                    <h3 className="text-white font-semibold text-sm mt-2 truncate" title={rec.entity_name}>
                        {rec.entity_name}
                    </h3>
                    <p className="text-gray-400 text-xs mt-0.5">
                        Campaign: <span className="text-gray-300">{rec.campaign_name}</span>
                    </p>
                    <p className="text-gray-300 text-sm mt-2">{rec.reason}</p>

                    <div className="mt-3 flex items-center justify-between">
                        <div className="space-y-1">
                            {rec.current_value && (
                                <p className="text-gray-500 text-xs">
                                    Current: <span className="text-gray-400">{rec.current_value}</span>
                                </p>
                            )}
                            {rec.recommended_action && (
                                <p className="text-emerald-400/80 text-xs font-medium">
                                    → {rec.recommended_action}
                                </p>
                            )}
                        </div>

                        <button
                            onClick={() => onApply(rec)}
                            disabled={isApplying}
                            className={`
                                flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
                                ${isApplying
                                    ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                                    : 'bg-brand-600 hover:bg-brand-500 text-white shadow-lg shadow-brand-500/20'}
                            `}
                        >
                            {isApplying ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Applying...
                                </>
                            ) : (
                                <>
                                    <Play className="w-4 h-4 fill-current" />
                                    Apply
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

function SummaryCards({ data }) {
    if (!data) return null
    const { by_priority, by_type, total } = data

    return (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-800/60 rounded-xl p-4 border border-gray-700/50">
                <div className="flex items-center gap-2 mb-1">
                    <Zap className="w-4 h-4 text-yellow-400" />
                    <span className="text-gray-400 text-xs uppercase">Total</span>
                </div>
                <p className="text-2xl font-bold text-white">{total}</p>
            </div>
            <div className="bg-red-500/10 rounded-xl p-4 border border-red-500/20">
                <div className="flex items-center gap-2 mb-1">
                    <AlertTriangle className="w-4 h-4 text-red-400" />
                    <span className="text-red-400/80 text-xs uppercase">High Priority</span>
                </div>
                <p className="text-2xl font-bold text-red-400">{by_priority?.HIGH || 0}</p>
            </div>
            <div className="bg-yellow-500/10 rounded-xl p-4 border border-yellow-500/20">
                <span className="text-yellow-400/80 text-xs uppercase">Medium</span>
                <p className="text-2xl font-bold text-yellow-400">{by_priority?.MEDIUM || 0}</p>
            </div>
            <div className="bg-gray-500/10 rounded-xl p-4 border border-gray-500/20">
                <span className="text-gray-400/80 text-xs uppercase">Low</span>
                <p className="text-2xl font-bold text-gray-400">{by_priority?.LOW || 0}</p>
            </div>
        </div>
    )
}

export default function Recommendations() {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [filterType, setFilterType] = useState('ALL')
    const [filterPriority, setFilterPriority] = useState('ALL')

    // Applying state
    const [applyingId, setApplyingId] = useState(null)
    const [toast, setToast] = useState(null) // { type: 'success'|'error', message: '' }

    useEffect(() => {
        loadData()
    }, [])

    useEffect(() => {
        if (toast) {
            const timer = setTimeout(() => setToast(null), 3000)
            return () => clearTimeout(timer)
        }
    }, [toast])

    async function loadData() {
        try {
            setLoading(true)
            setError(null)
            const result = await getRecommendations(1, 100)
            setData(result)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    async function handleApply(rec) {
        setApplyingId(rec.unique_id) // Assuming we have some unique ID, if not use index or composition
        // Wait, recommendations from backend might not have 'id'. Let's check.
        // The Service constructs them. It puts 'entity_id' but not a recommendation ID.
        // We can use entity_id + type as key.

        try {
            // For MVP: Parse recommended_action or use type logic.
            // The API expects: action, entity_id, params
            // We need to map rec.type to action string

            const params = {}
            if (rec.type === 'INCREASE_BID' || rec.type === 'DECREASE_BID') {
                // Parse amount from recommended_action string which looks like "Increase bid to 1.50"
                const match = rec.recommended_action.match(/([\d.]+)/)
                if (match) params.amount = parseFloat(match[1])
            }
            if (rec.type === 'ADD_KEYWORD') {
                params.text = rec.term // Search term text
                params.ad_group_id = rec.ad_group_id
            }

            // Map type to action
            let actionType = rec.type
            if (rec.type === 'ADD_KEYWORD') actionType = 'ADD_KEYWORD' // Same
            if (rec.type === 'INCREASE_BID' || rec.type === 'DECREASE_BID') actionType = 'SET_KEYWORD_BID'

            // Call API
            const result = await applyRecommendation(actionType, rec.entity_id, params)

            setToast({ type: 'success', message: `Successfully executed: ${rec.recommended_action}` })

            // Remove from list or reload
            loadData()

        } catch (err) {
            setToast({ type: 'error', message: `Failed: ${err.message}` })
        } finally {
            setApplyingId(null)
        }
    }

    if (loading) return <LoadingSpinner />
    if (error) return <ErrorMessage message={error} onRetry={loadData} />

    const recommendations = (data?.recommendations || []).map((r, i) => ({ ...r, unique_id: i }))

    const filtered = recommendations.filter(r => {
        if (filterType !== 'ALL' && r.type !== filterType) return false
        if (filterPriority !== 'ALL' && r.priority !== filterPriority) return false
        return true
    })

    const typeOptions = ['ALL', ...Object.keys(TYPE_CONFIG)]
    const priorityOptions = ['ALL', 'HIGH', 'MEDIUM', 'LOW']

    return (
        <div className="relative">
            {/* Toast Notification */}
            {toast && (
                <div className={`fixed bottom-4 right-4 z-50 px-4 py-3 rounded-lg shadow-xl flex items-center gap-3 animate-in slide-in-from-bottom-5 border ${toast.type === 'success'
                    ? 'bg-green-900/90 border-green-700 text-green-100'
                    : 'bg-red-900/90 border-red-700 text-red-100'
                    }`}>
                    {toast.type === 'success' ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
                    <p className="text-sm font-medium">{toast.message}</p>
                </div>
            )}

            <PageHeader
                title="Rekomendacje Optymalizacyjne"
                subtitle={`${data?.total || 0} sugestii z 7 reguł Playbooka`}
            >
                <div className="flex items-center gap-2 text-sm bg-brand-500/10 text-brand-300 px-3 py-1.5 rounded-lg border border-brand-500/20">
                    <Zap size={14} />
                    <span>Akcje są wykonywane natychmiastowo via Google Ads API (Mock)</span>
                </div>
            </PageHeader>

            <SummaryCards data={data} />

            {/* Filters */}
            <div className="flex flex-wrap gap-3 mb-6 bg-surface-800/40 p-3 rounded-xl border border-surface-700/50">
                <div className="flex items-center gap-2">
                    <Filter className="w-4 h-4 text-gray-400" />
                    <select
                        className="bg-surface-700 border border-surface-600 text-white text-sm rounded-lg px-3 py-1.5 focus:border-brand-500 focus:outline-none"
                        value={filterType}
                        onChange={(e) => setFilterType(e.target.value)}
                    >
                        {typeOptions.map(opt => (
                            <option key={opt} value={opt}>
                                {opt === 'ALL' ? 'Wszystkie Typy' : TYPE_CONFIG[opt]?.label || opt}
                            </option>
                        ))}
                    </select>
                </div>
                <div>
                    <select
                        className="bg-surface-700 border border-surface-600 text-white text-sm rounded-lg px-3 py-1.5 focus:border-brand-500 focus:outline-none"
                        value={filterPriority}
                        onChange={(e) => setFilterPriority(e.target.value)}
                    >
                        {priorityOptions.map(opt => (
                            <option key={opt} value={opt}>
                                {opt === 'ALL' ? 'Wszystkie Priorytety' : PRIORITY_CONFIG[opt]?.label}
                            </option>
                        ))}
                    </select>
                </div>
                <button
                    onClick={loadData}
                    className="ml-auto bg-surface-700 hover:bg-surface-600 text-white text-sm px-4 py-1.5 rounded-lg transition-colors flex items-center gap-2 border border-surface-600"
                >
                    <Loader2 className="w-3.5 h-3.5" />
                    Odśwież
                </button>
            </div>

            {/* Recommendations List */}
            {filtered.length === 0 ? (
                <div className="text-center py-16 bg-surface-800/30 rounded-xl border border-surface-700/30">
                    <CheckCircle2 className="w-12 h-12 text-green-400 mx-auto mb-3" />
                    <h3 className="text-lg font-semibold text-white">Wszystko czyste!</h3>
                    <p className="text-gray-400 mt-1">Brak rekomendacji spełniających kryteria.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {filtered.map((rec) => (
                        <RecommendationCard
                            key={rec.unique_id}
                            rec={rec}
                            onApply={handleApply}
                            isApplying={applyingId === rec.unique_id}
                        />
                    ))}
                </div>
            )}
        </div>
    )
}





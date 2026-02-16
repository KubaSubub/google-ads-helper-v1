import { useState, useEffect } from 'react'
import { LoadingSpinner, ErrorMessage, PageHeader } from '../components/UI'
import { getSearchTerms, getSegmentedSearchTerms } from '../api'
import {
    Search, ArrowUpDown, ChevronLeft, ChevronRight, Download,
    TrendingUp, AlertTriangle, HelpCircle, XCircle, LayoutGrid,
    List,
} from 'lucide-react'

const SEGMENT_CONFIG = {
    ALL: { label: 'Wszystkie', icon: List, color: 'text-white', bg: 'bg-gray-600/20', border: 'border-gray-500/30' },
    HIGH_PERFORMER: { label: 'Top Performerzy', icon: TrendingUp, color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/30' },
    WASTE: { label: 'Waste (strata)', icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30' },
    TESTING: { label: 'Do obserwacji', icon: HelpCircle, color: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/30' },
    IRRELEVANT: { label: 'Nieistotne', icon: XCircle, color: 'text-gray-400', bg: 'bg-gray-500/10', border: 'border-gray-500/30' },
    OTHER: { label: 'Inne', icon: LayoutGrid, color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/30' },
}

export default function SearchTerms() {
    const [viewMode, setViewMode] = useState('segments') // 'segments' or 'list'
    const [data, setData] = useState({ items: [], total: 0, page: 1, total_pages: 0 })
    const [segData, setSegData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [search, setSearch] = useState('')
    const [sortBy, setSortBy] = useState('cost')
    const [sortOrder, setSortOrder] = useState('desc')
    const [page, setPage] = useState(1)
    const [activeSegment, setActiveSegment] = useState('ALL')

    useEffect(() => {
        if (viewMode === 'list') loadListData()
        else loadSegmentedData()
    }, [viewMode, page, search, sortBy, sortOrder])

    async function loadListData() {
        setLoading(true)
        setError(null)
        try {
            const res = await getSearchTerms({
                page, page_size: 50, search,
                sort_by: sortBy, sort_order: sortOrder,
                client_id: 1
            })
            setData(res)
        } catch (err) { setError(err.message) }
        finally { setLoading(false) }
    }

    async function loadSegmentedData() {
        setLoading(true)
        setError(null)
        try {
            const res = await getSegmentedSearchTerms(1, 30)
            setSegData(res)
        } catch (err) { setError(err.message) }
        finally { setLoading(false) }
    }

    function handleSort(field) {
        if (sortBy === field) setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
        else { setSortBy(field); setSortOrder('desc') }
    }

    function handleSearch(e) {
        e.preventDefault()
        setPage(1)
        if (viewMode === 'list') loadListData()
    }

    function handleExport(format) {
        const params = new URLSearchParams({ client_id: 1, format })
        window.location.href = `/api/v1/export/search-terms?${params.toString()}`
    }

    const SortHeader = ({ field, children }) => (
        <th
            onClick={() => handleSort(field)}
            className="text-left py-3 px-3 text-xs font-medium text-surface-200/40 uppercase tracking-wider cursor-pointer hover:text-surface-200/70 transition-colors select-none"
        >
            <span className="inline-flex items-center gap-1">
                {children}
                {sortBy === field && <ArrowUpDown size={12} className="text-brand-400" />}
            </span>
        </th>
    )

    if (error) return <ErrorMessage message={error} onRetry={() => viewMode === 'list' ? loadListData() : loadSegmentedData()} />

    // Get items for active segment
    const segmentItems = segData && activeSegment !== 'ALL'
        ? segData.segments?.[activeSegment] || []
        : segData
            ? Object.values(segData.segments || {}).flat()
            : []

    return (
        <div className="max-w-[1400px] mx-auto">
            <PageHeader
                title="Search Terms"
                subtitle={viewMode === 'segments'
                    ? `Intelligence — ${segData?.summary?.total || 0} wyszukiwań`
                    : `${data.total} wyszukiwań`}
            >
                <div className="flex items-center gap-4">
                    {/* View mode toggle */}
                    <div className="flex bg-surface-700/40 rounded-lg p-0.5">
                        <button
                            onClick={() => setViewMode('segments')}
                            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${viewMode === 'segments' ? 'bg-brand-600 text-white' : 'text-surface-200/60 hover:text-white'
                                }`}
                        >
                            <LayoutGrid size={14} className="inline mr-1" />Segmenty
                        </button>
                        <button
                            onClick={() => setViewMode('list')}
                            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${viewMode === 'list' ? 'bg-brand-600 text-white' : 'text-surface-200/60 hover:text-white'
                                }`}
                        >
                            <List size={14} className="inline mr-1" />Lista
                        </button>
                    </div>

                    {viewMode === 'list' && (
                        <form onSubmit={handleSearch} className="flex gap-2">
                            <div className="relative">
                                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-200/30" />
                                <input
                                    type="text" value={search}
                                    onChange={e => setSearch(e.target.value)}
                                    placeholder="Szukaj frazy..."
                                    className="pl-9 pr-4 py-2 rounded-lg bg-surface-700/40 border border-surface-700/60 text-sm text-white placeholder:text-surface-200/30 focus:outline-none focus:border-brand-500/50 transition-colors w-56"
                                />
                            </div>
                            <button type="submit" className="px-3 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-500 transition-colors">
                                Szukaj
                            </button>
                        </form>
                    )}

                    <div className="flex gap-1">
                        <button onClick={() => handleExport('csv')} className="p-2 rounded-lg bg-surface-700/40 text-surface-200/60 hover:text-surface-200 hover:bg-surface-700/60 transition-colors" title="Eksportuj CSV">
                            <Download size={18} />
                        </button>
                        <button onClick={() => handleExport('xlsx')} className="p-2 rounded-lg bg-surface-700/40 text-green-400/80 hover:text-green-400 hover:bg-surface-700/60 transition-colors" title="Eksportuj Excel">
                            <Download size={18} />
                        </button>
                    </div>
                </div>
            </PageHeader>

            {/* ===== SEGMENTS VIEW ===== */}
            {viewMode === 'segments' && (
                <>
                    {/* Summary cards */}
                    {segData?.summary && (
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
                            {Object.entries(SEGMENT_CONFIG).filter(([k]) => k !== 'ALL').map(([key, conf]) => {
                                const count = segData.summary.counts?.[key] || 0
                                const Icon = conf.icon
                                return (
                                    <button
                                        key={key}
                                        onClick={() => setActiveSegment(activeSegment === key ? 'ALL' : key)}
                                        className={`${conf.bg} ${conf.border} border rounded-xl p-4 text-left transition-all hover:scale-[1.02] ${activeSegment === key ? 'ring-2 ring-brand-500/50' : ''
                                            }`}
                                    >
                                        <div className="flex items-center gap-2 mb-1">
                                            <Icon className={`w-4 h-4 ${conf.color}`} />
                                            <span className={`text-xs font-medium ${conf.color}`}>{conf.label}</span>
                                        </div>
                                        <p className={`text-2xl font-bold ${conf.color}`}>{count}</p>
                                    </button>
                                )
                            })}
                        </div>
                    )}

                    {/* Waste cost callout */}
                    {segData?.summary?.waste_cost > 0 && (
                        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 mb-6 flex items-center gap-3">
                            <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
                            <div>
                                <p className="text-red-400 font-semibold text-sm">
                                    Zmarnowany budżet: ${segData.summary.waste_cost.toFixed(2)}
                                </p>
                                <p className="text-red-400/60 text-xs">
                                    Frazy z segmentu WASTE — kliknięcia bez konwersji. Rozważ dodanie jako negatywne.
                                </p>
                            </div>
                        </div>
                    )}

                    {/* Segment table */}
                    <div className="glass rounded-xl overflow-hidden animate-fade-in">
                        {loading ? <LoadingSpinner /> : (
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b border-surface-700/40">
                                            <th className="text-left py-3 px-3 text-xs font-medium text-surface-200/40 uppercase">Segment</th>
                                            <th className="text-left py-3 px-3 text-xs font-medium text-surface-200/40 uppercase">Fraza</th>
                                            <th className="text-left py-3 px-3 text-xs font-medium text-surface-200/40 uppercase">Kliknięcia</th>
                                            <th className="text-left py-3 px-3 text-xs font-medium text-surface-200/40 uppercase">Koszt</th>
                                            <th className="text-left py-3 px-3 text-xs font-medium text-surface-200/40 uppercase">Konwersje</th>
                                            <th className="text-left py-3 px-3 text-xs font-medium text-surface-200/40 uppercase">CVR</th>
                                            <th className="text-left py-3 px-3 text-xs font-medium text-surface-200/40 uppercase">Powód</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-surface-700/20">
                                        {segmentItems.map((t, i) => {
                                            // Determine which segment this term belongs to
                                            let seg = 'OTHER'
                                            for (const [key, items] of Object.entries(segData?.segments || {})) {
                                                if (items.some(item => item.id === t.id)) { seg = key; break }
                                            }
                                            const conf = SEGMENT_CONFIG[seg] || SEGMENT_CONFIG.OTHER
                                            const Icon = conf.icon

                                            return (
                                                <tr key={t.id || i} className={`${conf.bg} hover:bg-surface-700/20 transition-colors`}>
                                                    <td className="py-3 px-3">
                                                        <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${conf.bg} ${conf.color} border ${conf.border}`}>
                                                            <Icon size={10} />{conf.label}
                                                        </span>
                                                    </td>
                                                    <td className="py-3 px-3 font-medium text-white max-w-xs truncate">{t.text}</td>
                                                    <td className="py-3 px-3 font-mono text-surface-200/80">{t.clicks?.toLocaleString()}</td>
                                                    <td className="py-3 px-3 font-mono text-surface-200/80">${t.cost?.toFixed(2)}</td>
                                                    <td className="py-3 px-3 font-mono text-surface-200/80">{t.conversions?.toFixed(1)}</td>
                                                    <td className="py-3 px-3 font-mono text-surface-200/60">{t.cvr?.toFixed(2)}%</td>
                                                    <td className="py-3 px-3 text-xs text-surface-200/50 max-w-xs truncate">{t.segment_reason || '—'}</td>
                                                </tr>
                                            )
                                        })}
                                    </tbody>
                                </table>
                                {segmentItems.length === 0 && (
                                    <div className="text-center py-12 text-surface-200/40">
                                        Brak wyników dla tego segmentu.
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </>
            )}

            {/* ===== LIST VIEW (original) ===== */}
            {viewMode === 'list' && (
                <div className="glass rounded-xl overflow-hidden animate-fade-in">
                    {loading ? <LoadingSpinner /> : (
                        <>
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b border-surface-700/40">
                                            <SortHeader field="text">Fraza</SortHeader>
                                            <SortHeader field="clicks">Kliknięcia</SortHeader>
                                            <SortHeader field="impressions">Wyświetlenia</SortHeader>
                                            <SortHeader field="cost">Koszt</SortHeader>
                                            <SortHeader field="conversions">Konwersje</SortHeader>
                                            <SortHeader field="ctr">CTR</SortHeader>
                                            <th className="text-left py-3 px-3 text-xs font-medium text-surface-200/40 uppercase tracking-wider">Koszt/konw.</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-surface-700/20">
                                        {data.items.map((t, i) => {
                                            const isWaste = t.cost > 20 && t.conversions === 0
                                            return (
                                                <tr key={t.id || i} className={`hover:bg-surface-700/20 transition-colors ${isWaste ? 'bg-red-500/5' : ''}`}>
                                                    <td className="py-3 px-3 font-medium text-white max-w-xs truncate">
                                                        {t.text}
                                                        {isWaste && (
                                                            <span className="ml-2 px-1.5 py-0.5 text-[10px] rounded bg-red-500/20 text-red-400">💸 waste</span>
                                                        )}
                                                    </td>
                                                    <td className="py-3 px-3 font-mono text-surface-200/80">{t.clicks.toLocaleString()}</td>
                                                    <td className="py-3 px-3 font-mono text-surface-200/60">{t.impressions.toLocaleString()}</td>
                                                    <td className="py-3 px-3 font-mono text-surface-200/80">{t.cost.toFixed(2)} zł</td>
                                                    <td className="py-3 px-3 font-mono text-surface-200/80">{t.conversions.toFixed(1)}</td>
                                                    <td className="py-3 px-3 font-mono text-surface-200/60">{t.ctr.toFixed(2)}%</td>
                                                    <td className="py-3 px-3 font-mono text-surface-200/60">
                                                        {t.conversions > 0 ? (t.cost / t.conversions).toFixed(2) + ' zł' : '—'}
                                                    </td>
                                                </tr>
                                            )
                                        })}
                                    </tbody>
                                </table>
                            </div>

                            {/* Pagination */}
                            <div className="flex items-center justify-between px-4 py-3 border-t border-surface-700/40">
                                <span className="text-xs text-surface-200/40">
                                    Strona {data.page} z {data.total_pages} ({data.total} wyników)
                                </span>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => setPage(p => Math.max(1, p - 1))}
                                        disabled={page <= 1}
                                        className="p-2 rounded-lg bg-surface-700/40 text-surface-200/60 hover:bg-surface-700/60 disabled:opacity-30 transition-colors"
                                    >
                                        <ChevronLeft size={14} />
                                    </button>
                                    <button
                                        onClick={() => setPage(p => Math.min(data.total_pages, p + 1))}
                                        disabled={page >= data.total_pages}
                                        className="p-2 rounded-lg bg-surface-700/40 text-surface-200/60 hover:bg-surface-700/60 disabled:opacity-30 transition-colors"
                                    >
                                        <ChevronRight size={14} />
                                    </button>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            )}
        </div>
    )
}

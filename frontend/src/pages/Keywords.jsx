import { useState, useEffect } from 'react'
import { LoadingSpinner, ErrorMessage, PageHeader } from '../components/UI'
import { getKeywords } from '../api'
import { ArrowUpDown, ChevronLeft, ChevronRight, Download } from 'lucide-react'

export default function Keywords() {
    // ... state ...
    const [data, setData] = useState({ items: [], total: 0, page: 1, total_pages: 0 })
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [sortBy, setSortBy] = useState('cost')
    const [sortOrder, setSortOrder] = useState('desc')
    const [page, setPage] = useState(1)
    const [matchFilter, setMatchFilter] = useState('')

    useEffect(() => {
        loadData()
    }, [page, matchFilter, sortBy, sortOrder])

    async function loadData() {
        setLoading(true)
        setError(null)
        try {
            const params = {
                page,
                page_size: 50,
                sort_by: sortBy,
                sort_order: sortOrder,
                client_id: 1 // Hardcoded for MVP
            }
            if (matchFilter) params.match_type = matchFilter

            const res = await getKeywords(params)
            setData(res)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    function handleSort(field) {
        if (sortBy === field) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
        } else {
            setSortBy(field)
            setSortOrder('desc')
        }
    }
    function handleExport(format) {
        const params = new URLSearchParams({
            client_id: 1,
            format: format
        })
        window.location.href = `/api/v1/export/keywords?${params.toString()}`
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

    const matchColors = {
        EXACT: 'text-green-400 bg-green-500/15',
        PHRASE: 'text-blue-400 bg-blue-500/15',
        BROAD: 'text-yellow-400 bg-yellow-500/15',
    }

    if (error) return <ErrorMessage message={error} onRetry={loadData} />

    return (
        <div className="max-w-[1400px] mx-auto">
            <PageHeader title="Słowa kluczowe" subtitle={`${data.total} słów kluczowych`}>
                <div className="flex items-center gap-4">
                    <div className="flex gap-2">
                        {['', 'EXACT', 'PHRASE', 'BROAD'].map(m => (
                            <button
                                key={m}
                                onClick={() => { setMatchFilter(m); setPage(1) }}
                                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${matchFilter === m
                                    ? 'bg-brand-600 text-white'
                                    : 'bg-surface-700/40 text-surface-200/50 hover:text-surface-200 hover:bg-surface-700/60'
                                    }`}
                            >
                                {m || 'Wszystkie'}
                            </button>
                        ))}
                    </div>

                    <div className="flex gap-1">
                        <button
                            onClick={() => handleExport('csv')}
                            className="p-2 rounded-lg bg-surface-700/40 text-surface-200/60 hover:text-surface-200 hover:bg-surface-700/60 transition-colors"
                            title="Eksportuj CSV"
                        >
                            <Download size={18} />
                        </button>
                        <button
                            onClick={() => handleExport('xlsx')}
                            className="p-2 rounded-lg bg-surface-700/40 text-green-400/80 hover:text-green-400 hover:bg-surface-700/60 transition-colors"
                            title="Eksportuj Excel"
                        >
                            <Download size={18} />
                        </button>
                    </div>
                </div>
            </PageHeader>

            <div className="glass rounded-xl overflow-hidden animate-fade-in">
                {loading ? (
                    <LoadingSpinner />
                ) : (
                    <>
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b border-surface-700/40">
                                        <th className="text-left py-3 px-3 text-xs font-medium text-surface-200/40 uppercase tracking-wider">Słowo kluczowe</th>
                                        <th className="text-left py-3 px-3 text-xs font-medium text-surface-200/40 uppercase tracking-wider">Dopasowanie</th>
                                        <SortHeader field="clicks">Kliknięcia</SortHeader>
                                        <SortHeader field="impressions">Wyświetlenia</SortHeader>
                                        <SortHeader field="cost">Koszt</SortHeader>
                                        <SortHeader field="conversions">Konwersje</SortHeader>
                                        <SortHeader field="ctr">CTR</SortHeader>
                                        <SortHeader field="avg_cpc">Avg CPC</SortHeader>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-surface-700/20">
                                    {data.items.map((k, i) => (
                                        <tr key={k.id || i} className="hover:bg-surface-700/20 transition-colors">
                                            <td className="py-3 px-3 font-medium text-white">{k.text}</td>
                                            <td className="py-3 px-3">
                                                <span className={`px-2 py-0.5 rounded text-[11px] font-medium ${matchColors[k.match_type] || ''}`}>
                                                    {k.match_type}
                                                </span>
                                            </td>
                                            <td className="py-3 px-3 font-mono text-surface-200/80">{k.clicks?.toLocaleString()}</td>
                                            <td className="py-3 px-3 font-mono text-surface-200/60">{k.impressions?.toLocaleString()}</td>
                                            <td className="py-3 px-3 font-mono text-surface-200/80">{k.cost?.toFixed(2)} zł</td>
                                            <td className="py-3 px-3 font-mono text-surface-200/80">{k.conversions?.toFixed(1)}</td>
                                            <td className="py-3 px-3 font-mono text-surface-200/60">{k.ctr?.toFixed(2)}%</td>
                                            <td className="py-3 px-3 font-mono text-surface-200/60">{k.avg_cpc?.toFixed(2)} zł</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        <div className="flex items-center justify-between px-4 py-3 border-t border-surface-700/40">
                            <span className="text-xs text-surface-200/40">
                                Strona {data.page} z {data.total_pages}
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
        </div>
    )
}

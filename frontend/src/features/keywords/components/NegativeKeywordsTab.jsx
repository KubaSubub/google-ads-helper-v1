import { useEffect, useState, useCallback } from 'react'
import { ChevronLeft, ChevronRight, Loader2, Plus, Trash2 } from 'lucide-react'

import { StatusBadge, TH_STYLE } from '../../../components/UI'
import { getNegativeKeywords, removeNegativeKeyword } from '../../../api'
import AddNegativeModal from './AddNegativeModal'
import {
    MATCH_COLORS,
    SCOPE_LABELS,
    SOURCE_LABELS,
    PILL_STYLE,
    INPUT_STYLE,
    BTN_PRIMARY,
} from './shared'

function MatchBadge({ matchType }) {
    const config = MATCH_COLORS[matchType]
    if (!config) return <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>{matchType || '-'}</span>
    return (
        <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 999, background: config.bg, color: config.color, border: `1px solid ${config.border}` }}>
            {matchType}
        </span>
    )
}

function Pagination({ page, totalPages, setPage }) {
    return (
        <div className="flex items-center justify-between" style={{ padding: '10px 16px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>Strona {page} z {totalPages}</span>
            <div className="flex items-center gap-1">
                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
                    style={{ padding: '5px 8px', borderRadius: 7, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', opacity: page <= 1 ? 0.3 : 1 }}>
                    <ChevronLeft size={14} />
                </button>
                <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
                    style={{ padding: '5px 8px', borderRadius: 7, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', opacity: page >= totalPages ? 0.3 : 1 }}>
                    <ChevronRight size={14} />
                </button>
            </div>
        </div>
    )
}

export default function NegativeKeywordsTab({ selectedClientId, showToast }) {
    const [data, setData] = useState({ items: [], total: 0, page: 1, total_pages: 0 })
    const [loading, setLoading] = useState(true)
    const [page, setPage] = useState(1)
    const [scopeFilter, setScopeFilter] = useState('')
    const [matchFilter, setMatchFilter] = useState('')
    const [search, setSearch] = useState('')
    const [includeRemoved, setIncludeRemoved] = useState(false)
    const [showAddModal, setShowAddModal] = useState(false)

    const loadData = useCallback(async () => {
        if (!selectedClientId) return
        setLoading(true)
        try {
            const params = { client_id: selectedClientId, page, page_size: 50, include_removed: includeRemoved }
            if (scopeFilter) params.negative_scope = scopeFilter
            if (matchFilter) params.match_type = matchFilter
            if (search) params.search = search
            const res = await getNegativeKeywords(params)
            setData(res)
        } catch { /* ignore */ } finally { setLoading(false) }
    }, [selectedClientId, page, scopeFilter, matchFilter, search, includeRemoved])

    useEffect(() => { loadData() }, [loadData])
    useEffect(() => { setPage(1) }, [scopeFilter, matchFilter, search, includeRemoved, selectedClientId])

    async function handleDelete(id) {
        try {
            await removeNegativeKeyword(id)
            showToast('Wykluczenie usunięte', 'success')
            loadData()
        } catch { showToast('Błąd usuwania', 'error') }
    }

    const totalPages = Math.max(1, data.total_pages || 1)

    return (
        <>
            <div className="flex items-center justify-between flex-wrap gap-3" style={{ marginBottom: 14 }}>
                <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>{data.total} wykluczonych hasel</p>
                <div className="flex items-center gap-3 flex-wrap">
                    {/* Scope pills */}
                    <div className="flex items-center gap-1">
                        {[['', 'Wszystkie'], ['CAMPAIGN', 'Kampania'], ['AD_GROUP', 'Grupa reklam']].map(([val, label]) => (
                            <button key={val} onClick={() => setScopeFilter(val)} style={PILL_STYLE(scopeFilter === val, '#7B5CE0')}>{label}</button>
                        ))}
                    </div>
                    {/* Match pills */}
                    <div className="flex items-center gap-1">
                        {['', 'EXACT', 'PHRASE', 'BROAD'].map(m => (
                            <button key={m || 'ALL'} onClick={() => setMatchFilter(m)}
                                style={PILL_STYLE(matchFilter === m, m ? MATCH_COLORS[m]?.color : null)}>
                                {m || 'Wszystkie'}
                            </button>
                        ))}
                    </div>
                    <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Szukaj..."
                        style={{ ...INPUT_STYLE, width: 160, padding: '5px 10px', fontSize: 11 }} />
                    <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '5px 10px', borderRadius: 999, border: '1px solid rgba(255,255,255,0.1)', background: includeRemoved ? 'rgba(248,113,113,0.08)' : 'rgba(255,255,255,0.03)', color: includeRemoved ? '#FCA5A5' : 'rgba(255,255,255,0.55)', fontSize: 11, cursor: 'pointer' }}>
                        <input type="checkbox" checked={includeRemoved} onChange={e => setIncludeRemoved(e.target.checked)} /> Usunięte
                    </label>
                    <button onClick={() => setShowAddModal(true)} style={{ ...BTN_PRIMARY, display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, padding: '6px 14px' }}>
                        <Plus size={12} /> Dodaj wykluczenie
                    </button>
                </div>
            </div>

            <div className="v2-card" style={{ overflow: 'hidden' }}>
                {loading ? (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px 0' }}>
                        <Loader2 size={24} style={{ color: '#4F8EF7' }} className="animate-spin" />
                    </div>
                ) : (
                    <>
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                                        <th style={TH_STYLE}>Fraza</th>
                                        <th style={TH_STYLE}>Dopasowanie</th>
                                        <th style={TH_STYLE}>Zakres</th>
                                        <th style={TH_STYLE}>Kampania</th>
                                        <th style={TH_STYLE}>Grupa reklam</th>
                                        <th style={TH_STYLE}>Status</th>
                                        <th style={TH_STYLE}>Zrodlo</th>
                                        <th style={TH_STYLE}>Dodano</th>
                                        <th style={TH_STYLE}>Akcje</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.items.length === 0 && (
                                        <tr><td colSpan={9} style={{ padding: '32px 12px', textAlign: 'center', fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>Brak wykluczonych hasel.</td></tr>
                                    )}
                                    {data.items.map((neg, i) => (
                                        <tr key={neg.id || i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.12s' }}
                                            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.025)' }}
                                            onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}>
                                            <td style={{ padding: '10px 12px', fontSize: 13, fontWeight: 500, color: '#F0F0F0' }}>{neg.text}</td>
                                            <td style={{ padding: '10px 12px' }}><MatchBadge matchType={neg.match_type} /></td>
                                            <td style={{ padding: '10px 12px' }}>
                                                <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 999, background: neg.negative_scope === 'AD_GROUP' ? 'rgba(123,92,224,0.1)' : 'rgba(79,142,247,0.1)', color: neg.negative_scope === 'AD_GROUP' ? '#7B5CE0' : '#4F8EF7', border: `1px solid ${neg.negative_scope === 'AD_GROUP' ? 'rgba(123,92,224,0.25)' : 'rgba(79,142,247,0.25)'}` }}>
                                                    {SCOPE_LABELS[neg.negative_scope] || neg.negative_scope}
                                                </span>
                                            </td>
                                            <td style={{ padding: '10px 12px', fontSize: 12, color: 'rgba(255,255,255,0.7)' }}>{neg.campaign_name || '-'}</td>
                                            <td style={{ padding: '10px 12px', fontSize: 12, color: 'rgba(255,255,255,0.5)' }}>{neg.ad_group_name || '-'}</td>
                                            <td style={{ padding: '10px 12px' }}><StatusBadge status={neg.status} /></td>
                                            <td style={{ padding: '10px 12px', fontSize: 11, color: 'rgba(255,255,255,0.5)' }}>{SOURCE_LABELS[neg.source] || neg.source}</td>
                                            <td style={{ padding: '10px 12px', fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>{neg.created_at ? new Date(neg.created_at).toLocaleDateString('pl') : '-'}</td>
                                            <td style={{ padding: '10px 12px' }}>
                                                {neg.status !== 'REMOVED' && (
                                                    <button onClick={() => handleDelete(neg.id)} title="Usun" style={{ padding: '3px 6px', borderRadius: 6, background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', color: '#F87171', cursor: 'pointer' }}>
                                                        <Trash2 size={12} />
                                                    </button>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        <Pagination page={page} totalPages={totalPages} setPage={setPage} />
                    </>
                )}
            </div>

            {showAddModal && <AddNegativeModal clientId={selectedClientId} onClose={() => setShowAddModal(false)} onDone={() => { setShowAddModal(false); loadData() }} showToast={showToast} />}
        </>
    )
}

import { useEffect, useState, useCallback } from 'react'
import { List, Loader2, Minus, Plus, Shield, Trash2 } from 'lucide-react'

import { MODAL_OVERLAY, MODAL_BOX, TH_STYLE } from '../../../components/UI'
import {
    getNegativeKeywordLists, createNegativeKeywordList, getNegativeKeywordListDetail,
    deleteNegativeKeywordList, addToNegativeKeywordList, removeFromNegativeKeywordList,
    applyNegativeKeywordList,
    getCampaigns,
} from '../../../api'
import DarkSelect from '../../../components/DarkSelect'
import { MATCH_COLORS, INPUT_STYLE, BTN_PRIMARY, BTN_SECONDARY } from './shared'

function MatchBadge({ matchType }) {
    const config = MATCH_COLORS[matchType]
    if (!config) return <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>{matchType || '-'}</span>
    return (
        <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 999, background: config.bg, color: config.color, border: `1px solid ${config.border}` }}>
            {matchType}
        </span>
    )
}

/* ── Create list modal ── */
function CreateListModal({ clientId, onClose, onDone, showToast }) {
    const [name, setName] = useState('')
    const [description, setDescription] = useState('')
    const [submitting, setSubmitting] = useState(false)

    async function handleSubmit() {
        if (!name.trim()) { showToast('Podaj nazwe listy', 'error'); return }
        setSubmitting(true)
        try {
            await createNegativeKeywordList({ client_id: clientId, name: name.trim(), description: description.trim() || null })
            showToast('Lista utworzona', 'success')
            onDone()
        } catch { showToast('Blad tworzenia listy', 'error') } finally { setSubmitting(false) }
    }

    return (
        <div style={MODAL_OVERLAY} onClick={onClose}>
            <div style={MODAL_BOX} onClick={e => e.stopPropagation()}>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', marginBottom: 16 }}>Nowa lista wykluczajaca</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div>
                        <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 4, display: 'block' }}>Nazwa</label>
                        <input value={name} onChange={e => setName(e.target.value)} style={INPUT_STYLE} placeholder="np. Ogolne wykluczenia" />
                    </div>
                    <div>
                        <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 4, display: 'block' }}>Opis (opcjonalny)</label>
                        <input value={description} onChange={e => setDescription(e.target.value)} style={INPUT_STYLE} placeholder="Opis listy..." />
                    </div>
                    <div className="flex justify-end gap-2" style={{ marginTop: 8 }}>
                        <button onClick={onClose} style={BTN_SECONDARY}>Anuluj</button>
                        <button onClick={handleSubmit} disabled={submitting} style={{ ...BTN_PRIMARY, opacity: submitting ? 0.5 : 1 }}>
                            {submitting ? 'Tworzenie...' : 'Utworz'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

/* ── Add items to list modal ── */
function AddItemsModal({ listId, onClose, onDone, showToast }) {
    const [texts, setTexts] = useState('')
    const [matchType, setMatchType] = useState('PHRASE')
    const [submitting, setSubmitting] = useState(false)

    async function handleSubmit() {
        const lines = texts.split('\n').map(l => l.trim()).filter(Boolean)
        if (!lines.length) { showToast('Wpisz przynajmniej jedno slowo', 'error'); return }
        setSubmitting(true)
        try {
            await addToNegativeKeywordList(listId, { texts: lines, match_type: matchType })
            showToast(`Dodano ${lines.length} slow`, 'success')
            onDone()
        } catch { showToast('Blad dodawania', 'error') } finally { setSubmitting(false) }
    }

    return (
        <div style={MODAL_OVERLAY} onClick={onClose}>
            <div style={MODAL_BOX} onClick={e => e.stopPropagation()}>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', marginBottom: 16 }}>Dodaj słowa do listy</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div>
                        <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 4, display: 'block' }}>Słowa (po jednym na linię)</label>
                        <textarea value={texts} onChange={e => setTexts(e.target.value)} rows={6} style={{ ...INPUT_STYLE, resize: 'vertical' }} placeholder="darmowe&#10;za darmo&#10;tanie" />
                    </div>
                    <div>
                        <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 4, display: 'block' }}>Typ dopasowania</label>
                        <DarkSelect
                            value={matchType}
                            onChange={(v) => setMatchType(v)}
                            options={[
                                { value: 'PHRASE', label: 'PHRASE' },
                                { value: 'EXACT', label: 'EXACT' },
                                { value: 'BROAD', label: 'BROAD' },
                            ]}
                        />
                    </div>
                    <div className="flex justify-end gap-2" style={{ marginTop: 8 }}>
                        <button onClick={onClose} style={BTN_SECONDARY}>Anuluj</button>
                        <button onClick={handleSubmit} disabled={submitting} style={{ ...BTN_PRIMARY, opacity: submitting ? 0.5 : 1 }}>
                            {submitting ? 'Dodawanie...' : 'Dodaj'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

/* ── Apply list to campaigns modal ── */
function ApplyListModal({ listId, clientId, onClose, onDone, showToast }) {
    const [campaigns, setCampaigns] = useState([])
    const [selectedCampaigns, setSelectedCampaigns] = useState([])
    const [submitting, setSubmitting] = useState(false)

    useEffect(() => {
        getCampaigns(clientId).then(r => {
            const items = r.items || r
            setCampaigns(items.filter(c => c.status !== 'REMOVED'))
        }).catch((err) => console.error('[Keywords] list campaigns load failed', err))
    }, [clientId])

    function toggleCampaign(id) {
        setSelectedCampaigns(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
    }

    async function handleSubmit() {
        if (!selectedCampaigns.length) { showToast('Wybierz przynajmniej jedna kampanie', 'error'); return }
        setSubmitting(true)
        try {
            const res = await applyNegativeKeywordList(listId, { campaign_ids: selectedCampaigns })
            const data = res.data || res
            showToast(`Zastosowano: ${data.created} nowych, ${data.skipped} pominieto (duplikaty)`, 'success')
            onDone()
        } catch { showToast('Blad stosowania listy', 'error') } finally { setSubmitting(false) }
    }

    return (
        <div style={MODAL_OVERLAY} onClick={onClose}>
            <div style={MODAL_BOX} onClick={e => e.stopPropagation()}>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', marginBottom: 16 }}>Zastosuj liste do kampanii</h3>
                <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginBottom: 12 }}>Wybierz kampanie, do ktorych chcesz dodac wykluczenia z tej listy:</p>
                <div style={{ maxHeight: 300, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 16 }}>
                    {campaigns.map(c => (
                        <label key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 10px', borderRadius: 8, background: selectedCampaigns.includes(c.id) ? 'rgba(79,142,247,0.1)' : 'transparent', border: `1px solid ${selectedCampaigns.includes(c.id) ? 'rgba(79,142,247,0.3)' : 'rgba(255,255,255,0.06)'}`, cursor: 'pointer', fontSize: 12, color: '#F0F0F0' }}>
                            <input type="checkbox" checked={selectedCampaigns.includes(c.id)} onChange={() => toggleCampaign(c.id)} />
                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.name}</span>
                            <span style={{ marginLeft: 'auto', fontSize: 10, color: 'rgba(255,255,255,0.35)' }}>{c.campaign_type}</span>
                        </label>
                    ))}
                </div>
                <div className="flex justify-end gap-2">
                    <button onClick={onClose} style={BTN_SECONDARY}>Anuluj</button>
                    <button onClick={handleSubmit} disabled={submitting} style={{ ...BTN_PRIMARY, opacity: submitting ? 0.5 : 1 }}>
                        {submitting ? 'Stosowanie...' : `Zastosuj do ${selectedCampaigns.length} kampanii`}
                    </button>
                </div>
            </div>
        </div>
    )
}

/* ── Main component ── */

export default function NegativeKeywordListsTab({ selectedClientId, showToast }) {
    const [lists, setLists] = useState([])
    const [loading, setLoading] = useState(true)
    const [showCreateModal, setShowCreateModal] = useState(false)
    const [expandedListId, setExpandedListId] = useState(null)
    const [expandedData, setExpandedData] = useState(null)
    const [showApplyModal, setShowApplyModal] = useState(null) // list id
    const [showAddItemsModal, setShowAddItemsModal] = useState(null) // list id

    const loadLists = useCallback(async () => {
        if (!selectedClientId) return
        setLoading(true)
        try {
            const res = await getNegativeKeywordLists({ client_id: selectedClientId })
            setLists(Array.isArray(res) ? res : res.data || [])
        } catch { /* ignore */ } finally { setLoading(false) }
    }, [selectedClientId])

    useEffect(() => { loadLists() }, [loadLists])

    async function handleExpand(listId) {
        if (expandedListId === listId) { setExpandedListId(null); setExpandedData(null); return }
        setExpandedListId(listId)
        try {
            const res = await getNegativeKeywordListDetail(listId)
            setExpandedData(res)
        } catch { showToast('Blad ladowania listy', 'error') }
    }

    async function handleDeleteList(listId) {
        try {
            await deleteNegativeKeywordList(listId)
            showToast('Lista usunieta', 'success')
            if (expandedListId === listId) { setExpandedListId(null); setExpandedData(null) }
            loadLists()
        } catch { showToast('Błąd usuwania', 'error') }
    }

    async function handleDeleteItem(listId, itemId) {
        try {
            await removeFromNegativeKeywordList(listId, itemId)
            showToast('Słowo usunięte z listy', 'success')
            const res = await getNegativeKeywordListDetail(listId)
            setExpandedData(res)
            loadLists()
        } catch { showToast('Błąd usuwania', 'error') }
    }

    return (
        <>
            <div className="flex items-center justify-between flex-wrap gap-3" style={{ marginBottom: 14 }}>
                <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>{lists.length} list wykluczajacych</p>
                <button onClick={() => setShowCreateModal(true)} style={{ ...BTN_PRIMARY, display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, padding: '6px 14px' }}>
                    <Plus size={12} /> Nowa lista
                </button>
            </div>

            {loading ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px 0' }}>
                    <Loader2 size={24} style={{ color: '#4F8EF7' }} className="animate-spin" />
                </div>
            ) : lists.length === 0 ? (
                <div className="v2-card" style={{ padding: 32, textAlign: 'center', color: 'rgba(255,255,255,0.45)', fontSize: 12 }}>
                    Brak list. Utworz pierwsza liste klikajac "Nowa lista".
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {lists.map(list => {
                        const isExpanded = expandedListId === list.id
                        return (
                            <div key={list.id} className="v2-card" style={{ overflow: 'hidden' }}>
                                <div className="flex items-center justify-between" style={{ padding: '14px 16px', cursor: 'pointer' }} onClick={() => handleExpand(list.id)}>
                                    <div className="flex items-center gap-3">
                                        <List size={16} style={{ color: '#7B5CE0' }} />
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <span style={{ fontSize: 14, fontWeight: 600, color: '#F0F0F0' }}>{list.name}</span>
                                                {list.source === 'GOOGLE_ADS_SYNC' && (
                                                    <span style={{ fontSize: 9, fontWeight: 600, padding: '2px 6px', borderRadius: 999, background: 'rgba(79,142,247,0.1)', color: '#4F8EF7', border: '1px solid rgba(79,142,247,0.25)' }}>Google Ads</span>
                                                )}
                                            </div>
                                            {list.description && <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>{list.description}</div>}
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', background: 'rgba(255,255,255,0.04)', padding: '3px 10px', borderRadius: 999, border: '1px solid rgba(255,255,255,0.08)' }}>
                                            {list.item_count} słów
                                        </span>
                                        {list.source !== 'GOOGLE_ADS_SYNC' && (
                                            <>
                                                <button onClick={e => { e.stopPropagation(); setShowAddItemsModal(list.id) }} title="Dodaj słowa" style={{ padding: '4px 8px', borderRadius: 6, background: 'rgba(79,142,247,0.08)', border: '1px solid rgba(79,142,247,0.2)', color: '#4F8EF7', cursor: 'pointer' }}>
                                                    <Plus size={12} />
                                                </button>
                                                <button onClick={e => { e.stopPropagation(); handleDeleteList(list.id) }} title="Usun liste" style={{ padding: '4px 8px', borderRadius: 6, background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', color: '#F87171', cursor: 'pointer' }}>
                                                    <Trash2 size={12} />
                                                </button>
                                            </>
                                        )}
                                        <button onClick={e => { e.stopPropagation(); setShowApplyModal(list.id) }} title="Zastosuj" style={{ padding: '4px 8px', borderRadius: 6, background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.2)', color: '#4ADE80', cursor: 'pointer' }}>
                                            <Shield size={12} />
                                        </button>
                                    </div>
                                </div>

                                {isExpanded && expandedData && (
                                    <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', padding: '0' }}>
                                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                            <thead>
                                                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                                                    <th style={TH_STYLE}>Fraza</th>
                                                    <th style={TH_STYLE}>Dopasowanie</th>
                                                    <th style={TH_STYLE}>Dodano</th>
                                                    <th style={{ ...TH_STYLE, width: 50 }}></th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {(expandedData.items || []).length === 0 && (
                                                    <tr><td colSpan={4} style={{ padding: '20px 12px', textAlign: 'center', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Lista pusta.</td></tr>
                                                )}
                                                {(expandedData.items || []).map(item => (
                                                    <tr key={item.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                                        <td style={{ padding: '8px 12px', fontSize: 13, color: '#F0F0F0' }}>{item.text}</td>
                                                        <td style={{ padding: '8px 12px' }}><MatchBadge matchType={item.match_type} /></td>
                                                        <td style={{ padding: '8px 12px', fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>{item.created_at ? new Date(item.created_at).toLocaleDateString('pl') : '-'}</td>
                                                        <td style={{ padding: '8px 12px' }}>
                                                            {list.source !== 'GOOGLE_ADS_SYNC' && (
                                                                <button onClick={() => handleDeleteItem(list.id, item.id)} style={{ padding: '2px 5px', borderRadius: 5, background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', color: '#F87171', cursor: 'pointer' }}>
                                                                    <Minus size={10} />
                                                                </button>
                                                            )}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>
                        )
                    })}
                </div>
            )}

            {showCreateModal && <CreateListModal clientId={selectedClientId} onClose={() => setShowCreateModal(false)} onDone={() => { setShowCreateModal(false); loadLists() }} showToast={showToast} />}
            {showAddItemsModal && <AddItemsModal listId={showAddItemsModal} onClose={() => setShowAddItemsModal(null)} onDone={async () => { setShowAddItemsModal(null); loadLists(); if (expandedListId) { const res = await getNegativeKeywordListDetail(expandedListId); setExpandedData(res) } }} showToast={showToast} />}
            {showApplyModal && <ApplyListModal listId={showApplyModal} clientId={selectedClientId} onClose={() => setShowApplyModal(null)} onDone={() => { setShowApplyModal(null) }} showToast={showToast} />}
        </>
    )
}

import { useState } from 'react'
import {
    AlertTriangle,
    TrendingUp,
    TrendingDown,
    PauseCircle,
    PlusCircle,
    MinusCircle,
    CheckCircle2,
    XCircle,
    Loader2,
    Zap,
    Play,
    RefreshCw,
    Download,
} from 'lucide-react'
import { LoadingSpinner } from '../components/UI'
import { useApp } from '../contexts/AppContext'
import { useRecommendations } from '../hooks/useRecommendations'
import ConfirmationModal from '../components/ConfirmationModal'
import EmptyState from '../components/EmptyState'

const TYPE_CONFIG = {
    PAUSE_KEYWORD: { icon: PauseCircle, color: '#F87171', bg: 'rgba(248,113,113,0.1)', label: 'Pauzuj słowo' },
    UPDATE_BID: { icon: TrendingUp, color: '#4ADE80', bg: 'rgba(74,222,128,0.1)', label: 'Zmień stawkę' },
    ADD_KEYWORD: { icon: PlusCircle, color: '#4F8EF7', bg: 'rgba(79,142,247,0.1)', label: 'Dodaj słowo' },
    ADD_NEGATIVE: { icon: MinusCircle, color: '#F87171', bg: 'rgba(248,113,113,0.1)', label: 'Dodaj wykluczenie' },
    PAUSE_AD: { icon: PauseCircle, color: '#FBBF24', bg: 'rgba(251,191,36,0.1)', label: 'Pauzuj reklamę' },
    INCREASE_BUDGET: { icon: TrendingUp, color: '#4ADE80', bg: 'rgba(74,222,128,0.1)', label: 'Zwiększ budżet' },
    DECREASE_BUDGET: { icon: TrendingDown, color: '#FBBF24', bg: 'rgba(251,191,36,0.1)', label: 'Zmniejsz budżet' },
    ENABLE_KEYWORD: { icon: Play, color: '#4ADE80', bg: 'rgba(74,222,128,0.1)', label: 'Włącz słowo' },
}

const PRIORITY_CONFIG = {
    HIGH: { color: '#F87171', bg: 'rgba(248,113,113,0.12)', border: 'rgba(248,113,113,0.25)', label: 'WYSOKI' },
    MEDIUM: { color: '#FBBF24', bg: 'rgba(251,191,36,0.12)', border: 'rgba(251,191,36,0.25)', label: 'ŚREDNI' },
    LOW: { color: 'rgba(255,255,255,0.4)', bg: 'rgba(255,255,255,0.06)', border: 'rgba(255,255,255,0.1)', label: 'NISKI' },
}

function PriorityPill({ priority }) {
    const cfg = PRIORITY_CONFIG[priority] || PRIORITY_CONFIG.LOW
    return (
        <span style={{
            fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 999,
            background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}`,
            textTransform: 'uppercase', letterSpacing: '0.05em',
        }}>
            {cfg.label}
        </span>
    )
}

function TypePill({ actionType }) {
    const cfg = TYPE_CONFIG[actionType] || { icon: Zap, color: 'rgba(255,255,255,0.4)', bg: 'rgba(255,255,255,0.06)', label: actionType }
    const Icon = cfg.icon
    return (
        <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 4,
            fontSize: 10, fontWeight: 500, padding: '2px 8px 2px 6px', borderRadius: 999,
            background: cfg.bg, color: cfg.color,
        }}>
            <Icon size={10} />
            {cfg.label}
        </span>
    )
}

function RecommendationCard({ rec, onApply, onDismiss, isApplying, selected, onToggle }) {
    const actionType = rec.suggested_action || rec.type
    const typeConf = TYPE_CONFIG[actionType] || { icon: Zap, color: 'rgba(255,255,255,0.4)', bg: 'rgba(255,255,255,0.06)', label: actionType }
    const Icon = typeConf.icon

    return (
        <div className="v2-card" style={{ padding: '16px 18px', border: selected ? '1px solid rgba(79,142,247,0.4)' : undefined }}>
            <div className="flex items-start gap-3">
                <input
                    type="checkbox"
                    checked={selected}
                    onChange={() => onToggle(rec.id)}
                    style={{ marginTop: 10, accentColor: '#4F8EF7', cursor: 'pointer', flexShrink: 0 }}
                />
                <div style={{
                    width: 34, height: 34, borderRadius: 8, flexShrink: 0,
                    background: typeConf.bg,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                    <Icon size={16} style={{ color: typeConf.color }} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="flex items-center gap-2 flex-wrap" style={{ marginBottom: 6 }}>
                        <PriorityPill priority={rec.priority} />
                        <TypePill actionType={actionType} />
                    </div>
                    <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.8)', lineHeight: 1.5, marginBottom: 12 }}>
                        {rec.reason}
                    </p>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => onApply(rec)}
                            disabled={isApplying}
                            style={{
                                display: 'flex', alignItems: 'center', gap: 6,
                                padding: '6px 14px', borderRadius: 7, fontSize: 12, fontWeight: 500,
                                background: '#4F8EF7', color: 'white', cursor: 'pointer', border: 'none',
                                opacity: isApplying ? 0.6 : 1,
                            }}
                        >
                            {isApplying
                                ? <><Loader2 size={12} className="animate-spin" /> Wykonuje...</>
                                : <><Play size={12} style={{ fill: 'white' }} /> Zastosuj</>
                            }
                        </button>
                        <button
                            onClick={() => onDismiss(rec)}
                            style={{
                                display: 'flex', alignItems: 'center', gap: 6,
                                padding: '6px 12px', borderRadius: 7, fontSize: 12,
                                background: 'transparent', color: 'rgba(255,255,255,0.4)', cursor: 'pointer',
                                border: '1px solid rgba(255,255,255,0.1)',
                            }}
                            className="hover:border-white/20 hover:text-white/60"
                        >
                            <XCircle size={12} /> Odrzuć
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default function Recommendations() {
    const { selectedClientId, showToast } = useApp()
    const { recommendations, summary, loading, refetch, apply, dismiss } = useRecommendations(selectedClientId)

    const [filterPriority, setFilterPriority] = useState('ALL')
    const [applyingId, setApplyingId] = useState(null)
    const [confirmModal, setConfirmModal] = useState(null)
    const [dryRunData, setDryRunData] = useState(null)
    const [selectedIds, setSelectedIds] = useState(new Set())
    const [bulkApplying, setBulkApplying] = useState(false)

    if (!selectedClientId) return <EmptyState message="Wybierz klienta w sidebarze" />
    if (loading) return <LoadingSpinner />

    async function handleApply(rec) {
        setApplyingId(rec.id)
        try {
            const preview = await apply(rec.id, true)
            setDryRunData(preview)
            setConfirmModal(rec)
        } catch (err) {
            showToast('Błąd podglądu: ' + err.message, 'error')
        } finally {
            setApplyingId(null)
        }
    }

    async function handleConfirm() {
        if (!confirmModal) return
        setApplyingId(confirmModal.id)
        try {
            await apply(confirmModal.id, false)
            showToast('Akcja wykonana', 'success')
            setConfirmModal(null)
            setDryRunData(null)
            refetch()
        } catch (err) {
            showToast('Błąd wykonania: ' + err.message, 'error')
        } finally {
            setApplyingId(null)
        }
    }

    async function handleDismiss(rec) {
        try {
            await dismiss(rec.id)
            showToast('Rekomendacja odrzucona', 'info')
        } catch (err) {
            showToast('Błąd: ' + err.message, 'error')
        }
    }

    function toggleSelect(id) {
        setSelectedIds(prev => {
            const next = new Set(prev)
            if (next.has(id)) next.delete(id)
            else next.add(id)
            return next
        })
    }

    function selectAll() {
        if (selectedIds.size === filtered.length) {
            setSelectedIds(new Set())
        } else {
            setSelectedIds(new Set(filtered.map(r => r.id)))
        }
    }

    async function handleBulkApply() {
        if (selectedIds.size === 0) return
        setBulkApplying(true)
        let success = 0, failed = 0
        for (const id of selectedIds) {
            try {
                await apply(id, false)
                success++
            } catch {
                failed++
            }
        }
        setBulkApplying(false)
        setSelectedIds(new Set())
        showToast(`Zastosowano ${success} akcji${failed ? `, ${failed} błędów` : ''}`, success > 0 ? 'success' : 'error')
        refetch()
    }

    async function handleBulkDismiss() {
        if (selectedIds.size === 0) return
        setBulkApplying(true)
        for (const id of selectedIds) {
            try { await dismiss(id) } catch {}
        }
        setBulkApplying(false)
        setSelectedIds(new Set())
        showToast('Zaznaczone odrzucone', 'info')
    }

    const filtered = (recommendations || []).filter(r => {
        if (filterPriority !== 'ALL' && r.priority !== filterPriority) return false
        return true
    })

    return (
        <div style={{ maxWidth: 1100 }}>
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 20 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Rekomendacje
                    </h1>
                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                        {(summary && summary.total) || (recommendations && recommendations.length) || 0} sugestii optymalizacyjnych
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => {
                            const params = new URLSearchParams({ client_id: selectedClientId, format: 'xlsx' })
                            window.location.href = `/api/v1/export/recommendations?${params.toString()}`
                        }}
                        style={{
                            display: 'flex', alignItems: 'center', gap: 5,
                            padding: '6px 12px', borderRadius: 7, fontSize: 11,
                            background: 'rgba(74,222,128,0.06)', border: '1px solid rgba(74,222,128,0.2)',
                            color: '#4ADE80', cursor: 'pointer',
                        }}
                    >
                        <Download size={11} /> Export
                    </button>
                    <button
                        onClick={() => refetch()}
                        style={{
                            display: 'flex', alignItems: 'center', gap: 6,
                            padding: '6px 14px', borderRadius: 7, fontSize: 12,
                            background: 'rgba(255,255,255,0.05)',
                            border: '1px solid rgba(255,255,255,0.1)',
                            color: 'rgba(255,255,255,0.6)', cursor: 'pointer',
                        }}
                        className="hover:border-white/20 hover:text-white/80"
                    >
                        <RefreshCw size={12} /> Odśwież
                    </button>
                </div>
            </div>

            {/* Summary + priority filter row */}
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 20 }}>
                {/* Summary mini cards */}
                <div className="flex items-center gap-3">
                    <div className="v2-card" style={{ padding: '8px 16px', display: 'flex', gap: 12, alignItems: 'center' }}>
                        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Razem</span>
                        <span style={{ fontSize: 18, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne' }}>{(summary && summary.total) || (recommendations && recommendations.length) || 0}</span>
                    </div>
                    <div style={{ padding: '8px 16px', borderRadius: 12, background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', display: 'flex', gap: 12, alignItems: 'center' }}>
                        <span style={{ fontSize: 11, color: 'rgba(248,113,113,0.7)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Wysoki</span>
                        <span style={{ fontSize: 18, fontWeight: 700, color: '#F87171', fontFamily: 'Syne' }}>{summary?.high_priority || 0}</span>
                    </div>
                    <div style={{ padding: '8px 16px', borderRadius: 12, background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.2)', display: 'flex', gap: 12, alignItems: 'center' }}>
                        <span style={{ fontSize: 11, color: 'rgba(251,191,36,0.7)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Średni</span>
                        <span style={{ fontSize: 18, fontWeight: 700, color: '#FBBF24', fontFamily: 'Syne' }}>{summary?.medium || 0}</span>
                    </div>
                </div>

                {/* Priority filter pills */}
                <div className="flex items-center gap-1.5">
                    {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map(p => {
                        const active = filterPriority === p
                        const cfg = p !== 'ALL' ? PRIORITY_CONFIG[p] : null
                        return (
                            <button
                                key={p}
                                onClick={() => setFilterPriority(p)}
                                style={{
                                    padding: '4px 12px', borderRadius: 999, fontSize: 11, fontWeight: active ? 500 : 400,
                                    border: `1px solid ${active ? (cfg?.color || '#4F8EF7') : 'rgba(255,255,255,0.1)'}`,
                                    background: active ? (cfg ? cfg.bg : 'rgba(79,142,247,0.18)') : 'transparent',
                                    color: active ? (cfg?.color || 'white') : 'rgba(255,255,255,0.4)',
                                    cursor: 'pointer',
                                }}
                            >
                                {p === 'ALL' ? 'Wszystkie' : cfg?.label}
                            </button>
                        )
                    })}
                </div>
            </div>

            {/* Bulk action bar */}
            {filtered.length > 0 && (
                <div className="flex items-center gap-3 flex-wrap" style={{ marginBottom: 12 }}>
                    <button
                        onClick={selectAll}
                        style={{
                            padding: '5px 12px', borderRadius: 7, fontSize: 11,
                            background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)',
                            color: 'rgba(255,255,255,0.5)', cursor: 'pointer',
                        }}
                    >
                        {selectedIds.size === filtered.length ? 'Odznacz wszystkie' : 'Zaznacz wszystkie'}
                    </button>
                    {selectedIds.size > 0 && (
                        <>
                            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>
                                {selectedIds.size} zaznaczonych
                            </span>
                            <button
                                onClick={handleBulkApply}
                                disabled={bulkApplying}
                                style={{
                                    display: 'flex', alignItems: 'center', gap: 5,
                                    padding: '5px 14px', borderRadius: 7, fontSize: 12, fontWeight: 500,
                                    background: '#4F8EF7', color: 'white', border: 'none', cursor: 'pointer',
                                    opacity: bulkApplying ? 0.6 : 1,
                                }}
                            >
                                {bulkApplying ? <><Loader2 size={12} className="animate-spin" /> Wykonuję...</> : <><Play size={12} style={{ fill: 'white' }} /> Zastosuj zaznaczone</>}
                            </button>
                            <button
                                onClick={handleBulkDismiss}
                                disabled={bulkApplying}
                                style={{
                                    display: 'flex', alignItems: 'center', gap: 5,
                                    padding: '5px 12px', borderRadius: 7, fontSize: 11,
                                    background: 'transparent', border: '1px solid rgba(255,255,255,0.1)',
                                    color: 'rgba(255,255,255,0.4)', cursor: 'pointer',
                                }}
                            >
                                <XCircle size={11} /> Odrzuć zaznaczone
                            </button>
                        </>
                    )}
                </div>
            )}

            {/* List */}
            {filtered.length === 0 ? (
                <div style={{ padding: '48px 0', textAlign: 'center' }}>
                    <CheckCircle2 size={40} style={{ color: '#4ADE80', margin: '0 auto 12px' }} />
                    <div style={{ fontSize: 15, fontWeight: 500, color: '#F0F0F0', marginBottom: 4 }}>Wszystko czyste!</div>
                    <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.4)' }}>Brak rekomendacji spełniających kryteria.</div>
                </div>
            ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(460px, 1fr))', gap: 12 }}>
                    {filtered.map((rec) => (
                        <RecommendationCard
                            key={rec.id}
                            rec={rec}
                            onApply={handleApply}
                            onDismiss={handleDismiss}
                            isApplying={applyingId === rec.id}
                            selected={selectedIds.has(rec.id)}
                            onToggle={toggleSelect}
                        />
                    ))}
                </div>
            )}

            {/* Confirmation Modal */}
            <ConfirmationModal
                isOpen={!!confirmModal}
                onClose={() => { setConfirmModal(null); setDryRunData(null); }}
                onConfirm={handleConfirm}
                title="Potwierdź akcję"
                actionType={dryRunData?.action_type || confirmModal?.suggested_action}
                reason={confirmModal?.reason}
                beforeState={dryRunData?.current_val ? { wartosc: dryRunData.current_val } : undefined}
                afterState={dryRunData?.new_val ? { wartosc: dryRunData.new_val } : undefined}
                isLoading={!!applyingId}
            />
        </div>
    )
}

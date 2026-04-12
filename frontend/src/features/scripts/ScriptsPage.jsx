// ScriptsPage — date-aware Search Terms / Keyword optimization scripts.
// Replaces the old Dashboard "Quick Scripts" and /recommendations action flow.
// Each script supports:
//   1. dry-run preview with editable parameters
//   2. per-item opt-out via checkboxes
//   3. execute with item_ids filter
//   4. result view with applied/failed breakdown
import { useState, useEffect, useCallback, useMemo } from 'react'
import {
    Play, RefreshCw, ChevronDown, CheckCircle2, XCircle, AlertTriangle,
    Loader2, ShieldAlert, TrendingUp, Zap, Clock, Search, Target,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../../contexts/AppContext'
import { useFilter } from '../../contexts/FilterContext'
import { getScriptsCatalog, dryRunScript, executeScript, saveScriptConfig } from '../../api'
import { C, T, B } from '../../constants/designTokens'
import EmptyState from '../../components/EmptyState'

// ── Category icons & colors ─────────────────────────────────────────────────
const CATEGORY_META = {
    waste_elimination: { icon: XCircle,    color: C.danger,     bg: 'rgba(248,113,113,0.06)' },
    expansion:         { icon: TrendingUp, color: C.success,    bg: 'rgba(74,222,128,0.06)' },
    match_type:        { icon: Target,     color: C.accentBlue, bg: 'rgba(79,142,247,0.06)' },
    ngram:             { icon: Search,     color: C.accentPurple || '#7B5CE0', bg: 'rgba(123,92,224,0.06)' },
    temporal:          { icon: Clock,      color: C.warning,    bg: 'rgba(251,191,36,0.06)' },
    brand:             { icon: ShieldAlert, color: C.accentBlue, bg: 'rgba(79,142,247,0.06)' },
}

// ── Single script tile ──────────────────────────────────────────────────────
function ScriptTile({ script, count, savings, loading, onRun }) {
    const meta = CATEGORY_META[script.category] || CATEGORY_META.waste_elimination
    const hasItems = count > 0
    return (
        <div style={{
            padding: '14px 18px',
            borderRadius: 10,
            border: `1px solid ${hasItems ? meta.color + '30' : C.w07}`,
            background: hasItems ? meta.bg : 'rgba(255,255,255,0.02)',
            marginBottom: 10,
            display: 'flex',
            alignItems: 'center',
            gap: 14,
        }}>
            <div style={{
                width: 32, height: 32, borderRadius: 8,
                background: meta.color + '15',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
                <meta.icon size={15} style={{ color: meta.color }} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary }}>
                        [{script.id}] {script.name}
                    </span>
                    {hasItems ? (
                        <span style={{
                            fontSize: 10, fontWeight: 600,
                            color: meta.color,
                            background: meta.color + '18',
                            padding: '1px 8px', borderRadius: 999,
                        }}>
                            {count} do wykonania · ~{Math.round(savings)} zł
                        </span>
                    ) : (
                        <span style={{ fontSize: 10, fontWeight: 500, color: C.success }}>
                            ✓ czysto
                        </span>
                    )}
                </div>
                <div style={{ fontSize: 11, color: C.w40, lineHeight: 1.45 }}>
                    {script.description}
                </div>
            </div>
            <button
                onClick={onRun}
                disabled={loading || !hasItems}
                style={{
                    display: 'flex', alignItems: 'center', gap: 5,
                    padding: '7px 14px', borderRadius: 7,
                    fontSize: 11, fontWeight: 600,
                    background: hasItems ? meta.color + '20' : C.w05,
                    border: `1px solid ${hasItems ? meta.color + '40' : C.w08}`,
                    color: hasItems ? meta.color : C.w30,
                    cursor: hasItems && !loading ? 'pointer' : 'not-allowed',
                    flexShrink: 0,
                }}
            >
                {loading ? <Loader2 size={11} className="animate-spin" /> : <Play size={11} />}
                Uruchom
            </button>
        </div>
    )
}

// ── Param labels (Polish) ────────────────────────────────────────────────
const PARAM_LABELS = {
    min_clicks: { label: 'Min. kliknięć', type: 'number', step: 1 },
    min_cost_pln: { label: 'Min. koszt (zł)', type: 'number', step: 5 },
    min_impressions: { label: 'Min. wyświetleń', type: 'number', step: 10 },
    negative_level: { label: 'Zakres negatywu', type: 'select', options: [
        { value: 'CAMPAIGN', label: 'Kampania' },
        { value: 'AD_GROUP', label: 'Grupa reklam' },
    ]},
    match_type: { label: 'Match type', type: 'select', options: [
        { value: 'PHRASE', label: 'Phrase (zalecany)' },
        { value: 'EXACT', label: 'Exact' },
        { value: 'BROAD', label: 'Broad (agresywny)' },
    ]},
    brand_protection: { label: 'Ochrona brandu', type: 'select', options: [
        { value: true, label: 'Włączona' },
        { value: false, label: 'Wyłączona' },
    ]},
    include_soft: { label: 'Cross-campaign sugestie', type: 'select', options: [
        { value: true, label: 'Pokaż' },
        { value: false, label: 'Ukryj' },
    ]},
    soft_min_clicks: { label: 'Min. kliknięć (cross-camp)', type: 'number', step: 1 },
    custom_brand_words: { label: 'Brand words', type: 'hidden' },
    min_conversions: { label: 'Min. konwersji', type: 'number', step: 1 },
    min_cvr_pct: { label: 'Min. CVR (%)', type: 'number', step: 1 },
    max_cpa_pln: { label: 'Max CPA (zł, 0=brak)', type: 'number', step: 5 },
    keyword_match_type: { label: 'Match type keywordu', type: 'select', options: [
        { value: 'EXACT', label: 'Exact (zalecany)' },
        { value: 'PHRASE', label: 'Phrase' },
    ]},
    include_pmax_alerts: { label: 'Alerty PMax', type: 'select', options: [
        { value: true, label: 'Pokaż' },
        { value: false, label: 'Ukryj' },
    ]},
    allowed_scripts: { label: 'Dozwolone pisma', type: 'multiselect', options: [
        { value: 'LATIN', label: 'Łaciński (PL/EN/DE/FR/...)' },
        { value: 'CYRILLIC', label: 'Cyrylica (RU/UA/BG)' },
        { value: 'GREEK', label: 'Grecki' },
        { value: 'HEBREW', label: 'Hebrajski' },
        { value: 'ARABIC', label: 'Arabski' },
        { value: 'CJK', label: 'Chiński/Japoński (CJK)' },
        { value: 'HIRAGANA', label: 'Hiragana (JP)' },
        { value: 'KATAKANA', label: 'Katakana (JP)' },
        { value: 'HANGUL', label: 'Hangul (KR)' },
        { value: 'THAI', label: 'Tajski' },
        { value: 'DEVANAGARI', label: 'Devanagari (Hindi)' },
    ]},
    min_foreign_chars: { label: 'Min. obcych znakow', type: 'number', step: 1 },
    show_converting: { label: 'Pokaz konwertujace', type: 'select', options: [
        { value: true, label: 'Tak' },
        { value: false, label: 'Nie' },
    ]},
}

// ── Run modal — dry run preview + execute ─────────────────────────────────
function RunModal({ script, clientId, dateFrom, dateTo, onClose, onDone, showToast }) {
    const [phase, setPhase] = useState('loading') // loading | params | preview | executing | result
    const [preview, setPreview] = useState(null)
    const [selectedIds, setSelectedIds] = useState(new Set())
    const [result, setResult] = useState(null)
    const [error, setError] = useState(null)
    const [params, setParams] = useState(null) // merged params from backend
    const [paramsEdited, setParamsEdited] = useState(false)
    const [saving, setSaving] = useState(false)
    const [itemOverrides, setItemOverrides] = useState({}) // {itemId: {ad_group_id: X}}
    const [ngramTab, setNgramTab] = useState(1) // 1-gram, 2-gram, 3-gram, 4-gram
    const navigate = useNavigate()

    const runDryRun = useCallback(async (overrideParams) => {
        setPhase('loading')
        setError(null)
        try {
            const res = await dryRunScript(script.id, {
                client_id: clientId,
                date_from: dateFrom,
                date_to: dateTo,
                params: overrideParams || {},
            })
            setPreview(res)
            if (res.params_used && !overrideParams) {
                setParams(res.params_used)
            }
            // Hard matches selected by default, soft unselected
            const hardIds = res.items
                .filter(i => !i.action_payload?.match_source || i.action_payload.match_source === 'hard')
                .map(i => i.id)
            setSelectedIds(new Set(hardIds.length > 0 ? hardIds : res.items.map(i => i.id)))
            setPhase('preview')
        } catch (e) {
            setError(e.message || 'Błąd podglądu')
            setPhase('preview')
        }
    }, [script.id, clientId, dateFrom, dateTo])

    useEffect(() => { runDryRun() }, [runDryRun])

    const updateParam = (key, value) => {
        setParams(prev => ({ ...prev, [key]: value }))
        setParamsEdited(true)
    }

    const handleRerun = () => runDryRun(params)

    const handleSaveConfig = async () => {
        setSaving(true)
        try {
            await saveScriptConfig(script.id, { client_id: clientId, params })
            showToast?.('Parametry zapisane dla tego klienta', 'success')
            setParamsEdited(false)
        } catch (e) {
            showToast?.(`Błąd zapisu: ${e.message}`, 'error')
        } finally {
            setSaving(false)
        }
    }

    const toggleItem = (id) => {
        setSelectedIds(prev => {
            const next = new Set(prev)
            if (next.has(id)) next.delete(id); else next.add(id)
            return next
        })
    }

    const toggleAll = () => {
        if (!preview) return
        if (selectedIds.size === preview.items.length) {
            setSelectedIds(new Set())
        } else {
            setSelectedIds(new Set(preview.items.map(i => i.id)))
        }
    }

    const handleExecute = async () => {
        if (selectedIds.size === 0) return
        setPhase('executing')
        try {
            const res = await executeScript(script.id, {
                client_id: clientId,
                date_from: dateFrom,
                date_to: dateTo,
                params: params || {},
                item_ids: Array.from(selectedIds),
                ...(Object.keys(itemOverrides).length > 0 ? { item_overrides: itemOverrides } : {}),
            })
            setResult(res)
            setPhase('result')
            onDone?.()
        } catch (e) {
            setResult({ applied: 0, failed: selectedIds.size, errors: [e.message], applied_items: [] })
            setPhase('result')
        }
    }

    const totalSavings = preview?.items
        .filter(i => selectedIds.has(i.id))
        .reduce((s, i) => s + (i.estimated_savings_pln || 0), 0) || 0

    return (
        <div
            onClick={(e) => e.target === e.currentTarget && onClose()}
            style={{
                position: 'fixed', inset: 0, zIndex: 100,
                background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(4px)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
            }}
        >
            <div style={{
                width: '100%', maxWidth: 760, maxHeight: '90vh',
                background: '#111318', borderRadius: 14,
                border: B.card, overflow: 'hidden',
                display: 'flex', flexDirection: 'column',
            }}>
                <div style={{ padding: '18px 24px', borderBottom: B.card, display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 14, fontWeight: 700, color: C.textPrimary, fontFamily: 'Syne' }}>
                            [{script.id}] {script.name}
                        </div>
                        <div style={{ fontSize: 11, color: C.w40, marginTop: 2 }}>
                            Okres: {dateFrom} — {dateTo}
                        </div>
                    </div>
                    <button onClick={onClose} style={{
                        background: 'none', border: 'none', color: C.w40,
                        cursor: 'pointer', fontSize: 18,
                    }}>×</button>
                </div>

                <div style={{ padding: '20px 24px', flex: 1, overflowY: 'auto' }}>
                    {phase === 'loading' && (
                        <div style={{ textAlign: 'center', padding: 40, color: C.w40 }}>
                            <Loader2 size={24} className="animate-spin" style={{ margin: '0 auto 10px' }} />
                            <div style={{ fontSize: 12 }}>Przygotowuję podgląd...</div>
                        </div>
                    )}

                    {phase === 'preview' && preview && (
                        <>
                            {error && (
                                <div style={{
                                    padding: '10px 14px', borderRadius: 8, marginBottom: 14,
                                    background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.3)',
                                    fontSize: 12, color: C.danger,
                                }}>{error}</div>
                            )}

                            {/* ── Params form ──────────────────────────────── */}
                            {params && (
                                <div style={{
                                    padding: '12px 16px', borderRadius: 8, marginBottom: 14,
                                    background: 'rgba(255,255,255,0.03)',
                                    border: '1px solid rgba(255,255,255,0.07)',
                                }}>
                                    <div style={{ fontSize: 10, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
                                        Parametry skryptu
                                    </div>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px 18px', alignItems: 'flex-end' }}>
                                        {Object.entries(params).map(([key, value]) => {
                                            const meta = PARAM_LABELS[key] || { label: key, type: 'number' }
                                            if (meta.type === 'hidden') return null
                                            const isMulti = meta.type === 'multiselect'
                                            return (
                                                <div key={key} style={{ minWidth: isMulti ? 260 : 140 }}>
                                                    <label style={{ fontSize: 10, color: C.w50, display: 'block', marginBottom: 3 }}>
                                                        {meta.label}
                                                    </label>
                                                    {meta.type === 'select' ? (
                                                        <select
                                                            value={value}
                                                            onChange={e => updateParam(key, e.target.value)}
                                                            style={{
                                                                background: C.w06, border: B.medium, borderRadius: 6,
                                                                padding: '5px 8px', fontSize: 12, color: C.textPrimary,
                                                                cursor: 'pointer', width: '100%',
                                                            }}
                                                        >
                                                            {(meta.options || []).map(o => (
                                                                <option key={o.value} value={o.value}>{o.label}</option>
                                                            ))}
                                                        </select>
                                                    ) : isMulti ? (
                                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                                                            {(meta.options || []).map(o => {
                                                                const current = Array.isArray(value) ? value : (value ? String(value).split(',').map(s => s.trim()) : [])
                                                                const checked = current.includes(o.value)
                                                                return (
                                                                    <label
                                                                        key={o.value}
                                                                        style={{
                                                                            padding: '3px 8px', borderRadius: 999, fontSize: 10,
                                                                            border: `1px solid ${checked ? 'rgba(79,142,247,0.5)' : C.w08}`,
                                                                            background: checked ? 'rgba(79,142,247,0.12)' : 'rgba(255,255,255,0.02)',
                                                                            color: checked ? C.accentBlue : C.w60,
                                                                            cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 4,
                                                                        }}
                                                                    >
                                                                        <input
                                                                            type="checkbox"
                                                                            checked={checked}
                                                                            onChange={() => {
                                                                                const next = checked
                                                                                    ? current.filter(x => x !== o.value)
                                                                                    : [...current, o.value]
                                                                                updateParam(key, next)
                                                                            }}
                                                                            style={{ display: 'none' }}
                                                                        />
                                                                        {o.label}
                                                                    </label>
                                                                )
                                                            })}
                                                        </div>
                                                    ) : (
                                                        <input
                                                            type="number"
                                                            value={value}
                                                            step={meta.step || 1}
                                                            min={0}
                                                            onChange={e => updateParam(key, meta.step && meta.step >= 1 ? parseInt(e.target.value) || 0 : parseFloat(e.target.value) || 0)}
                                                            style={{
                                                                background: C.w06, border: B.medium, borderRadius: 6,
                                                                padding: '5px 8px', fontSize: 12, color: C.textPrimary,
                                                                width: 90,
                                                            }}
                                                        />
                                                    )}
                                                </div>
                                            )
                                        })}
                                    </div>
                                    <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                                        {paramsEdited && (
                                            <button onClick={handleRerun} style={{
                                                padding: '5px 12px', borderRadius: 6, fontSize: 11, fontWeight: 600,
                                                background: 'rgba(79,142,247,0.15)', border: '1px solid rgba(79,142,247,0.3)',
                                                color: C.accentBlue, cursor: 'pointer',
                                            }}>
                                                Odśwież podgląd
                                            </button>
                                        )}
                                        <button onClick={handleSaveConfig} disabled={saving} style={{
                                            padding: '5px 12px', borderRadius: 6, fontSize: 11,
                                            background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.2)',
                                            color: C.success, cursor: saving ? 'wait' : 'pointer',
                                        }}>
                                            {saving ? 'Zapisuję...' : 'Zapisz jako domyślne dla klienta'}
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* N-gram tabs — only for D1 */}
                            {preview.items.some(i => i.metrics?.ngram_size) && (() => {
                                const counts = {}
                                preview.items.forEach(i => {
                                    const n = i.metrics?.ngram_size || 1
                                    counts[n] = (counts[n] || 0) + 1
                                })
                                return (
                                    <div style={{ display: 'flex', gap: 6, marginBottom: 14 }}>
                                        {[1, 2, 3, 4].map(n => (
                                            <button
                                                key={n}
                                                onClick={() => setNgramTab(n)}
                                                style={{
                                                    padding: '5px 14px', borderRadius: 999, fontSize: 11, fontWeight: 600,
                                                    border: ngramTab === n ? '1px solid rgba(123,92,224,0.5)' : '1px solid rgba(255,255,255,0.08)',
                                                    background: ngramTab === n ? 'rgba(123,92,224,0.15)' : 'transparent',
                                                    color: ngramTab === n ? '#7B5CE0' : counts[n] ? C.w60 : C.w25,
                                                    cursor: counts[n] ? 'pointer' : 'default',
                                                }}
                                            >
                                                {n}-gram {counts[n] ? `(${counts[n]})` : '(0)'}
                                            </button>
                                        ))}
                                    </div>
                                )
                            })()}

                            {preview.items.length === 0 ? (
                                <div style={{ textAlign: 'center', padding: 40 }}>
                                    <CheckCircle2 size={32} style={{ color: C.success, margin: '0 auto 10px' }} />
                                    <div style={{ fontSize: 13, color: C.textPrimary, marginBottom: 4 }}>
                                        Nic do zrobienia
                                    </div>
                                    <div style={{ fontSize: 11, color: C.w40 }}>
                                        Dla tego okresu i parametrów — brak wyników pasujących do kryteriów skryptu.
                                    </div>
                                </div>
                            ) : (
                                <>
                                    <div style={{
                                        padding: '10px 14px', borderRadius: 8, marginBottom: 14,
                                        background: 'rgba(79,142,247,0.08)', border: '1px solid rgba(79,142,247,0.25)',
                                        fontSize: 12, color: C.w70,
                                        display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
                                    }}>
                                        <div>
                                            <strong>{preview.total_matching}</strong> pasujących pozycji ·
                                            zaznaczone: <strong>{selectedIds.size}</strong> ·
                                            szacowana oszczędność ~<strong>{Math.round(totalSavings)} zł</strong>
                                        </div>
                                        <button onClick={toggleAll} style={{
                                            background: 'none', border: 'none', color: C.accentBlue,
                                            fontSize: 11, cursor: 'pointer', fontWeight: 600,
                                        }}>
                                            {selectedIds.size === preview.items.length ? 'Odznacz wszystkie' : 'Zaznacz wszystkie'}
                                        </button>
                                    </div>

                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                                        {/* Split items into sections based on match_source */}
                                        {(() => {
                                            // Filter by n-gram tab if items have ngram_size
                                            const hasNgram = preview.items.some(i => i.metrics?.ngram_size)
                                            const visibleItems = hasNgram
                                                ? preview.items.filter(i => (i.metrics?.ngram_size || 1) === ngramTab)
                                                : preview.items

                                            const hasSourceField = visibleItems.some(i => i.action_payload?.match_source)

                                            // Categorize: primary (executable) vs secondary (soft/alerts)
                                            const primarySources = new Set(['hard', 'search_action'])
                                            const alertSources = new Set(['pmax_alert'])
                                            const softSources = new Set(['soft'])

                                            const primaryItems = hasSourceField
                                                ? visibleItems.filter(i => primarySources.has(i.action_payload?.match_source) || !i.action_payload?.match_source)
                                                : visibleItems
                                            const softItems = hasSourceField ? visibleItems.filter(i => softSources.has(i.action_payload?.match_source)) : []
                                            const alertItems = hasSourceField ? visibleItems.filter(i => alertSources.has(i.action_payload?.match_source)) : []

                                            const renderItem = (item, { selectable = true } = {}) => {
                                                const selected = selectable && selectedIds.has(item.id)
                                                const isSoft = softSources.has(item.action_payload?.match_source)
                                                const isAlert = alertSources.has(item.action_payload?.match_source)
                                                const accentColor = isAlert ? C.w30 : isSoft ? C.warning : C.accentBlue
                                                const hasLocations = item.metrics?.locations?.length > 1
                                                return (
                                                    <div
                                                        key={item.id}
                                                        onClick={selectable && !hasLocations ? () => toggleItem(item.id) : undefined}
                                                        style={{
                                                            padding: '10px 14px', borderRadius: 8,
                                                            border: `1px solid ${selected ? accentColor + '60' : C.w08}`,
                                                            background: selected ? accentColor + '0A' : 'rgba(255,255,255,0.02)',
                                                            cursor: selectable && !hasLocations ? 'pointer' : 'default',
                                                            opacity: isAlert ? 0.6 : 1,
                                                            display: hasLocations ? 'block' : 'flex',
                                                            alignItems: hasLocations ? 'stretch' : 'center',
                                                            gap: 10,
                                                        }}
                                                    >
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                                        {selectable ? (
                                                            <div style={{
                                                                width: 16, height: 16, borderRadius: 4, flexShrink: 0,
                                                                border: `1.5px solid ${selected ? accentColor : C.w25}`,
                                                                background: selected ? accentColor : 'transparent',
                                                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                            }}>
                                                                {selected && <CheckCircle2 size={11} style={{ color: '#fff' }} />}
                                                            </div>
                                                        ) : (
                                                            <AlertTriangle size={14} style={{ color: C.w30, flexShrink: 0 }} />
                                                        )}
                                                        <div style={{ flex: 1, minWidth: 0 }}>
                                                            <div style={{ fontSize: 12, fontWeight: 600, color: isAlert ? C.w50 : C.textPrimary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                                {item.entity_name}
                                                            </div>
                                                            <div style={{ fontSize: 10, color: isSoft ? C.warning : isAlert ? C.w30 : C.w40, marginTop: 2 }}>
                                                                {item.campaign_name} · {item.reason}
                                                            </div>
                                                            {item.metrics?.example_terms?.length > 0 && (
                                                                <div style={{ fontSize: 9, color: C.w25, marginTop: 2 }}>
                                                                    np. {item.metrics.example_terms.slice(0, 3).join(', ')}
                                                                </div>
                                                            )}
                                                        </div>
                                                        <div style={{ fontSize: 11, color: C.w50, fontFamily: 'monospace', flexShrink: 0 }}>
                                                            {item.metrics?.conversions > 0 ? `${item.metrics.conversions} konw` : item.metrics?.cost_pln > 0 ? `~${Math.round(item.estimated_savings_pln)} zł` : ''}
                                                        </div>
                                                        {/* Ad group selector for B1 search_action items */}
                                                        {selectable && !item.action_payload?.ad_group_id && preview?.search_ad_groups?.length > 0 && item.action_payload?.match_source === 'search_action' && (
                                                            <select
                                                                value={itemOverrides[item.id]?.ad_group_id || ''}
                                                                onClick={e => e.stopPropagation()}
                                                                onChange={e => {
                                                                    e.stopPropagation()
                                                                    const agId = parseInt(e.target.value)
                                                                    if (agId) {
                                                                        setItemOverrides(prev => ({ ...prev, [item.id]: { ad_group_id: agId } }))
                                                                        if (!selectedIds.has(item.id)) toggleItem(item.id)
                                                                    }
                                                                }}
                                                                style={{
                                                                    background: C.w06, border: B.medium, borderRadius: 5,
                                                                    padding: '3px 6px', fontSize: 10, color: C.textPrimary,
                                                                    cursor: 'pointer', flexShrink: 0, maxWidth: 160,
                                                                }}
                                                            >
                                                                <option value="">-- ad group --</option>
                                                                {preview.search_ad_groups.map(ag => (
                                                                    <option key={ag.id} value={ag.id}>
                                                                        {ag.campaign_name} / {ag.name}
                                                                    </option>
                                                                ))}
                                                            </select>
                                                        )}
                                                    </div>
                                                    {hasLocations && (
                                                        <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px dashed rgba(255,255,255,0.06)' }}>
                                                            <div style={{ fontSize: 9, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                                                                Wybierz ktora lokalizacje zostawic (pozostale dostana EXACT negative)
                                                            </div>
                                                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                                                {item.metrics.locations.map((loc, idx) => {
                                                                    const overrideKeeper = itemOverrides[item.id]?.keeper_campaign_id
                                                                    const overrideKeeperAg = itemOverrides[item.id]?.keeper_ad_group_id ?? null
                                                                    const recKeeper = !overrideKeeper && loc.campaign_id === item.metrics.recommended_keeper?.campaign_id && (loc.ad_group_id ?? null) === (item.metrics.recommended_keeper?.ad_group_id ?? null)
                                                                    const manualKeeper = overrideKeeper === loc.campaign_id && (overrideKeeperAg ?? null) === (loc.ad_group_id ?? null)
                                                                    const isKeeper = recKeeper || manualKeeper
                                                                    return (
                                                                        <div
                                                                            key={idx}
                                                                            onClick={(e) => {
                                                                                e.stopPropagation()
                                                                                setItemOverrides(prev => ({
                                                                                    ...prev,
                                                                                    [item.id]: {
                                                                                        keeper_campaign_id: loc.campaign_id,
                                                                                        keeper_ad_group_id: loc.ad_group_id,
                                                                                    },
                                                                                }))
                                                                                if (!selectedIds.has(item.id)) toggleItem(item.id)
                                                                            }}
                                                                            style={{
                                                                                padding: '6px 10px', borderRadius: 6,
                                                                                border: `1px solid ${isKeeper ? 'rgba(74,222,128,0.5)' : 'rgba(255,255,255,0.06)'}`,
                                                                                background: isKeeper ? 'rgba(74,222,128,0.06)' : 'rgba(255,255,255,0.015)',
                                                                                cursor: 'pointer',
                                                                                display: 'flex', alignItems: 'center', gap: 10,
                                                                                fontSize: 10,
                                                                            }}
                                                                        >
                                                                            <div style={{
                                                                                width: 12, height: 12, borderRadius: '50%', flexShrink: 0,
                                                                                border: `1.5px solid ${isKeeper ? C.success : C.w25}`,
                                                                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                                            }}>
                                                                                {isKeeper && <div style={{ width: 6, height: 6, borderRadius: '50%', background: C.success }} />}
                                                                            </div>
                                                                            <div style={{ flex: 1, color: isKeeper ? C.textPrimary : C.w60, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                                                {loc.label}
                                                                            </div>
                                                                            <div style={{ color: C.w40, fontFamily: 'monospace', fontSize: 10 }}>
                                                                                {loc.clicks} clk · {Math.round(loc.cost_pln)} zl · {loc.conversions} konw
                                                                            </div>
                                                                            {recKeeper && !overrideKeeper && (
                                                                                <span style={{ fontSize: 8, color: C.success, fontWeight: 600, flexShrink: 0 }}>REKOMEND</span>
                                                                            )}
                                                                        </div>
                                                                    )
                                                                })}
                                                            </div>
                                                        </div>
                                                    )}
                                                    </div>
                                                )
                                            }

                                            return (
                                                <>
                                                    {primaryItems.length > 0 && hasSourceField && (softItems.length > 0 || alertItems.length > 0) && (
                                                        <div style={{ fontSize: 10, color: C.accentBlue, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4, marginTop: 4 }}>
                                                            Akcje ({primaryItems.length})
                                                        </div>
                                                    )}
                                                    {primaryItems.map(i => renderItem(i))}

                                                    {softItems.length > 0 && (
                                                        <>
                                                            <div style={{
                                                                fontSize: 10, color: C.warning, textTransform: 'uppercase',
                                                                letterSpacing: '0.08em', marginBottom: 4, marginTop: 12,
                                                                display: 'flex', alignItems: 'center', gap: 6,
                                                            }}>
                                                                Sugestie z innych kampanii ({softItems.length})
                                                                <span style={{ fontSize: 9, color: C.w30, textTransform: 'none', letterSpacing: 'normal' }}>
                                                                    — domyślnie odznaczone
                                                                </span>
                                                            </div>
                                                            {softItems.map(i => renderItem(i))}
                                                        </>
                                                    )}

                                                    {alertItems.length > 0 && (
                                                        <>
                                                            <div style={{
                                                                fontSize: 10, color: C.w40, textTransform: 'uppercase',
                                                                letterSpacing: '0.08em', marginBottom: 4, marginTop: 12,
                                                                display: 'flex', alignItems: 'center', gap: 6,
                                                            }}>
                                                                Alerty — tylko informacja ({alertItems.length})
                                                                <span style={{ fontSize: 9, color: C.w30, textTransform: 'none', letterSpacing: 'normal' }}>
                                                                    — brak auto-akcji
                                                                </span>
                                                            </div>
                                                            {alertItems.map(i => renderItem(i, { selectable: false }))}
                                                        </>
                                                    )}
                                                </>
                                            )
                                        })()}
                                    </div>
                                </>
                            )}
                        </>
                    )}

                    {phase === 'executing' && (
                        <div style={{ textAlign: 'center', padding: 40 }}>
                            <Loader2 size={24} className="animate-spin" style={{ margin: '0 auto 10px', color: C.accentBlue }} />
                            <div style={{ fontSize: 13, color: C.textPrimary, marginBottom: 4 }}>
                                Wykonuję skrypt...
                            </div>
                            <div style={{ fontSize: 11, color: C.w40 }}>
                                Nie zamykaj okna, to zajmie kilka sekund.
                            </div>
                        </div>
                    )}

                    {phase === 'result' && result && (
                        <div>
                            <div style={{
                                padding: '18px 22px', borderRadius: 10, marginBottom: 16,
                                background: result.applied > 0 ? 'rgba(74,222,128,0.08)' : 'rgba(248,113,113,0.08)',
                                border: `1px solid ${result.applied > 0 ? 'rgba(74,222,128,0.3)' : 'rgba(248,113,113,0.3)'}`,
                                textAlign: 'center',
                            }}>
                                <div style={{ fontSize: 24, fontWeight: 700, color: result.applied > 0 ? C.success : C.danger, fontFamily: 'Syne' }}>
                                    {result.applied} wykonanych
                                </div>
                                {result.failed > 0 && (
                                    <div style={{ fontSize: 12, color: C.danger, marginTop: 4 }}>
                                        {result.failed} nieudanych
                                    </div>
                                )}
                            </div>

                            {result.applied_items?.length > 0 && (
                                <div style={{ marginBottom: 14 }}>
                                    <div style={{ fontSize: 10, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
                                        Szczegóły zmian
                                    </div>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 260, overflowY: 'auto' }}>
                                        {result.applied_items.map((item, i) => (
                                            <div key={item.id || i} style={{
                                                padding: '8px 12px', borderRadius: 7,
                                                background: 'rgba(74,222,128,0.04)',
                                                border: '1px solid rgba(74,222,128,0.12)',
                                                fontSize: 12, color: C.w70,
                                                display: 'flex', alignItems: 'center', gap: 8,
                                            }}>
                                                <CheckCircle2 size={12} style={{ color: C.success, flexShrink: 0 }} />
                                                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                    {item.entity_name} <span style={{ color: C.w30 }}>· {item.campaign_name}</span>
                                                </span>
                                                {item.estimated_savings_pln > 0 && (
                                                    <span style={{ fontSize: 10, color: C.w40, fontFamily: 'monospace' }}>
                                                        ~{Math.round(item.estimated_savings_pln)} zł
                                                    </span>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {result.errors?.length > 0 && (
                                <div style={{ marginBottom: 14 }}>
                                    <div style={{ fontSize: 10, color: C.danger, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                                        Błędy
                                    </div>
                                    {result.errors.slice(0, 10).map((err, i) => (
                                        <div key={i} style={{
                                            padding: '6px 10px', borderRadius: 7, marginBottom: 3,
                                            background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)',
                                            fontSize: 11, color: C.danger,
                                        }}>{err}</div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>

                <div style={{ padding: '14px 24px', borderTop: B.card, display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
                    {phase === 'preview' && preview?.items?.length > 0 && (
                        <>
                            <button onClick={onClose} style={{
                                padding: '8px 18px', borderRadius: 7, fontSize: 12,
                                background: C.w05, border: B.medium, color: C.w60, cursor: 'pointer',
                            }}>Anuluj</button>
                            <button
                                onClick={handleExecute}
                                disabled={selectedIds.size === 0}
                                style={{
                                    padding: '8px 18px', borderRadius: 7, fontSize: 12, fontWeight: 600,
                                    background: selectedIds.size > 0 ? 'rgba(79,142,247,0.2)' : C.w05,
                                    border: `1px solid ${selectedIds.size > 0 ? 'rgba(79,142,247,0.4)' : C.w08}`,
                                    color: selectedIds.size > 0 ? C.accentBlue : C.w30,
                                    cursor: selectedIds.size > 0 ? 'pointer' : 'not-allowed',
                                }}
                            >
                                Wykonaj ({selectedIds.size})
                            </button>
                        </>
                    )}
                    {phase === 'preview' && preview?.items?.length === 0 && (
                        <button onClick={onClose} style={{
                            padding: '8px 18px', borderRadius: 7, fontSize: 12,
                            background: C.w05, border: B.medium, color: C.w60, cursor: 'pointer',
                        }}>Zamknij</button>
                    )}
                    {phase === 'result' && (
                        <>
                            <button onClick={() => navigate('/action-history')} style={{
                                padding: '8px 18px', borderRadius: 7, fontSize: 12,
                                background: 'rgba(79,142,247,0.12)', border: '1px solid rgba(79,142,247,0.3)',
                                color: C.accentBlue, cursor: 'pointer',
                            }}>Zobacz w historii</button>
                            <button onClick={onClose} style={{
                                padding: '8px 18px', borderRadius: 7, fontSize: 12,
                                background: C.w05, border: B.medium, color: C.w60, cursor: 'pointer',
                            }}>Zamknij</button>
                        </>
                    )}
                </div>
            </div>
        </div>
    )
}

// ── Main page ───────────────────────────────────────────────────────────────
export default function ScriptsPage() {
    const { selectedClientId, showToast } = useApp()
    const { filters, dateParams } = useFilter()
    const [catalog, setCatalog] = useState(null)
    const [counts, setCounts] = useState({}) // script_id -> { total, savings, loading }
    const [runningScript, setRunningScript] = useState(null)
    const [loading, setLoading] = useState(false)
    const [expandedCats, setExpandedCats] = useState(new Set(['waste_elimination']))
    const [refreshToken, setRefreshToken] = useState(0)
    const refreshCounts = useCallback(() => setRefreshToken(t => t + 1), [])

    // Load catalog once
    useEffect(() => {
        getScriptsCatalog()
            .then(setCatalog)
            .catch(err => console.error('[ScriptsPage] catalog error', err))
    }, [])

    // Fetch counts for all scripts (parallel dry-runs).
    // A `cancelled` flag prevents stale results from overwriting counts when
    // the user switches client or date range while a previous batch is in
    // flight. Matches the pattern used in DashboardPage.
    useEffect(() => {
        if (!selectedClientId || !catalog) return
        let cancelled = false
        setLoading(true)
        const allScripts = catalog.groups.flatMap(g => g.scripts)
        Promise.allSettled(
            allScripts.map(s => dryRunScript(s.id, {
                client_id: selectedClientId,
                date_from: dateParams.date_from,
                date_to: dateParams.date_to,
                params: {},
            }))
        ).then(results => {
            if (cancelled) return
            const next = {}
            allScripts.forEach((s, i) => {
                const r = results[i]
                if (r.status === 'fulfilled') {
                    next[s.id] = {
                        total: r.value.total_matching || 0,
                        savings: r.value.estimated_savings_pln || 0,
                    }
                } else {
                    next[s.id] = { total: 0, savings: 0, error: true }
                }
            })
            setCounts(next)
            setLoading(false)
        }).catch(() => {
            if (cancelled) return
            setLoading(false)
        })
        return () => { cancelled = true }
    }, [selectedClientId, catalog, dateParams, refreshToken])

    const toggleCat = (cat) => {
        setExpandedCats(prev => {
            const next = new Set(prev)
            if (next.has(cat)) next.delete(cat); else next.add(cat)
            return next
        })
    }

    const totalPending = useMemo(
        () => Object.values(counts).reduce((s, c) => s + (c.total || 0), 0),
        [counts]
    )
    const totalSavings = useMemo(
        () => Object.values(counts).reduce((s, c) => s + (c.savings || 0), 0),
        [counts]
    )

    if (!selectedClientId) return <EmptyState message="Wybierz klienta w sidebarze" />
    if (!catalog) return (
        <div style={{ padding: 40, textAlign: 'center', color: C.w40 }}>
            <Loader2 size={20} className="animate-spin" style={{ margin: '0 auto 8px' }} />
            <div style={{ fontSize: 12 }}>Ładowanie skryptów...</div>
        </div>
    )

    return (
        <div style={{ maxWidth: 1140 }}>
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 20 }}>
                <div>
                    <h1 style={{ ...T.pageTitle }}>Skrypty</h1>
                    <p style={{ ...T.pageSubtitle }}>
                        {typeof filters.period === 'number'
                            ? `Ostatnie ${filters.period} dni`
                            : `${filters.dateFrom} — ${filters.dateTo}`}
                        {totalPending > 0 && (
                            <> · <strong style={{ color: C.accentBlue }}>{totalPending} do wykonania</strong>
                            · ~<strong>{Math.round(totalSavings)} zł</strong> potencjalnej oszczędności</>
                        )}
                    </p>
                </div>
                <button onClick={refreshCounts} disabled={loading} style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '7px 14px', borderRadius: 7, fontSize: 12,
                    background: C.w05, border: B.medium, color: C.w60,
                    cursor: loading ? 'wait' : 'pointer',
                }}>
                    {loading ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
                    Odśwież
                </button>
            </div>

            {/* Categories */}
            {catalog.groups.map(group => {
                const meta = CATEGORY_META[group.category] || CATEGORY_META.waste_elimination
                const catTotal = group.scripts.reduce((s, sc) => s + (counts[sc.id]?.total || 0), 0)
                const expanded = expandedCats.has(group.category)
                return (
                    <div key={group.category} style={{ marginBottom: 14 }}>
                        <div
                            onClick={() => toggleCat(group.category)}
                            style={{
                                display: 'flex', alignItems: 'center', gap: 10,
                                padding: '10px 4px', cursor: 'pointer', userSelect: 'none',
                                marginBottom: expanded ? 10 : 0,
                            }}
                        >
                            <ChevronDown size={13} style={{
                                color: C.w40,
                                transform: expanded ? 'none' : 'rotate(-90deg)',
                                transition: 'transform 0.15s',
                            }} />
                            <meta.icon size={13} style={{ color: meta.color }} />
                            <span style={{ fontSize: 11, fontWeight: 600, color: C.w60, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                                {group.label}
                            </span>
                            {catTotal > 0 && (
                                <span style={{
                                    fontSize: 10, fontWeight: 600, color: meta.color,
                                    background: meta.color + '18',
                                    padding: '1px 8px', borderRadius: 999,
                                }}>
                                    {catTotal}
                                </span>
                            )}
                        </div>
                        {expanded && (
                            <div>
                                {group.scripts.map(script => (
                                    <ScriptTile
                                        key={script.id}
                                        script={script}
                                        count={counts[script.id]?.total || 0}
                                        savings={counts[script.id]?.savings || 0}
                                        loading={loading}
                                        onRun={() => setRunningScript(script)}
                                    />
                                ))}
                            </div>
                        )}
                    </div>
                )
            })}

            {/* Placeholder info for categories without scripts yet */}
            <div style={{
                marginTop: 24, padding: '14px 18px', borderRadius: 10,
                border: '1px dashed rgba(255,255,255,0.08)',
                background: 'rgba(255,255,255,0.02)',
                fontSize: 11, color: C.w40, lineHeight: 1.6,
            }}>
                <strong style={{ color: C.w60 }}>Sprint 1 — P0 scripts</strong>
                <br />
                Obecnie dostępny: A1 (Zero Conversion Waste). Kolejne w przygotowaniu:
                A2 (Irrelevant Dictionary), B1 (High-Converting Promotion), D1 (N-gram Waste),
                D3 (N-gram Audit Report). Zobacz{' '}
                <a href="/docs/specs/search-terms-scripts-research.md" style={{ color: C.accentBlue }}>
                    pełny katalog
                </a>.
            </div>

            {runningScript && (
                <RunModal
                    script={runningScript}
                    clientId={selectedClientId}
                    dateFrom={dateParams.date_from}
                    dateTo={dateParams.date_to}
                    onClose={() => setRunningScript(null)}
                    onDone={refreshCounts}
                    showToast={showToast}
                />
            )}
        </div>
    )
}

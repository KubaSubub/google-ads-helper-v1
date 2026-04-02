import { useState, useEffect, useCallback } from 'react'
import {
    AlertTriangle,
    Ban,
    Bell,
    Check,
    ChevronDown,
    ChevronUp,
    Loader2,
    Pause,
    PenLine,
    Play,
    Plus,
    RefreshCw,
    Settings2,
    Trash2,
    X,
    Zap,
} from 'lucide-react'
import { useApp } from '../../contexts/AppContext'
import { getRules, createRule, updateRule, deleteRule, dryRunRule, executeRule } from '../../api'
import EmptyState from '../../components/EmptyState'
import { C, T, S, R, B, PILL, MODAL, TOOLTIP_STYLE, SEVERITY, TRANSITION, FONT } from '../../constants/designTokens'

// ── Design tokens ──────────────────────────────────────────────────────

const CARD = {
    background: C.w03,
    border: B.card,
    borderRadius: 12,
}

const ENTITY_TYPES = [
    { value: 'keyword', label: 'Slowo kluczowe' },
    { value: 'campaign', label: 'Kampania' },
    { value: 'search_term', label: 'Fraza wyszukiwania' },
]

const ACTION_TYPES = [
    { value: 'PAUSE', label: 'Wstrzymaj', icon: Pause, color: C.warning },
    { value: 'ADD_NEGATIVE', label: 'Dodaj wykluczenie', icon: Ban, color: C.danger },
    { value: 'ALERT', label: 'Utworz alert', icon: Bell, color: C.accentBlue },
]

const OPERATORS = ['>', '<', '>=', '<=', '=', '!=', 'contains']

const FIELD_OPTIONS = {
    keyword: [
        { value: 'cost_micros', label: 'Koszt (micros)' },
        { value: 'clicks', label: 'Klikniecia' },
        { value: 'impressions', label: 'Wyswietlenia' },
        { value: 'conversions', label: 'Konwersje' },
        { value: 'ctr', label: 'CTR (%)' },
        { value: 'quality_score', label: 'Wynik jakosci' },
        { value: 'status', label: 'Status' },
        { value: 'text', label: 'Tekst' },
        { value: 'match_type', label: 'Typ dopasowania' },
    ],
    campaign: [
        { value: 'budget_micros', label: 'Budzet (micros)' },
        { value: 'status', label: 'Status' },
        { value: 'name', label: 'Nazwa' },
        { value: 'campaign_type', label: 'Typ kampanii' },
        { value: 'bidding_strategy', label: 'Strategia licytacji' },
    ],
    search_term: [
        { value: 'cost_micros', label: 'Koszt (micros)' },
        { value: 'clicks', label: 'Klikniecia' },
        { value: 'impressions', label: 'Wyswietlenia' },
        { value: 'conversions', label: 'Konwersje' },
        { value: 'ctr', label: 'CTR (%)' },
        { value: 'text', label: 'Tekst frazy' },
        { value: 'segment', label: 'Segment' },
    ],
}

// ── Subcomponents ──────────────────────────────────────────────────────

function ActionBadge({ actionType }) {
    const cfg = ACTION_TYPES.find(a => a.value === actionType) || ACTION_TYPES[2]
    const Icon = cfg.icon
    return (
        <span
            style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
                fontSize: 10,
                fontWeight: 600,
                padding: '2px 8px 2px 6px',
                borderRadius: 999,
                background: `${cfg.color}15`,
                border: `1px solid ${cfg.color}30`,
                color: cfg.color,
            }}
        >
            <Icon size={11} />
            {cfg.label}
        </span>
    )
}

function EntityBadge({ entityType }) {
    const cfg = ENTITY_TYPES.find(e => e.value === entityType)
    return (
        <span
            style={{
                fontSize: 10,
                fontWeight: 500,
                padding: '2px 8px',
                borderRadius: 999,
                background: C.w04,
                border: `1px solid ${C.w08}`,
                color: C.w50,
            }}
        >
            {cfg?.label || entityType}
        </span>
    )
}

function ConditionsSummary({ conditions }) {
    if (!conditions || conditions.length === 0) return null
    return (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
            {conditions.map((c, i) => (
                <span
                    key={i}
                    style={{
                        fontSize: 10,
                        padding: '1px 6px',
                        borderRadius: 4,
                        background: 'rgba(79,142,247,0.08)',
                        border: '1px solid rgba(79,142,247,0.15)',
                        color: C.textSecondary,
                        fontFamily: 'monospace',
                    }}
                >
                    {c.field} {c.op} {String(c.value)}
                </span>
            ))}
        </div>
    )
}

function ToggleSwitch({ enabled, onChange, disabled }) {
    return (
        <button
            onClick={onChange}
            disabled={disabled}
            style={{
                width: 36,
                height: 20,
                borderRadius: 10,
                border: 'none',
                background: enabled ? C.success : C.w12,
                cursor: disabled ? 'not-allowed' : 'pointer',
                position: 'relative',
                transition: 'background 0.2s',
                padding: 0,
                flexShrink: 0,
            }}
        >
            <div
                style={{
                    width: 16,
                    height: 16,
                    borderRadius: '50%',
                    background: 'white',
                    position: 'absolute',
                    top: 2,
                    left: enabled ? 18 : 2,
                    transition: 'left 0.2s',
                }}
            />
        </button>
    )
}

function SelectInput({ value, onChange, options, placeholder, style: extraStyle }) {
    return (
        <select
            value={value}
            onChange={e => onChange(e.target.value)}
            style={{
                background: C.w05,
                border: B.medium,
                borderRadius: 8,
                padding: '8px 12px',
                fontSize: 13,
                color: C.textPrimary,
                outline: 'none',
                cursor: 'pointer',
                ...extraStyle,
            }}
        >
            {placeholder && <option value="">{placeholder}</option>}
            {options.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
            ))}
        </select>
    )
}

function TextInput({ value, onChange, placeholder, style: extraStyle, type = 'text' }) {
    return (
        <input
            type={type}
            value={value}
            onChange={e => onChange(e.target.value)}
            placeholder={placeholder}
            style={{
                background: C.w05,
                border: B.medium,
                borderRadius: 8,
                padding: '8px 12px',
                fontSize: 13,
                color: C.textPrimary,
                outline: 'none',
                width: '100%',
                ...extraStyle,
            }}
        />
    )
}

function PillButton({ active, onClick, children }) {
    return (
        <button
            onClick={onClick}
            style={{
                padding: '6px 16px',
                borderRadius: 999,
                fontSize: 12,
                fontWeight: active ? 500 : 400,
                border: `1px solid ${active ? C.accentBlue : C.w10}`,
                background: active ? C.accentBlueBg : 'transparent',
                color: active ? 'white' : C.textPlaceholder,
                cursor: 'pointer',
                transition: 'all 0.15s',
                whiteSpace: 'nowrap',
            }}
        >
            {children}
        </button>
    )
}

// ── Condition Row Builder ──────────────────────────────────────────────

function ConditionRow({ condition, index, entityType, onChange, onRemove }) {
    const fields = FIELD_OPTIONS[entityType] || []
    return (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <SelectInput
                value={condition.field}
                onChange={v => onChange(index, { ...condition, field: v })}
                options={fields}
                placeholder="Pole..."
                style={{ flex: '1 1 140px', minWidth: 120 }}
            />
            <SelectInput
                value={condition.op}
                onChange={v => onChange(index, { ...condition, op: v })}
                options={OPERATORS.map(o => ({ value: o, label: o }))}
                placeholder="Op..."
                style={{ flex: '0 0 80px', minWidth: 70 }}
            />
            <TextInput
                value={condition.value}
                onChange={v => onChange(index, { ...condition, value: v })}
                placeholder="Wartosc..."
                style={{ flex: '1 1 120px', minWidth: 100 }}
            />
            <button
                onClick={() => onRemove(index)}
                style={{
                    padding: 6,
                    borderRadius: 6,
                    border: '1px solid rgba(248,113,113,0.2)',
                    background: C.dangerBg,
                    color: C.danger,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    flexShrink: 0,
                }}
                title="Usun warunek"
            >
                <X size={14} />
            </button>
        </div>
    )
}

// ── Create / Edit Form ─────────────────────────────────────────────────

function RuleForm({ initialData, onSave, onCancel, saving }) {
    const [name, setName] = useState(initialData?.name || '')
    const [entityType, setEntityType] = useState(initialData?.entity_type || 'keyword')
    const [actionType, setActionType] = useState(initialData?.action_type || 'PAUSE')
    const [conditions, setConditions] = useState(
        initialData?.conditions?.length > 0
            ? initialData.conditions
            : [{ field: '', op: '>', value: '' }]
    )
    const [intervalHours, setIntervalHours] = useState(initialData?.check_interval_hours || 24)

    const handleConditionChange = (idx, newCond) => {
        setConditions(prev => prev.map((c, i) => i === idx ? newCond : c))
    }

    const addCondition = () => {
        setConditions(prev => [...prev, { field: '', op: '>', value: '' }])
    }

    const removeCondition = (idx) => {
        setConditions(prev => prev.filter((_, i) => i !== idx))
    }

    const handleSubmit = () => {
        if (!name.trim()) return
        const validConditions = conditions.filter(c => c.field && c.op && c.value !== '')
        if (validConditions.length === 0) return

        // Cast numeric values
        const parsed = validConditions.map(c => {
            const numVal = Number(c.value)
            return {
                field: c.field,
                op: c.op,
                value: !isNaN(numVal) && c.op !== 'contains' ? numVal : c.value,
            }
        })

        onSave({
            name: name.trim(),
            entity_type: entityType,
            action_type: actionType,
            conditions: parsed,
            check_interval_hours: intervalHours,
            enabled: initialData?.enabled !== undefined ? initialData.enabled : true,
        })
    }

    const isValid = name.trim() && conditions.some(c => c.field && c.op && c.value !== '')

    return (
        <div style={{ ...CARD, padding: 20, marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <h3 style={{ fontSize: 15, fontWeight: 600, color: C.textPrimary, margin: 0 }}>
                    {initialData ? 'Edytuj regule' : 'Nowa regula'}
                </h3>
                <button
                    onClick={onCancel}
                    style={{
                        padding: 6,
                        borderRadius: 6,
                        border: `1px solid ${C.w08}`,
                        background: 'transparent',
                        color: C.w40,
                        cursor: 'pointer',
                    }}
                >
                    <X size={16} />
                </button>
            </div>

            {/* Name */}
            <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 11, color: C.w40, marginBottom: 4, display: 'block' }}>
                    Nazwa reguly
                </label>
                <TextInput value={name} onChange={setName} placeholder="np. Wstrzymaj drogie slowa bez konwersji" />
            </div>

            {/* Entity type + Action type row */}
            <div style={{ display: 'flex', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
                <div style={{ flex: '1 1 200px' }}>
                    <label style={{ fontSize: 11, color: C.w40, marginBottom: 4, display: 'block' }}>
                        Typ encji
                    </label>
                    <SelectInput
                        value={entityType}
                        onChange={v => {
                            setEntityType(v)
                            setConditions([{ field: '', op: '>', value: '' }])
                        }}
                        options={ENTITY_TYPES}
                        style={{ width: '100%' }}
                    />
                </div>
                <div style={{ flex: '1 1 200px' }}>
                    <label style={{ fontSize: 11, color: C.w40, marginBottom: 4, display: 'block' }}>
                        Akcja
                    </label>
                    <SelectInput
                        value={actionType}
                        onChange={setActionType}
                        options={ACTION_TYPES.map(a => ({ value: a.value, label: a.label }))}
                        style={{ width: '100%' }}
                    />
                </div>
                <div style={{ flex: '0 0 120px' }}>
                    <label style={{ fontSize: 11, color: C.w40, marginBottom: 4, display: 'block' }}>
                        Interwal (h)
                    </label>
                    <TextInput
                        type="number"
                        value={intervalHours}
                        onChange={v => setIntervalHours(Math.max(1, parseInt(v) || 24))}
                        placeholder="24"
                        style={{ width: '100%' }}
                    />
                </div>
            </div>

            {/* Conditions */}
            <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 11, color: C.w40, marginBottom: 8, display: 'block' }}>
                    Warunki
                </label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {conditions.map((c, i) => (
                        <ConditionRow
                            key={i}
                            condition={c}
                            index={i}
                            entityType={entityType}
                            onChange={handleConditionChange}
                            onRemove={removeCondition}
                        />
                    ))}
                </div>
                <button
                    onClick={addCondition}
                    style={{
                        marginTop: 8,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                        padding: '6px 12px',
                        borderRadius: 999,
                        fontSize: 11,
                        fontWeight: 500,
                        border: `1px solid ${C.w08}`,
                        background: C.w03,
                        color: C.w50,
                        cursor: 'pointer',
                    }}
                >
                    <Plus size={12} /> Dodaj warunek
                </button>
            </div>

            {/* Submit */}
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                <button
                    onClick={onCancel}
                    style={{
                        padding: '8px 20px',
                        borderRadius: 999,
                        fontSize: 12,
                        fontWeight: 500,
                        border: B.medium,
                        background: 'transparent',
                        color: C.w50,
                        cursor: 'pointer',
                    }}
                >
                    Anuluj
                </button>
                <button
                    onClick={handleSubmit}
                    disabled={!isValid || saving}
                    style={{
                        padding: '8px 20px',
                        borderRadius: 999,
                        fontSize: 12,
                        fontWeight: 500,
                        border: '1px solid #4F8EF7',
                        background: C.accentBlueBg,
                        color: isValid && !saving ? 'white' : C.w30,
                        cursor: isValid && !saving ? 'pointer' : 'not-allowed',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                    }}
                >
                    {saving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                    {initialData ? 'Zapisz zmiany' : 'Utworz regule'}
                </button>
            </div>
        </div>
    )
}

// ── Dry Run Results ────────────────────────────────────────────────────

function DryRunResults({ result, onClose }) {
    if (!result) return null
    const details = result.details || []
    return (
        <div style={{ ...CARD, padding: 16, marginTop: 8, borderColor: C.infoBorder }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: C.accentBlue }}>
                    {result.dry_run ? 'Podglad (dry run)' : 'Wynik wykonania'} — {result.matches_found} dopasowani{result.matches_found === 1 ? 'e' : result.matches_found < 5 ? 'a' : ''}
                    {!result.dry_run && `, ${result.actions_taken} akcji`}
                </span>
                <button
                    onClick={onClose}
                    style={{ padding: 4, background: 'transparent', border: 'none', color: C.w40, cursor: 'pointer' }}
                >
                    <X size={14} />
                </button>
            </div>
            {details.length === 0 ? (
                <p style={{ fontSize: 12, color: C.textMuted, margin: 0 }}>Brak dopasowanych encji.</p>
            ) : (
                <div style={{ maxHeight: 240, overflowY: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr>
                                {['ID', 'Nazwa', 'Status', 'Koszt', 'Klik.', 'Wynik'].map(h => (
                                    <th
                                        key={h}
                                        style={{
                                            fontSize: 10,
                                            fontWeight: 500,
                                            color: C.textMuted,
                                            textTransform: 'uppercase',
                                            textAlign: 'left',
                                            padding: '4px 8px',
                                            borderBottom: B.subtle,
                                        }}
                                    >
                                        {h}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {details.map((d, i) => (
                                <tr key={i}>
                                    <td style={tdStyle}>{d.id}</td>
                                    <td style={{ ...tdStyle, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.name}</td>
                                    <td style={tdStyle}>{d.status || '-'}</td>
                                    <td style={tdStyle}>{d.cost_micros != null ? (d.cost_micros / 1_000_000).toFixed(2) : '-'}</td>
                                    <td style={tdStyle}>{d.clicks ?? '-'}</td>
                                    <td style={tdStyle}>
                                        <span style={{
                                            fontSize: 10,
                                            padding: '1px 6px',
                                            borderRadius: 4,
                                            background: d.action_result === 'dry_run' ? C.infoBg : d.action_result?.startsWith?.('error') ? C.dangerBg : C.successBg,
                                            color: d.action_result === 'dry_run' ? C.accentBlue : d.action_result?.startsWith?.('error') ? C.danger : C.success,
                                        }}>
                                            {d.action_result || 'dry_run'}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    )
}

const tdStyle = { fontSize: 12, color: C.w60, padding: '6px 8px', borderBottom: `1px solid ${C.w04}` }

// ── Rule Card ──────────────────────────────────────────────────────────

function RuleCard({ rule, onToggle, onEdit, onDelete, onDryRun, onExecute, dryRunResult, onClearResult, actionLoading }) {
    const [expanded, setExpanded] = useState(false)

    const lastRun = rule.last_run_at
        ? new Date(rule.last_run_at).toLocaleString('pl-PL', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
        : 'Nigdy'

    return (
        <div style={{ ...CARD, padding: '14px 18px', opacity: rule.enabled ? 1 : 0.65, transition: 'opacity 0.2s' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
                {/* Toggle */}
                <div style={{ paddingTop: 2 }}>
                    <ToggleSwitch enabled={rule.enabled} onChange={() => onToggle(rule)} />
                </div>

                {/* Content */}
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
                        <span style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary }}>{rule.name}</span>
                        <EntityBadge entityType={rule.entity_type} />
                        <ActionBadge actionType={rule.action_type} />
                    </div>

                    <ConditionsSummary conditions={rule.conditions} />

                    <div style={{ display: 'flex', gap: 16, marginTop: 8, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: 11, color: C.textMuted }}>
                            Ostatnie uruchomienie: {lastRun}
                        </span>
                        <span style={{ fontSize: 11, color: C.textMuted }}>
                            Dopasowania: {rule.matches_last_run ?? 0}
                        </span>
                        <span style={{ fontSize: 11, color: C.textMuted }}>
                            Interwal: {rule.check_interval_hours}h
                        </span>
                    </div>
                </div>

                {/* Action buttons */}
                <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexShrink: 0 }}>
                    <button
                        onClick={() => onDryRun(rule)}
                        disabled={actionLoading}
                        style={iconBtnStyle(C.accentBlue)}
                        title="Dry run (podglad)"
                    >
                        {actionLoading ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                    </button>
                    <button
                        onClick={() => onExecute(rule)}
                        disabled={actionLoading}
                        style={iconBtnStyle(C.success)}
                        title="Wykonaj"
                    >
                        <Zap size={14} />
                    </button>
                    <button
                        onClick={() => onEdit(rule)}
                        style={iconBtnStyle(C.w40)}
                        title="Edytuj"
                    >
                        <PenLine size={14} />
                    </button>
                    <button
                        onClick={() => onDelete(rule)}
                        style={iconBtnStyle(C.danger)}
                        title="Usun"
                    >
                        <Trash2 size={14} />
                    </button>
                    <button
                        onClick={() => setExpanded(p => !p)}
                        style={{ ...iconBtnStyle(C.w30), border: 'none' }}
                        title={expanded ? 'Zwin' : 'Rozwin'}
                    >
                        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </button>
                </div>
            </div>

            {/* Expanded: show conditions detail */}
            {expanded && (
                <div style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${C.w05}` }}>
                    <div style={{ fontSize: 11, color: C.textMuted, marginBottom: 6 }}>Warunki:</div>
                    {(rule.conditions || []).map((c, i) => (
                        <div key={i} style={{ fontSize: 12, color: C.textSecondary, marginBottom: 2, fontFamily: 'monospace' }}>
                            {i > 0 && <span style={{ color: C.w25 }}>AND </span>}
                            {c.field} <span style={{ color: C.accentBlue }}>{c.op}</span> {String(c.value)}
                        </div>
                    ))}
                    {rule.action_params && Object.keys(rule.action_params).length > 0 && (
                        <>
                            <div style={{ fontSize: 11, color: C.textMuted, marginTop: 8, marginBottom: 4 }}>Parametry akcji:</div>
                            <div style={{ fontSize: 12, color: C.w50, fontFamily: 'monospace' }}>
                                {JSON.stringify(rule.action_params)}
                            </div>
                        </>
                    )}
                </div>
            )}

            {/* Dry run results */}
            {dryRunResult && <DryRunResults result={dryRunResult} onClose={onClearResult} />}
        </div>
    )
}

function iconBtnStyle(color) {
    return {
        padding: 6,
        borderRadius: 6,
        border: `1px solid ${color}25`,
        background: `${color}10`,
        color,
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        transition: 'all 0.15s',
    }
}

// ── Main Page ──────────────────────────────────────────────────────────

export default function RulesPage() {
    const { selectedClientId, showToast } = useApp()

    const [rules, setRules] = useState([])
    const [loading, setLoading] = useState(true)
    const [showForm, setShowForm] = useState(false)
    const [editingRule, setEditingRule] = useState(null)
    const [saving, setSaving] = useState(false)
    const [actionLoading, setActionLoading] = useState(null) // rule id
    const [dryRunResults, setDryRunResults] = useState({}) // { [ruleId]: result }
    const [filter, setFilter] = useState('all') // 'all' | 'enabled' | 'disabled'

    const fetchRules = useCallback(async () => {
        if (!selectedClientId) return
        setLoading(true)
        try {
            const data = await getRules(selectedClientId)
            setRules(data?.rules || [])
        } catch (err) {
            showToast?.('Blad ladowania regul', 'error')
        } finally {
            setLoading(false)
        }
    }, [selectedClientId, showToast])

    useEffect(() => {
        fetchRules()
    }, [fetchRules])

    const handleCreate = async (data) => {
        setSaving(true)
        try {
            await createRule({ ...data, client_id: selectedClientId })
            showToast?.('Regula utworzona', 'success')
            setShowForm(false)
            fetchRules()
        } catch (err) {
            showToast?.(err.message || 'Blad tworzenia reguly', 'error')
        } finally {
            setSaving(false)
        }
    }

    const handleUpdate = async (data) => {
        if (!editingRule) return
        setSaving(true)
        try {
            await updateRule(editingRule.id, data, selectedClientId)
            showToast?.('Regula zaktualizowana', 'success')
            setEditingRule(null)
            fetchRules()
        } catch (err) {
            showToast?.(err.message || 'Blad aktualizacji reguly', 'error')
        } finally {
            setSaving(false)
        }
    }

    const handleToggle = async (rule) => {
        try {
            await updateRule(rule.id, { enabled: !rule.enabled }, selectedClientId)
            setRules(prev => prev.map(r => r.id === rule.id ? { ...r, enabled: !r.enabled } : r))
        } catch (err) {
            showToast?.(err.message || 'Blad zmiany statusu', 'error')
        }
    }

    const handleDelete = async (rule) => {
        if (!confirm(`Usunac regule "${rule.name}"?`)) return
        try {
            await deleteRule(rule.id, selectedClientId)
            showToast?.('Regula usunieta', 'success')
            setRules(prev => prev.filter(r => r.id !== rule.id))
        } catch (err) {
            showToast?.(err.message || 'Blad usuwania reguly', 'error')
        }
    }

    const handleDryRun = async (rule) => {
        setActionLoading(rule.id)
        try {
            const result = await dryRunRule(rule.id, selectedClientId)
            setDryRunResults(prev => ({ ...prev, [rule.id]: result }))
        } catch (err) {
            showToast?.(err.message || 'Blad dry run', 'error')
        } finally {
            setActionLoading(null)
        }
    }

    const handleExecute = async (rule) => {
        if (!confirm(`Wykonac regule "${rule.name}"? Akcje zostana zastosowane na prawdziwych danych.`)) return
        setActionLoading(rule.id)
        try {
            const result = await executeRule(rule.id, selectedClientId)
            setDryRunResults(prev => ({ ...prev, [rule.id]: result }))
            showToast?.(`Wykonano: ${result.actions_taken} akcji na ${result.matches_found} dopasowaniach`, 'success')
            fetchRules()
        } catch (err) {
            showToast?.(err.message || 'Blad wykonania reguly', 'error')
        } finally {
            setActionLoading(null)
        }
    }

    const filteredRules = rules.filter(r => {
        if (filter === 'enabled') return r.enabled
        if (filter === 'disabled') return !r.enabled
        return true
    })

    const enabledCount = rules.filter(r => r.enabled).length

    if (!selectedClientId) {
        return (
            <div style={{ padding: 24 }}>
                <EmptyState message="Wybierz klienta, aby zarzadzac regulami" icon={Settings2} />
            </div>
        )
    }

    return (
        <div style={{ padding: 24, maxWidth: 960 }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, fontFamily: 'Syne', color: C.textPrimary, margin: 0 }}>
                        Reguly automatyczne
                    </h1>
                    <p style={{ fontSize: 13, color: C.w40, margin: '4px 0 0 0' }}>
                        Automatyzuj powtarzalne dzialania optymalizacyjne
                    </p>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                    <button
                        onClick={fetchRules}
                        disabled={loading}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 6,
                            padding: '8px 16px',
                            borderRadius: 999,
                            fontSize: 12,
                            fontWeight: 500,
                            border: B.medium,
                            background: C.w04,
                            color: C.w60,
                            cursor: loading ? 'not-allowed' : 'pointer',
                        }}
                    >
                        {loading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                        Odswiez
                    </button>
                    <button
                        onClick={() => { setShowForm(true); setEditingRule(null) }}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 6,
                            padding: '8px 16px',
                            borderRadius: 999,
                            fontSize: 12,
                            fontWeight: 500,
                            border: '1px solid #4F8EF7',
                            background: C.accentBlueBg,
                            color: 'white',
                            cursor: 'pointer',
                        }}
                    >
                        <Plus size={14} />
                        Nowa regula
                    </button>
                </div>
            </div>

            {/* Stats bar */}
            {rules.length > 0 && (
                <div style={{ ...CARD, padding: '12px 18px', marginBottom: 16, display: 'flex', gap: 24, flexWrap: 'wrap' }}>
                    <div>
                        <span style={{ fontSize: 20, fontWeight: 700, fontFamily: 'Syne', color: C.textPrimary }}>{rules.length}</span>
                        <span style={{ fontSize: 11, color: C.textMuted, marginLeft: 6 }}>regul</span>
                    </div>
                    <div>
                        <span style={{ fontSize: 20, fontWeight: 700, fontFamily: 'Syne', color: C.success }}>{enabledCount}</span>
                        <span style={{ fontSize: 11, color: C.textMuted, marginLeft: 6 }}>aktywnych</span>
                    </div>
                    <div>
                        <span style={{ fontSize: 20, fontWeight: 700, fontFamily: 'Syne', color: C.w40 }}>{rules.length - enabledCount}</span>
                        <span style={{ fontSize: 11, color: C.textMuted, marginLeft: 6 }}>wstrzymanych</span>
                    </div>
                </div>
            )}

            {/* Create form */}
            {showForm && !editingRule && (
                <RuleForm
                    onSave={handleCreate}
                    onCancel={() => setShowForm(false)}
                    saving={saving}
                />
            )}

            {/* Edit form */}
            {editingRule && (
                <RuleForm
                    initialData={editingRule}
                    onSave={handleUpdate}
                    onCancel={() => setEditingRule(null)}
                    saving={saving}
                />
            )}

            {/* Filters */}
            {rules.length > 0 && (
                <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
                    <PillButton active={filter === 'all'} onClick={() => setFilter('all')}>
                        Wszystkie ({rules.length})
                    </PillButton>
                    <PillButton active={filter === 'enabled'} onClick={() => setFilter('enabled')}>
                        Aktywne ({enabledCount})
                    </PillButton>
                    <PillButton active={filter === 'disabled'} onClick={() => setFilter('disabled')}>
                        Wstrzymane ({rules.length - enabledCount})
                    </PillButton>
                </div>
            )}

            {/* Loading */}
            {loading && (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 60 }}>
                    <Loader2 size={24} className="animate-spin" style={{ color: C.w30 }} />
                    <span style={{ marginLeft: 10, fontSize: 13, color: C.textMuted }}>
                        Ladowanie regul...
                    </span>
                </div>
            )}

            {/* Empty state */}
            {!loading && rules.length === 0 && !showForm && (
                <EmptyState
                    message="Brak regul automatycznych. Utworz pierwsza regule, aby zautomatyzowac optymalizacje."
                    icon={Settings2}
                />
            )}

            {/* Rules list */}
            {!loading && filteredRules.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {filteredRules.map(rule => (
                        <RuleCard
                            key={rule.id}
                            rule={rule}
                            onToggle={handleToggle}
                            onEdit={r => { setEditingRule(r); setShowForm(false) }}
                            onDelete={handleDelete}
                            onDryRun={handleDryRun}
                            onExecute={handleExecute}
                            dryRunResult={dryRunResults[rule.id]}
                            onClearResult={() => setDryRunResults(prev => { const next = { ...prev }; delete next[rule.id]; return next })}
                            actionLoading={actionLoading === rule.id}
                        />
                    ))}
                </div>
            )}

            {/* No matches for filter */}
            {!loading && rules.length > 0 && filteredRules.length === 0 && (
                <EmptyState message="Brak regul pasujacych do filtru" icon={Settings2} />
            )}
        </div>
    )
}

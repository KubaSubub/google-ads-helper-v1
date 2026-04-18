import { useEffect, useState, useCallback } from 'react'
import { useLocation } from 'react-router-dom'
import { AlertTriangle, BarChart3, Building2, Calendar, CheckCircle, Clock, Compass, FileText, Lightbulb, Loader2, MessageSquare, Plus, RefreshCw, RotateCcw, Save, ShieldAlert, Sparkles, Target, Trash2, X, XCircle } from 'lucide-react'

import api, { getClient, updateClient, getMccAccounts, getSyncLogs, getScheduledSync, updateScheduledSync, syncClient } from '../api'
import EmptyState from '../components/EmptyState'
import ConversionGoalsSection from '../components/settings/ConversionGoalsSection'
import { useApp } from '../contexts/AppContext'
import { C, T, S, R, B, PILL, MODAL, TOOLTIP_STYLE, SEVERITY, TRANSITION, FONT } from '../constants/designTokens'

const SAFETY_FIELDS = [
    { key: 'MAX_BID_CHANGE_PCT', label: 'Max zmiana stawki (%)', unit: '%', multiply: 100, tooltip: 'Maksymalna jednorazowa zmiana stawki CPC w procentach', min: 1, max: 100 },
    { key: 'MAX_BUDGET_CHANGE_PCT', label: 'Max zmiana budżetu (%)', unit: '%', multiply: 100, tooltip: 'Maksymalna jednorazowa zmiana budżetu kampanii', min: 1, max: 100 },
    { key: 'MIN_BID_USD', label: 'Min stawka', unit: '', multiply: 1, tooltip: 'Minimalna dopuszczalna stawka CPC', min: 0.01, max: 100 },
    { key: 'MAX_BID_USD', label: 'Max stawka', unit: '', multiply: 1, tooltip: 'Maksymalna dopuszczalna stawka CPC', min: 0.01, max: 1000 },
    { key: 'MAX_KEYWORD_PAUSE_PCT', label: 'Max pause keywords/dzień (%)', unit: '%', multiply: 100, tooltip: 'Max procent słów kluczowych wstrzymanych w jednym dniu na kampanię', min: 1, max: 50 },
    { key: 'MAX_NEGATIVES_PER_DAY', label: 'Max negatywów/dzień', unit: '', multiply: 1, tooltip: 'Limit dodawanych negatywnych fraz dziennie', min: 1, max: 500 },
]

const GLOBAL_DEFAULTS = {
    MAX_BID_CHANGE_PCT: 0.50,
    MAX_BUDGET_CHANGE_PCT: 0.30,
    MIN_BID_USD: 0.10,
    MAX_BID_USD: 100.00,
    MAX_KEYWORD_PAUSE_PCT: 0.20,
    MAX_NEGATIVES_PER_DAY: 100,
}

const INTERVAL_OPTIONS = [
    { value: 1, label: 'Co 1 godzinę' },
    { value: 3, label: 'Co 3 godziny' },
    { value: 6, label: 'Co 6 godzin' },
    { value: 12, label: 'Co 12 godzin' },
    { value: 24, label: 'Co 24 godziny' },
    { value: 48, label: 'Co 2 dni' },
    { value: 168, label: 'Co 7 dni' },
]

function formatDate(dateStr) {
    if (!dateStr) return null
    const d = new Date(dateStr)
    return d.toLocaleString('pl-PL', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatDuration(startStr, endStr) {
    if (!startStr || !endStr) return null
    const ms = new Date(endStr) - new Date(startStr)
    if (ms < 1000) return '<1s'
    const s = Math.floor(ms / 1000)
    if (s < 60) return `${s}s`
    const m = Math.floor(s / 60)
    const rs = s % 60
    return `${m}m ${rs}s`
}

function SectionGroupHeader({ label }) {
    return (
        <div
            data-testid={`section-group-${label.toLowerCase().replace(/\s+/g, '-')}`}
            style={{
                display: 'flex', alignItems: 'center', gap: 10,
                fontSize: 10, fontWeight: 600, color: 'rgba(255,255,255,0.35)',
                textTransform: 'uppercase', letterSpacing: '0.12em',
                margin: '24px 0 8px',
            }}
        >
            <span>{label}</span>
            <div style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.07)' }} />
        </div>
    )
}

export default function Settings() {
    const { selectedClientId, showToast, refreshClients } = useApp()
    const [formData, setFormData] = useState(null)
    const [originalData, setOriginalData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [mccAccounts, setMccAccounts] = useState(null)
    const [saving, setSaving] = useState(false)
    const [resetting, setResetting] = useState(false)
    const [resetConfirmation, setResetConfirmation] = useState('')
    const [error, setError] = useState(null)
    const [newCompetitor, setNewCompetitor] = useState('')
    const [newBrandTerm, setNewBrandTerm] = useState('')
    const [lastSync, setLastSync] = useState(null)
    const [syncSchedule, setSyncSchedule] = useState(null)
    const [syncScheduleSaving, setSyncScheduleSaving] = useState(false)
    // New lesson form state (win/loss/test journal)
    const [newLesson, setNewLesson] = useState({ type: 'win', title: '', description: '', date: '' })

    useEffect(() => {
        if (selectedClientId) {
            loadClient()
            loadSyncInfo()
        }
    }, [selectedClientId])

    async function loadClient() {
        setLoading(true)
        setError(null)
        try {
            const data = await getClient(selectedClientId)
            setFormData(data)
            setOriginalData(JSON.parse(JSON.stringify(data)))
            setResetConfirmation('')
            if (data.google_customer_id) {
                getMccAccounts(data.google_customer_id.replace(/-/g, ''))
                    .then(setMccAccounts)
                    .catch(() => setMccAccounts(null))
            }
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    async function loadSyncInfo() {
        try {
            const [logs, schedule] = await Promise.all([
                getSyncLogs(selectedClientId, 1).catch(() => []),
                getScheduledSync(selectedClientId).catch(() => null),
            ])
            setLastSync(Array.isArray(logs) && logs.length > 0 ? logs[0] : null)
            setSyncSchedule(schedule)
        } catch {
            // Sync info is non-critical
        }
    }

    const [validationErrors, setValidationErrors] = useState({})

    const isDirty = formData && originalData && JSON.stringify(formData) !== JSON.stringify(originalData)

    const validate = useCallback((data) => {
        if (!data) return {}
        const errors = {}

        if (!data.name || !data.name.trim()) {
            errors.name = 'Nazwa klienta jest wymagana'
        }

        const minRoas = data.business_rules?.min_roas
        if (minRoas != null && minRoas !== '' && (minRoas < 0 || minRoas > 100)) {
            errors.min_roas = 'ROAS: 0–100'
        }

        const maxBudget = data.business_rules?.max_daily_budget
        if (maxBudget != null && maxBudget !== '' && (maxBudget < 0 || maxBudget > 100000)) {
            errors.max_daily_budget = 'Budżet: 0–100 000'
        }

        const sl = data.business_rules?.safety_limits || {}
        for (const { key, multiply, min, max } of SAFETY_FIELDS) {
            const raw = sl[key]
            if (raw == null) continue
            const display = raw * multiply
            if (display < min || display > max) {
                errors[`safety_${key}`] = `${min}–${max}`
            }
        }

        return errors
    }, [])

    useEffect(() => {
        if (formData) {
            setValidationErrors(validate(formData))
        }
    }, [formData, validate])

    const hasErrors = Object.keys(validationErrors).length > 0

    const location = useLocation()
    useEffect(() => {
        if (!isDirty) return
        const handlePopState = (e) => {
            if (!window.confirm('Masz niezapisane zmiany. Czy na pewno chcesz opuścić stronę?')) {
                e.preventDefault()
                window.history.pushState(null, '', location.pathname)
            }
        }
        window.addEventListener('popstate', handlePopState)
        return () => window.removeEventListener('popstate', handlePopState)
    }, [isDirty, location.pathname])

    useEffect(() => {
        if (!isDirty) return
        const handler = (e) => { e.preventDefault(); e.returnValue = '' }
        window.addEventListener('beforeunload', handler)
        return () => window.removeEventListener('beforeunload', handler)
    }, [isDirty])

    async function handleSave() {
        const errors = validate(formData)
        setValidationErrors(errors)
        if (Object.keys(errors).length > 0) {
            showToast('Popraw błędy walidacji przed zapisem', 'error')
            return
        }
        setSaving(true)
        try {
            await updateClient(formData.id, formData)
            setOriginalData(JSON.parse(JSON.stringify(formData)))
            showToast('Ustawienia zapisane', 'success')
        } catch (err) {
            showToast('Błąd zapisu: ' + err.message, 'error')
        } finally {
            setSaving(false)
        }
    }

    async function handleHardReset() {
        if (!formData) return

        if (resetConfirmation.trim() !== (formData.name || '')) {
            showToast('Wpisz pełną nazwę klienta, aby potwierdzić reset', 'error')
            return
        }

        setResetting(true)
        try {
            const result = await api.post(`/clients/${formData.id}/hard-reset`)
            setResetConfirmation('')
            await loadClient()
            await refreshClients()
            showToast(result.message || 'Dane klienta zostały wyczyszczone', 'success')
        } catch (err) {
            if (err.status === 404) {
                showToast('Endpoint resetu nie jest dostępny. Zrestartuj backend lub całą aplikację.', 'error')
            } else {
                showToast('Błąd resetu: ' + err.message, 'error')
            }
        } finally {
            setResetting(false)
        }
    }

    function handleChange(field, value) {
        setFormData((prev) => ({ ...prev, [field]: value }))
    }

    function handleBusinessRule(rule, value) {
        const parsedValue = value === '' ? null : parseFloat(value)
        setFormData((prev) => ({
            ...prev,
            business_rules: { ...prev.business_rules, [rule]: parsedValue },
        }))
    }

    function handleSafetyLimit(key, displayValue, multiply) {
        const rawValue = displayValue === '' ? null : parseFloat(displayValue) / multiply
        setFormData((prev) => ({
            ...prev,
            business_rules: {
                ...prev.business_rules,
                safety_limits: {
                    ...(prev.business_rules?.safety_limits || {}),
                    [key]: rawValue,
                },
            },
        }))
    }

    function handleResetSafetyDefaults() {
        setFormData((prev) => ({
            ...prev,
            business_rules: {
                ...prev.business_rules,
                safety_limits: {},
            },
        }))
    }

    function addCompetitor() {
        const value = newCompetitor.trim()
        if (!value) return
        setFormData((prev) => ({
            ...prev,
            competitors: [...(prev.competitors || []), value],
        }))
        setNewCompetitor('')
    }

    function handleCompetitorKeyDown(e) {
        if (e.key === 'Enter') {
            e.preventDefault()
            addCompetitor()
        }
    }

    function removeCompetitor(index) {
        setFormData((prev) => ({
            ...prev,
            competitors: prev.competitors.filter((_, currentIndex) => currentIndex !== index),
        }))
    }

    function addBrandTerm() {
        const value = newBrandTerm.trim()
        if (!value) return
        setFormData((prev) => ({
            ...prev,
            business_rules: {
                ...prev.business_rules,
                brand_terms: [...(prev.business_rules?.brand_terms || []), value],
            },
        }))
        setNewBrandTerm('')
    }

    function handleBrandTermKeyDown(e) {
        if (e.key === 'Enter') { e.preventDefault(); addBrandTerm() }
    }

    function removeBrandTerm(index) {
        setFormData((prev) => ({
            ...prev,
            business_rules: {
                ...prev.business_rules,
                brand_terms: (prev.business_rules?.brand_terms || []).filter((_, i) => i !== index),
            },
        }))
    }

    // ─── Strategy context (Marketing Mastermind Brief) ──────────────────────

    function handleStrategyField(field, value) {
        // field ∈ {strategy_narrative, roadmap, brand_voice, restrictions}
        setFormData((prev) => ({
            ...prev,
            strategy_context: {
                ...(prev.strategy_context || {}),
                [field]: value === '' ? null : value,
            },
        }))
    }

    function handleTogglePriorityConversion(name) {
        setFormData((prev) => {
            const current = prev.business_rules?.priority_conversions || []
            const next = current.includes(name)
                ? current.filter(n => n !== name)
                : [...current, name]
            return {
                ...prev,
                business_rules: { ...prev.business_rules, priority_conversions: next },
            }
        })
    }

    function addLesson() {
        const title = newLesson.title.trim()
        const description = newLesson.description.trim()
        if (!title || !description) {
            showToast?.('Tytuł i opis są wymagane', 'error')
            return
        }
        if (title.length > 200) {
            showToast?.('Tytuł max 200 znaków', 'error')
            return
        }
        if (description.length < 10) {
            showToast?.('Opis min 10 znaków', 'error')
            return
        }
        if (description.length > 2000) {
            showToast?.('Opis max 2000 znaków', 'error')
            return
        }
        const entry = {
            type: newLesson.type,
            title,
            description,
            date: newLesson.date || new Date().toISOString().slice(0, 10),
        }
        setFormData((prev) => ({
            ...prev,
            strategy_context: {
                ...(prev.strategy_context || {}),
                lessons_learned: [...((prev.strategy_context || {}).lessons_learned || []), entry],
            },
        }))
        setNewLesson({ type: 'win', title: '', description: '', date: '' })
    }

    function removeLesson(index) {
        if (!window.confirm('Usunąć ten wpis?')) return
        setFormData((prev) => ({
            ...prev,
            strategy_context: {
                ...(prev.strategy_context || {}),
                lessons_learned: ((prev.strategy_context || {}).lessons_learned || []).filter((_, i) => i !== index),
            },
        }))
    }

    async function handleScheduleToggle(enabled = true) {
        setSyncScheduleSaving(true)
        try {
            const interval = syncSchedule?.interval_hours || 6
            const result = await updateScheduledSync(selectedClientId, enabled, interval)
            setSyncSchedule(result)
            showToast(enabled ? 'Automatyczna synchronizacja włączona' : 'Automatyczna synchronizacja wyłączona', 'success')
        } catch (err) {
            showToast('Błąd zapisu harmonogramu: ' + err.message, 'error')
        } finally {
            setSyncScheduleSaving(false)
        }
    }

    async function handleScheduleInterval(intervalHours) {
        setSyncScheduleSaving(true)
        try {
            const result = await updateScheduledSync(selectedClientId, syncSchedule?.enabled ?? true, intervalHours)
            setSyncSchedule(result)
            showToast('Interwał synchronizacji zaktualizowany', 'success')
        } catch (err) {
            showToast('Błąd zapisu harmonogramu: ' + err.message, 'error')
        } finally {
            setSyncScheduleSaving(false)
        }
    }

    async function handleSyncNow() {
        try {
            showToast('Synchronizacja rozpoczęta...', 'info')
            await syncClient(selectedClientId)
            const tid = setTimeout(() => loadSyncInfo(), 3000)
            return () => clearTimeout(tid)
        } catch (err) {
            showToast('Błąd synchronizacji: ' + err.message, 'error')
        }
    }

    if (!selectedClientId) return <EmptyState message="Wybierz klienta" />

    if (loading) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '60px 0' }}>
                <Loader2 size={28} style={{ color: C.accentBlue }} className="animate-spin" />
            </div>
        )
    }

    if (error) {
        return (
            <div className="v2-card" style={{ padding: 24, textAlign: 'center', maxWidth: 500, margin: '40px auto' }}>
                <p style={{ color: C.danger, fontSize: 13, marginBottom: 8 }}>{error}</p>
                <button
                    onClick={loadClient}
                    style={{
                        padding: '5px 14px',
                        borderRadius: 7,
                        fontSize: 12,
                        background: C.infoBg,
                        border: '1px solid rgba(79,142,247,0.3)',
                        color: C.accentBlue,
                        cursor: 'pointer',
                    }}
                >
                    Spróbuj ponownie
                </button>
            </div>
        )
    }

    if (!formData) return null

    const inputStyle = {
        width: '100%',
        background: C.w04,
        border: `1px solid ${C.w08}`,
        borderRadius: 8,
        padding: '8px 12px',
        fontSize: 13,
        color: 'white',
        outline: 'none',
    }

    const labelStyle = {
        display: 'block',
        fontSize: 10,
        fontWeight: 500,
        color: C.textMuted,
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
        marginBottom: 6,
    }

    const errorStyle = {
        fontSize: 11,
        color: C.danger,
        marginTop: 4,
    }

    const inputErrorBorder = {
        borderColor: 'rgba(248,113,113,0.5)',
    }

    const safetyLimits = formData.business_rules?.safety_limits || {}
    const hasSafetyOverrides = Object.values(safetyLimits).some(v => v != null)
    const resetReady = resetConfirmation.trim() === (formData.name || '')

    const syncStatusColor = lastSync?.status === 'success' ? C.success : lastSync?.status === 'failed' ? C.danger : lastSync?.status === 'partial' ? C.warning : C.w40
    const SyncStatusIcon = lastSync?.status === 'success' ? CheckCircle : lastSync?.status === 'failed' ? XCircle : Clock

    return (
        <div style={{ maxWidth: 900, paddingBottom: 48 }}>
            {isDirty && (
                <div
                    className="flex items-center gap-2"
                    style={{
                        padding: '8px 14px',
                        marginBottom: 16,
                        borderRadius: 8,
                        fontSize: 12,
                        background: 'rgba(251,191,36,0.08)',
                        border: '1px solid rgba(251,191,36,0.2)',
                        color: C.warning,
                    }}
                >
                    <AlertTriangle size={14} />
                    Niezapisane zmiany
                    {hasErrors && (
                        <span style={{ color: C.danger, marginLeft: 8 }}>
                            — popraw błędy walidacji
                        </span>
                    )}
                </div>
            )}

            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: C.textPrimary, fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Ustawienia klienta
                    </h1>
                    <p style={{ fontSize: 12, color: C.textMuted, marginTop: 3 }}>
                        Kontekst biznesowy, reguły i limity bezpieczeństwa
                    </p>
                </div>
                <button
                    onClick={handleSave}
                    disabled={saving || hasErrors}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        padding: '7px 16px',
                        borderRadius: 8,
                        fontSize: 12,
                        fontWeight: 500,
                        background: hasErrors ? C.dangerBg : C.infoBg,
                        border: `1px solid ${hasErrors ? 'rgba(248,113,113,0.25)' : C.infoBorder}`,
                        color: hasErrors ? C.danger : C.accentBlue,
                        cursor: (saving || hasErrors) ? 'not-allowed' : 'pointer',
                        opacity: saving ? 0.5 : 1,
                    }}
                >
                    <Save size={14} />
                    {saving ? 'Zapisywanie...' : hasErrors ? 'Błędy walidacji' : isDirty ? 'Zapisz *' : 'Zapisz'}
                </button>
            </div>

            {/* ═══ BRIEF KLIENCKI (Marketing Mastermind) ═══════════════════════ */}
            <SectionGroupHeader label="Brief kliencki" />

            <ConversionGoalsSection
                clientId={selectedClientId}
                priorityConversions={formData.business_rules?.priority_conversions || []}
                onTogglePriority={handleTogglePriorityConversion}
            />

            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                {/* Informacje ogólne */}
                <section>
                    <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary, marginBottom: 12 }}>
                        <Building2 size={16} style={{ color: C.accentBlue }} />
                        Informacje ogólne
                    </h3>
                    <div className="v2-card" style={{ padding: '18px 20px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                            <div>
                                <label style={labelStyle}>Nazwa klienta *</label>
                                <input style={{ ...inputStyle, ...(validationErrors.name ? inputErrorBorder : {}) }} value={formData.name || ''} onChange={e => handleChange('name', e.target.value)} />
                                {validationErrors.name && <p style={errorStyle}>{validationErrors.name}</p>}
                            </div>
                            <div>
                                <label style={labelStyle}>Branża</label>
                                <input style={inputStyle} value={formData.industry || ''} onChange={e => handleChange('industry', e.target.value)} />
                            </div>
                            <div>
                                <label style={labelStyle}>Strona WWW</label>
                                <input style={inputStyle} value={formData.website || ''} onChange={e => handleChange('website', e.target.value)} />
                            </div>
                            <div>
                                <label style={labelStyle}>Google Customer ID</label>
                                <input style={{ ...inputStyle, opacity: 0.5 }} value={formData.google_customer_id || ''} readOnly />
                            </div>
                            <div style={{ gridColumn: '1 / -1' }}>
                                <label style={labelStyle}>Notatki</label>
                                <textarea style={{ ...inputStyle, minHeight: 60, resize: 'vertical' }} value={formData.notes || ''} onChange={e => handleChange('notes', e.target.value)} />
                            </div>
                        </div>
                    </div>
                </section>

                {/* Strategia i konkurencja */}
                <section>
                    <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary, marginBottom: 12 }}>
                        <Target size={16} style={{ color: C.success }} />
                        Strategia i konkurencja
                    </h3>
                    <div className="v2-card" style={{ padding: '18px 20px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                            <div>
                                <label style={labelStyle}>Grupa docelowa</label>
                                <textarea style={{ ...inputStyle, minHeight: 60, resize: 'vertical' }} value={formData.target_audience || ''} onChange={e => handleChange('target_audience', e.target.value)} />
                            </div>
                            <div>
                                <label style={labelStyle}>USP (unikalna propozycja wartości)</label>
                                <textarea style={{ ...inputStyle, minHeight: 60, resize: 'vertical' }} value={formData.usp || ''} onChange={e => handleChange('usp', e.target.value)} />
                            </div>
                        </div>
                        <div>
                            <label style={labelStyle}>Konkurencja</label>
                            <div className="flex flex-wrap gap-2" style={{ marginBottom: 8 }}>
                                {formData.competitors?.map((competitor, index) => (
                                    <div
                                        key={`${competitor}-${index}`}
                                        className="flex items-center gap-1.5"
                                        style={{
                                            padding: '3px 10px',
                                            borderRadius: 999,
                                            fontSize: 12,
                                            background: C.w04,
                                            border: `1px solid ${C.w08}`,
                                            color: C.w60,
                                        }}
                                    >
                                        {competitor}
                                        <button onClick={() => removeCompetitor(index)} style={{ color: C.w30, cursor: 'pointer', background: 'none', border: 'none' }}>
                                            <X size={12} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                            <div className="flex items-center gap-2">
                                <input
                                    style={{ ...inputStyle, width: 220 }}
                                    value={newCompetitor}
                                    onChange={e => setNewCompetitor(e.target.value)}
                                    onKeyDown={handleCompetitorKeyDown}
                                    placeholder="Nazwa konkurenta"
                                />
                                <button
                                    onClick={addCompetitor}
                                    disabled={!newCompetitor.trim()}
                                    className="flex items-center gap-1"
                                    style={{
                                        padding: '8px 14px',
                                        borderRadius: 8,
                                        fontSize: 12,
                                        background: 'rgba(79,142,247,0.08)',
                                        border: '1px solid rgba(79,142,247,0.2)',
                                        color: C.accentBlue,
                                        cursor: newCompetitor.trim() ? 'pointer' : 'not-allowed',
                                        opacity: newCompetitor.trim() ? 1 : 0.5,
                                    }}
                                >
                                    <Plus size={12} /> Dodaj
                                </button>
                            </div>
                        </div>
                    </div>
                </section>

                {/* ─── Strategia marketingowa (narrative) ─── */}
                <section>
                    <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary, marginBottom: 4 }}>
                        <Sparkles size={16} style={{ color: C.accentPurple }} />
                        Strategia marketingowa
                    </h3>
                    <p style={{ fontSize: 11, color: C.textMuted, marginBottom: 12 }}>
                        Narrative dla teamu i AI — markdown dozwolony, w przyszłości sync z Obsidian.
                    </p>
                    <div className="v2-card" style={{ padding: '18px 20px' }}>
                        <textarea
                            data-testid="strategy-narrative-input"
                            value={formData.strategy_context?.strategy_narrative || ''}
                            onChange={e => handleStrategyField('strategy_narrative', e.target.value)}
                            rows={8}
                            placeholder="Jaka jest nasza strategia dla tego klienta? Positioning, target personas, GTM approach, długoterminowe cele..."
                            style={{
                                ...inputStyle,
                                minHeight: 180,
                                fontFamily: FONT.body,
                                resize: 'vertical',
                                lineHeight: 1.6,
                            }}
                        />
                    </div>
                </section>

                {/* ─── Plan działań / Roadmap ─── */}
                <section>
                    <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary, marginBottom: 4 }}>
                        <Compass size={16} style={{ color: C.accentBlue }} />
                        Plan działań / Roadmap
                    </h3>
                    <p style={{ fontSize: 11, color: C.textMuted, marginBottom: 12 }}>
                        Co planujemy w najbliższych tygodniach i kwartale.
                    </p>
                    <div className="v2-card" style={{ padding: '18px 20px' }}>
                        <textarea
                            data-testid="strategy-roadmap-input"
                            value={formData.strategy_context?.roadmap || ''}
                            onChange={e => handleStrategyField('roadmap', e.target.value)}
                            rows={8}
                            placeholder="Co planujemy w najbliższych tygodniach/kwartale? Nadchodzące testy, seasonal campaigns, priorytety..."
                            style={{
                                ...inputStyle,
                                minHeight: 180,
                                fontFamily: FONT.body,
                                resize: 'vertical',
                                lineHeight: 1.6,
                            }}
                        />
                    </div>
                </section>

                {/* ─── Log decyzji (AI-written, MVP read-only) ─── */}
                <section>
                    <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary, marginBottom: 4 }}>
                        <FileText size={16} style={{ color: C.textMuted }} />
                        Log decyzji
                    </h3>
                    <p style={{ fontSize: 11, color: C.textMuted, marginBottom: 12 }}>
                        Automatyczny log decyzji i walidacji AI agenta.
                    </p>
                    <div className="v2-card" style={{ padding: '18px 20px' }}>
                        {(formData.strategy_context?.decisions_log || []).length === 0 ? (
                            <div data-testid="decisions-log-empty" style={{
                                display: 'flex', alignItems: 'flex-start', gap: 10,
                                padding: '12px 14px', borderRadius: R.md,
                                background: C.infoBg, border: `1px solid ${C.infoBorder}`,
                            }}>
                                <Sparkles size={14} color={C.accentBlue} style={{ marginTop: 2, flexShrink: 0 }} />
                                <div style={{ fontSize: 12, color: C.textSecondary, lineHeight: 1.5 }}>
                                    Log decyzji jest zapisywany automatycznie przez AI agent po każdej
                                    analizie i zmianie. <strong style={{ color: C.accentBlue }}>AI zostanie dołączony w v2</strong> — obecnie sekcja jest pusta.
                                </div>
                            </div>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                                {(formData.strategy_context?.decisions_log || [])
                                    .slice()
                                    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
                                    .map((entry, idx) => (
                                        <div key={idx} data-testid="decisions-log-entry" style={{
                                            padding: '12px 14px', borderRadius: R.md,
                                            background: C.w03, border: `1px solid ${C.w07}`,
                                        }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                                <strong style={{ fontSize: 13, color: C.textPrimary }}>{entry.title}</strong>
                                                <span style={{ fontSize: 10, color: C.textMuted }}>
                                                    {formatDate(entry.timestamp)}
                                                </span>
                                            </div>
                                            <div style={{ fontSize: 12, color: C.textSecondary, marginBottom: 4 }}>{entry.decision}</div>
                                            <div style={{ fontSize: 11, color: C.textMuted, fontStyle: 'italic' }}>{entry.rationale}</div>
                                            {entry.validation_result && (
                                                <span style={{
                                                    display: 'inline-block', marginTop: 6,
                                                    padding: '2px 8px', borderRadius: R.full,
                                                    background: C.successBg, color: C.success,
                                                    fontSize: 10, fontWeight: 600,
                                                }}>
                                                    {entry.validation_result}
                                                </span>
                                            )}
                                        </div>
                                    ))}
                            </div>
                        )}
                    </div>
                </section>

                {/* ─── Wnioski i lessons learned ─── */}
                <section>
                    <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary, marginBottom: 4 }}>
                        <Lightbulb size={16} style={{ color: C.warning }} />
                        Wnioski i lessons learned
                    </h3>
                    <p style={{ fontSize: 11, color: C.textMuted, marginBottom: 12 }}>
                        Co zadziałało, co nie, co testowaliśmy. Wpisy append-only — korekty przez nowe wpisy.
                    </p>
                    <div className="v2-card" style={{ padding: '18px 20px' }}>
                        {/* Form: add new lesson */}
                        <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr 140px auto', gap: 8, marginBottom: 14, alignItems: 'start' }}>
                            <select
                                data-testid="lesson-type-select"
                                value={newLesson.type}
                                onChange={e => setNewLesson(l => ({ ...l, type: e.target.value }))}
                                style={{ ...inputStyle, padding: '8px 10px' }}
                            >
                                <option value="win">✓ Win</option>
                                <option value="loss">✗ Loss</option>
                                <option value="test">⚗ Test</option>
                            </select>
                            <input
                                data-testid="lesson-title-input"
                                type="text"
                                value={newLesson.title}
                                onChange={e => setNewLesson(l => ({ ...l, title: e.target.value }))}
                                placeholder="Tytuł wniosku (max 200 znaków)"
                                style={inputStyle}
                                maxLength={200}
                            />
                            <input
                                type="date"
                                value={newLesson.date}
                                onChange={e => setNewLesson(l => ({ ...l, date: e.target.value }))}
                                style={inputStyle}
                            />
                            <button
                                data-testid="lesson-add-button"
                                onClick={addLesson}
                                disabled={!newLesson.title.trim() || !newLesson.description.trim()}
                                style={{
                                    display: 'flex', alignItems: 'center', gap: 5,
                                    padding: '8px 14px', borderRadius: 8, fontSize: 12,
                                    background: C.infoBg, border: `1px solid ${C.infoBorder}`,
                                    color: C.accentBlue,
                                    cursor: (newLesson.title.trim() && newLesson.description.trim()) ? 'pointer' : 'not-allowed',
                                    opacity: (newLesson.title.trim() && newLesson.description.trim()) ? 1 : 0.5,
                                    whiteSpace: 'nowrap',
                                }}
                            >
                                <Plus size={12} /> Dodaj
                            </button>
                        </div>
                        <textarea
                            data-testid="lesson-description-input"
                            value={newLesson.description}
                            onChange={e => setNewLesson(l => ({ ...l, description: e.target.value }))}
                            placeholder="Opis — co konkretnie się wydarzyło, dlaczego i co z tego wynika dla przyszłych kampanii (max 2000 znaków)"
                            rows={3}
                            style={{ ...inputStyle, marginBottom: 14, minHeight: 70, resize: 'vertical', fontFamily: FONT.body }}
                            maxLength={2000}
                        />

                        {/* Existing lessons grouped by type */}
                        {(() => {
                            const lessons = formData.strategy_context?.lessons_learned || []
                            if (lessons.length === 0) {
                                return <div style={{ fontSize: 11, color: C.textMuted, fontStyle: 'italic' }}>Brak wpisów — dodaj pierwszy powyżej.</div>
                            }
                            const groups = { win: [], loss: [], test: [] }
                            lessons.forEach((l, originalIdx) => {
                                (groups[l.type] || groups.test).push({ ...l, originalIdx })
                            })
                            Object.keys(groups).forEach(k => {
                                groups[k].sort((a, b) => new Date(b.date) - new Date(a.date))
                            })
                            const ICON = {
                                win: { icon: '✓', color: C.success, bg: C.successBg, label: 'Wins' },
                                loss: { icon: '✗', color: C.danger, bg: C.dangerBg, label: 'Losses' },
                                test: { icon: '⚗', color: C.warning, bg: C.warningBg, label: 'Tests' },
                            }
                            return (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                                    {['win', 'loss', 'test'].map(type => {
                                        const items = groups[type]
                                        if (items.length === 0) return null
                                        const cfg = ICON[type]
                                        return (
                                            <div key={type}>
                                                <div style={{
                                                    fontSize: 10, fontWeight: 600, color: cfg.color,
                                                    textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6,
                                                }}>
                                                    {cfg.icon} {cfg.label} ({items.length})
                                                </div>
                                                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                                                    {items.map(item => (
                                                        <div
                                                            key={`${type}-${item.originalIdx}`}
                                                            data-testid="lesson-entry"
                                                            style={{
                                                                padding: '10px 12px', borderRadius: R.md,
                                                                background: C.w03, border: `1px solid ${C.w07}`,
                                                                display: 'flex', alignItems: 'flex-start', gap: 10,
                                                            }}
                                                        >
                                                            <div style={{ flex: 1, minWidth: 0 }}>
                                                                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 3 }}>
                                                                    <strong style={{ fontSize: 12, color: C.textPrimary }}>{item.title}</strong>
                                                                    <span style={{ fontSize: 10, color: C.textMuted, whiteSpace: 'nowrap' }}>{item.date}</span>
                                                                </div>
                                                                <div style={{ fontSize: 11, color: C.textSecondary, lineHeight: 1.5 }}>{item.description}</div>
                                                            </div>
                                                            <button
                                                                onClick={() => removeLesson(item.originalIdx)}
                                                                aria-label="Usuń wpis"
                                                                style={{
                                                                    background: 'none', border: 'none', color: C.textMuted,
                                                                    cursor: 'pointer', padding: 4, flexShrink: 0,
                                                                }}
                                                            >
                                                                <Trash2 size={12} />
                                                            </button>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )
                                    })}
                                </div>
                            )
                        })()}
                    </div>
                </section>

                {/* ─── Brand voice & zakazy ─── */}
                <section>
                    <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary, marginBottom: 4 }}>
                        <MessageSquare size={16} style={{ color: C.accentPurple }} />
                        Brand voice & zakazy
                    </h3>
                    <p style={{ fontSize: 11, color: C.textMuted, marginBottom: 12 }}>
                        Jak pisać reklamy dla tego klienta i czego unikać.
                    </p>
                    <div className="v2-card" style={{ padding: '18px 20px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                            <div>
                                <label style={labelStyle}>Tone of voice</label>
                                <textarea
                                    data-testid="brand-voice-input"
                                    value={formData.strategy_context?.brand_voice || ''}
                                    onChange={e => handleStrategyField('brand_voice', e.target.value)}
                                    rows={4}
                                    placeholder="Jak piszemy reklamy dla tego klienta? Język, styl, energia..."
                                    style={{ ...inputStyle, minHeight: 100, resize: 'vertical', fontFamily: FONT.body }}
                                />
                            </div>
                            <div>
                                <label style={labelStyle}>Ograniczenia / Zakazy</label>
                                <textarea
                                    data-testid="restrictions-input"
                                    value={formData.strategy_context?.restrictions || ''}
                                    onChange={e => handleStrategyField('restrictions', e.target.value)}
                                    rows={4}
                                    placeholder="Czego unikamy? Forbidden claims, competitors nieakceptowani, zakazane słowa..."
                                    style={{ ...inputStyle, minHeight: 100, resize: 'vertical', fontFamily: FONT.body }}
                                />
                            </div>
                        </div>
                    </div>
                </section>

                {/* ═══ EXECUTION (operational config) ═══════════════════════════ */}
                <SectionGroupHeader label="Execution" />

                {/* Reguły biznesowe */}
                <section>
                    <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary, marginBottom: 12 }}>
                        <BarChart3 size={16} style={{ color: C.warning }} />
                        Reguły biznesowe
                    </h3>
                    <div className="v2-card" style={{ padding: '18px 20px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                            <div>
                                <label style={labelStyle} title="ROAS = przychód / koszt. Minimalna wartość poniżej której system alarmuje">Minimalny ROAS</label>
                                <input style={{ ...inputStyle, ...(validationErrors.min_roas ? inputErrorBorder : {}) }} type="number" step="0.1" min="0" max="100" value={formData.business_rules?.min_roas ?? ''} onChange={e => handleBusinessRule('min_roas', e.target.value)} placeholder="np. 2.0" />
                                {validationErrors.min_roas && <p style={errorStyle}>{validationErrors.min_roas}</p>}
                            </div>
                            <div>
                                <label style={labelStyle}>Max budżet dzienny ({formData.currency || 'PLN'})</label>
                                <input style={{ ...inputStyle, ...(validationErrors.max_daily_budget ? inputErrorBorder : {}) }} type="number" step="1" min="0" max="100000" value={formData.business_rules?.max_daily_budget ?? ''} onChange={e => handleBusinessRule('max_daily_budget', e.target.value)} placeholder="np. 500" />
                                {validationErrors.max_daily_budget && <p style={errorStyle}>{validationErrors.max_daily_budget}</p>}
                            </div>
                            {/* AI Context — structured fields for recommendations, reports, AI agent */}
                            <div>
                                <label style={labelStyle} title="Docelowy koszt pozyskania klienta — używany przez rekomendacje i raporty">Target CPA ({formData.currency || 'PLN'})</label>
                                <input style={inputStyle} type="number" step="1" min="0" value={formData.business_rules?.target_cpa ?? ''} onChange={e => handleBusinessRule('target_cpa', e.target.value)} placeholder="np. 80" />
                            </div>
                            <div>
                                <label style={labelStyle} title="Docelowy ROAS — używany przez rekomendacje i raporty">Target ROAS (x)</label>
                                <input style={inputStyle} type="number" step="0.1" min="0" value={formData.business_rules?.target_roas ?? ''} onChange={e => handleBusinessRule('target_roas', e.target.value)} placeholder="np. 4.0" />
                            </div>
                            <div>
                                <label style={labelStyle} title="Średnia wartość życiowa klienta — pozwala kalibrować maks. CPA">LTV klienta ({formData.currency || 'PLN'})</label>
                                <input style={inputStyle} type="number" step="1" min="0" value={formData.business_rules?.ltv_per_customer ?? ''} onChange={e => handleBusinessRule('ltv_per_customer', e.target.value)} placeholder="np. 1200" />
                            </div>
                            <div>
                                <label style={labelStyle} title="Marża zysku w % — używana do oceny rentowności kampanii">Marża zysku (%)</label>
                                <input style={inputStyle} type="number" step="1" min="0" max="100" value={formData.business_rules?.profit_margin_pct ?? ''} onChange={e => handleBusinessRule('profit_margin_pct', e.target.value)} placeholder="np. 35" />
                            </div>
                        </div>

                        {/* Brand terms — tag input */}
                        <div style={{ marginTop: 16 }}>
                            <label style={labelStyle} title="Frazy brandowe — używane do segmentacji i wykluczeń. AI używa tej listy przy analizie kampanii.">Brand terms</label>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
                                {(formData.business_rules?.brand_terms || []).map((term, i) => (
                                    <span key={i} style={{
                                        display: 'inline-flex', alignItems: 'center', gap: 5,
                                        padding: '3px 10px', borderRadius: 999,
                                        background: C.w05, border: `1px solid ${C.w10}`,
                                        fontSize: 12, color: C.textSecondary,
                                    }}>
                                        {term}
                                        <button onClick={() => removeBrandTerm(i)} style={{ background: 'none', border: 'none', color: C.w40, cursor: 'pointer', padding: 0, lineHeight: 1 }}>
                                            <X size={11} />
                                        </button>
                                    </span>
                                ))}
                            </div>
                            <div style={{ display: 'flex', gap: 8 }}>
                                <input
                                    style={{ ...inputStyle, width: 220 }}
                                    value={newBrandTerm}
                                    onChange={e => setNewBrandTerm(e.target.value)}
                                    onKeyDown={handleBrandTermKeyDown}
                                    placeholder="np. NazwaMarki"
                                />
                                <button onClick={addBrandTerm} style={{
                                    display: 'flex', alignItems: 'center', gap: 5,
                                    padding: '7px 12px', borderRadius: 8, fontSize: 12,
                                    background: C.w06, border: `1px solid ${C.w10}`,
                                    color: C.textSecondary, cursor: 'pointer',
                                }}>
                                    <Plus size={12} /> Dodaj
                                </button>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Limity bezpieczeństwa */}
                <section>
                    <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
                        <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary }}>
                            <ShieldAlert size={16} style={{ color: C.danger }} />
                            Limity bezpieczeństwa
                        </h3>
                        {hasSafetyOverrides && (
                            <button
                                onClick={handleResetSafetyDefaults}
                                className="flex items-center gap-1"
                                style={{
                                    padding: '4px 10px',
                                    borderRadius: 6,
                                    fontSize: 11,
                                    background: C.w04,
                                    border: `1px solid ${C.w08}`,
                                    color: C.w50,
                                    cursor: 'pointer',
                                }}
                            >
                                <RotateCcw size={11} />
                                Przywróć domyślne
                            </button>
                        )}
                    </div>
                    <p style={{ fontSize: 11, color: C.w30, marginBottom: 12 }}>
                        Nadpisz domyślne limity dla tego klienta. Puste pole = wartość globalna.
                    </p>
                    <div className="v2-card" style={{ padding: '18px 20px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
                            {SAFETY_FIELDS.map(({ key, label, unit, multiply, tooltip, min, max }) => {
                                const clientValue = safetyLimits[key]
                                const displayValue = clientValue != null ? (clientValue * multiply).toFixed(multiply > 1 ? 0 : 2) : ''
                                const defaultValue = (GLOBAL_DEFAULTS[key] * multiply).toFixed(multiply > 1 ? 0 : 2)
                                const errKey = `safety_${key}`
                                return (
                                    <div key={key}>
                                        <label style={labelStyle} title={tooltip}>{label}</label>
                                        <div style={{ position: 'relative' }}>
                                            <input
                                                style={{ ...inputStyle, ...(validationErrors[errKey] ? inputErrorBorder : {}) }}
                                                type="number"
                                                step={multiply > 1 ? '1' : '0.01'}
                                                min={min}
                                                max={max}
                                                value={displayValue}
                                                onChange={e => handleSafetyLimit(key, e.target.value, multiply)}
                                                placeholder={`domyślnie: ${defaultValue}${unit}`}
                                            />
                                            {unit && (
                                                <span style={{
                                                    position: 'absolute',
                                                    right: 10,
                                                    top: '50%',
                                                    transform: 'translateY(-50%)',
                                                    fontSize: 11,
                                                    color: C.w20,
                                                    pointerEvents: 'none',
                                                }}>
                                                    {unit}
                                                </span>
                                            )}
                                        </div>
                                        {validationErrors[errKey] && <p style={errorStyle}>{validationErrors[errKey]}</p>}
                                    </div>
                                )
                            })}
                        </div>
                    </div>
                </section>

                {/* ADR-020: Synchronizacja section hidden — sync lives only in MCC Overview.
                    State, handlers and JSX left as dead code for quick re-enable if policy changes. */}
                {false && (
                <section>
                    <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary, marginBottom: 4 }}>
                        <RefreshCw size={16} style={{ color: C.accentBlue }} />
                        Synchronizacja
                    </h3>
                    <p style={{ fontSize: 11, color: C.w30, marginBottom: 12 }}>
                        Status ostatniego pobrania danych z Google Ads i harmonogram automatycznej synchronizacji.
                    </p>
                    <div className="v2-card" style={{ padding: '18px 20px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                            {/* Ostatnia synchronizacja */}
                            <div>
                                <label style={labelStyle}>Ostatnia synchronizacja</label>
                                {lastSync ? (
                                    <div className="flex items-start gap-3" style={{ padding: '10px 14px', borderRadius: 8, background: C.w04, border: `1px solid ${C.w08}` }}>
                                        <SyncStatusIcon size={16} style={{ color: syncStatusColor, marginTop: 2, flexShrink: 0 }} />
                                        <div>
                                            <div style={{ fontSize: 13, color: C.textPrimary, marginBottom: 2 }}>
                                                {lastSync.status === 'success' ? 'Zakończona pomyślnie' : lastSync.status === 'failed' ? 'Zakończona z błędem' : lastSync.status === 'partial' ? 'Częściowo zakończona' : lastSync.status === 'running' ? 'W trakcie...' : lastSync.status}
                                            </div>
                                            <div style={{ fontSize: 11, color: C.w40 }}>
                                                {formatDate(lastSync.started_at)}
                                                {lastSync.finished_at && ` (${formatDuration(lastSync.started_at, lastSync.finished_at)})`}
                                            </div>
                                            {lastSync.total_synced != null && (
                                                <div style={{ fontSize: 11, color: C.w30, marginTop: 2 }}>
                                                    {lastSync.total_synced} rekordów zsynchronizowano
                                                    {lastSync.total_errors > 0 && <span style={{ color: C.danger }}> ({lastSync.total_errors} błędów)</span>}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ) : (
                                    <div style={{ padding: '10px 14px', borderRadius: 8, background: C.w04, border: `1px solid ${C.w08}` }}>
                                        <div style={{ fontSize: 12, color: C.w40 }}>Jeszcze nie synchronizowano</div>
                                    </div>
                                )}
                                <button
                                    onClick={handleSyncNow}
                                    className="flex items-center gap-1"
                                    style={{
                                        marginTop: 8,
                                        padding: '5px 12px',
                                        borderRadius: 6,
                                        fontSize: 11,
                                        background: C.infoBg,
                                        border: `1px solid ${C.infoBorder}`,
                                        color: C.accentBlue,
                                        cursor: 'pointer',
                                    }}
                                >
                                    <RefreshCw size={11} />
                                    Synchronizuj teraz
                                </button>
                            </div>

                            {/* Zaplanowana synchronizacja */}
                            <div>
                                <label style={labelStyle}>Zaplanowana synchronizacja</label>
                                <div style={{ padding: '10px 14px', borderRadius: 8, background: C.w04, border: `1px solid ${C.w08}` }}>
                                    <div className="flex items-center justify-between" style={{ marginBottom: syncSchedule?.enabled ? 12 : 0 }}>
                                        <span style={{ fontSize: 13, color: C.textPrimary }}>
                                            Automatyczna synchronizacja
                                        </span>
                                        <button
                                            onClick={() => handleScheduleToggle(!syncSchedule?.enabled)}
                                            disabled={syncScheduleSaving}
                                            style={{
                                                padding: '3px 12px',
                                                borderRadius: 999,
                                                fontSize: 11,
                                                fontWeight: 500,
                                                background: syncSchedule?.enabled ? 'rgba(74,222,128,0.12)' : C.w04,
                                                border: `1px solid ${syncSchedule?.enabled ? 'rgba(74,222,128,0.3)' : C.w08}`,
                                                color: syncSchedule?.enabled ? C.success : C.w40,
                                                cursor: syncScheduleSaving ? 'not-allowed' : 'pointer',
                                                opacity: syncScheduleSaving ? 0.5 : 1,
                                            }}
                                        >
                                            {syncSchedule?.enabled ? 'Włączona' : 'Wyłączona'}
                                        </button>
                                    </div>
                                    {syncSchedule?.enabled && (
                                        <>
                                            <label style={{ ...labelStyle, marginBottom: 4 }}>Interwał</label>
                                            <select
                                                value={syncSchedule?.interval_hours || 6}
                                                onChange={e => handleScheduleInterval(parseInt(e.target.value))}
                                                disabled={syncScheduleSaving}
                                                style={{
                                                    ...inputStyle,
                                                    cursor: 'pointer',
                                                    appearance: 'auto',
                                                }}
                                            >
                                                {INTERVAL_OPTIONS.map(opt => (
                                                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                                                ))}
                                            </select>
                                            {syncSchedule?.next_run_at && (
                                                <div className="flex items-center gap-1" style={{ fontSize: 11, color: C.w30, marginTop: 6 }}>
                                                    <Calendar size={10} />
                                                    Następna: {formatDate(syncSchedule.next_run_at)}
                                                </div>
                                            )}
                                        </>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                </section>
                )}

                {/* Konta MCC */}
                {mccAccounts && mccAccounts.accounts && mccAccounts.accounts.length > 0 && (
                    <section>
                        <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary, marginBottom: 4 }}>
                            <Building2 size={16} style={{ color: C.accentPurple }} />
                            Konta MCC ({mccAccounts.total})
                        </h3>
                        <p style={{ fontSize: 11, color: C.w30, marginBottom: 12 }}>
                            Konta podrzędne pod menadżerem Google Ads
                        </p>
                        <div className="v2-card" style={{ padding: '18px 20px' }}>
                            <div style={{ overflowX: 'auto' }}>
                                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                    <thead>
                                        <tr style={{ borderBottom: B.subtle }}>
                                            <th style={{ padding: '6px 10px', fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', textAlign: 'left' }}>ID konta</th>
                                            <th style={{ padding: '6px 10px', fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', textAlign: 'left' }}>Nazwa</th>
                                            <th style={{ padding: '6px 10px', fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', textAlign: 'center' }}>Status</th>
                                            <th style={{ padding: '6px 10px', fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', textAlign: 'center' }}>W aplikacji</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {mccAccounts.accounts.map((acc, i) => (
                                            <tr key={i} style={{ borderBottom: `1px solid ${C.w04}` }}>
                                                <td style={{ padding: '6px 10px', fontSize: 12, fontFamily: 'monospace', color: C.w60 }}>{acc.customer_id}</td>
                                                <td style={{ padding: '6px 10px', fontSize: 12, color: C.textPrimary }}>{acc.name || '—'}</td>
                                                <td style={{ padding: '6px 10px', fontSize: 10, textAlign: 'center', color: acc.status === 'ENABLED' ? C.success : C.w40 }}>{acc.status}</td>
                                                <td style={{ padding: '6px 10px', fontSize: 10, textAlign: 'center', color: acc.local_client_id ? C.success : C.w25 }}>
                                                    {acc.local_client_id ? 'Połączony' : '—'}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </section>
                )}

                {/* Twardy reset */}
                <section>
                    <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary, marginBottom: 4 }}>
                        <ShieldAlert size={16} style={{ color: C.danger }} />
                        Twardy reset danych klienta
                    </h3>
                    <p style={{ fontSize: 11, color: C.w30, marginBottom: 12 }}>
                        Usuwa lokalne dane tego klienta: kampanie, grupy reklam, słowa kluczowe, search terms, rekomendacje, alerty, historię i logi sync. Nie usuwa profilu klienta ani credentials Google Ads.
                    </p>
                    <div className="v2-card" style={{ padding: '18px 20px', border: '1px solid rgba(248,113,113,0.22)', background: 'rgba(248,113,113,0.05)' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1.6fr auto', gap: 16, alignItems: 'end' }}>
                            <div>
                                <label style={labelStyle}>Aby potwierdzić, wpisz nazwę klienta</label>
                                <input
                                    style={inputStyle}
                                    value={resetConfirmation}
                                    onChange={e => setResetConfirmation(e.target.value)}
                                    placeholder={formData.name || ''}
                                />
                                <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.38)', marginTop: 8 }}>
                                    Potwierdzenie: {formData.name}
                                </p>
                            </div>
                            <button
                                onClick={handleHardReset}
                                disabled={resetting || !resetReady}
                                style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: 6,
                                    padding: '9px 16px',
                                    borderRadius: 8,
                                    fontSize: 12,
                                    fontWeight: 600,
                                    background: 'rgba(248,113,113,0.12)',
                                    border: '1px solid rgba(248,113,113,0.28)',
                                    color: '#FCA5A5',
                                    cursor: 'pointer',
                                    opacity: resetting || !resetReady ? 0.5 : 1,
                                    minWidth: 220,
                                }}
                            >
                                <ShieldAlert size={14} />
                                {resetting ? 'Resetowanie...' : 'Twardy reset danych klienta'}
                            </button>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    )
}

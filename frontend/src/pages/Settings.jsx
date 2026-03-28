import { useEffect, useState, useRef } from 'react'
import { BarChart3, Building2, Loader2, Plus, Save, ShieldAlert, Target, X } from 'lucide-react'

import api, { getClient, updateClient, getMccAccounts } from '../api'
import EmptyState from '../components/EmptyState'
import { useApp } from '../contexts/AppContext'

const SAFETY_FIELDS = [
    { key: 'MAX_BID_CHANGE_PCT', label: 'Max zmiana stawki (%)', unit: '%', multiply: 100, tooltip: 'Maksymalna jednorazowa zmiana stawki CPC w procentach', min: 1, max: 100 },
    { key: 'MAX_BUDGET_CHANGE_PCT', label: 'Max zmiana budżetu (%)', unit: '%', multiply: 100, tooltip: 'Maksymalna jednorazowa zmiana budżetu kampanii', min: 1, max: 100 },
    { key: 'MIN_BID_USD', label: 'Min stawka (USD)', unit: '$', multiply: 1, tooltip: 'Minimalna dopuszczalna stawka CPC', min: 0.01, max: 100 },
    { key: 'MAX_BID_USD', label: 'Max stawka (USD)', unit: '$', multiply: 1, tooltip: 'Maksymalna dopuszczalna stawka CPC', min: 0.01, max: 1000 },
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

    useEffect(() => {
        if (selectedClientId) {
            loadClient()
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
            // Load MCC accounts if client has a customer ID
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

    const isDirty = formData && originalData && JSON.stringify(formData) !== JSON.stringify(originalData)

    useEffect(() => {
        if (!isDirty) return
        const handler = (e) => { e.preventDefault(); e.returnValue = '' }
        window.addEventListener('beforeunload', handler)
        return () => window.removeEventListener('beforeunload', handler)
    }, [isDirty])

    async function handleSave() {
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
            showToast('Wpisz pelna nazwe klienta, aby potwierdzic reset', 'error')
            return
        }

        setResetting(true)
        try {
            const result = await api.post(`/clients/${formData.id}/hard-reset`)
            setResetConfirmation('')
            await loadClient()
            await refreshClients()
            showToast(result.message || 'Dane klienta zostaly wyczyszczone', 'success')
        } catch (err) {
            if (err.status === 404) {
                showToast('Endpoint resetu nie jest dostepny. Zrestartuj backend lub cala aplikacje.', 'error')
            } else {
                showToast('Blad resetu: ' + err.message, 'error')
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

    function addCompetitor() {
        const competitor = prompt('Podaj nazwe konkurenta:')
        if (!competitor) return

        setFormData((prev) => ({
            ...prev,
            competitors: [...(prev.competitors || []), competitor],
        }))
    }

    function removeCompetitor(index) {
        setFormData((prev) => ({
            ...prev,
            competitors: prev.competitors.filter((_, currentIndex) => currentIndex !== index),
        }))
    }

    if (!selectedClientId) return <EmptyState message="Wybierz klienta" />

    if (loading) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '60px 0' }}>
                <Loader2 size={28} style={{ color: '#4F8EF7' }} className="animate-spin" />
            </div>
        )
    }

    if (error) {
        return (
            <div className="v2-card" style={{ padding: 24, textAlign: 'center', maxWidth: 500, margin: '40px auto' }}>
                <p style={{ color: '#F87171', fontSize: 13, marginBottom: 8 }}>{error}</p>
                <button
                    onClick={loadClient}
                    style={{
                        padding: '5px 14px',
                        borderRadius: 7,
                        fontSize: 12,
                        background: 'rgba(79,142,247,0.15)',
                        border: '1px solid rgba(79,142,247,0.3)',
                        color: '#4F8EF7',
                        cursor: 'pointer',
                    }}
                >
                    Sprobuj ponownie
                </button>
            </div>
        )
    }

    if (!formData) return null

    const inputStyle = {
        width: '100%',
        background: 'rgba(255,255,255,0.04)',
        border: '1px solid rgba(255,255,255,0.08)',
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
        color: 'rgba(255,255,255,0.35)',
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
        marginBottom: 6,
    }

    const safetyLimits = formData.business_rules?.safety_limits || {}
    const resetReady = resetConfirmation.trim() === (formData.name || '')

    return (
        <div style={{ maxWidth: 900, paddingBottom: 48 }}>
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Ustawienia klienta
                    </h1>
                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                        Kontekst biznesowy, reguly i limity bezpieczenstwa
                    </p>
                </div>
                <button
                    onClick={handleSave}
                    disabled={saving}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        padding: '7px 16px',
                        borderRadius: 8,
                        fontSize: 12,
                        fontWeight: 500,
                        background: 'rgba(79,142,247,0.15)',
                        border: '1px solid rgba(79,142,247,0.3)',
                        color: '#4F8EF7',
                        cursor: 'pointer',
                        opacity: saving ? 0.5 : 1,
                    }}
                >
                    <Save size={14} />
                    {saving ? 'Zapisywanie...' : isDirty ? 'Zapisz *' : 'Zapisz'}
                </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                <section>
                    <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: '#F0F0F0', marginBottom: 12 }}>
                        <Building2 size={16} style={{ color: '#4F8EF7' }} />
                        Informacje ogolne
                    </h3>
                    <div className="v2-card" style={{ padding: '18px 20px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                            <div>
                                <label style={labelStyle}>Nazwa klienta</label>
                                <input style={inputStyle} value={formData.name || ''} onChange={e => handleChange('name', e.target.value)} />
                            </div>
                            <div>
                                <label style={labelStyle}>Branza</label>
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

                <section>
                    <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: '#F0F0F0', marginBottom: 12 }}>
                        <Target size={16} style={{ color: '#4ADE80' }} />
                        Strategia i konkurencja
                    </h3>
                    <div className="v2-card" style={{ padding: '18px 20px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                            <div>
                                <label style={labelStyle}>Target audience</label>
                                <textarea style={{ ...inputStyle, minHeight: 60, resize: 'vertical' }} value={formData.target_audience || ''} onChange={e => handleChange('target_audience', e.target.value)} />
                            </div>
                            <div>
                                <label style={labelStyle}>USP (unikalna propozycja wartosci)</label>
                                <textarea style={{ ...inputStyle, minHeight: 60, resize: 'vertical' }} value={formData.usp || ''} onChange={e => handleChange('usp', e.target.value)} />
                            </div>
                        </div>
                        <div>
                            <label style={labelStyle}>Konkurencja</label>
                            <div className="flex flex-wrap gap-2">
                                {formData.competitors?.map((competitor, index) => (
                                    <div
                                        key={`${competitor}-${index}`}
                                        className="flex items-center gap-1.5"
                                        style={{
                                            padding: '3px 10px',
                                            borderRadius: 999,
                                            fontSize: 12,
                                            background: 'rgba(255,255,255,0.04)',
                                            border: '1px solid rgba(255,255,255,0.08)',
                                            color: 'rgba(255,255,255,0.6)',
                                        }}
                                    >
                                        {competitor}
                                        <button onClick={() => removeCompetitor(index)} style={{ color: 'rgba(255,255,255,0.3)', cursor: 'pointer', background: 'none', border: 'none' }}>
                                            <X size={12} />
                                        </button>
                                    </div>
                                ))}
                                <button
                                    onClick={addCompetitor}
                                    className="flex items-center gap-1"
                                    style={{
                                        padding: '3px 10px',
                                        borderRadius: 999,
                                        fontSize: 12,
                                        background: 'rgba(79,142,247,0.08)',
                                        border: '1px solid rgba(79,142,247,0.2)',
                                        color: '#4F8EF7',
                                        cursor: 'pointer',
                                    }}
                                >
                                    <Plus size={12} /> Dodaj
                                </button>
                            </div>
                        </div>
                    </div>
                </section>

                <section>
                    <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: '#F0F0F0', marginBottom: 12 }}>
                        <BarChart3 size={16} style={{ color: '#FBBF24' }} />
                        Reguly biznesowe
                    </h3>
                    <div className="v2-card" style={{ padding: '18px 20px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                            <div>
                                <label style={labelStyle} title="ROAS = przychód / koszt. Minimalna wartość poniżej której system alarmuje">Minimalny ROAS</label>
                                <input style={inputStyle} type="number" step="0.1" min="0" max="100" value={formData.business_rules?.min_roas ?? ''} onChange={e => handleBusinessRule('min_roas', e.target.value)} placeholder="np. 2.0" />
                            </div>
                            <div>
                                <label style={labelStyle}>Max budżet dzienny (USD)</label>
                                <input style={inputStyle} type="number" step="1" min="0" max="100000" value={formData.business_rules?.max_daily_budget ?? ''} onChange={e => handleBusinessRule('max_daily_budget', e.target.value)} placeholder="np. 500" />
                            </div>
                        </div>
                    </div>
                </section>

                <section>
                    <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: '#F0F0F0', marginBottom: 4 }}>
                        <ShieldAlert size={16} style={{ color: '#F87171' }} />
                        Limity bezpieczeństwa
                    </h3>
                    <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', marginBottom: 12 }}>
                        Nadpisz domyślne limity dla tego klienta. Puste pole = wartość globalna.
                    </p>
                    <div className="v2-card" style={{ padding: '18px 20px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
                            {SAFETY_FIELDS.map(({ key, label, unit, multiply, tooltip, min, max }) => {
                                const clientValue = safetyLimits[key]
                                const displayValue = clientValue != null ? (clientValue * multiply).toFixed(multiply > 1 ? 0 : 2) : ''
                                const defaultValue = (GLOBAL_DEFAULTS[key] * multiply).toFixed(multiply > 1 ? 0 : 2)
                                return (
                                    <div key={key}>
                                        <label style={labelStyle} title={tooltip}>{label}</label>
                                        <div style={{ position: 'relative' }}>
                                            <input
                                                style={inputStyle}
                                                type="number"
                                                step={multiply > 1 ? '1' : '0.01'}
                                                min={min}
                                                max={max}
                                                value={displayValue}
                                                onChange={e => handleSafetyLimit(key, e.target.value, multiply)}
                                                placeholder={`domyslnie: ${defaultValue}${unit}`}
                                            />
                                            {unit && (
                                                <span style={{
                                                    position: 'absolute',
                                                    right: 10,
                                                    top: '50%',
                                                    transform: 'translateY(-50%)',
                                                    fontSize: 11,
                                                    color: 'rgba(255,255,255,0.2)',
                                                    pointerEvents: 'none',
                                                }}>
                                                    {unit}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    </div>
                </section>

                <section>
                    <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: '#F0F0F0', marginBottom: 4 }}>
                        <ShieldAlert size={16} style={{ color: '#F87171' }} />
                        Twardy reset danych klienta
                    </h3>
                    <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', marginBottom: 12 }}>
                        Usuwa lokalne dane tego klienta: kampanie, grupy reklam, słowa kluczowe, search terms, rekomendacje, alerty, historię i logi sync. Nie usuwa profilu klienta ani credentials Google Ads.
                    </p>
                    <div className="v2-card" style={{ padding: '18px 20px', border: '1px solid rgba(248,113,113,0.22)', background: 'rgba(248,113,113,0.05)' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1.6fr auto', gap: 16, alignItems: 'end' }}>
                            <div>
                                <label style={labelStyle}>Aby potwierdzic, wpisz nazwe klienta</label>
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

            {/* MCC Accounts */}
            {mccAccounts && mccAccounts.accounts && mccAccounts.accounts.length > 0 && (
                <div style={{ maxWidth: 800 }}>
                    <section className="v2-card" style={{ padding: '18px 22px' }}>
                        <h2 style={{ fontSize: 15, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne', display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
                            <Building2 size={16} style={{ color: '#7B5CE0' }} />
                            Konta MCC ({mccAccounts.total})
                        </h2>
                        <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', marginBottom: 12 }}>
                            Konta podrzędne pod menadżerem Google Ads
                        </p>
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                                        <th style={{ padding: '6px 10px', fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', textAlign: 'left' }}>ID konta</th>
                                        <th style={{ padding: '6px 10px', fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', textAlign: 'left' }}>Nazwa</th>
                                        <th style={{ padding: '6px 10px', fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', textAlign: 'center' }}>Status</th>
                                        <th style={{ padding: '6px 10px', fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', textAlign: 'center' }}>W aplikacji</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {mccAccounts.accounts.map((acc, i) => (
                                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                            <td style={{ padding: '6px 10px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.6)' }}>{acc.customer_id}</td>
                                            <td style={{ padding: '6px 10px', fontSize: 12, color: '#F0F0F0' }}>{acc.name || '—'}</td>
                                            <td style={{ padding: '6px 10px', fontSize: 10, textAlign: 'center', color: acc.status === 'ENABLED' ? '#4ADE80' : 'rgba(255,255,255,0.4)' }}>{acc.status}</td>
                                            <td style={{ padding: '6px 10px', fontSize: 10, textAlign: 'center', color: acc.local_client_id ? '#4ADE80' : 'rgba(255,255,255,0.25)' }}>
                                                {acc.local_client_id ? '✓ Połączony' : '—'}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </section>
                </div>
            )}
        </div>
    )
}


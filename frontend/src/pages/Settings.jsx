import { useState, useEffect } from 'react'
import { getClient, updateClient } from '../api'
import { useApp } from '../contexts/AppContext'
import EmptyState from '../components/EmptyState'
import { Save, Plus, X, Building2, Target, ShieldAlert, BarChart3, Loader2 } from 'lucide-react'

const SAFETY_FIELDS = [
    { key: 'MAX_BID_CHANGE_PCT', label: 'Max zmiana stawki (%)', unit: '%', multiply: 100, tooltip: 'Maksymalna jednorazowa zmiana stawki CPC w procentach' },
    { key: 'MAX_BUDGET_CHANGE_PCT', label: 'Max zmiana budżetu (%)', unit: '%', multiply: 100, tooltip: 'Maksymalna jednorazowa zmiana budżetu kampanii' },
    { key: 'MIN_BID_USD', label: 'Min stawka (USD)', unit: '$', multiply: 1, tooltip: 'Minimalna dopuszczalna stawka CPC' },
    { key: 'MAX_BID_USD', label: 'Max stawka (USD)', unit: '$', multiply: 1, tooltip: 'Maksymalna dopuszczalna stawka CPC' },
    { key: 'MAX_KEYWORD_PAUSE_PCT', label: 'Max pause keywords/dzień (%)', unit: '%', multiply: 100, tooltip: 'Max procent słów kluczowych wstrzymanych w jednym dniu na kampanię' },
    { key: 'MAX_NEGATIVES_PER_DAY', label: 'Max negatywów/dzień', unit: '', multiply: 1, tooltip: 'Limit dodawanych negatywnych fraz dziennie' },
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
    const { selectedClientId, showToast } = useApp()
    const [formData, setFormData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (selectedClientId) loadClient()
    }, [selectedClientId])

    async function loadClient() {
        setLoading(true)
        try {
            const data = await getClient(selectedClientId)
            setFormData(data)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    async function handleSave() {
        setSaving(true)
        try {
            await updateClient(formData.id, formData)
            showToast('Ustawienia zapisane', 'success')
        } catch (err) {
            showToast('Błąd zapisu: ' + err.message, 'error')
        } finally {
            setSaving(false)
        }
    }

    function handleChange(field, value) {
        setFormData(prev => ({ ...prev, [field]: value }))
    }

    function handleBusinessRule(rule, value) {
        const val = value === '' ? null : parseFloat(value)
        setFormData(prev => ({
            ...prev,
            business_rules: { ...prev.business_rules, [rule]: val }
        }))
    }

    function handleSafetyLimit(key, displayValue, multiply) {
        const raw = displayValue === '' ? null : parseFloat(displayValue) / multiply
        setFormData(prev => ({
            ...prev,
            business_rules: {
                ...prev.business_rules,
                safety_limits: {
                    ...(prev.business_rules?.safety_limits || {}),
                    [key]: raw,
                }
            }
        }))
    }

    function addCompetitor() {
        const comp = prompt('Podaj nazwę konkurenta:')
        if (comp) {
            setFormData(prev => ({
                ...prev,
                competitors: [...(prev.competitors || []), comp]
            }))
        }
    }

    function removeCompetitor(index) {
        setFormData(prev => ({
            ...prev,
            competitors: prev.competitors.filter((_, i) => i !== index)
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
                <button onClick={loadClient} style={{
                    padding: '5px 14px', borderRadius: 7, fontSize: 12,
                    background: 'rgba(79,142,247,0.15)', border: '1px solid rgba(79,142,247,0.3)',
                    color: '#4F8EF7', cursor: 'pointer',
                }}>
                    Spróbuj ponownie
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

    return (
        <div style={{ maxWidth: 900, paddingBottom: 48 }}>
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Ustawienia klienta
                    </h1>
                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                        Kontekst biznesowy, reguły i limity bezpieczeństwa
                    </p>
                </div>
                <button
                    onClick={handleSave}
                    disabled={saving}
                    style={{
                        display: 'flex', alignItems: 'center', gap: 6,
                        padding: '7px 16px', borderRadius: 8, fontSize: 12, fontWeight: 500,
                        background: 'rgba(79,142,247,0.15)',
                        border: '1px solid rgba(79,142,247,0.3)',
                        color: '#4F8EF7', cursor: 'pointer',
                        opacity: saving ? 0.5 : 1,
                    }}
                >
                    <Save size={14} />
                    {saving ? 'Zapisywanie...' : 'Zapisz'}
                </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                {/* General Info */}
                <section>
                    <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: '#F0F0F0', marginBottom: 12 }}>
                        <Building2 size={16} style={{ color: '#4F8EF7' }} />
                        Informacje ogólne
                    </h3>
                    <div className="v2-card" style={{ padding: '18px 20px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                            <div>
                                <label style={labelStyle}>Nazwa klienta</label>
                                <input style={inputStyle} value={formData.name || ''} onChange={e => handleChange('name', e.target.value)} />
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

                {/* Strategy */}
                <section>
                    <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: '#F0F0F0', marginBottom: 12 }}>
                        <Target size={16} style={{ color: '#4ADE80' }} />
                        Strategia i konkurencja
                    </h3>
                    <div className="v2-card" style={{ padding: '18px 20px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                            <div>
                                <label style={labelStyle}>Target Audience</label>
                                <textarea style={{ ...inputStyle, minHeight: 60, resize: 'vertical' }} value={formData.target_audience || ''} onChange={e => handleChange('target_audience', e.target.value)} />
                            </div>
                            <div>
                                <label style={labelStyle}>USP (Unikalna Propozycja Wartości)</label>
                                <textarea style={{ ...inputStyle, minHeight: 60, resize: 'vertical' }} value={formData.usp || ''} onChange={e => handleChange('usp', e.target.value)} />
                            </div>
                        </div>
                        <div>
                            <label style={labelStyle}>Konkurencja</label>
                            <div className="flex flex-wrap gap-2">
                                {formData.competitors?.map((comp, i) => (
                                    <div key={i} className="flex items-center gap-1.5" style={{
                                        padding: '3px 10px', borderRadius: 999, fontSize: 12,
                                        background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
                                        color: 'rgba(255,255,255,0.6)',
                                    }}>
                                        {comp}
                                        <button onClick={() => removeCompetitor(i)} style={{ color: 'rgba(255,255,255,0.3)', cursor: 'pointer', background: 'none', border: 'none' }}>
                                            <X size={12} />
                                        </button>
                                    </div>
                                ))}
                                <button
                                    onClick={addCompetitor}
                                    className="flex items-center gap-1"
                                    style={{
                                        padding: '3px 10px', borderRadius: 999, fontSize: 12,
                                        background: 'rgba(79,142,247,0.08)', border: '1px solid rgba(79,142,247,0.2)',
                                        color: '#4F8EF7', cursor: 'pointer',
                                    }}
                                >
                                    <Plus size={12} /> Dodaj
                                </button>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Business Rules */}
                <section>
                    <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: '#F0F0F0', marginBottom: 12 }}>
                        <BarChart3 size={16} style={{ color: '#FBBF24' }} />
                        Reguły biznesowe
                    </h3>
                    <div className="v2-card" style={{ padding: '18px 20px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                            <div>
                                <label style={labelStyle} title="ROAS = przychód / koszt. Minimalna wartość poniżej której system alarmuje">Minimalny ROAS</label>
                                <input style={inputStyle} type="number" step="0.1" value={formData.business_rules?.min_roas ?? ''} onChange={e => handleBusinessRule('min_roas', e.target.value)} placeholder="np. 2.0" />
                            </div>
                            <div>
                                <label style={labelStyle}>Max budżet dzienny (USD)</label>
                                <input style={inputStyle} type="number" step="1" value={formData.business_rules?.max_daily_budget ?? ''} onChange={e => handleBusinessRule('max_daily_budget', e.target.value)} placeholder="np. 500" />
                            </div>
                        </div>
                    </div>
                </section>

                {/* Safety Limits */}
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
                            {SAFETY_FIELDS.map(({ key, label, unit, multiply, tooltip }) => {
                                const clientVal = safetyLimits[key]
                                const displayVal = clientVal != null ? (clientVal * multiply).toFixed(multiply > 1 ? 0 : 2) : ''
                                const defaultVal = (GLOBAL_DEFAULTS[key] * multiply).toFixed(multiply > 1 ? 0 : 2)
                                return (
                                    <div key={key}>
                                        <label style={labelStyle} title={tooltip}>{label}</label>
                                        <div style={{ position: 'relative' }}>
                                            <input
                                                style={inputStyle}
                                                type="number"
                                                step={multiply > 1 ? '1' : '0.01'}
                                                value={displayVal}
                                                onChange={e => handleSafetyLimit(key, e.target.value, multiply)}
                                                placeholder={`domyślnie: ${defaultVal}${unit}`}
                                            />
                                            {unit && (
                                                <span style={{
                                                    position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                                                    fontSize: 11, color: 'rgba(255,255,255,0.2)', pointerEvents: 'none',
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
            </div>
        </div>
    )
}

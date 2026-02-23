import { useState, useEffect } from 'react'
import { LoadingSpinner, ErrorMessage, PageHeader, Badge } from '../components/UI'
import { getClient, updateClient } from '../api'
import { useApp } from '../contexts/AppContext'
import EmptyState from '../components/EmptyState'
import { Save, Plus, X, Globe, Building2, Target, StickyNote, ShieldAlert, BarChart3, Users, DollarSign } from 'lucide-react'

export default function Settings() {
    const { selectedClientId } = useApp()
    const [formData, setFormData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState(null)
    const [success, setSuccess] = useState(false)

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
        setSuccess(false)
        try {
            await updateClient(formData.id, formData)
            setSuccess(true)
            setTimeout(() => setSuccess(false), 3000)
        } catch (err) {
            setError(err.message)
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

    if (loading) return <LoadingSpinner />
    if (error) return <ErrorMessage message={error} onRetry={loadClient} />

    const Input = ({ label, value, onChange, icon: Icon, type = 'text', placeholder = '' }) => (
        <div>
            <label className="block text-[10px] text-surface-200/40 uppercase tracking-wider mb-1.5">{label}</label>
            <div className="relative">
                {Icon && (
                    <div className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-200/30">
                        <Icon size={14} />
                    </div>
                )}
                <input
                    type={type}
                    value={value || ''}
                    onChange={e => onChange(e.target.value)}
                    placeholder={placeholder}
                    className={`w-full bg-surface-700/40 border border-surface-700/60 rounded-lg py-2.5 text-sm text-white focus:outline-none focus:border-brand-500/50 transition-colors ${Icon ? 'pl-9 pr-4' : 'px-4'}`}
                />
            </div>
        </div>
    )

    const Textarea = ({ label, value, onChange, icon: Icon, rows = 3 }) => (
        <div>
            <label className="block text-[10px] text-surface-200/40 uppercase tracking-wider mb-1.5">{label}</label>
            <div className="relative">
                <textarea
                    value={value || ''}
                    onChange={e => onChange(e.target.value)}
                    rows={rows}
                    className="w-full bg-surface-700/40 border border-surface-700/60 rounded-lg p-3 text-sm text-white focus:outline-none focus:border-brand-500/50 transition-colors"
                />
                {Icon && (
                    <div className="absolute right-3 top-3 text-surface-200/30">
                        <Icon size={14} />
                    </div>
                )}
            </div>
        </div>
    )

    return (
        <div className="max-w-[1000px] mx-auto pb-12">
            <PageHeader title="Ustawienia klienta" subtitle="Zarządzaj kontekstem biznesowym i regułami automatyzacji">
                <div className="flex items-center gap-3">
                    {success && <Badge variant="success">Zapisano zmianę!</Badge>}
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                        <Save size={16} />
                        {saving ? 'Zapisywanie...' : 'Zapisz'}
                    </button>
                </div>
            </PageHeader>

            <div className="grid gap-8">
                {/* General Info */}
                <section>
                    <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                        <Building2 size={20} className="text-brand-400" />
                        Informacje ogólne
                    </h3>
                    <div className="glass rounded-xl p-6 grid lg:grid-cols-2 gap-6">
                        <Input
                            label="Nazwa klienta"
                            value={formData.name}
                            onChange={v => handleChange('name', v)}
                            icon={Building2}
                        />
                        <Input
                            label="Branża"
                            value={formData.industry}
                            onChange={v => handleChange('industry', v)}
                            icon={BarChart3}
                        />
                        <Input
                            label="Strona WWW"
                            value={formData.website}
                            onChange={v => handleChange('website', v)}
                            icon={Globe}
                        />
                        <Input
                            label="Google Customer ID"
                            value={formData.google_customer_id}
                            onChange={() => { }}
                            icon={ShieldAlert}
                        />
                        <div className="lg:col-span-2">
                            <Textarea
                                label="Notatki wewnętrzne"
                                value={formData.notes}
                                onChange={v => handleChange('notes', v)}
                                icon={StickyNote}
                            />
                        </div>
                    </div>
                </section>

                {/* Strategy */}
                <section>
                    <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                        <Target size={20} className="text-brand-400" />
                        Strategia i Konkurencja
                    </h3>
                    <div className="glass rounded-xl p-6 grid gap-6">
                        <div className="grid lg:grid-cols-2 gap-6">
                            <Textarea
                                label="Target Audience (Grupa docelowa)"
                                value={formData.target_audience}
                                onChange={v => handleChange('target_audience', v)}
                                icon={Users}
                            />
                            <Textarea
                                label="USP (Unikalna Propozycja Wartości)"
                                value={formData.usp}
                                onChange={v => handleChange('usp', v)}
                                icon={Target}
                            />
                        </div>

                        <div>
                            <label className="block text-[10px] text-surface-200/40 uppercase tracking-wider mb-2">Konkurencja</label>
                            <div className="flex flex-wrap gap-2">
                                {formData.competitors?.map((comp, i) => (
                                    <div key={i} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-surface-700/60 border border-surface-700/80 text-sm text-surface-200">
                                        {comp}
                                        <button onClick={() => removeCompetitor(i)} className="text-surface-200/40 hover:text-red-400">
                                            <X size={14} />
                                        </button>
                                    </div>
                                ))}
                                <button
                                    onClick={addCompetitor}
                                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-brand-600/10 border border-brand-500/20 text-brand-300 text-sm hover:bg-brand-600/20 transition-colors"
                                >
                                    <Plus size={14} />
                                    Dodaj
                                </button>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Business Rules */}
                <section>
                    <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                        <ShieldAlert size={20} className="text-brand-400" />
                        Zasady Biznesowe
                    </h3>
                    <div className="glass rounded-xl p-6 grid lg:grid-cols-2 gap-6">
                        <Input
                            label="Minimalny ROAS"
                            value={formData.business_rules?.min_roas}
                            onChange={v => handleBusinessRule('min_roas', v)}
                            type="number"
                            icon={BarChart3}
                        />
                        <Input
                            label="Maksymalny budżet dzienny (zabezpieczenie)"
                            value={formData.business_rules?.max_daily_budget}
                            onChange={v => handleBusinessRule('max_daily_budget', v)}
                            type="number"
                            icon={DollarSign}
                        />
                    </div>
                </section>
            </div>
        </div>
    )
}

import { useEffect, useState } from 'react'
import { MODAL_OVERLAY, MODAL_BOX } from '../../../components/UI'
import { getCampaigns, getAdGroups, addNegativeKeyword } from '../../../api'
import DarkSelect from '../../../components/DarkSelect'
import { INPUT_STYLE, BTN_PRIMARY, BTN_SECONDARY } from './shared'

export default function AddNegativeModal({ clientId, onClose, onDone, showToast }) {
    const [texts, setTexts] = useState('')
    const [matchType, setMatchType] = useState('PHRASE')
    const [scope, setScope] = useState('CAMPAIGN')
    const [campaignId, setCampaignId] = useState('')
    const [adGroupId, setAdGroupId] = useState('')
    const [campaigns, setCampaigns] = useState([])
    const [adGroups, setAdGroups] = useState([])
    const [submitting, setSubmitting] = useState(false)

    useEffect(() => {
        getCampaigns(clientId).then(r => {
            const items = r.items || r
            setCampaigns(items.filter(c => c.status !== 'REMOVED'))
        }).catch((err) => console.error('[Keywords] campaigns load failed', err))
    }, [clientId])

    useEffect(() => {
        if (scope === 'AD_GROUP' && campaignId) {
            getAdGroups({ client_id: clientId, campaign_id: campaignId }).then(r => {
                setAdGroups(Array.isArray(r) ? r : r.data || [])
            }).catch((err) => console.error('[Keywords] ad groups load failed', err))
        }
    }, [scope, campaignId, clientId])

    async function handleSubmit() {
        const lines = texts.split('\n').map(l => l.trim()).filter(Boolean)
        if (!lines.length) { showToast('Wpisz przynajmniej jedna fraze', 'error'); return }
        if (scope === 'CAMPAIGN' && !campaignId) { showToast('Wybierz kampanie', 'error'); return }
        if (scope === 'AD_GROUP' && !adGroupId) { showToast('Wybierz grupe reklam', 'error'); return }
        setSubmitting(true)
        try {
            const body = { client_id: clientId, texts: lines, match_type: matchType, negative_scope: scope }
            if (campaignId) body.campaign_id = Number(campaignId)
            if (scope === 'AD_GROUP' && adGroupId) body.ad_group_id = Number(adGroupId)
            await addNegativeKeyword(body)
            showToast(`Dodano ${lines.length} wykluczenie(-a)`, 'success')
            onDone()
        } catch { showToast('Blad dodawania', 'error') } finally { setSubmitting(false) }
    }

    return (
        <div style={MODAL_OVERLAY} onClick={onClose}>
            <div style={MODAL_BOX} onClick={e => e.stopPropagation()}>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', marginBottom: 16 }}>Dodaj wykluczenia</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div>
                        <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 4, display: 'block' }}>Frazy (po jednej na linie)</label>
                        <textarea value={texts} onChange={e => setTexts(e.target.value)} rows={5} style={{ ...INPUT_STYLE, resize: 'vertical' }} placeholder="darmowe&#10;za darmo&#10;DIY" />
                    </div>
                    <div className="flex gap-3">
                        <div style={{ flex: 1 }}>
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
                        <div style={{ flex: 1 }}>
                            <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 4, display: 'block' }}>Zakres</label>
                            <DarkSelect
                                value={scope}
                                onChange={(v) => { setScope(v); setAdGroupId('') }}
                                options={[
                                    { value: 'CAMPAIGN', label: 'Kampania' },
                                    { value: 'AD_GROUP', label: 'Grupa reklam' },
                                ]}
                            />
                        </div>
                    </div>
                    <div>
                        <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 4, display: 'block' }}>Kampania</label>
                        <DarkSelect
                            value={campaignId}
                            onChange={(v) => { setCampaignId(v); setAdGroupId('') }}
                            options={[
                                { value: '', label: '-- wybierz --' },
                                ...campaigns.map(c => ({ value: c.id, label: c.name })),
                            ]}
                            placeholder="-- wybierz --"
                        />
                    </div>
                    {scope === 'AD_GROUP' && (
                        <div>
                            <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 4, display: 'block' }}>Grupa reklam</label>
                            <DarkSelect
                                value={adGroupId}
                                onChange={(v) => setAdGroupId(v)}
                                options={[
                                    { value: '', label: '-- wybierz --' },
                                    ...adGroups.map(ag => ({ value: ag.id, label: ag.name })),
                                ]}
                                placeholder="-- wybierz --"
                            />
                        </div>
                    )}
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

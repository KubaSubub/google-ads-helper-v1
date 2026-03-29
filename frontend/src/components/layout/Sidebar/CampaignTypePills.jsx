import { useFilter } from '../../../contexts/FilterContext'
import { CAMPAIGN_TYPE_PILLS } from './navConfig'

export default function CampaignTypePills() {
    const { filters, setFilter } = useFilter()
    const activeCampType = filters.campaignType || 'ALL'

    return (
        <div style={{ padding: '6px 12px 2px' }}>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.1em', textTransform: 'uppercase', padding: '0 0 6px', fontWeight: 500 }}>
                Typ kampanii
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {CAMPAIGN_TYPE_PILLS.map(t => (
                    <button
                        key={t.value}
                        onClick={() => setFilter('campaignType', t.value)}
                        style={{
                            padding: '3px 10px', borderRadius: 999, fontSize: 10, fontWeight: 500,
                            cursor: 'pointer', border: 'none', transition: 'all 0.15s',
                            background: activeCampType === t.value ? '#4F8EF7' : 'transparent',
                            color: activeCampType === t.value ? '#FFFFFF' : 'rgba(255,255,255,0.45)',
                            outline: activeCampType === t.value ? 'none' : '1px solid rgba(255,255,255,0.1)',
                        }}
                    >{t.label}</button>
                ))}
            </div>
        </div>
    )
}

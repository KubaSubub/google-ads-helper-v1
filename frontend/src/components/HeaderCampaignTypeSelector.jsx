import { useFilter } from '../contexts/FilterContext'
import { CAMPAIGN_TYPE_PILLS } from './layout/Sidebar/navConfig'
import { C, TRANSITION } from '../constants/designTokens'

export default function HeaderCampaignTypeSelector() {
    const { filters, setFilter } = useFilter()
    const active = filters.campaignType || 'ALL'

    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            padding: 3,
            borderRadius: 10,
            background: C.w04,
            border: `1px solid ${C.w08}`,
            height: 36,
        }}>
            {CAMPAIGN_TYPE_PILLS.map(t => {
                const isActive = active === t.value
                return (
                    <button
                        key={t.value}
                        onClick={() => setFilter('campaignType', t.value)}
                        style={{
                            padding: '0 12px',
                            height: 28,
                            borderRadius: 7,
                            fontSize: 11,
                            fontWeight: 500,
                            cursor: 'pointer',
                            border: 'none',
                            background: isActive ? 'rgba(79,142,247,0.18)' : 'transparent',
                            color: isActive ? '#FFFFFF' : C.w50,
                            transition: TRANSITION.fast,
                            whiteSpace: 'nowrap',
                        }}
                        className={!isActive ? 'hover:bg-white/[0.05] hover:text-white/80' : ''}
                    >
                        {t.label}
                    </button>
                )
            })}
        </div>
    )
}

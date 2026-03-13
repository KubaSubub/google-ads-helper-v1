import { useFilter } from '../contexts/FilterContext'

const CAMPAIGN_TYPES = [
    { value: 'ALL', label: 'Wszystkie' },
    { value: 'SEARCH', label: 'Search' },
    { value: 'PERFORMANCE_MAX', label: 'PMax' },
    { value: 'DISPLAY', label: 'Display' },
    { value: 'SHOPPING', label: 'Shopping' },
]

const STATUSES = [
    { value: 'ENABLED', label: 'Aktywne' },
    { value: 'PAUSED', label: 'Wstrzymane' },
    { value: 'REMOVED', label: 'Usuniete' },
    { value: 'ALL', label: 'Wszystkie' },
]

const PERIODS = [
    { value: 7, label: '7d' },
    { value: 14, label: '14d' },
    { value: 30, label: '30d' },
    { value: 90, label: '90d' },
]

function PillGroup({ items, activeValue, onSelect, valueKey = 'value', labelKey = 'label' }) {
    return (
        <div className="flex items-center gap-1">
            {items.map(item => {
                const val = item[valueKey]
                const active = val === activeValue
                return (
                    <button
                        key={val}
                        onClick={() => onSelect(val)}
                        style={{
                            padding: '4px 10px',
                            borderRadius: 999,
                            fontSize: 12,
                            fontWeight: active ? 500 : 400,
                            border: `1px solid ${active ? '#4F8EF7' : 'rgba(255,255,255,0.1)'}`,
                            background: active ? 'rgba(79,142,247,0.2)' : 'transparent',
                            color: active ? 'white' : 'rgba(255,255,255,0.45)',
                            cursor: 'pointer',
                            transition: 'all 0.15s',
                            whiteSpace: 'nowrap',
                        }}
                        className="hover:border-white/20 hover:text-white/70"
                    >
                        {item[labelKey]}
                    </button>
                )
            })}
        </div>
    )
}

const SEP = () => (
    <div style={{ width: 1, height: 18, background: 'rgba(255,255,255,0.08)', flexShrink: 0 }} />
)

export default function FilterBar({ hideCampaignType = false, hidePeriod = false }) {
    const { filters, setFilter } = useFilter()

    return (
        <div
            className="flex items-center gap-4 flex-wrap"
            style={{ fontSize: 12 }}
        >
            {!hideCampaignType && (
                <>
                    <PillGroup
                        items={CAMPAIGN_TYPES}
                        activeValue={filters.campaignType}
                        onSelect={v => setFilter('campaignType', v)}
                    />
                    <SEP />
                </>
            )}

            <PillGroup
                items={STATUSES}
                activeValue={filters.status}
                onSelect={v => setFilter('status', v)}
            />

            {!hidePeriod && (
                <>
                    <SEP />
                    <PillGroup
                        items={PERIODS}
                        activeValue={filters.period}
                        onSelect={v => setFilter('period', v)}
                    />
                </>
            )}
        </div>
    )
}

import { ChevronDown } from 'lucide-react'
import { useFilter } from '../contexts/FilterContext'
import { CAMPAIGN_STATUS_OPTIONS, CAMPAIGN_TYPE_OPTIONS } from '../constants/globalFilters'

const CONTROL_STYLE = {
    width: '100%',
    height: 40,
    borderRadius: 10,
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.1)',
    color: '#F0F0F0',
    fontSize: 13,
    padding: '0 38px 0 12px',
    outline: 'none',
    appearance: 'none',
    WebkitAppearance: 'none',
    MozAppearance: 'none',
}

function FilterField({ label, children }) {
    return (
        <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.32)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 6 }}>
                {label}
            </div>
            {children}
        </div>
    )
}

function SelectField({ label, value, onChange, options }) {
    return (
        <FilterField label={label}>
            <div style={{ position: 'relative' }}>
                <select value={value} onChange={onChange} style={CONTROL_STYLE}>
                    {options.map((option) => (
                        <option key={option.value} value={option.value}>
                            {option.label}
                        </option>
                    ))}
                </select>
                <ChevronDown size={14} style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', color: 'rgba(255,255,255,0.35)', pointerEvents: 'none' }} />
            </div>
        </FilterField>
    )
}

export default function GlobalFilterBar() {
    const { filters, setFilter } = useFilter()

    return (
        <div className="v2-card" style={{ padding: '16px 18px', marginBottom: 24 }}>
            <div className="flex items-center justify-between flex-wrap gap-3" style={{ marginBottom: 14 }}>
                <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                        Filtry kampanii
                    </div>
                    <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.38)', marginTop: 2 }}>
                        Wspolne filtrowanie widokow bez dublowania klienta i dat.
                    </div>
                </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2" style={{ alignItems: 'start' }}>
                <SelectField
                    label="Typ kampanii"
                    value={filters.campaignType}
                    onChange={(event) => setFilter('campaignType', event.target.value)}
                    options={CAMPAIGN_TYPE_OPTIONS}
                />
                <SelectField
                    label="Status kampanii"
                    value={filters.status}
                    onChange={(event) => setFilter('status', event.target.value)}
                    options={CAMPAIGN_STATUS_OPTIONS}
                />
            </div>
        </div>
    )
}

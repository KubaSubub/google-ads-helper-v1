import { useMemo } from 'react'
import { useFilter } from '../contexts/FilterContext'
import { useApp } from '../contexts/AppContext'
import { CAMPAIGN_STATUS_OPTIONS } from '../constants/globalFilters'
import DarkSelect from './DarkSelect'
import { Search } from 'lucide-react'
import { getCampaigns } from '../api'
import { useState, useEffect } from 'react'
import { C, T, S, R, B, PILL, MODAL, TOOLTIP_STYLE, SEVERITY, TRANSITION, FONT } from '../constants/designTokens'

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

export default function GlobalFilterBar() {
    const { filters, setFilter } = useFilter()
    const { selectedClientId } = useApp()
    const [allLabels, setAllLabels] = useState([])

    useEffect(() => {
        if (!selectedClientId) return
        getCampaigns(selectedClientId)
            .then((data) => {
                const items = Array.isArray(data) ? data : data.items || []
                const labelSet = new Set()
                items.forEach((c) => {
                    if (Array.isArray(c.labels)) {
                        c.labels.forEach((l) => labelSet.add(l))
                    }
                })
                setAllLabels([...labelSet].sort())
            })
            .catch(() => setAllLabels([]))
    }, [selectedClientId])

    const labelOptions = useMemo(() => [
        { value: 'ALL', label: 'Wszystkie' },
        ...allLabels.map((l) => ({ value: l, label: l })),
    ], [allLabels])

    const hasLabels = allLabels.length > 0

    return (
        <div className="v2-card" style={{ padding: '14px 18px', marginBottom: 24 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne', marginBottom: 12 }}>
                Filtry kampanii
            </div>

            <div className="grid gap-4" style={{ alignItems: 'start', gridTemplateColumns: hasLabels ? 'repeat(3, 1fr)' : 'repeat(2, 1fr)' }}>
                <FilterField label="Status">
                    <DarkSelect
                        value={filters.status}
                        onChange={(v) => setFilter('status', v)}
                        options={CAMPAIGN_STATUS_OPTIONS}
                        style={{ height: 38 }}
                    />
                </FilterField>
                {hasLabels && (
                    <FilterField label="Etykieta">
                        <DarkSelect
                            value={filters.campaignLabel}
                            onChange={(v) => setFilter('campaignLabel', v)}
                            options={labelOptions}
                            style={{ height: 38 }}
                        />
                    </FilterField>
                )}
                <FilterField label="Nazwa kampanii">
                    <div style={{ position: 'relative' }}>
                        <Search size={13} style={{
                            position: 'absolute',
                            left: 10,
                            top: '50%',
                            transform: 'translateY(-50%)',
                            color: C.w25,
                            pointerEvents: 'none',
                        }} />
                        <input
                            type="text"
                            value={filters.campaignName}
                            onChange={(e) => setFilter('campaignName', e.target.value)}
                            placeholder="Szukaj..."
                            style={{
                                width: '100%',
                                height: 38,
                                padding: '0 10px 0 30px',
                                borderRadius: 8,
                                fontSize: 13,
                                color: C.textPrimary,
                                background: C.w04,
                                border: `1px solid ${C.w08}`,
                                outline: 'none',
                                transition: 'border-color 0.15s',
                            }}
                            onFocus={(e) => e.target.style.borderColor = 'rgba(79,142,247,0.4)'}
                            onBlur={(e) => e.target.style.borderColor = C.w08}
                        />
                    </div>
                </FilterField>
            </div>
        </div>
    )
}

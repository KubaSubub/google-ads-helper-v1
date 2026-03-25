import { createContext, useContext, useState, useMemo } from 'react';

const FilterContext = createContext(null);

function daysAgo(n) {
    const d = new Date();
    d.setDate(d.getDate() - n);
    return d.toISOString().slice(0, 10);
}

const today = () => new Date().toISOString().slice(0, 10);

function computePresetDates(preset) {
    const now = new Date();
    if (typeof preset === 'number') {
        return { from: daysAgo(preset), to: today() };
    }
    switch (preset) {
        case 'this_month': {
            const from = new Date(now.getFullYear(), now.getMonth(), 1);
            return { from: from.toISOString().slice(0, 10), to: today() };
        }
        case 'prev_month': {
            const from = new Date(now.getFullYear(), now.getMonth() - 1, 1);
            const to = new Date(now.getFullYear(), now.getMonth(), 0);
            return { from: from.toISOString().slice(0, 10), to: to.toISOString().slice(0, 10) };
        }
        case 'this_quarter': {
            const q = Math.floor(now.getMonth() / 3);
            const from = new Date(now.getFullYear(), q * 3, 1);
            return { from: from.toISOString().slice(0, 10), to: today() };
        }
        case 'all_time':
            return { from: '2020-01-01', to: today() };
        default:
            return { from: daysAgo(30), to: today() };
    }
}

export const DATE_PRESETS = [
    { value: 7,              label: '7 dni' },
    { value: 14,             label: '14 dni' },
    { value: 30,             label: '30 dni' },
    { value: 90,             label: '90 dni' },
    { value: 'this_month',   label: 'Ten miesiąc' },
    { value: 'prev_month',   label: 'Poprz. miesiąc' },
    { value: 'this_quarter', label: 'Ten kwartał' },
    { value: 'all_time',     label: 'Od początku konta' },
];

const defaultFilters = {
    campaignType: 'ALL',
    status: 'ALL',
    campaignName: '',
    campaignLabel: 'ALL',
    period: 30,
    dateFrom: daysAgo(30),
    dateTo: today(),
};

export function FilterProvider({ children }) {
    const [filters, setFilters] = useState(defaultFilters);

    function setFilter(key, value) {
        setFilters(prev => {
            const next = { ...prev, [key]: value };
            if (key === 'period') {
                const { from, to } = computePresetDates(value);
                next.dateFrom = from;
                next.dateTo = to;
            }
            if (key === 'dateFrom' || key === 'dateTo') {
                next.period = null;
            }
            return next;
        });
    }

    function resetFilters() {
        setFilters(defaultFilters);
    }

    // Computed days count for backward compatibility with APIs using `days` param
    const days = useMemo(() => {
        if (filters.period) return filters.period;
        const from = new Date(filters.dateFrom);
        const to = new Date(filters.dateTo);
        return Math.max(1, Math.round((to - from) / 86400000));
    }, [filters.period, filters.dateFrom, filters.dateTo]);

    // Pre-built param objects for API calls — avoids per-page boilerplate
    const dateParams = useMemo(() => ({
        date_from: filters.dateFrom,
        date_to: filters.dateTo,
    }), [filters.dateFrom, filters.dateTo]);

    const campaignParams = useMemo(() => {
        const p = {};
        if (filters.campaignType !== 'ALL') p.campaign_type = filters.campaignType;
        if (filters.status !== 'ALL') p.campaign_status = filters.status;
        if (filters.campaignName) p.campaign_name = filters.campaignName;
        if (filters.campaignLabel !== 'ALL') p.campaign_label = filters.campaignLabel;
        return p;
    }, [filters.campaignType, filters.status, filters.campaignName, filters.campaignLabel]);

    const allParams = useMemo(() => ({
        ...dateParams,
        ...campaignParams,
    }), [dateParams, campaignParams]);

    return (
        <FilterContext.Provider value={{ filters, setFilter, resetFilters, days, dateParams, campaignParams, allParams }}>
            {children}
        </FilterContext.Provider>
    );
}

export function useFilter() {
    const ctx = useContext(FilterContext);
    if (!ctx) throw new Error('useFilter must be inside FilterProvider');
    return ctx;
}


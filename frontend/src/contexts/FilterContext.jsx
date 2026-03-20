import { createContext, useContext, useState, useMemo } from 'react';

const FilterContext = createContext(null);

function daysAgo(n) {
    const d = new Date();
    d.setDate(d.getDate() - n);
    return d.toISOString().slice(0, 10);
}

const today = () => new Date().toISOString().slice(0, 10);

const defaultFilters = {
    campaignType: 'ALL',   // 'ALL' | 'SEARCH' | 'PERFORMANCE_MAX' | 'DISPLAY' | 'SHOPPING'
    status: 'ALL',         // 'ALL' | 'ENABLED' | 'PAUSED' | 'REMOVED'
    period: 30,            // 7 | 14 | 30 | 90 (quick-select) or null (custom range)
    dateFrom: daysAgo(30), // YYYY-MM-DD
    dateTo: today(),
};

export function FilterProvider({ children }) {
    const [filters, setFilters] = useState(defaultFilters);

    function setFilter(key, value) {
        setFilters(prev => {
            const next = { ...prev, [key]: value };
            // When period changes, auto-update dateFrom/dateTo
            if (key === 'period') {
                next.dateFrom = daysAgo(value);
                next.dateTo = today();
            }
            // When dateFrom/dateTo is set manually, clear period preset
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
        return p;
    }, [filters.campaignType, filters.status]);

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


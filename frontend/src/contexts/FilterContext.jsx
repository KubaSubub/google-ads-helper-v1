import { createContext, useContext, useState } from 'react';

const FilterContext = createContext(null);

const defaultFilters = {
    campaignType: 'ALL',   // 'ALL' | 'SEARCH' | 'PERFORMANCE_MAX' | 'DISPLAY' | 'SHOPPING'
    status: 'ALL',         // 'ALL' | 'ENABLED' | 'PAUSED'
    period: 30,            // 7 | 14 | 30 | 90 (dni)
};

export function FilterProvider({ children }) {
    const [filters, setFilters] = useState(defaultFilters);

    function setFilter(key, value) {
        setFilters(prev => ({ ...prev, [key]: value }));
    }

    function resetFilters() {
        setFilters(defaultFilters);
    }

    return (
        <FilterContext.Provider value={{ filters, setFilter, resetFilters }}>
            {children}
        </FilterContext.Provider>
    );
}

export function useFilter() {
    const ctx = useContext(FilterContext);
    if (!ctx) throw new Error('useFilter must be inside FilterProvider');
    return ctx;
}

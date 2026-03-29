// Campaign type labels and status config used across multiple pages

export const TYPE_LABELS = {
    SEARCH: 'Search',
    PERFORMANCE_MAX: 'PMax',
    SHOPPING: 'Shopping',
    DISPLAY: 'Display',
    VIDEO: 'Video',
    DISCOVERY: 'Discovery',
    SMART: 'Smart',
    LOCAL: 'Local',
    APP: 'App',
    HOTEL: 'Hotel',
    UNKNOWN: 'Inne',
}

export const STATUS_CONFIG = {
    ENABLED:  { label: 'Aktywna',     color: '#4ADE80', bg: 'rgba(74,222,128,0.1)',  border: 'rgba(74,222,128,0.2)' },
    PAUSED:   { label: 'Wstrzymana',  color: '#FBBF24', bg: 'rgba(251,191,36,0.1)',  border: 'rgba(251,191,36,0.2)' },
    REMOVED:  { label: 'Usunięta',    color: '#F87171', bg: 'rgba(248,113,113,0.1)', border: 'rgba(248,113,113,0.2)' },
}

export const CAMP_TYPES = ['ALL', 'SEARCH', 'PERFORMANCE_MAX', 'SHOPPING', 'DISPLAY', 'VIDEO']

export const CAMP_LABELS = {
    ALL: 'Wszystkie',
    SEARCH: 'Search',
    PERFORMANCE_MAX: 'PMax',
    SHOPPING: 'Shopping',
    DISPLAY: 'Display',
    VIDEO: 'Video',
}

import {
    Award,
    BarChart3,
    Bell,
    Brain,
    Calendar,
    ClipboardCheck,
    Crosshair,
    FileBarChart2,
    GitCompare,
    History,
    KeyRound,
    Layers,
    LayoutDashboard,
    Lightbulb,
    Megaphone,
    Monitor,
    Search,
    Settings2,
    ShoppingCart,
    Sparkles,
    Youtube,
    ListChecks,
    Zap,
} from 'lucide-react'

export const NAV_GROUPS = [
    {
        label: 'PRZEGLĄD',
        always: true,
        items: [
            { to: '/', label: 'Pulpit', icon: LayoutDashboard },
            { to: '/daily-audit', label: 'Poranny przegląd', icon: ClipboardCheck },
        ],
    },
    {
        label: 'DANE KAMPANII',
        items: [
            { to: '/campaigns', label: 'Kampanie', icon: Megaphone },
            { to: '/keywords', label: 'Słowa kluczowe', icon: KeyRound, types: ['SEARCH'] },
            { to: '/search-terms', label: 'Wyszukiwane frazy', icon: Search, types: ['SEARCH', 'PERFORMANCE_MAX'] },
            { to: '/shopping', label: 'Produkty', icon: ShoppingCart, types: ['SHOPPING'] },
            { to: '/pmax', label: 'Performance Max', icon: Layers, types: ['PERFORMANCE_MAX'] },
            { to: '/display', label: 'Display', icon: Monitor, types: ['DISPLAY'] },
            { to: '/video', label: 'Video / YouTube', icon: Youtube, types: ['VIDEO'] },
        ],
    },
    {
        label: 'DZIAŁANIA',
        items: [
            { to: '/tasks', label: 'Plan dnia', icon: ListChecks },
            { to: '/recommendations', label: 'Rekomendacje', icon: Lightbulb },
            { to: '/rules', label: 'Reguły', icon: Settings2 },
            { to: '/action-history', label: 'Historia zmian', icon: History },
        ],
    },
    {
        label: 'MONITORING',
        items: [
            { to: '/alerts', label: 'Monitoring', icon: Bell, showBadge: true },
        ],
    },
    {
        label: 'AI',
        items: [
            { to: '/agent', label: 'Asystent AI', icon: Sparkles },
            { to: '/reports', label: 'Raporty', icon: FileBarChart2 },
        ],
    },
    {
        label: 'ANALIZA',
        items: [
            { to: '/audit-center', label: 'Centrum audytu', icon: Zap },
            { to: '/competitive', label: 'Konkurencja', icon: Crosshair },
            { to: '/cross-campaign', label: 'Analiza cross', icon: GitCompare },
            { to: '/benchmarks', label: 'Benchmarki', icon: BarChart3 },
            { to: '/forecast', label: 'Prognoza', icon: Calendar, types: ['SEARCH'] },
            { to: '/semantic', label: 'Inteligencja', icon: Brain, types: ['SEARCH'] },
            { to: '/quality-score', label: 'Wynik jakości', icon: Award, types: ['SEARCH'] },
        ],
    },
]

export const CAMPAIGN_TYPE_PILLS = [
    { value: 'ALL', label: 'Wszystkie' },
    { value: 'SEARCH', label: 'Search' },
    { value: 'PERFORMANCE_MAX', label: 'PMax' },
    { value: 'SHOPPING', label: 'Shopping' },
    { value: 'DISPLAY', label: 'Display' },
    { value: 'VIDEO', label: 'Video' },
]

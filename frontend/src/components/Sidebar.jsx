import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
    Award,
    Bell,
    Brain,
    Calendar,
    ChevronRight,
    ClipboardCheck,
    History,
    KeyRound,
    LayoutDashboard,
    Lightbulb,
    LogOut,
    Megaphone,
    Menu,
    Search,
    Settings,
    FileBarChart2,
    Sparkles,
    Users,
    X,
    Zap,
} from 'lucide-react'
import clsx from 'clsx'
import { useApp } from '../contexts/AppContext'
import { useFilter } from '../contexts/FilterContext'
import { logout } from '../api'

const NAV_GROUPS = [
    {
        label: 'PRZEGLAD',
        items: [
            { to: '/', label: 'Pulpit', icon: LayoutDashboard },
            { to: '/daily-audit', label: 'Codzienny audyt', icon: ClipboardCheck },
            { to: '/clients', label: 'Klienci', icon: Users },
        ],
    },
    {
        label: 'DANE KAMPANII',
        items: [
            { to: '/campaigns', label: 'Kampanie', icon: Megaphone },
            { to: '/keywords', label: 'Slowa kluczowe', icon: KeyRound },
            { to: '/search-terms', label: 'Wyszukiwane frazy', icon: Search },
        ],
    },
    {
        label: 'DZIALANIA',
        items: [
            { to: '/recommendations', label: 'Rekomendacje', icon: Lightbulb },
            { to: '/action-history', label: 'Historia akcji', icon: History },
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
            { to: '/agent', label: 'Raport AI', icon: Sparkles },
            { to: '/reports', label: 'Raporty', icon: FileBarChart2 },
        ],
    },
    {
        label: 'ANALIZA',
        items: [
            { to: '/search-optimization', label: 'Optymalizacja', icon: Zap },
            { to: '/forecast', label: 'Prognoza', icon: Calendar },
            { to: '/semantic', label: 'Inteligencja', icon: Brain },
            { to: '/quality-score', label: 'Wynik jakosci', icon: Award },
        ],
    },
]

const PERIOD_PRESETS = [
    { label: '7d', value: 7 },
    { label: '14d', value: 14 },
    { label: '30d', value: 30 },
    { label: '90d', value: 90 },
]

function NavItem({ to, label, icon: Icon, showBadge, alertCount, onClick }) {
    const location = useLocation()
    const active = location.pathname === to || (to !== '/' && location.pathname.startsWith(to))

    return (
        <NavLink
            to={to}
            onClick={onClick}
            className={clsx(
                'group flex items-center gap-2.5 px-2 py-[7px] rounded-[7px] text-sm transition-all duration-150 relative',
                active
                    ? 'text-white font-medium'
                    : 'text-white/55 hover:text-white/85 hover:bg-white/[0.05]'
            )}
            style={active ? {
                background: 'rgba(79,142,247,0.15)',
                borderLeft: '2px solid #4F8EF7',
                borderRadius: '0 7px 7px 0',
                paddingLeft: '6px',
            } : {}}
        >
            <Icon size={15} style={{ width: 18, flexShrink: 0, textAlign: 'center' }} />
            <span className="flex-1 text-[13.5px]">{label}</span>
            {showBadge && alertCount > 0 && (
                <span
                    style={{
                        background: '#EF4444',
                        fontSize: 10,
                        padding: '1px 6px',
                        borderRadius: 999,
                        color: 'white',
                        fontWeight: 600,
                        lineHeight: '16px',
                    }}
                >
                    {alertCount}
                </span>
            )}
        </NavLink>
    )
}

function DateRangePicker() {
    const { filters, setFilter } = useFilter()
    const [showCustom, setShowCustom] = useState(filters.period === null)

    return (
        <div style={{ padding: '0 10px 8px' }}>
            <div
                style={{
                    background: 'rgba(255,255,255,0.04)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: 10,
                    padding: '8px 10px',
                }}
            >
                <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 6 }}>
                    Zakres dat
                </div>
                <div style={{ display: 'flex', gap: 4, marginBottom: showCustom ? 8 : 0 }}>
                    {PERIOD_PRESETS.map((preset) => {
                        const active = filters.period === preset.value
                        return (
                            <button
                                key={preset.value}
                                onClick={() => {
                                    setFilter('period', preset.value)
                                    setShowCustom(false)
                                }}
                                style={{
                                    flex: 1,
                                    padding: '4px 0',
                                    borderRadius: 6,
                                    fontSize: 11,
                                    fontWeight: active ? 600 : 400,
                                    border: `1px solid ${active ? '#4F8EF7' : 'rgba(255,255,255,0.08)'}`,
                                    background: active ? 'rgba(79,142,247,0.18)' : 'transparent',
                                    color: active ? '#4F8EF7' : 'rgba(255,255,255,0.4)',
                                    cursor: 'pointer',
                                    transition: 'all 0.15s',
                                }}
                            >
                                {preset.label}
                            </button>
                        )
                    })}
                    <button
                        onClick={() => setShowCustom((current) => !current)}
                        title="Wlasny zakres"
                        style={{
                            padding: '4px 6px',
                            borderRadius: 6,
                            fontSize: 11,
                            border: `1px solid ${filters.period === null ? '#4F8EF7' : 'rgba(255,255,255,0.08)'}`,
                            background: filters.period === null ? 'rgba(79,142,247,0.18)' : 'transparent',
                            color: filters.period === null ? '#4F8EF7' : 'rgba(255,255,255,0.4)',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                        }}
                    >
                        <Calendar size={11} />
                    </button>
                </div>
                {showCustom && (
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <input
                            type="date"
                            value={filters.dateFrom}
                            onChange={(event) => setFilter('dateFrom', event.target.value)}
                            style={{
                                flex: 1,
                                padding: '4px 6px',
                                borderRadius: 6,
                                fontSize: 11,
                                background: 'rgba(255,255,255,0.06)',
                                border: '1px solid rgba(255,255,255,0.1)',
                                color: 'rgba(255,255,255,0.7)',
                                outline: 'none',
                            }}
                        />
                        <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)' }}>-</span>
                        <input
                            type="date"
                            value={filters.dateTo}
                            onChange={(event) => setFilter('dateTo', event.target.value)}
                            style={{
                                flex: 1,
                                padding: '4px 6px',
                                borderRadius: 6,
                                fontSize: 11,
                                background: 'rgba(255,255,255,0.06)',
                                border: '1px solid rgba(255,255,255,0.1)',
                                color: 'rgba(255,255,255,0.7)',
                                outline: 'none',
                            }}
                        />
                    </div>
                )}
            </div>
        </div>
    )
}

function SidebarContent({ onNavigate }) {
    const { selectedClientId, setSelectedClientId, alertCount, clients } = useApp()
    const selectedClient = clients.find((client) => client.id === selectedClientId)

    const handleLogout = async () => {
        try {
            await logout()
        } catch {}
        window.location.reload()
    }

    return (
        <div className="flex flex-col h-full" style={{ background: '#111318' }}>
            <div style={{ borderBottom: '1px solid rgba(255,255,255,0.07)', padding: '16px 16px 14px' }}>
                <div className="flex items-center gap-2.5">
                    <div
                        style={{
                            width: 32,
                            height: 32,
                            borderRadius: 8,
                            flexShrink: 0,
                            background: 'linear-gradient(135deg, #4F8EF7 0%, #7B5CE0 100%)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                        }}
                    >
                        <Zap size={16} className="text-white" />
                    </div>
                    <div>
                        <div className="text-white font-semibold text-[13px] leading-tight" style={{ fontFamily: 'DM Sans' }}>
                            Google Ads
                        </div>
                        <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
                            Helper
                        </div>
                    </div>
                </div>
            </div>

            <div style={{ padding: '10px 10px 8px' }}>
                <div
                    style={{
                        position: 'relative',
                        overflow: 'hidden',
                        background: 'rgba(255,255,255,0.04)',
                        border: '1px solid rgba(255,255,255,0.08)',
                        borderRadius: 10,
                        padding: '8px 10px',
                        cursor: 'pointer',
                        transition: 'background 0.15s',
                    }}
                    className="hover:bg-white/[0.06]"
                >
                    <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 5 }}>
                        Aktywny klient
                    </div>
                    {selectedClient ? (
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2 min-w-0">
                                <span
                                    style={{
                                        width: 6,
                                        height: 6,
                                        borderRadius: '50%',
                                        flexShrink: 0,
                                        background: '#4ADE80',
                                        boxShadow: '0 0 6px #4ade80',
                                    }}
                                />
                                <span className="text-white text-[13px] font-medium truncate">{selectedClient.name}</span>
                            </div>
                            <ChevronRight size={14} style={{ color: 'rgba(255,255,255,0.3)', flexShrink: 0 }} />
                        </div>
                    ) : (
                        <div className="flex items-center justify-between">
                            <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: 13 }}>Wybierz klienta...</span>
                            <ChevronRight size={14} style={{ color: 'rgba(255,255,255,0.3)' }} />
                        </div>
                    )}
                    {selectedClient && (
                        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', marginTop: 3 }}>
                            Sync * aktywny
                        </div>
                    )}
                    <select
                        value={selectedClientId || ''}
                        onChange={(event) => setSelectedClientId(event.target.value ? Number(event.target.value) : null)}
                        style={{
                            position: 'absolute',
                            opacity: 0,
                            inset: 0,
                            width: '100%',
                            height: '100%',
                            cursor: 'pointer',
                        }}
                    >
                        <option value="">Wybierz klienta...</option>
                        {clients.map((client) => (
                            <option key={client.id} value={client.id}>{client.name}</option>
                        ))}
                    </select>
                </div>
            </div>

            <DateRangePicker />

            <nav className="flex-1 overflow-y-auto" style={{ padding: '4px 8px' }}>
                {NAV_GROUPS.map((group) => (
                    <div key={group.label} style={{ marginBottom: 4 }}>
                        <div
                            style={{
                                fontSize: 10,
                                color: 'rgba(255,255,255,0.3)',
                                letterSpacing: '0.1em',
                                textTransform: 'uppercase',
                                padding: '8px 8px 4px',
                                fontWeight: 500,
                            }}
                        >
                            {group.label}
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                            {group.items.map((item) => (
                                <NavItem
                                    key={item.to}
                                    {...item}
                                    alertCount={alertCount}
                                    onClick={onNavigate}
                                />
                            ))}
                        </div>
                    </div>
                ))}
            </nav>

            <div style={{ borderTop: '1px solid rgba(255,255,255,0.07)', padding: '8px 8px 10px' }}>
                <NavItem to="/settings" label="Ustawienia" icon={Settings} onClick={onNavigate} />
                <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)', margin: '6px 0' }} />
                <div className="flex items-center gap-2.5 px-2 py-1.5">
                    <div
                        style={{
                            width: 28,
                            height: 28,
                            borderRadius: '50%',
                            flexShrink: 0,
                            background: 'linear-gradient(135deg, #4F8EF7, #7B5CE0)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: 11,
                            color: 'white',
                            fontWeight: 600,
                        }}
                    >
                        GA
                    </div>
                    <div className="flex-1 min-w-0">
                        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)', fontWeight: 500 }}>Uzytkownik</div>
                        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)' }}>Admin</div>
                    </div>
                    <button
                        onClick={handleLogout}
                        style={{ color: 'rgba(255,255,255,0.3)', padding: 4, borderRadius: 6 }}
                        className="hover:text-red-400 hover:bg-red-500/10 transition-colors"
                        title="Wyloguj"
                    >
                        <LogOut size={14} />
                    </button>
                </div>
            </div>
        </div>
    )
}

export default function Sidebar() {
    const [mobileOpen, setMobileOpen] = useState(false)

    return (
        <>
            <div
                className="lg:hidden fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 py-3"
                style={{ background: 'rgba(17,19,24,0.95)', backdropFilter: 'blur(12px)', borderBottom: '1px solid rgba(255,255,255,0.07)' }}
            >
                <div className="flex items-center gap-2">
                    <div
                        style={{
                            width: 28,
                            height: 28,
                            borderRadius: 7,
                            background: 'linear-gradient(135deg, #4F8EF7, #7B5CE0)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                        }}
                    >
                        <Zap size={14} className="text-white" />
                    </div>
                    <span style={{ fontSize: 13, fontWeight: 600, color: 'white' }}>Google Ads Helper</span>
                </div>
                <button
                    onClick={() => setMobileOpen((open) => !open)}
                    style={{ padding: 6, borderRadius: 7, color: 'rgba(255,255,255,0.5)' }}
                    className="hover:bg-white/5"
                >
                    {mobileOpen ? <X size={20} /> : <Menu size={20} />}
                </button>
            </div>

            {mobileOpen && (
                <div
                    className="lg:hidden fixed inset-0 z-40"
                    style={{ background: 'rgba(0,0,0,0.6)' }}
                    onClick={() => setMobileOpen(false)}
                >
                    <div
                        className="absolute left-0 top-0 bottom-0 w-64"
                        style={{ paddingTop: 56 }}
                        onClick={(event) => event.stopPropagation()}
                    >
                        <SidebarContent onNavigate={() => setMobileOpen(false)} />
                    </div>
                </div>
            )}

            <aside className="hidden lg:flex flex-col w-64 flex-shrink-0" style={{ borderRight: '1px solid rgba(255,255,255,0.07)' }}>
                <SidebarContent onNavigate={undefined} />
            </aside>
        </>
    )
}

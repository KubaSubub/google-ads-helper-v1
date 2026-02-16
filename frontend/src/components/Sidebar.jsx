import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
    LayoutDashboard,
    Megaphone,
    Search,
    KeyRound,
    AlertTriangle,
    Settings,
    Brain,
    Zap,
    Lightbulb,
    Award,
    TrendingUp,
    Menu,
    X,
} from 'lucide-react'
import clsx from 'clsx'

const nav = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/campaigns', label: 'Kampanie', icon: Megaphone },
    { to: '/search-terms', label: 'Search Terms', icon: Search },
    { to: '/keywords', label: 'Słowa kluczowe', icon: KeyRound },
    { to: '/anomalies', label: 'Anomalie', icon: AlertTriangle },
    { to: '/semantic', label: 'Inteligencja', icon: Brain },
    { to: '/recommendations', label: 'Rekomendacje', icon: Lightbulb },
    { to: '/quality-score', label: 'Quality Score', icon: Award },
    { to: '/forecast', label: 'Prognozy (AI)', icon: TrendingUp },
    { to: '/settings', label: 'Ustawienia', icon: Settings },
]

export default function Sidebar() {
    const location = useLocation()
    const [mobileOpen, setMobileOpen] = useState(false)

    const NavItems = () => (
        <>
            {nav.map(({ to, label, icon: Icon }) => {
                const active = location.pathname === to
                return (
                    <NavLink
                        key={to}
                        to={to}
                        onClick={() => setMobileOpen(false)}
                        className={clsx(
                            'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                            active
                                ? 'bg-brand-600/20 text-brand-300 border border-brand-500/30 glow-brand'
                                : 'text-surface-200/60 hover:text-surface-200 hover:bg-surface-700/40'
                        )}
                    >
                        <Icon size={18} />
                        {label}
                    </NavLink>
                )
            })}
        </>
    )

    return (
        <>
            {/* Mobile header */}
            <div className="lg:hidden fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 py-3 bg-surface-900/95 backdrop-blur-xl border-b border-surface-700/40">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
                        <Zap size={16} className="text-white" />
                    </div>
                    <span className="text-sm font-bold text-white">Google Ads Helper</span>
                </div>
                <button
                    onClick={() => setMobileOpen(!mobileOpen)}
                    className="p-2 rounded-lg hover:bg-surface-700/40 text-surface-200/60"
                >
                    {mobileOpen ? <X size={20} /> : <Menu size={20} />}
                </button>
            </div>

            {/* Mobile drawer */}
            {mobileOpen && (
                <div className="lg:hidden fixed inset-0 z-40 bg-black/60" onClick={() => setMobileOpen(false)}>
                    <div
                        className="absolute left-0 top-0 bottom-0 w-64 bg-surface-900 border-r border-surface-700/40 pt-16 px-3 py-4 space-y-1"
                        onClick={e => e.stopPropagation()}
                    >
                        <NavItems />
                    </div>
                </div>
            )}

            {/* Desktop sidebar */}
            <aside className="hidden lg:flex flex-col w-64 border-r border-surface-700/60 bg-surface-900/80 backdrop-blur-xl">
                {/* Logo */}
                <div className="flex items-center gap-3 px-6 py-5 border-b border-surface-700/40">
                    <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
                        <Zap size={18} className="text-white" />
                    </div>
                    <div>
                        <h1 className="text-sm font-bold text-white tracking-tight">Google Ads</h1>
                        <p className="text-[10px] text-brand-400 font-medium tracking-widest uppercase">Helper</p>
                    </div>
                </div>

                {/* Nav */}
                <nav className="flex-1 px-3 py-4 space-y-1">
                    <NavItems />
                </nav>

                {/* Status */}
                <div className="px-4 py-4 border-t border-surface-700/40">
                    <div className="flex items-center gap-2 text-xs text-surface-200/50">
                        <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse-dot" />
                        Demo Meble Sp. z o.o.
                    </div>
                </div>
            </aside>
        </>
    )
}

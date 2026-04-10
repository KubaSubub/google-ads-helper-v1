import { useLocation } from 'react-router-dom'
import { LogOut, Settings, Zap } from 'lucide-react'
import { useApp } from '../../../contexts/AppContext'
import { useFilter } from '../../../contexts/FilterContext'
import { logout } from '../../../api'
import { NAV_GROUPS } from './navConfig'
import NavItem from './NavItem'

export default function SidebarContent({ onNavigate }) {
    const { alertCount } = useApp()
    const { filters } = useFilter()
    const location = useLocation()
    const activeCampType = filters.campaignType || 'ALL'
    const isMccPage = location.pathname === '/mcc-overview'

    const handleLogout = async () => {
        try {
            await logout()
        } catch {}
        window.location.reload()
    }

    return (
        <div className="flex flex-col h-full" style={{ background: '#111318' }}>
            <div style={{ padding: '16px 12px 12px' }}>
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
            <div style={{ height: 1, background: 'rgba(255,255,255,0.07)' }} />

            <nav className="flex-1 overflow-y-auto" style={{ padding: '8px 8px' }}>
                {NAV_GROUPS.map((group) => {
                    let visibleItems = (activeCampType === 'ALL' || group.always
                        ? group.items
                        : group.items.filter(item => !item.types || item.types.includes(activeCampType))
                    ).filter(item => !item.hidden)
                    // On MCC page: show only alwaysVisible items across all groups
                    if (isMccPage) {
                        visibleItems = visibleItems.filter(item => item.alwaysVisible)
                    }
                    if (visibleItems.length === 0) return null
                    return (
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
                                {visibleItems.map((item) => (
                                    <NavItem
                                        key={item.to}
                                        {...item}
                                        alertCount={alertCount}
                                        onClick={onNavigate}
                                    />
                                ))}
                            </div>
                        </div>
                    )
                })}
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
                        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)', fontWeight: 500 }}>Użytkownik</div>
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

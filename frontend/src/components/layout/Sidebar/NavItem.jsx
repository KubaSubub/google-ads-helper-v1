import { NavLink, useLocation } from 'react-router-dom'
import clsx from 'clsx'

export default function NavItem({ to, label, icon: Icon, showBadge, alertCount, onClick }) {
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
                        background: '#F87171',
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

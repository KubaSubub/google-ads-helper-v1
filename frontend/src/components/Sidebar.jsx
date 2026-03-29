import { useState } from 'react'
import { Menu, X, Zap } from 'lucide-react'
import SidebarContent from './layout/Sidebar/SidebarContent'

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

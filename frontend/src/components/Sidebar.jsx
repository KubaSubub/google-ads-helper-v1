import { useState, useRef, useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
    Award,
    Bell,
    Brain,
    Calendar,
    ChevronDown,
    ClipboardCheck,
    Download,
    History,
    KeyRound,
    LayoutDashboard,
    Lightbulb,
    Loader2,
    LogOut,
    Megaphone,
    Menu,
    Plus,
    RefreshCw,
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
import { logout, discoverClients, getDataCoverage } from '../api'
import SyncModal from './SyncModal'

const NAV_GROUPS = [
    {
        label: 'PRZEGLĄD',
        items: [
            { to: '/', label: 'Pulpit', icon: LayoutDashboard },
            { to: '/daily-audit', label: 'Poranny przegląd', icon: ClipboardCheck },
        ],
    },
    {
        label: 'DANE KAMPANII',
        items: [
            { to: '/campaigns', label: 'Kampanie', icon: Megaphone },
            { to: '/keywords', label: 'Słowa kluczowe', icon: KeyRound },
            { to: '/search-terms', label: 'Wyszukiwane frazy', icon: Search },
        ],
    },
    {
        label: 'DZIAŁANIA',
        items: [
            { to: '/recommendations', label: 'Rekomendacje', icon: Lightbulb },
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
            { to: '/search-optimization', label: 'Optymalizacja', icon: Zap },
            { to: '/forecast', label: 'Prognoza', icon: Calendar },
            { to: '/semantic', label: 'Inteligencja', icon: Brain },
            { to: '/quality-score', label: 'Wynik jakości', icon: Award },
        ],
    },
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

function ClientDrawer({ open, onClose }) {
    const { selectedClientId, setSelectedClientId, clients, showToast, refreshClients } = useApp()
    const [discovering, setDiscovering] = useState(false)
    const [syncModalClient, setSyncModalClient] = useState(null) // {id, name}
    const [customerId, setCustomerId] = useState('')
    const [fetchingSingle, setFetchingSingle] = useState(false)
    const [showAddInput, setShowAddInput] = useState(false)
    const [coverageMap, setCoverageMap] = useState({})
    const drawerRef = useRef(null)

    useEffect(() => {
        if (!open) return
        const handler = (e) => {
            // Don't close drawer if click is inside SyncModal overlay
            if (e.target.closest('[data-sync-modal]')) return
            if (drawerRef.current && !drawerRef.current.contains(e.target)) onClose()
        }
        document.addEventListener('mousedown', handler)
        return () => document.removeEventListener('mousedown', handler)
    }, [open, onClose])

    useEffect(() => {
        if (!open) {
            setShowAddInput(false)
            setCustomerId('')
            return
        }
        clients.forEach((client) => {
            getDataCoverage(client.id)
                .then((data) => setCoverageMap((prev) => ({ ...prev, [client.id]: data })))
                .catch((err) => console.error('[ClientDrawer] coverage fetch failed', err))
        })
    }, [open, clients])

    const handleSync = (clientId) => {
        const client = clients.find(c => c.id === clientId)
        setSyncModalClient({ id: clientId, name: client?.name || `Klient #${clientId}` })
    }

    const handleSyncModalClose = () => {
        setSyncModalClient(null)
        // Refresh coverage after sync
        clients.forEach((client) => {
            getDataCoverage(client.id)
                .then((data) => setCoverageMap((prev) => ({ ...prev, [client.id]: data })))
                .catch((err) => console.error('[ClientDrawer] coverage refresh failed', err))
        })
    }

    const handleDiscover = async () => {
        setDiscovering(true)
        try {
            const result = await discoverClients()
            showToast(result.message, 'success')
            const updated = await refreshClients()
            if (!selectedClientId && updated?.length > 0) setSelectedClientId(updated[0].id)
        } catch (err) {
            showToast(err.message || 'Błąd pobierania klientów', 'error')
        } finally {
            setDiscovering(false)
        }
    }

    const handleFetchSingle = async () => {
        if (!customerId.trim()) return
        setFetchingSingle(true)
        try {
            const result = await discoverClients(customerId.trim())
            showToast(result.message, 'success')
            setCustomerId('')
            setShowAddInput(false)
            const updated = await refreshClients()
            if (!selectedClientId && updated?.length > 0) setSelectedClientId(updated[0].id)
        } catch (err) {
            showToast(err.message || 'Błąd pobierania konta', 'error')
        } finally {
            setFetchingSingle(false)
        }
    }

    if (!open) return null

    return (
        <div style={{
            position: 'fixed',
            inset: 0,
            zIndex: 60,
            background: 'rgba(0,0,0,0.5)',
            transition: 'opacity 0.2s',
        }}>
            <div
                ref={drawerRef}
                style={{
                    position: 'absolute',
                    right: 0,
                    top: 0,
                    bottom: 0,
                    width: 380,
                    maxWidth: '100vw',
                    background: '#111318',
                    borderLeft: '1px solid rgba(255,255,255,0.1)',
                    display: 'flex',
                    flexDirection: 'column',
                    animation: 'slideInRight 0.2s ease-out',
                }}
            >
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '16px 20px',
                    borderBottom: '1px solid rgba(255,255,255,0.07)',
                }}>
                    <h2 style={{ fontSize: 16, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne' }}>
                        Zarządzanie klientami
                    </h2>
                    <button
                        onClick={onClose}
                        style={{
                            width: 28,
                            height: 28,
                            borderRadius: 6,
                            background: 'rgba(255,255,255,0.06)',
                            border: 'none',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            cursor: 'pointer',
                            color: 'rgba(255,255,255,0.4)',
                            transition: 'background 0.15s',
                        }}
                        className="hover:bg-white/[0.1]"
                    >
                        <X size={14} />
                    </button>
                </div>

                <div style={{
                    display: 'flex',
                    gap: 8,
                    padding: '12px 20px',
                    borderBottom: '1px solid rgba(255,255,255,0.07)',
                }}>
                    <button
                        onClick={handleDiscover}
                        disabled={discovering}
                        style={{
                            flex: 1,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: 6,
                            padding: '8px 12px',
                            borderRadius: 8,
                            fontSize: 12,
                            fontWeight: 500,
                            background: 'rgba(79,142,247,0.12)',
                            border: '1px solid rgba(79,142,247,0.3)',
                            color: '#4F8EF7',
                            cursor: 'pointer',
                            opacity: discovering ? 0.5 : 1,
                            transition: 'all 0.15s',
                        }}
                    >
                        {discovering ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
                        Pobierz klientów
                    </button>
                    <button
                        onClick={() => setShowAddInput((v) => !v)}
                        style={{
                            flex: 1,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: 6,
                            padding: '8px 12px',
                            borderRadius: 8,
                            fontSize: 12,
                            background: 'rgba(255,255,255,0.04)',
                            border: '1px solid rgba(255,255,255,0.08)',
                            color: 'rgba(255,255,255,0.5)',
                            cursor: 'pointer',
                            transition: 'all 0.15s',
                        }}
                        className="hover:bg-white/[0.06]"
                    >
                        <Plus size={13} />
                        Dodaj ręcznie
                    </button>
                </div>

                {showAddInput && (
                    <div style={{
                        display: 'flex',
                        gap: 8,
                        padding: '10px 20px',
                        borderBottom: '1px solid rgba(255,255,255,0.07)',
                    }}>
                        <input
                            type="text"
                            value={customerId}
                            onChange={(e) => setCustomerId(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleFetchSingle()}
                            placeholder="np. 123-456-7890"
                            autoFocus
                            style={{
                                flex: 1,
                                background: 'rgba(255,255,255,0.05)',
                                border: '1px solid rgba(255,255,255,0.1)',
                                borderRadius: 6,
                                padding: '6px 10px',
                                fontSize: 12,
                                color: '#F0F0F0',
                                outline: 'none',
                            }}
                        />
                        <button
                            onClick={handleFetchSingle}
                            disabled={fetchingSingle || !customerId.trim()}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 5,
                                padding: '6px 14px',
                                borderRadius: 6,
                                fontSize: 12,
                                fontWeight: 500,
                                background: 'rgba(79,142,247,0.15)',
                                border: '1px solid rgba(79,142,247,0.3)',
                                color: '#4F8EF7',
                                cursor: 'pointer',
                                opacity: (fetchingSingle || !customerId.trim()) ? 0.4 : 1,
                                transition: 'all 0.15s',
                            }}
                        >
                            {fetchingSingle ? <Loader2 size={13} className="animate-spin" /> : <Search size={13} />}
                            Pobierz
                        </button>
                    </div>
                )}

                <div style={{
                    padding: '8px 20px 4px',
                }}>
                    <div style={{
                        fontSize: 9,
                        color: 'rgba(255,255,255,0.3)',
                        letterSpacing: '0.15em',
                        textTransform: 'uppercase',
                        fontWeight: 500,
                    }}>
                        Połączone konta
                    </div>
                </div>

                <div style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: '4px 16px 16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 6,
                }}>
                    {clients.length === 0 ? (
                        <div style={{
                            padding: '32px 0',
                            textAlign: 'center',
                            color: 'rgba(255,255,255,0.3)',
                            fontSize: 12,
                        }}>
                            <Users size={24} style={{ margin: '0 auto 8px', opacity: 0.4 }} />
                            Brak klientów. Kliknij "Pobierz klientów".
                        </div>
                    ) : (
                        clients.map((client) => {
                            const isSelected = selectedClientId === client.id
                            const cov = coverageMap[client.id]
                            return (
                                <div
                                    key={client.id}
                                    onClick={() => {
                                        setSelectedClientId(client.id)
                                    }}
                                    style={{
                                        padding: '10px 14px',
                                        borderRadius: 8,
                                        cursor: 'pointer',
                                        background: isSelected ? 'rgba(79,142,247,0.08)' : 'rgba(255,255,255,0.03)',
                                        border: `1px solid ${isSelected ? 'rgba(79,142,247,0.3)' : 'rgba(255,255,255,0.07)'}`,
                                        transition: 'all 0.15s',
                                    }}
                                    className={!isSelected ? 'hover:bg-white/[0.05]' : ''}
                                >
                                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                            {isSelected && (
                                                <span style={{
                                                    width: 6,
                                                    height: 6,
                                                    borderRadius: '50%',
                                                    background: '#4ADE80',
                                                    boxShadow: '0 0 6px #4ade80',
                                                    flexShrink: 0,
                                                }} />
                                            )}
                                            <span style={{ fontSize: 13, fontWeight: 500, color: '#F0F0F0' }}>
                                                {client.name}
                                            </span>
                                        </div>
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                handleSync(client.id)
                                            }}
                                            style={{
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: 4,
                                                padding: '4px 10px',
                                                borderRadius: 5,
                                                fontSize: 10,
                                                background: 'rgba(255,255,255,0.06)',
                                                border: 'none',
                                                color: 'rgba(255,255,255,0.4)',
                                                cursor: 'pointer',
                                                transition: 'all 0.15s',
                                            }}
                                            className="hover:bg-white/[0.1]"
                                        >
                                            <RefreshCw size={10} />
                                            Sync
                                        </button>
                                    </div>
                                    <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', display: 'flex', flexDirection: 'column', gap: 2 }}>
                                        <span>{client.google_customer_id}</span>
                                        {cov?.last_sync_at && (
                                            <span>
                                                Ostatni sync: {new Date(cov.last_sync_at).toLocaleString('pl-PL')}
                                            </span>
                                        )}
                                        {cov?.data_from && cov?.data_to && (
                                            <span>
                                                Dane: {new Date(cov.data_from).toLocaleDateString('pl-PL')} — {new Date(cov.data_to).toLocaleDateString('pl-PL')}
                                            </span>
                                        )}
                                        {!cov?.data_from && !cov?.last_sync_at && (
                                            <span style={{ fontStyle: 'italic' }}>Brak zsynchronizowanych danych</span>
                                        )}
                                    </div>
                                </div>
                            )
                        })
                    )}
                </div>
            </div>

            <SyncModal
                isOpen={!!syncModalClient}
                clientId={syncModalClient?.id}
                clientName={syncModalClient?.name}
                onClose={handleSyncModalClose}
            />
        </div>
    )
}

function ClientSelector({ onOpenDrawer }) {
    const { selectedClientId, setSelectedClientId, clients } = useApp()
    const selectedClient = clients.find((c) => c.id === selectedClientId)
    const [open, setOpen] = useState(false)
    const ref = useRef(null)

    useEffect(() => {
        if (!open) return
        const handler = (e) => {
            if (ref.current && !ref.current.contains(e.target)) setOpen(false)
        }
        document.addEventListener('mousedown', handler)
        return () => document.removeEventListener('mousedown', handler)
    }, [open])

    return (
        <div style={{ padding: '10px 12px 8px' }}>
            <div style={{
                fontSize: 10,
                color: 'rgba(255,255,255,0.3)',
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                padding: '0 2px 6px',
                fontWeight: 500,
            }}>
                Klient
            </div>
            <div style={{ display: 'flex', gap: 6, alignItems: 'stretch' }}>
                <div ref={ref} style={{ position: 'relative', flex: 1, minWidth: 0 }}>
                    <button
                        onClick={() => setOpen((o) => !o)}
                        style={{
                            width: '100%',
                            height: 38,
                            padding: '0 32px 0 12px',
                            borderRadius: 8,
                            fontSize: 13,
                            fontWeight: 500,
                            color: selectedClient ? '#FFFFFF' : 'rgba(255,255,255,0.4)',
                            background: open ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.04)',
                            border: `1px solid ${open ? 'rgba(79,142,247,0.4)' : 'rgba(255,255,255,0.08)'}`,
                            outline: 'none',
                            cursor: 'pointer',
                            transition: 'border-color 0.15s, background 0.15s',
                            textAlign: 'left',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                        }}
                        className="hover:bg-white/[0.06]"
                    >
                        {selectedClient ? selectedClient.name : 'Wybierz klienta...'}
                    </button>
                    <ChevronDown
                        size={14}
                        style={{
                            position: 'absolute',
                            right: 10,
                            top: '50%',
                            transform: `translateY(-50%) rotate(${open ? 180 : 0}deg)`,
                            color: 'rgba(255,255,255,0.3)',
                            pointerEvents: 'none',
                            transition: 'transform 0.15s',
                        }}
                    />
                    {open && (
                        <div style={{
                            position: 'absolute',
                            top: 'calc(100% + 4px)',
                            left: 0,
                            right: 0,
                            zIndex: 50,
                            background: '#1A1D24',
                            border: '1px solid rgba(255,255,255,0.1)',
                            borderRadius: 10,
                            padding: 4,
                            boxShadow: '0 12px 32px rgba(0,0,0,0.5)',
                            maxHeight: 240,
                            overflowY: 'auto',
                        }}>
                            {clients.map((client) => {
                                const active = client.id === selectedClientId
                                return (
                                    <button
                                        key={client.id}
                                        onClick={() => {
                                            setSelectedClientId(client.id)
                                            setOpen(false)
                                        }}
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: 8,
                                            width: '100%',
                                            padding: '8px 10px',
                                            borderRadius: 7,
                                            fontSize: 12,
                                            fontWeight: active ? 500 : 400,
                                            color: active ? '#FFFFFF' : 'rgba(255,255,255,0.65)',
                                            background: active ? 'rgba(79,142,247,0.15)' : 'transparent',
                                            border: 'none',
                                            cursor: 'pointer',
                                            textAlign: 'left',
                                            transition: 'background 0.1s',
                                        }}
                                        className={!active ? 'hover:bg-white/[0.05]' : ''}
                                    >
                                        <span style={{
                                            width: 6,
                                            height: 6,
                                            borderRadius: '50%',
                                            flexShrink: 0,
                                            background: active ? '#4ADE80' : 'rgba(255,255,255,0.15)',
                                        }} />
                                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                            {client.name}
                                        </span>
                                    </button>
                                )
                            })}
                        </div>
                    )}
                </div>
                <button
                    onClick={onOpenDrawer}
                    title="Zarządzanie klientami"
                    style={{
                        width: 38,
                        borderRadius: 8,
                        background: 'rgba(79,142,247,0.12)',
                        border: '1px solid rgba(79,142,247,0.25)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer',
                        color: '#4F8EF7',
                        flexShrink: 0,
                        transition: 'all 0.15s',
                    }}
                    className="hover:bg-[rgba(79,142,247,0.2)]"
                >
                    <Settings size={14} />
                </button>
            </div>
            {selectedClient && (
                <div style={{
                    fontSize: 10,
                    color: 'rgba(255,255,255,0.25)',
                    padding: '5px 4px 0',
                }}>
                    ID: {selectedClient.google_customer_id}
                </div>
            )}
        </div>
    )
}

function SidebarContent({ onNavigate }) {
    const { selectedClientId, setSelectedClientId, alertCount, clients } = useApp()
    const selectedClient = clients.find((client) => client.id === selectedClientId)
    const [drawerOpen, setDrawerOpen] = useState(false)

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

            <ClientSelector onOpenDrawer={() => setDrawerOpen(true)} />
            <ClientDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />

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

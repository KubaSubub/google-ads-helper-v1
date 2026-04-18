import { useState, useRef, useEffect } from 'react'
import { Download, Loader2, Plus, Search, Users, X } from 'lucide-react'
import { useApp } from '../../../contexts/AppContext'
import { discoverClients, getDataCoverage } from '../../../api'

export default function ClientDrawer({ open, onClose }) {
    const { selectedClientId, setSelectedClientId, clients, showToast, refreshClients } = useApp()
    const [discovering, setDiscovering] = useState(false)
    const [syncModalClient, setSyncModalClient] = useState(null)
    const [customerId, setCustomerId] = useState('')
    const [fetchingSingle, setFetchingSingle] = useState(false)
    const [showAddInput, setShowAddInput] = useState(false)
    const [coverageMap, setCoverageMap] = useState({})
    const drawerRef = useRef(null)

    useEffect(() => {
        if (!open) return
        const handler = (e) => {
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
                                        {/* ADR-020: per-client Sync button removed — sync lives only in MCC Overview */}
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

            {/* ADR-020: SyncModal not rendered here — sync lives only in MCC Overview */}
        </div>
    )
}

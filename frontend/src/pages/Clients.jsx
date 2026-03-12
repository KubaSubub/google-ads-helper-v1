import { useState } from 'react';
import { useSync } from '../hooks/useSync';
import { useApp } from '../contexts/AppContext';
import SyncButton from '../components/SyncButton';
import EmptyState from '../components/EmptyState';
import { discoverClients } from '../api';
import { Users, Loader2, Download, Search } from 'lucide-react';

function getSyncToast(result) {
    if (result?.success) {
        return {
            type: 'success',
            message: result.message || 'Synchronizacja zakonczona pomyslnie.',
        };
    }

    if (result?.status === 'partial') {
        return {
            type: 'info',
            message: result.message || 'Synchronizacja zakonczona czesciowo.',
        };
    }

    return {
        type: 'error',
        message: result?.message || 'Synchronizacja nie powiodla sie.',
    };
}

export default function Clients() {
    const { sync } = useSync();
    const { selectedClientId, setSelectedClientId, showToast, clients, clientsLoading: loading, refreshClients } = useApp();
    const [discovering, setDiscovering] = useState(false);
    const [syncingClientId, setSyncingClientId] = useState(null);
    const [customerId, setCustomerId] = useState('');
    const [fetchingSingle, setFetchingSingle] = useState(false);

    const handleSync = async (clientId) => {
        setSyncingClientId(clientId);
        try {
            const result = await sync(clientId);
            const toast = getSyncToast(result);
            showToast(toast.message, toast.type);
            if (result?.status !== 'failed') {
                await refreshClients();
            }
        } catch (err) {
            showToast(err.message || 'Blad synchronizacji', 'error');
        } finally {
            setSyncingClientId(null);
        }
    };

    const handleFetchSingle = async () => {
        if (!customerId.trim()) return;
        setFetchingSingle(true);
        try {
            const result = await discoverClients(customerId.trim());
            showToast(result.message, 'success');
            setCustomerId('');
            const updated = await refreshClients();
            if (!selectedClientId && updated && updated.length > 0) {
                setSelectedClientId(updated[0].id);
            }
        } catch (err) {
            showToast(err.message || 'Blad pobierania konta', 'error');
        } finally {
            setFetchingSingle(false);
        }
    };

    const handleDiscover = async () => {
        setDiscovering(true);
        try {
            const result = await discoverClients();
            showToast(result.message, 'success');
            const updated = await refreshClients();
            if (!selectedClientId && updated && updated.length > 0) {
                setSelectedClientId(updated[0].id);
            }
        } catch (err) {
            showToast(err.message || 'Blad pobierania klientow', 'error');
        } finally {
            setDiscovering(false);
        }
    };

    if (loading) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '60px 0' }}>
                <Loader2 size={28} style={{ color: '#4F8EF7' }} className="animate-spin" />
            </div>
        );
    }

    return (
        <div style={{ maxWidth: 900 }}>
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Klienci
                    </h1>
                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                        Zarzadzanie kontami Google Ads
                    </p>
                </div>
                <button
                    onClick={handleDiscover}
                    disabled={discovering}
                    style={{
                        display: 'flex', alignItems: 'center', gap: 6,
                        padding: '7px 16px', borderRadius: 8, fontSize: 12, fontWeight: 500,
                        background: 'rgba(79,142,247,0.15)',
                        border: '1px solid rgba(79,142,247,0.3)',
                        color: '#4F8EF7', cursor: 'pointer',
                        opacity: discovering ? 0.5 : 1,
                        transition: 'all 0.15s',
                    }}
                >
                    {discovering
                        ? <Loader2 size={14} className="animate-spin" />
                        : <Download size={14} />
                    }
                    {discovering ? 'Pobieram...' : 'Pobierz klientow z Google Ads'}
                </button>
            </div>

            <div
                className="v2-card"
                style={{
                    padding: '12px 16px',
                    marginBottom: 16,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                }}
            >
                <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', whiteSpace: 'nowrap' }}>
                    Numer konta:
                </span>
                <input
                    type="text"
                    value={customerId}
                    onChange={(e) => setCustomerId(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleFetchSingle()}
                    placeholder="np. 123-456-7890"
                    style={{
                        flex: 1,
                        background: 'rgba(255,255,255,0.05)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: 6,
                        padding: '6px 10px',
                        fontSize: 12,
                        color: '#F0F0F0',
                        outline: 'none',
                        minWidth: 0,
                    }}
                />
                <button
                    onClick={handleFetchSingle}
                    disabled={fetchingSingle || !customerId.trim()}
                    style={{
                        display: 'flex', alignItems: 'center', gap: 5,
                        padding: '6px 14px', borderRadius: 6, fontSize: 12, fontWeight: 500,
                        background: 'rgba(79,142,247,0.15)',
                        border: '1px solid rgba(79,142,247,0.3)',
                        color: '#4F8EF7', cursor: 'pointer',
                        opacity: (fetchingSingle || !customerId.trim()) ? 0.4 : 1,
                        transition: 'all 0.15s',
                        whiteSpace: 'nowrap',
                    }}
                >
                    {fetchingSingle
                        ? <Loader2 size={13} className="animate-spin" />
                        : <Search size={13} />
                    }
                    Pobierz konto
                </button>
            </div>

            {!clients.length ? (
                <EmptyState
                    message="Brak klientow. Kliknij 'Pobierz klientow z Google Ads', aby zaimportowac konta."
                    icon={Users}
                />
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {clients.map((client) => {
                        const isSelected = selectedClientId === client.id;
                        return (
                            <div
                                key={client.id}
                                className="v2-card"
                                onClick={() => setSelectedClientId(client.id)}
                                style={{
                                    padding: '14px 18px',
                                    cursor: 'pointer',
                                    borderColor: isSelected ? 'rgba(79,142,247,0.4)' : undefined,
                                    background: isSelected ? 'rgba(79,142,247,0.08)' : undefined,
                                    transition: 'all 0.15s',
                                }}
                            >
                                <div className="flex items-center justify-between">
                                    <div>
                                        <div className="flex items-center gap-2" style={{ marginBottom: 3 }}>
                                            {isSelected && (
                                                <span style={{
                                                    width: 6, height: 6, borderRadius: '50%',
                                                    background: '#4ADE80',
                                                    boxShadow: '0 0 6px #4ade80',
                                                    flexShrink: 0,
                                                }} />
                                            )}
                                            <span style={{ fontSize: 14, fontWeight: 500, color: '#F0F0F0' }}>
                                                {client.name}
                                            </span>
                                        </div>
                                        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>
                                            ID: {client.google_customer_id}
                                            {client.last_synced_at && (
                                                <span style={{ marginLeft: 12 }}>
                                                    Ostatni sync: {new Date(client.last_synced_at).toLocaleString('pl-PL')}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    <SyncButton
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleSync(client.id);
                                        }}
                                        loading={syncingClientId === client.id}
                                        lastSynced={client.last_synced_at}
                                    />
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

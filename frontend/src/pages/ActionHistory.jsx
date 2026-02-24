import { useState, useEffect } from 'react';
import { useApp } from '../contexts/AppContext';
import { getActionHistory, revertAction } from '../api';
import ConfirmationModal from '../components/ConfirmationModal';
import DataTable from '../components/DataTable';
import EmptyState from '../components/EmptyState';
import { Undo2, Loader2 } from 'lucide-react';

export default function ActionHistory() {
    const { selectedClientId, showToast } = useApp();
    const [actions, setActions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [revertModal, setRevertModal] = useState(null);
    const [reverting, setReverting] = useState(false);

    const fetchActions = async () => {
        if (!selectedClientId) return;
        setLoading(true);
        try {
            const data = await getActionHistory(selectedClientId, { limit: 100 });
            setActions(data.actions || []);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchActions();
    }, [selectedClientId]);

    const canRevert = (action) => {
        if (action.status !== 'SUCCESS') return false;
        if (action.action_type === 'ADD_NEGATIVE') return false;
        const age = Date.now() - new Date(action.executed_at).getTime();
        return age < 24 * 60 * 60 * 1000;
    };

    const handleRevert = async () => {
        if (!revertModal) return;
        setReverting(true);
        try {
            await revertAction(revertModal.id, selectedClientId);
            showToast('Akcja cofnięta', 'success');
            setRevertModal(null);
            await fetchActions();
        } catch (err) {
            showToast('Błąd cofania: ' + err.message, 'error');
        } finally {
            setReverting(false);
        }
    };

    const STATUS_COLORS = {
        SUCCESS: '#4ADE80',
        FAILED: '#F87171',
        REVERTED: 'rgba(255,255,255,0.35)',
    };

    const columns = [
        {
            accessorKey: 'executed_at',
            header: 'Data',
            cell: ({ getValue }) => new Date(getValue()).toLocaleString('pl-PL'),
        },
        { accessorKey: 'action_type', header: 'Akcja' },
        {
            accessorKey: 'entity_name',
            header: 'Encja',
            cell: ({ row }) => {
                const name = row.original.entity_name;
                const type = row.original.entity_type;
                return (
                    <span>
                        {name || `${type} #${row.original.entity_id}`}
                    </span>
                );
            },
        },
        {
            accessorKey: 'campaign_name',
            header: 'Kampania',
            cell: ({ getValue }) => (
                <span style={{ color: 'rgba(255,255,255,0.4)' }}>{getValue() || '—'}</span>
            ),
        },
        {
            accessorKey: 'status',
            header: 'Status',
            cell: ({ getValue }) => (
                <span style={{ color: STATUS_COLORS[getValue()] || 'rgba(255,255,255,0.4)' }}>
                    {getValue()}
                </span>
            ),
        },
        {
            id: 'actions',
            header: '',
            cell: ({ row }) =>
                canRevert(row.original) ? (
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            setRevertModal(row.original);
                        }}
                        style={{
                            display: 'flex', alignItems: 'center', gap: 4,
                            fontSize: 11, fontWeight: 500,
                            color: '#FBBF24', background: 'none', border: 'none',
                            cursor: 'pointer',
                        }}
                    >
                        <Undo2 size={12} /> Cofnij
                    </button>
                ) : null,
        },
    ];

    if (!selectedClientId) return <EmptyState message="Wybierz klienta" />;

    if (loading) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '60px 0' }}>
                <Loader2 size={28} style={{ color: '#4F8EF7' }} className="animate-spin" />
            </div>
        );
    }

    return (
        <div style={{ maxWidth: 1100 }}>
            <div style={{ marginBottom: 24 }}>
                <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                    Historia akcji
                </h1>
                <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                    Wszystkie wykonane operacje z możliwością cofnięcia
                </p>
            </div>

            <DataTable
                data={actions}
                columns={columns}
                searchable
                emptyMessage="Brak wykonanych akcji"
            />

            <ConfirmationModal
                isOpen={!!revertModal}
                onClose={() => setRevertModal(null)}
                onConfirm={handleRevert}
                title="Cofnij akcję?"
                actionType={revertModal?.action_type}
                entity={revertModal?.entity_name || revertModal?.entity_id}
                reason="Akcja zostanie cofnięta do poprzedniego stanu"
                isLoading={reverting}
            />
        </div>
    );
}

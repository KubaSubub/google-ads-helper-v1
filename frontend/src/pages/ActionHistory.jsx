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
        SUCCESS: 'text-green-400',
        FAILED: 'text-red-400',
        REVERTED: 'text-gray-400',
    };

    const columns = [
        {
            accessorKey: 'executed_at',
            header: 'Data',
            cell: ({ getValue }) => new Date(getValue()).toLocaleString('pl-PL'),
        },
        { accessorKey: 'action_type', header: 'Akcja' },
        { accessorKey: 'entity_type', header: 'Typ' },
        { accessorKey: 'entity_id', header: 'Entity ID' },
        {
            accessorKey: 'status',
            header: 'Status',
            cell: ({ getValue }) => (
                <span className={STATUS_COLORS[getValue()] || 'text-app-muted'}>
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
                        className="flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300"
                    >
                        <Undo2 className="w-3 h-3" /> Cofnij
                    </button>
                ) : null,
        },
    ];

    if (!selectedClientId) return <EmptyState message="Wybierz klienta" />;

    if (loading) {
        return (
            <div className="flex items-center justify-center py-16">
                <Loader2 className="w-8 h-8 animate-spin text-app-muted" />
            </div>
        );
    }

    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold text-app-text mb-6">Historia akcji</h1>
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
                entity={revertModal?.entity_id}
                reason="Akcja zostanie cofnięta do poprzedniego stanu"
                isLoading={reverting}
            />
        </div>
    );
}

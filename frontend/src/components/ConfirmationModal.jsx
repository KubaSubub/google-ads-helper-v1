import { AlertTriangle, X } from 'lucide-react';

export default function ConfirmationModal({
    isOpen,
    onClose,
    onConfirm,
    title = 'Potwierdź akcję',
    actionType,
    entity,
    beforeState,
    afterState,
    reason,
    isLoading = false,
}) {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/60" onClick={onClose} />

            {/* Modal */}
            <div className="relative bg-app-card border border-white/10 rounded-xl p-6 max-w-lg w-full mx-4 shadow-2xl">
                {/* Header */}
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <AlertTriangle className="w-5 h-5 text-amber-400" />
                        <h3 className="text-lg font-semibold text-app-text">{title}</h3>
                    </div>
                    <button onClick={onClose} className="text-app-muted hover:text-app-text">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Action type badge */}
                {actionType && (
                    <div className="mb-4">
                        <span className="inline-block px-2 py-1 text-xs font-mono bg-blue-500/20 text-blue-300 rounded">
                            {actionType}
                        </span>
                    </div>
                )}

                {/* Entity */}
                {entity && (
                    <p className="text-sm text-app-muted mb-4">
                        Obiekt: <span className="text-app-text font-medium">{entity}</span>
                    </p>
                )}

                {/* Before / After */}
                {(beforeState || afterState) && (
                    <div className="grid grid-cols-2 gap-4 mb-4 p-3 bg-white/5 rounded-lg">
                        <div>
                            <p className="text-xs text-app-muted mb-1">Przed</p>
                            {beforeState && Object.entries(beforeState).map(([k, v]) => (
                                <p key={k} className="text-sm text-red-300">
                                    {k}: {v}
                                </p>
                            ))}
                        </div>
                        <div>
                            <p className="text-xs text-app-muted mb-1">Po</p>
                            {afterState && Object.entries(afterState).map(([k, v]) => (
                                <p key={k} className="text-sm text-green-300">
                                    {k}: {v}
                                </p>
                            ))}
                        </div>
                    </div>
                )}

                {/* Reason */}
                {reason && (
                    <p className="text-sm text-app-muted mb-6">
                        Powód: {reason}
                    </p>
                )}

                {/* Buttons */}
                <div className="flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm text-app-muted hover:text-app-text rounded-lg border border-white/10"
                        disabled={isLoading}
                    >
                        Anuluj
                    </button>
                    <button
                        onClick={onConfirm}
                        className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50"
                        disabled={isLoading}
                    >
                        {isLoading ? 'Wykonuję...' : 'Potwierdź'}
                    </button>
                </div>
            </div>
        </div>
    );
}

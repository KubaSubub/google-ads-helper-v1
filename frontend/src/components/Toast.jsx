import { useEffect } from 'react';
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';

const ICONS = {
    success: CheckCircle,
    error: AlertCircle,
    info: Info,
};

const COLORS = {
    success: 'bg-green-500/20 border-green-500/50 text-green-300',
    error: 'bg-red-500/20 border-red-500/50 text-red-300',
    info: 'bg-blue-500/20 border-blue-500/50 text-blue-300',
};

export default function Toast({ toast, onClose }) {
    if (!toast) return null;

    const Icon = ICONS[toast.type] || Info;

    return (
        <div className="fixed bottom-4 right-4 z-50 animate-slide-up">
            <div className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${COLORS[toast.type] || COLORS.info}`}>
                <Icon className="w-5 h-5 flex-shrink-0" />
                <span className="text-sm">{toast.message}</span>
                <button onClick={onClose} className="ml-2 hover:opacity-70">
                    <X className="w-4 h-4" />
                </button>
            </div>
        </div>
    );
}

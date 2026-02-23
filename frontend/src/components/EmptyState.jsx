import { Inbox } from 'lucide-react';

export default function EmptyState({
    message = 'Brak danych',
    icon: Icon = Inbox,
    action,
    actionLabel,
}) {
    return (
        <div className="flex flex-col items-center justify-center py-16 text-app-muted">
            <Icon className="w-12 h-12 mb-4 opacity-30" />
            <p className="text-sm mb-4">{message}</p>
            {action && (
                <button
                    onClick={action}
                    className="px-4 py-2 text-sm bg-app-accent/20 text-app-accent rounded-lg hover:bg-app-accent/30"
                >
                    {actionLabel}
                </button>
            )}
        </div>
    );
}

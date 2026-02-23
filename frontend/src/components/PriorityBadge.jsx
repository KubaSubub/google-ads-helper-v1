const COLORS = {
    HIGH: 'bg-red-500/20 text-red-300',
    MEDIUM: 'bg-amber-500/20 text-amber-300',
};

export default function PriorityBadge({ priority }) {
    return (
        <span className={`inline-flex px-2 py-0.5 text-xs font-bold rounded ${COLORS[priority] || 'bg-gray-500/20 text-gray-300'}`}>
            {priority}
        </span>
    );
}

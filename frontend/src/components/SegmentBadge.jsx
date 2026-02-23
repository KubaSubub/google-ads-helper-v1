const COLORS = {
    HIGH_PERFORMER: 'bg-green-500/20 text-green-300 border-green-500/30',
    WASTE: 'bg-red-500/20 text-red-300 border-red-500/30',
    IRRELEVANT: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
    OTHER: 'bg-gray-500/20 text-gray-300 border-gray-500/30',
};

const LABELS = {
    HIGH_PERFORMER: 'Wysoka wydajnosc',
    WASTE: 'Marnowanie',
    IRRELEVANT: 'Nieistotne',
    OTHER: 'Inne',
};

export default function SegmentBadge({ segment }) {
    return (
        <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded border ${COLORS[segment] || COLORS.OTHER}`}>
            {LABELS[segment] || segment}
        </span>
    );
}

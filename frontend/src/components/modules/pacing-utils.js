// Shared pacing color/label logic for BudgetPacingModule

export function getPacingColor(status) {
    if (status === 'overspend') return '#F87171'
    if (status === 'underspend') return '#FBBF24'
    return '#4ADE80'
}

export function getPacingBg(status) {
    if (status === 'overspend') return 'rgba(248,113,113,0.08)'
    if (status === 'underspend') return 'rgba(251,191,36,0.08)'
    return 'rgba(74,222,128,0.08)'
}

export function getPacingLabel(status) {
    if (status === 'overspend') return 'Przekroczenie'
    if (status === 'underspend') return 'Niedostateczne'
    return 'Na torze'
}

export function getTableBarColor(pct) {
    if (pct > 120) return '#F87171'
    if (pct >= 80) return '#4ADE80'
    if (pct >= 50) return '#FBBF24'
    return '#F87171'
}

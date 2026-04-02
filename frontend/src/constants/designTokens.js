// ═══════════════════════════════════════════════════════════════════════════════
// Design Tokens — Single Source of Truth for all visual values
// ═══════════════════════════════════════════════════════════════════════════════
// Import what you need:  import { C, T, S, ... } from '@/constants/designTokens'
// NEVER hardcode hex colors, font sizes, or spacing in components.

// ─── Colors ──────────────────────────────────────────────────────────────────
export const C = {
    // Backgrounds
    bg:              '#0D0F14',
    sidebar:         '#111318',
    surfaceElevated: '#1A1D24',
    modal:           '#151720',

    // Brand / Accent
    accentBlue:   '#4F8EF7',
    accentPurple: '#7B5CE0',

    // Semantic
    success: '#4ADE80',
    warning: '#FBBF24',
    danger:  '#F87171',
    info:    '#4F8EF7',

    // Text
    textPrimary:   '#F0F0F0',
    textSecondary: 'rgba(255,255,255,0.55)',
    textMuted:     'rgba(255,255,255,0.35)',
    textDim:       'rgba(255,255,255,0.3)',
    textPlaceholder: 'rgba(255,255,255,0.45)',

    // White opacity scale (backgrounds, borders, overlays)
    w03: 'rgba(255,255,255,0.03)',
    w04: 'rgba(255,255,255,0.04)',
    w05: 'rgba(255,255,255,0.05)',
    w06: 'rgba(255,255,255,0.06)',
    w07: 'rgba(255,255,255,0.07)',
    w08: 'rgba(255,255,255,0.08)',
    w10: 'rgba(255,255,255,0.1)',
    w12: 'rgba(255,255,255,0.12)',
    w15: 'rgba(255,255,255,0.15)',
    w20: 'rgba(255,255,255,0.2)',
    w25: 'rgba(255,255,255,0.25)',
    w30: 'rgba(255,255,255,0.3)',
    w40: 'rgba(255,255,255,0.4)',
    w50: 'rgba(255,255,255,0.5)',
    w60: 'rgba(255,255,255,0.6)',
    w70: 'rgba(255,255,255,0.7)',
    w80: 'rgba(255,255,255,0.8)',

    // Semantic with alpha (for backgrounds/borders of colored elements)
    successBg:     'rgba(74,222,128,0.1)',
    successBorder: 'rgba(74,222,128,0.2)',
    warningBg:     'rgba(251,191,36,0.1)',
    warningBorder: 'rgba(251,191,36,0.2)',
    dangerBg:      'rgba(248,113,113,0.1)',
    dangerBorder:  'rgba(248,113,113,0.2)',
    infoBg:        'rgba(79,142,247,0.1)',
    infoBorder:    'rgba(79,142,247,0.2)',
    accentBlueBg:  'rgba(79,142,247,0.18)',
}

// ─── Typography ──────────────────────────────────────────────────────────────
export const FONT = {
    body:    "'DM Sans', 'Inter', system-ui, -apple-system, sans-serif",
    display: "'Syne', 'DM Sans', system-ui, sans-serif",
    mono:    "'JetBrains Mono', 'Fira Code', monospace",
}

export const T = {
    // Page-level
    pageTitle:    { fontSize: 22, fontWeight: 700, fontFamily: FONT.display, color: C.textPrimary, lineHeight: 1.2 },
    pageSubtitle: { fontSize: 12, color: C.textMuted, marginTop: 3 },

    // Section-level
    sectionTitle: { fontSize: 14, fontWeight: 600, fontFamily: FONT.display, color: C.textPrimary },
    sectionLabel: { fontSize: 12, fontWeight: 500, color: C.textSecondary },

    // KPI / metrics
    kpiValue:     { fontSize: 22, fontWeight: 700, fontFamily: FONT.display, color: C.textPrimary },
    kpiValueLg:   { fontSize: 28, fontWeight: 700, fontFamily: FONT.display, color: C.textPrimary },
    kpiLabel:     { fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em' },
    metricValue:  { fontSize: 16, fontWeight: 700, fontFamily: FONT.display },
    metricLabel:  { fontSize: 11, fontWeight: 500, color: C.textMuted },

    // Table
    th: { padding: '8px 12px', fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em', whiteSpace: 'nowrap', textAlign: 'left' },
    td: { padding: '8px 12px', fontSize: 12, fontFamily: 'monospace', color: C.w80 },
    tdDim: { padding: '8px 12px', fontSize: 12, fontFamily: 'monospace', color: C.textPlaceholder },

    // Body text
    body:    { fontSize: 13, fontWeight: 400, color: C.textPrimary },
    bodyS:   { fontSize: 12, fontWeight: 400, color: C.textSecondary },
    bodySm:  { fontSize: 11, fontWeight: 400, color: C.textSecondary },

    // Captions / labels
    caption: { fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em' },
    label:   { fontSize: 11, fontWeight: 500, color: C.textMuted },
    labelSm: { fontSize: 10, fontWeight: 500, color: C.textDim },
}

// ─── Spacing scale ───────────────────────────────────────────────────────────
export const S = {
    xs:  4,
    sm:  6,
    md:  8,
    lg:  10,
    xl:  12,
    '2xl': 14,
    '3xl': 16,
    '4xl': 20,
    '5xl': 24,
    '6xl': 32,
}

// ─── Border radii ────────────────────────────────────────────────────────────
export const R = {
    sm:   6,
    md:   8,
    lg:   10,
    card: 12,
    modal: 14,
    pill: 999,
}

// ─── Borders (pre-built strings) ─────────────────────────────────────────────
export const B = {
    card:      `1px solid ${C.w07}`,
    subtle:    `1px solid ${C.w06}`,
    medium:    `1px solid ${C.w10}`,
    hover:     `1px solid ${C.w12}`,
    active:    `1px solid ${C.accentBlue}`,
    divider:   `1px solid ${C.w07}`,
    danger:    `1px solid ${C.dangerBorder}`,
    warning:   `1px solid ${C.warningBorder}`,
    success:   `1px solid ${C.successBorder}`,
    info:      `1px solid ${C.infoBorder}`,
}

// ─── Shadows ─────────────────────────────────────────────────────────────────
export const SHADOW = {
    dropdown: '0 8px 32px rgba(0,0,0,0.4)',
    glow:     '0 0 20px rgba(79,142,247,0.15)',
}

// ─── Transitions ─────────────────────────────────────────────────────────────
export const TRANSITION = {
    fast: 'all 0.15s',
    normal: 'all 0.2s',
    slow: 'all 0.3s',
}

// ─── Composite style presets (common patterns) ──────────────────────────────

export const CARD = 'v2-card'

export const SECTION_STYLE = { marginBottom: S['5xl'] }

export const PILL = {
    base: {
        borderRadius: R.pill,
        fontSize: 11,
        fontWeight: 500,
        cursor: 'pointer',
        transition: TRANSITION.fast,
        whiteSpace: 'nowrap',
    },
    sm: { padding: '2px 8px' },
    md: { padding: '4px 12px' },
    lg: { padding: '4px 14px', fontSize: 12 },
    active: {
        border: `1px solid ${C.accentBlue}`,
        background: C.accentBlueBg,
        color: 'white',
    },
    inactive: {
        border: `1px solid ${C.w08}`,
        background: C.w04,
        color: C.textPlaceholder,
    },
}

export const MODAL = {
    overlay: {
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center',
    },
    box: {
        background: C.modal, borderRadius: R.modal, border: B.medium,
        padding: S['5xl'], minWidth: 420, maxWidth: 540, maxHeight: '80vh', overflowY: 'auto',
    },
}

export const TOOLTIP_STYLE = {
    background: C.surfaceElevated,
    border: `1px solid ${C.w12}`,
    borderRadius: R.sm,
    fontSize: 10,
    padding: '4px 8px',
}

// ─── Semantic color maps (status / severity / channels) ─────────────────────

export const STATUS_COLORS = {
    danger:  { border: C.dangerBorder,  dot: C.danger,  valueFill: C.danger  },
    warning: { border: C.warningBorder, dot: C.warning, valueFill: C.warning },
    ok:      { border: C.successBorder, dot: C.success, valueFill: C.success },
    info:    { border: C.infoBorder,    dot: C.info,    valueFill: C.info    },
    neutral: { border: C.w07,           dot: C.w30,     valueFill: C.textPrimary },
}

export const SEVERITY = {
    HIGH:   { color: C.danger,  bg: C.dangerBg,  border: C.dangerBorder  },
    MEDIUM: { color: C.warning, bg: C.warningBg, border: C.warningBorder },
    LOW:    { color: C.info,    bg: C.infoBg,     border: C.infoBorder    },
}

export const CHANNEL_COLORS = {
    SEARCH: C.accentBlue, DISPLAY: C.accentPurple, VIDEO: C.warning,
    SHOPPING: C.success, DISCOVER: '#F472B6', CROSS_NETWORK: '#94A3B8',
}

export const AD_STRENGTH_COLOR = { EXCELLENT: C.success, GOOD: C.accentBlue, AVERAGE: C.warning, POOR: C.danger }

export const CAMPAIGN_STATUS = {
    ENABLED:  { dot: C.success, label: 'Aktywna'    },
    PAUSED:   { dot: C.warning, label: 'Wstrzymana' },
    REMOVED:  { dot: C.danger,  label: 'Usunięta'   },
}

// ─── Legacy aliases (backwards compat — prefer named exports above) ─────────
export const TH = T.th
export const TD = T.td
export const TD_DIM = T.tdDim
export const MODAL_OVERLAY = MODAL.overlay
export const MODAL_BOX = MODAL.box

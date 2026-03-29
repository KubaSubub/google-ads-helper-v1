// Shared constants and helper components used across keyword tab components

export const MATCH_COLORS = {
    EXACT: { color: '#4ADE80', bg: 'rgba(74,222,128,0.1)', border: 'rgba(74,222,128,0.2)' },
    PHRASE: { color: '#4F8EF7', bg: 'rgba(79,142,247,0.1)', border: 'rgba(79,142,247,0.2)' },
    BROAD: { color: '#FBBF24', bg: 'rgba(251,191,36,0.1)', border: 'rgba(251,191,36,0.2)' },
}

export const SCOPE_LABELS = { CAMPAIGN: 'Kampania', AD_GROUP: 'Grupa reklam' }
export const SOURCE_LABELS = { LOCAL_ACTION: 'Reczne', GOOGLE_ADS_SYNC: 'Google Ads' }

export const SERVING_STATUS_CONFIG = {
    LOW_SEARCH_VOLUME: { label: 'Malo zapytan', color: '#FBBF24' },
    BELOW_FIRST_PAGE_BID: { label: 'Bid za niski', color: '#F87171' },
    RARELY_SERVED: { label: 'Rzadko', color: '#FBBF24' },
}

export const PILL_STYLE = (active, color) => ({
    padding: '4px 11px',
    borderRadius: 999,
    fontSize: 11,
    fontWeight: active ? 500 : 400,
    border: `1px solid ${active ? (color || '#4F8EF7') : 'rgba(255,255,255,0.1)'}`,
    background: active ? `${color || '#4F8EF7'}18` : 'transparent',
    color: active ? (color || 'white') : 'rgba(255,255,255,0.4)',
    cursor: 'pointer',
})

export const TAB_STYLE = (active) => ({
    padding: '7px 16px',
    borderRadius: 999,
    fontSize: 12,
    fontWeight: active ? 600 : 400,
    border: `1px solid ${active ? '#4F8EF7' : 'rgba(255,255,255,0.1)'}`,
    background: active ? 'rgba(79,142,247,0.15)' : 'transparent',
    color: active ? '#4F8EF7' : 'rgba(255,255,255,0.45)',
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
})

export const INPUT_STYLE = {
    width: '100%', padding: '8px 12px', borderRadius: 8, fontSize: 13,
    background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)',
    color: '#F0F0F0', outline: 'none',
}

export const SELECT_STYLE = { ...INPUT_STYLE, cursor: 'pointer' }

export const BTN_PRIMARY = {
    padding: '8px 18px', borderRadius: 8, fontSize: 12, fontWeight: 600,
    background: '#4F8EF7', border: 'none', color: 'white', cursor: 'pointer',
}

export const BTN_SECONDARY = {
    padding: '8px 18px', borderRadius: 8, fontSize: 12, fontWeight: 500,
    background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
    color: 'rgba(255,255,255,0.6)', cursor: 'pointer',
}

export const BTN_DANGER = {
    ...BTN_PRIMARY, background: 'rgba(248,113,113,0.15)', color: '#F87171',
    border: '1px solid rgba(248,113,113,0.3)',
}

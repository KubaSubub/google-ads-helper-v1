import { useMemo } from 'react';
import { C, T, S, R, B, PILL, MODAL, TOOLTIP_STYLE, SEVERITY, TRANSITION, FONT } from '../constants/designTokens'

/**
 * Formats a value for display — converts micros fields to currency.
 */
function formatValue(key, value) {
    if (value === null || value === undefined) return '—';
    if (typeof value === 'object') return JSON.stringify(value);
    const str = String(value);
    // Convert micros to readable currency
    if (key && (key.includes('micros') || key.includes('amount_micros') || key.includes('bid_micros'))) {
        const num = parseFloat(str);
        if (!isNaN(num)) return `${(num / 1_000_000).toFixed(2)} PLN`;
    }
    return str;
}

/**
 * Flattens a nested JSON object into dot-separated keys.
 */
function flattenObj(obj, prefix = '') {
    const result = {};
    if (!obj || typeof obj !== 'object') return result;
    for (const [key, val] of Object.entries(obj)) {
        const fullKey = prefix ? `${prefix}.${key}` : key;
        if (val && typeof val === 'object' && !Array.isArray(val)) {
            Object.assign(result, flattenObj(val, fullKey));
        } else {
            result[fullKey] = val;
        }
    }
    return result;
}

export default function DiffView({ oldJson, newJson, changedFields }) {
    const { oldFlat, newFlat, fields } = useMemo(() => {
        let oldParsed = {};
        let newParsed = {};
        let fieldsList = [];

        try { if (oldJson) oldParsed = JSON.parse(oldJson); } catch {}
        try { if (newJson) newParsed = JSON.parse(newJson); } catch {}
        try { if (changedFields) fieldsList = JSON.parse(changedFields); } catch {}

        const oldFlat = flattenObj(oldParsed);
        const newFlat = flattenObj(newParsed);

        // If changedFields is available, use those; otherwise diff all keys
        let fields;
        if (fieldsList && fieldsList.length > 0) {
            fields = fieldsList;
        } else {
            const allKeys = new Set([...Object.keys(oldFlat), ...Object.keys(newFlat)]);
            fields = [...allKeys].filter(k => {
                return String(oldFlat[k] ?? '') !== String(newFlat[k] ?? '');
            });
        }

        return { oldFlat, newFlat, fields };
    }, [oldJson, newJson, changedFields]);

    if (fields.length === 0) {
        return (
            <div style={{ padding: '12px 16px', color: C.w40, fontSize: 13 }}>
                Brak szczegółów zmian.
            </div>
        );
    }

    return (
        <div style={{
            background: 'rgba(255,255,255,0.02)',
            borderRadius: 8,
            border: B.subtle,
            overflow: 'hidden',
        }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                    <tr style={{ background: C.w04 }}>
                        <th style={thStyle}>Pole</th>
                        <th style={{ ...thStyle, color: C.danger }}>Przed</th>
                        <th style={{ ...thStyle, color: C.success }}>Po</th>
                    </tr>
                </thead>
                <tbody>
                    {fields.map((field) => {
                        const oldVal = oldFlat[field];
                        const newVal = newFlat[field];
                        const changed = String(oldVal ?? '') !== String(newVal ?? '');
                        return (
                            <tr key={field} style={{ borderTop: `1px solid ${C.w05}` }}>
                                <td style={{ ...tdStyle, color: C.w60, fontFamily: 'monospace' }}>
                                    {field}
                                </td>
                                <td style={{
                                    ...tdStyle,
                                    color: changed ? C.danger : C.textMuted,
                                    background: changed ? 'rgba(248,113,113,0.06)' : 'transparent',
                                }}>
                                    {formatValue(field, oldVal)}
                                </td>
                                <td style={{
                                    ...tdStyle,
                                    color: changed ? C.success : C.textMuted,
                                    background: changed ? 'rgba(74,222,128,0.06)' : 'transparent',
                                }}>
                                    {formatValue(field, newVal)}
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}

const thStyle = {
    padding: '8px 12px',
    textAlign: 'left',
    fontSize: 10,
    fontWeight: 500,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    color: C.textMuted,
};

const tdStyle = {
    padding: '8px 12px',
    fontFamily: "'DM Sans', sans-serif",
    fontSize: 13,
};

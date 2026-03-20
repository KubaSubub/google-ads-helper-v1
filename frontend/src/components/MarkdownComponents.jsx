/**
 * Shared markdown renderer components for react-markdown (v10+).
 * Used by Agent.jsx and Reports.jsx.
 */
export const markdownComponents = {
    table: ({ children }) => (
        <div style={{ overflowX: 'auto', margin: '12px 0' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>{children}</table>
        </div>
    ),
    th: ({ children }) => (
        <th style={{
            textAlign: 'left', padding: '8px 12px',
            borderBottom: '1px solid rgba(255,255,255,0.1)',
            fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)',
            textTransform: 'uppercase', letterSpacing: '0.05em',
        }}>{children}</th>
    ),
    td: ({ children }) => (
        <td style={{
            padding: '6px 12px', borderBottom: '1px solid rgba(255,255,255,0.05)',
            color: 'rgba(255,255,255,0.75)',
        }}>{children}</td>
    ),
    strong: ({ children }) => <strong style={{ color: '#fff', fontWeight: 600 }}>{children}</strong>,
    h1: ({ children }) => <h1 style={{ fontSize: 20, fontWeight: 700, fontFamily: 'Syne', color: '#fff', margin: '16px 0 8px' }}>{children}</h1>,
    h2: ({ children }) => <h2 style={{ fontSize: 16, fontWeight: 600, fontFamily: 'Syne', color: '#fff', margin: '14px 0 6px' }}>{children}</h2>,
    h3: ({ children }) => <h3 style={{ fontSize: 14, fontWeight: 600, color: 'rgba(255,255,255,0.85)', margin: '12px 0 4px' }}>{children}</h3>,
    p: ({ children }) => <p style={{ color: 'rgba(255,255,255,0.7)', lineHeight: 1.6, margin: '6px 0' }}>{children}</p>,
    li: ({ children }) => <li style={{ color: 'rgba(255,255,255,0.7)', lineHeight: 1.6, marginBottom: 2 }}>{children}</li>,
    pre: ({ children }) => (
        <pre style={{
            background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 8, padding: 12, overflowX: 'auto', fontSize: 12, color: 'rgba(255,255,255,0.7)',
        }}>
            {children}
        </pre>
    ),
    code: ({ children }) => (
        <code style={{
            background: 'rgba(255,255,255,0.08)', padding: '2px 6px',
            borderRadius: 4, fontSize: 12, color: '#4F8EF7',
        }}>{children}</code>
    ),
}

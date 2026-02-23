/** @type {import('tailwindcss').Config} */
export default {
    content: ['./index.html', './src/**/*.{js,jsx}'],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                // Legacy (keep for compatibility with existing components)
                brand: {
                    50: '#eef2ff',
                    100: '#e0e7ff',
                    200: '#c7d2fe',
                    300: '#a5b4fc',
                    400: '#818cf8',
                    500: '#6366f1',
                    600: '#4f46e5',
                    700: '#4338ca',
                    800: '#3730a3',
                    900: '#312e81',
                },
                surface: {
                    50: '#f8fafc',
                    100: '#f1f5f9',
                    200: '#e2e8f0',
                    700: '#1e293b',
                    800: '#0f172a',
                    900: '#020617',
                },
                // Legacy aliases (keep existing pages working)
                'app-bg': '#0D0F14',
                'app-sidebar': '#111318',
                'app-card': '#334155',
                'app-text': '#F0F0F0',
                'app-muted': '#94A3B8',
                'app-accent': '#4F8EF7',
                'app-success': '#4ADE80',
                'app-warning': '#FBBF24',
                'app-danger': '#F87171',

                // V2 Design System
                v2: {
                    bg: '#0D0F14',
                    sidebar: '#111318',
                    card: 'rgba(255,255,255,0.03)',
                    'border-subtle': 'rgba(255,255,255,0.07)',
                    'border-hover': 'rgba(255,255,255,0.12)',
                    'accent-blue': '#4F8EF7',
                    'accent-purple': '#7B5CE0',
                    'text-primary': '#F0F0F0',
                    'text-secondary': 'rgba(255,255,255,0.55)',
                    'text-muted': 'rgba(255,255,255,0.3)',
                    success: '#4ADE80',
                    danger: '#F87171',
                    warning: '#FBBF24',
                },
            },
            fontFamily: {
                sans: ['DM Sans', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
                display: ['Syne', 'DM Sans', 'system-ui', 'sans-serif'],
                mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
            },
            borderRadius: {
                'card': '12px',
                'btn': '7px',
                'badge': '5px',
            },
            boxShadow: {
                'dropdown': '0 8px 32px rgba(0,0,0,0.4)',
                'modal': '0 8px 32px rgba(0,0,0,0.4)',
            },
        },
    },
    plugins: [],
}

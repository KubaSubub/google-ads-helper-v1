import { useState, useRef, useEffect } from 'react';
import { Info } from 'lucide-react';

const METRIC_DEFINITIONS = {
    CTR: 'Click-Through Rate — stosunek kliknięć do wyświetleń. Wyższy CTR = reklama bardziej trafna.',
    CPC: 'Cost Per Click — średni koszt jednego kliknięcia w reklamę.',
    CPA: 'Cost Per Action/Acquisition — koszt pozyskania jednej konwersji.',
    ROAS: 'Return On Ad Spend — przychód wygenerowany na każdą wydaną złotówkę (np. 3.0 = 3 zł przychodu za 1 zł wydatku).',
    CVR: 'Conversion Rate — procent kliknięć, które zakończyły się konwersją.',
    CPM: 'Cost Per Mille — koszt 1000 wyświetleń reklamy.',
    QS: 'Quality Score — ocena Google jakości słowa kluczowego (1-10). Wpływa na pozycję reklamy i CPC.',
    'Impression Share': 'Udział w wyświetleniach — procent wyświetleń uzyskanych vs dostępnych.',
    'Z-score': 'Odchylenie standardowe od średniej. Im wyższy z-score, tym bardziej nietypowa wartość.',
    'R²': 'Współczynnik determinacji — mierzy jak dobrze model pasuje do danych (0-1). Bliżej 1 = lepszy.',
    Konwersje: 'Działania użytkownika uznane za wartościowe (zakup, formularz, telefon). Google Ads raportuje ułamkowo.',
    ROAS_formula: 'Przychód z konwersji ÷ Koszt reklamy',
};

export function MetricTooltip({ term, children, inline = false }) {
    const [visible, setVisible] = useState(false);
    const [position, setPosition] = useState({ top: 0, left: 0 });
    const triggerRef = useRef(null);
    const tooltipRef = useRef(null);

    const definition = METRIC_DEFINITIONS[term];
    if (!definition) return children || <span>{term}</span>;

    useEffect(() => {
        if (visible && triggerRef.current) {
            const rect = triggerRef.current.getBoundingClientRect();
            const tooltipWidth = 260;
            let left = rect.left + rect.width / 2 - tooltipWidth / 2;
            if (left < 8) left = 8;
            if (left + tooltipWidth > window.innerWidth - 8) left = window.innerWidth - tooltipWidth - 8;
            setPosition({
                top: rect.bottom + 6,
                left,
            });
        }
    }, [visible]);

    return (
        <span
            ref={triggerRef}
            onMouseEnter={() => setVisible(true)}
            onMouseLeave={() => setVisible(false)}
            style={{
                position: 'relative',
                cursor: 'help',
                display: inline ? 'inline-flex' : 'inline-flex',
                alignItems: 'center',
                gap: 3,
            }}
        >
            {children || <span>{term}</span>}
            <Info size={11} style={{ color: 'rgba(255,255,255,0.25)', flexShrink: 0 }} />

            {visible && (
                <div
                    ref={tooltipRef}
                    style={{
                        position: 'fixed',
                        top: position.top,
                        left: position.left,
                        width: 260,
                        padding: '10px 14px',
                        background: '#1A1D24',
                        border: '1px solid rgba(255,255,255,0.12)',
                        borderRadius: 8,
                        fontSize: 11,
                        lineHeight: 1.5,
                        color: 'rgba(255,255,255,0.7)',
                        zIndex: 9999,
                        pointerEvents: 'none',
                        boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
                    }}
                >
                    <div style={{ fontWeight: 600, color: '#4F8EF7', marginBottom: 3, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                        {term}
                    </div>
                    {definition}
                </div>
            )}
        </span>
    );
}

export { METRIC_DEFINITIONS };
export default MetricTooltip;

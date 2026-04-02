import { useState, useEffect, useRef } from 'react';
import { useApp } from '../contexts/AppContext';
import { getAgentStatus } from '../api';
import {
    Bot,
    Send,
    Loader2,
    FileText,
    Megaphone,
    Wallet,
    Search,
    KeyRound,
    AlertTriangle,
    Sparkles,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { C, T, S, R, B, PILL, MODAL, TOOLTIP_STYLE, SEVERITY, TRANSITION, FONT } from '../constants/designTokens'
import { markdownComponents } from '../components/MarkdownComponents'

const QUICK_ACTIONS = [
    {
        label: 'Raport tygodniowy',
        icon: FileText,
        reportType: 'weekly',
        message: 'Przygotuj raport tygodniowy z KPI, zmianami tydzień do tygodnia, aktywnymi alertami i top rekomendacjami.',
    },
    {
        label: 'Analiza kampanii',
        icon: Megaphone,
        reportType: 'campaigns',
        message: 'Przeanalizuj wszystkie aktywne kampanie. Porównaj wyniki, zidentyfikuj najlepsze i najgorsze, sprawdź pacing budżetów.',
    },
    {
        label: 'Analiza budżetów',
        icon: Wallet,
        reportType: 'budget',
        message: 'Sprawdź pacing budżetów i zidentyfikuj zmarnowane wydatki. Zaproponuj realokację.',
    },
    {
        label: 'Wyszukiwane frazy',
        icon: Search,
        reportType: 'search_terms',
        message: 'Przeanalizuj wyszukiwane frazy. Znajdź frazy marnujące budżet, zaproponuj wykluczenia.',
    },
    {
        label: 'Słowa kluczowe',
        icon: KeyRound,
        reportType: 'keywords',
        message: 'Przeanalizuj wydajność słów kluczowych. Znajdź słowa z niskim Quality Score, wysokim kosztem bez konwersji.',
    },
    {
        label: 'Alerty i anomalie',
        icon: AlertTriangle,
        reportType: 'alerts',
        message: 'Podsumuj aktywne alerty i anomalie. Wyjaśnij każdy problem, zaproponuj działania naprawcze.',
    },
];


export default function Agent() {
    const { selectedClientId } = useApp();
    const [messages, setMessages] = useState(() => {
        try {
            const saved = localStorage.getItem('agent_chat');
            return saved ? JSON.parse(saved) : [];
        } catch { return []; }
    });
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [status, setStatus] = useState(''); // status text during generation
    const [agentAvailable, setAgentAvailable] = useState(null);
    const [tokenUsage, setTokenUsage] = useState(null);
    const [modelName, setModelName] = useState(null);
    const messagesEndRef = useRef(null);
    const textareaRef = useRef(null);

    useEffect(() => {
        getAgentStatus()
            .then((data) => setAgentAvailable(data.available))
            .catch(() => setAgentAvailable(false));
    }, []);

    useEffect(() => {
        if (messages.length > 0) {
            const toSave = messages.slice(-50);
            try { localStorage.setItem('agent_chat', JSON.stringify(toSave)); } catch {}
        }
    }, [messages]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, status]);

    const sendMessageSSE = async (message, reportType = 'freeform') => {
        if (!message.trim() || isLoading || !selectedClientId) return;

        const userMsg = { role: 'user', content: message.trim() };
        setMessages((prev) => [...prev, userMsg]);
        setInput('');
        setIsLoading(true);
        setTokenUsage(null);
        setModelName(null);
        setStatus('Pobieram dane...');

        let fullContent = '';

        try {
            const abortCtrl = new AbortController();
            const timeoutId = setTimeout(() => abortCtrl.abort(), 120_000); // 2 min timeout
            const response = await fetch(`/api/v1/agent/chat?client_id=${selectedClientId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ message: message.trim(), report_type: reportType }),
                signal: abortCtrl.signal,
            });

            if (!response.ok) {
                if (response.status === 401) {
                    window.dispatchEvent(new CustomEvent('auth:unauthorized'));
                }
                throw new Error(`Blad serwera: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // Split on double newline (SSE event boundary)
                const parts = buffer.split('\n\n');
                buffer = parts.pop(); // keep incomplete event

                for (const part of parts) {
                    const lines = part.trim().split('\n');
                    let eventType = 'delta';
                    let eventData = '';

                    for (const line of lines) {
                        if (line.startsWith('event: ')) {
                            eventType = line.slice(7).trim();
                        } else if (line.startsWith('data: ')) {
                            eventData = line.slice(6).replace(/\\n/g, '\n');
                        }
                    }

                    if (eventType === 'status') {
                        setStatus(eventData);
                    } else if (eventType === 'model') {
                        setModelName(eventData);
                    } else if (eventType === 'usage') {
                        try { setTokenUsage(JSON.parse(eventData)); } catch {}
                    } else if (eventType === 'delta') {
                        fullContent += eventData;
                        // Update assistant message in real-time
                        setMessages((prev) => {
                            const newMsgs = [...prev];
                            const lastIdx = newMsgs.length - 1;
                            if (lastIdx >= 0 && newMsgs[lastIdx].role === 'assistant') {
                                newMsgs[lastIdx] = { ...newMsgs[lastIdx], content: fullContent };
                            } else {
                                newMsgs.push({ role: 'assistant', content: fullContent });
                            }
                            return newMsgs;
                        });
                    } else if (eventType === 'error') {
                        fullContent += `\n\n**Blad:** ${eventData}`;
                        setMessages((prev) => {
                            const newMsgs = [...prev];
                            const lastIdx = newMsgs.length - 1;
                            if (lastIdx >= 0 && newMsgs[lastIdx].role === 'assistant') {
                                newMsgs[lastIdx] = { ...newMsgs[lastIdx], content: fullContent };
                            } else {
                                newMsgs.push({ role: 'assistant', content: fullContent });
                            }
                            return newMsgs;
                        });
                    } else if (eventType === 'done') {
                        // Ensure assistant message exists
                        if (!fullContent) {
                            setMessages((prev) => [...prev, { role: 'assistant', content: 'Raport wygenerowany.' }]);
                        }
                    }
                }
            }
            clearTimeout(timeoutId);
        } catch (err) {
            clearTimeout(timeoutId);
            const msg = err.name === 'AbortError' ? 'Przekroczono limit czasu (120s). Sprobuj ponownie.' : err.message;
            setMessages((prev) => [
                ...prev,
                { role: 'assistant', content: `**Blad:** ${msg}` },
            ]);
        }

        setIsLoading(false);
        setStatus('');
    };

    const handleSend = () => sendMessageSSE(input, 'freeform');
    const handleQuickAction = (action) => sendMessageSSE(action.message, action.reportType);

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
                <Sparkles size={22} style={{ color: C.accentPurple }} />
                <h1 style={{ fontSize: 22, fontWeight: 700, fontFamily: 'Syne', color: '#fff', margin: 0 }}>
                    Asystent AI
                </h1>
                {agentAvailable !== null && (
                    <span
                        style={{
                            fontSize: 11,
                            padding: '2px 10px',
                            borderRadius: 999,
                            background: agentAvailable ? 'rgba(74,222,128,0.12)' : 'rgba(248,113,113,0.12)',
                            color: agentAvailable ? C.success : C.danger,
                            border: `1px solid ${agentAvailable ? 'rgba(74,222,128,0.25)' : 'rgba(248,113,113,0.25)'}`,
                        }}
                    >
                        {agentAvailable ? 'Claude dostepny' : 'Claude niedostepny'}
                    </span>
                )}
                {messages.length > 0 && (
                    <button
                        onClick={() => { setMessages([]); localStorage.removeItem('agent_chat') }}
                        style={{
                            fontSize: 11, padding: '2px 10px', borderRadius: 999,
                            background: C.w04, border: `1px solid ${C.w08}`,
                            color: C.w40, cursor: 'pointer', marginLeft: 'auto',
                        }}
                    >
                        Wyczyść historię
                    </button>
                )}
            </div>

            <div style={{ display: 'flex', gap: 20 }}>
                {/* Chat area */}
                <div style={{ flex: '1 1 70%', display: 'flex', flexDirection: 'column', minHeight: 500 }}>
                    {/* Messages */}
                    <div
                        style={{
                            flex: 1,
                            background: 'rgba(255,255,255,0.02)',
                            border: B.card,
                            borderRadius: 12,
                            padding: 16,
                            overflowY: 'auto',
                            maxHeight: 'calc(100vh - 320px)',
                            minHeight: 400,
                        }}
                    >
                        {messages.length === 0 && !isLoading && (
                            <div style={{ textAlign: 'center', padding: '60px 20px', color: C.w30 }}>
                                <Bot size={40} style={{ marginBottom: 12, opacity: 0.4 }} />
                                <p style={{ fontSize: 14, margin: 0 }}>
                                    Wybierz typ raportu lub zadaj pytanie o swoje kampanie
                                </p>
                            </div>
                        )}

                        {messages.map((msg, i) => (
                            <div
                                key={i}
                                style={{
                                    marginBottom: 16,
                                    display: 'flex',
                                    justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                                }}
                            >
                                <div
                                    style={{
                                        maxWidth: msg.role === 'user' ? '70%' : '100%',
                                        padding: msg.role === 'user' ? '10px 16px' : '0',
                                        borderRadius: 10,
                                        background: msg.role === 'user' ? C.infoBg : 'transparent',
                                        border: msg.role === 'user' ? '1px solid rgba(79,142,247,0.2)' : 'none',
                                        color: msg.role === 'user' ? '#fff' : C.w80,
                                        fontSize: 13.5,
                                        lineHeight: 1.6,
                                    }}
                                >
                                    {msg.role === 'assistant' ? (
                                        <ReactMarkdown
                                            remarkPlugins={[remarkGfm]}
                                            components={markdownComponents}
                                        >
                                            {msg.content}
                                        </ReactMarkdown>
                                    ) : (
                                        msg.content
                                    )}
                                </div>
                            </div>
                        ))}

                        {isLoading && status && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0' }}>
                                <Loader2 size={14} className="animate-spin" style={{ color: C.accentPurple }} />
                                <span style={{ fontSize: 12, color: C.w40 }}>{status}</span>
                            </div>
                        )}

                        {/* Token usage */}
                        {tokenUsage && !isLoading && (
                            <div style={{
                                display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
                                padding: '6px 12px', borderRadius: 8,
                                background: C.w03, border: B.card,
                                fontSize: 11, color: C.w50,
                            }}>
                                {modelName && (
                                    <span style={{
                                        padding: '1px 6px', borderRadius: 999, fontSize: 10,
                                        background: 'rgba(123,92,224,0.12)', color: C.accentPurple,
                                        border: '1px solid rgba(123,92,224,0.25)',
                                    }}>{modelName}</span>
                                )}
                                <span><span style={{ color: C.w30 }}>in:</span> {(tokenUsage.input_tokens || 0).toLocaleString('pl-PL')}</span>
                                <span><span style={{ color: C.w30 }}>out:</span> {(tokenUsage.output_tokens || 0).toLocaleString('pl-PL')}</span>
                                {tokenUsage.cache_read_tokens > 0 && (
                                    <span><span style={{ color: C.w30 }}>cache:</span> <span style={{ color: C.accentBlue }}>{tokenUsage.cache_read_tokens.toLocaleString('pl-PL')}</span></span>
                                )}
                                {tokenUsage.duration_ms > 0 && (
                                    <span style={{ color: C.w30 }}>{(tokenUsage.duration_ms / 1000).toFixed(1)}s</span>
                                )}
                                {tokenUsage.total_cost_usd > 0 && (
                                    <span style={{ color: C.warning }}>${tokenUsage.total_cost_usd.toFixed(4)}</span>
                                )}
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input */}
                    <div
                        style={{
                            marginTop: 12,
                            display: 'flex',
                            gap: 8,
                            alignItems: 'flex-end',
                        }}
                    >
                        <textarea
                            ref={textareaRef}
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder={selectedClientId ? 'Zadaj pytanie o kampanie...' : 'Wybierz klienta w sidebar'}
                            disabled={isLoading || !selectedClientId || !agentAvailable}
                            rows={1}
                            style={{
                                flex: 1,
                                padding: '10px 14px',
                                borderRadius: 10,
                                border: B.medium,
                                background: C.w04,
                                color: '#fff',
                                fontSize: 13.5,
                                resize: 'none',
                                outline: 'none',
                                fontFamily: 'DM Sans, sans-serif',
                                minHeight: 42,
                                maxHeight: 120,
                            }}
                            onInput={(e) => {
                                e.target.style.height = 'auto';
                                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
                            }}
                        />
                        <button
                            onClick={handleSend}
                            disabled={!input.trim() || isLoading || !selectedClientId || !agentAvailable}
                            style={{
                                padding: '10px 16px',
                                borderRadius: 10,
                                border: 'none',
                                background: input.trim() && !isLoading ? C.accentBlue : C.w08,
                                color: input.trim() && !isLoading ? '#fff' : C.w30,
                                cursor: input.trim() && !isLoading ? 'pointer' : 'not-allowed',
                                transition: 'all 0.15s',
                                display: 'flex',
                                alignItems: 'center',
                                height: 42,
                            }}
                        >
                            <Send size={16} />
                        </button>
                    </div>
                </div>

                {/* Quick actions sidebar */}
                <div style={{ flex: '0 0 280px' }}>
                    <div
                        style={{
                            fontSize: 10,
                            fontWeight: 500,
                            color: C.textMuted,
                            textTransform: 'uppercase',
                            letterSpacing: '0.1em',
                            marginBottom: 10,
                        }}
                    >
                        Szybkie raporty
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        {QUICK_ACTIONS.map((action) => {
                            const Icon = action.icon;
                            return (
                                <button
                                    key={action.reportType}
                                    onClick={() => handleQuickAction(action)}
                                    disabled={isLoading || !selectedClientId || !agentAvailable}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: 10,
                                        padding: '10px 14px',
                                        borderRadius: 10,
                                        border: B.card,
                                        background: C.w03,
                                        color: C.w70,
                                        cursor: isLoading ? 'not-allowed' : 'pointer',
                                        fontSize: 13,
                                        textAlign: 'left',
                                        transition: 'all 0.15s',
                                        opacity: isLoading ? 0.5 : 1,
                                    }}
                                    onMouseEnter={(e) => {
                                        if (!isLoading) {
                                            e.currentTarget.style.background = C.w06;
                                            e.currentTarget.style.borderColor = C.infoBorder;
                                            e.currentTarget.style.color = '#fff';
                                        }
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.background = C.w03;
                                        e.currentTarget.style.borderColor = C.w07;
                                        e.currentTarget.style.color = C.w70;
                                    }}
                                >
                                    <Icon size={15} style={{ flexShrink: 0, color: C.accentPurple }} />
                                    <span>{action.label}</span>
                                </button>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}

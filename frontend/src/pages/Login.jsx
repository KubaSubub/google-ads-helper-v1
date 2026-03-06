import { useState, useRef, useEffect } from 'react';
import { getLoginUrl, getAuthStatus, getSetupStatus, saveSetup } from '../api';
import { Zap, LogIn, Loader2, Key, ChevronRight, CheckCircle, ExternalLink } from 'lucide-react';

const inputStyle = {
    width: '100%',
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 8,
    padding: '10px 14px',
    fontSize: 13,
    color: 'white',
    outline: 'none',
    fontFamily: 'DM Sans, sans-serif',
};

const labelStyle = {
    display: 'block',
    fontSize: 11,
    fontWeight: 500,
    color: 'rgba(255,255,255,0.5)',
    marginBottom: 6,
};

export default function Login({ onAuthComplete }) {
    const [step, setStep] = useState(null); // null = loading, 'setup', 'login'
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [setupData, setSetupData] = useState({
        developer_token: '',
        client_id: '',
        client_secret: '',
        login_customer_id: '',
    });
    const intervalRef = useRef(null);

    useEffect(() => {
        checkSetup();
        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
        };
    }, []);

    async function checkSetup() {
        const maxWaitMs = 30000;
        const started = Date.now();

        while (Date.now() - started < maxWaitMs) {
            try {
                const data = await getSetupStatus();
                setStep(data.configured ? 'login' : 'setup');
                return;
            } catch (err) {
                if (err.status && err.status < 500) break;
                await new Promise(r => setTimeout(r, 1000));
            }
        }
        setStep('setup');
    }

    function handleSetupChange(field, value) {
        setSetupData(prev => ({ ...prev, [field]: value }));
    }

    async function handleSetupSubmit(e) {
        e.preventDefault();
        if (!setupData.developer_token || !setupData.client_id || !setupData.client_secret) {
            setError('Wypelnij wszystkie wymagane pola.');
            return;
        }
        setLoading(true);
        setError(null);
        try {
            await saveSetup(setupData);
            setStep('login');
        } catch (err) {
            setError(err.message || 'Blad zapisu credentials.');
        } finally {
            setLoading(false);
        }
    }

    async function handleLogin() {
        setLoading(true);
        setError(null);
        try {
            const data = await getLoginUrl();
            window.open(data.auth_url, '_blank');
            startPolling();
        } catch (err) {
            setError(err.message || 'Nie udalo sie rozpoczac logowania');
            setLoading(false);
        }
    }

    function startPolling() {
        intervalRef.current = setInterval(async () => {
            try {
                const data = await getAuthStatus();
                if (data.authenticated) {
                    clearInterval(intervalRef.current);
                    intervalRef.current = null;
                    setLoading(false);
                    onAuthComplete();
                }
            } catch {
                // keep polling
            }
        }, 2000);

        setTimeout(() => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
                setLoading(false);
                setError('Timeout — nie zalogowano w ciagu 5 minut. Sprobuj ponownie.');
            }
        }, 300_000);
    }

    if (step === null) {
        return (
            <div style={{
                minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: '#0D0F14',
            }}>
                <Loader2 size={28} style={{ color: '#4F8EF7' }} className="animate-spin" />
            </div>
        );
    }

    return (
        <div style={{
            minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: '#0D0F14',
        }}>
            <div style={{
                maxWidth: 440, width: '100%', padding: 32,
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.07)',
                borderRadius: 16, textAlign: 'center',
            }}>
                {/* Logo */}
                <div style={{
                    width: 56, height: 56, margin: '0 auto 20px',
                    borderRadius: 14,
                    background: 'linear-gradient(135deg, #4F8EF7, #7B5CE0)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                    <Zap size={28} color="white" />
                </div>

                <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', marginBottom: 4 }}>
                    Google Ads Helper
                </h1>

                {/* Step indicator */}
                <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                    margin: '16px 0 24px', fontSize: 11, color: 'rgba(255,255,255,0.35)',
                }}>
                    <span style={{
                        display: 'flex', alignItems: 'center', gap: 4,
                        color: step === 'setup' ? '#4F8EF7' : '#4ADE80',
                    }}>
                        {step === 'login' ? <CheckCircle size={12} /> : <Key size={12} />}
                        Konfiguracja API
                    </span>
                    <ChevronRight size={12} style={{ color: 'rgba(255,255,255,0.15)' }} />
                    <span style={{
                        display: 'flex', alignItems: 'center', gap: 4,
                        color: step === 'login' ? '#4F8EF7' : 'rgba(255,255,255,0.25)',
                    }}>
                        <LogIn size={12} />
                        Logowanie Google
                    </span>
                </div>

                {error && (
                    <div style={{
                        marginBottom: 16, padding: '10px 14px', borderRadius: 8,
                        background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.2)',
                        color: '#F87171', fontSize: 12, textAlign: 'left',
                    }}>
                        {error}
                    </div>
                )}

                {/* STEP 1: Setup credentials */}
                {step === 'setup' && (
                    <form onSubmit={handleSetupSubmit} style={{ textAlign: 'left' }}>
                        <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginBottom: 20, textAlign: 'center' }}>
                            Wpisz dane z Google Cloud Console i Google Ads API.
                            {' '}
                            <a
                                href="https://developers.google.com/google-ads/api/docs/first-call/overview"
                                target="_blank"
                                rel="noopener noreferrer"
                                style={{ color: '#4F8EF7', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 2 }}
                            >
                                Jak uzyskac? <ExternalLink size={10} />
                            </a>
                        </p>

                        <div style={{ marginBottom: 14 }}>
                            <label style={labelStyle}>Developer Token *</label>
                            <input
                                style={inputStyle}
                                value={setupData.developer_token}
                                onChange={e => handleSetupChange('developer_token', e.target.value)}
                                placeholder="np. aBcDeFgHiJkLmNoPqRs"
                            />
                        </div>

                        <div style={{ marginBottom: 14 }}>
                            <label style={labelStyle}>OAuth Client ID *</label>
                            <input
                                style={inputStyle}
                                value={setupData.client_id}
                                onChange={e => handleSetupChange('client_id', e.target.value)}
                                placeholder="np. 123456789-abc.apps.googleusercontent.com"
                            />
                        </div>

                        <div style={{ marginBottom: 14 }}>
                            <label style={labelStyle}>OAuth Client Secret *</label>
                            <input
                                style={inputStyle}
                                type="password"
                                value={setupData.client_secret}
                                onChange={e => handleSetupChange('client_secret', e.target.value)}
                                placeholder="GOCSPX-..."
                            />
                        </div>

                        <div style={{ marginBottom: 20 }}>
                            <label style={labelStyle}>Login Customer ID (MCC)</label>
                            <input
                                style={inputStyle}
                                value={setupData.login_customer_id}
                                onChange={e => handleSetupChange('login_customer_id', e.target.value)}
                                placeholder="np. 1234567890 (opcjonalne)"
                            />
                            <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', marginTop: 4 }}>
                                Wymagane jesli korzystasz z konta MCC (menadzera).
                            </p>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            style={{
                                width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                                padding: '10px 20px', borderRadius: 10, fontSize: 13, fontWeight: 600,
                                background: 'rgba(79,142,247,0.15)', border: '1px solid rgba(79,142,247,0.3)',
                                color: '#4F8EF7', cursor: loading ? 'wait' : 'pointer',
                                opacity: loading ? 0.6 : 1,
                            }}
                        >
                            {loading ? <Loader2 size={16} className="animate-spin" /> : <Key size={16} />}
                            {loading ? 'Zapisywanie...' : 'Zapisz i przejdz dalej'}
                        </button>
                    </form>
                )}

                {/* STEP 2: OAuth Login */}
                {step === 'login' && (
                    <div>
                        <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginBottom: 20 }}>
                            Credentials skonfigurowane. Zaloguj sie kontem Google z dostepem do Google Ads.
                        </p>

                        <button
                            onClick={handleLogin}
                            disabled={loading}
                            style={{
                                width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                                padding: '10px 20px', borderRadius: 10, fontSize: 13, fontWeight: 600,
                                background: 'rgba(79,142,247,0.15)', border: '1px solid rgba(79,142,247,0.3)',
                                color: '#4F8EF7', cursor: loading ? 'wait' : 'pointer',
                                opacity: loading ? 0.6 : 1,
                            }}
                        >
                            {loading ? (
                                <>
                                    <Loader2 size={16} className="animate-spin" />
                                    Czekam na logowanie...
                                </>
                            ) : (
                                <>
                                    <LogIn size={16} />
                                    Zaloguj sie przez Google
                                </>
                            )}
                        </button>

                        {loading && (
                            <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', marginTop: 12 }}>
                                Otworzylo sie okno przegladarki. Zaloguj sie tam i wroc tutaj.
                            </p>
                        )}

                        <button
                            onClick={() => { setStep('setup'); setError(null); }}
                            style={{
                                marginTop: 16, background: 'none', border: 'none',
                                color: 'rgba(255,255,255,0.3)', fontSize: 11, cursor: 'pointer',
                                textDecoration: 'underline',
                            }}
                        >
                            Zmien credentials API
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

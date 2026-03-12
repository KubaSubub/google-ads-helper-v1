import { useState, useRef, useEffect, useCallback } from 'react';
import {
    getLoginUrl,
    getAuthStatus,
    getSetupStatus,
    getStoredSetupValues,
    saveSetup,
} from '../api';
import {
    Zap,
    LogIn,
    Loader2,
    Key,
    ChevronRight,
    CheckCircle,
    ExternalLink,
    AlertTriangle,
    Eye,
    EyeOff,
} from 'lucide-react';

const EMPTY_AUTH_STATUS = {
    authenticated: false,
    configured: false,
    ready: false,
    reason: '',
    missing_credentials: [],
};

const EMPTY_SETUP_STATUS = {
    configured: false,
    has_developer_token: false,
    has_client_id: false,
    has_client_secret: false,
    has_login_customer_id: false,
    missing_credentials: [],
};

const EMPTY_SETUP_DATA = {
    developer_token: '',
    client_id: '',
    client_secret: '',
    login_customer_id: '',
};

const HIDDEN_SETUP_FIELDS = {
    developer_token: false,
    client_id: false,
    client_secret: false,
    login_customer_id: false,
};

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

const hiddenFieldInputStyle = {
    ...inputStyle,
    paddingRight: 44,
};

const labelStyle = {
    display: 'block',
    fontSize: 11,
    fontWeight: 500,
    color: 'rgba(255,255,255,0.5)',
    marginBottom: 6,
};

const inputWrapStyle = {
    position: 'relative',
};

const eyeButtonStyle = {
    position: 'absolute',
    top: '50%',
    right: 12,
    transform: 'translateY(-50%)',
    background: 'none',
    border: 'none',
    color: 'rgba(255,255,255,0.38)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 0,
    cursor: 'pointer',
};

export default function Login({ onAuthComplete, initialAuthStatus = EMPTY_AUTH_STATUS }) {
    const [step, setStep] = useState(null); // null = loading, 'setup', 'oauth', 'ready-blocked'
    const [loading, setLoading] = useState(false);
    const [loadingStoredSetup, setLoadingStoredSetup] = useState(false);
    const [error, setError] = useState(initialAuthStatus.reason || null);
    const [authStatus, setAuthStatus] = useState({ ...EMPTY_AUTH_STATUS, ...initialAuthStatus });
    const [setupStatus, setSetupStatus] = useState(EMPTY_SETUP_STATUS);
    const [setupData, setSetupData] = useState(EMPTY_SETUP_DATA);
    const [visibleSetupFields, setVisibleSetupFields] = useState({ ...HIDDEN_SETUP_FIELDS });
    const intervalRef = useRef(null);
    const timeoutRef = useRef(null);

    const clearTimers = useCallback(() => {
        if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
        }
        if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
        }
    }, []);

    const resetSetupVisibility = useCallback(() => {
        setVisibleSetupFields({ ...HIDDEN_SETUP_FIELDS });
    }, []);

    const loadStoredSetupValues = useCallback(async () => {
        setLoadingStoredSetup(true);
        try {
            const storedValues = await getStoredSetupValues();
            setSetupData({ ...EMPTY_SETUP_DATA, ...storedValues });
        } catch (err) {
            setError(err.message || 'Nie udalo sie wczytac zapisanych credentials.');
        } finally {
            setLoadingStoredSetup(false);
        }
    }, []);

    const applyStatus = useCallback((setupDataResponse, authDataResponse) => {
        const nextSetupStatus = { ...EMPTY_SETUP_STATUS, ...setupDataResponse };
        const nextAuthStatus = { ...EMPTY_AUTH_STATUS, ...authDataResponse };

        setSetupStatus(nextSetupStatus);
        setAuthStatus(nextAuthStatus);

        if (!nextSetupStatus.configured) {
            setStep('setup');
            setError(null);
            return nextAuthStatus;
        }

        if (nextAuthStatus.ready) {
            setError(null);
            setStep('oauth');
            onAuthComplete();
            return nextAuthStatus;
        }

        if (nextAuthStatus.authenticated) {
            setStep('ready-blocked');
            setError(nextAuthStatus.reason || 'Logowanie zakonczone, ale API nadal nie jest gotowe.');
            return nextAuthStatus;
        }

        setStep('oauth');
        setError(null);
        return nextAuthStatus;
    }, [onAuthComplete]);

    const refreshStatus = useCallback(async () => {
        const maxWaitMs = 30000;
        const started = Date.now();

        while (Date.now() - started < maxWaitMs) {
            try {
                const [setupResponse, authResponse] = await Promise.all([
                    getSetupStatus(),
                    getAuthStatus(),
                ]);
                return applyStatus(setupResponse, authResponse);
            } catch (err) {
                if (err.status && err.status < 500) break;
                await new Promise((resolve) => setTimeout(resolve, 1000));
            }
        }

        setSetupStatus(EMPTY_SETUP_STATUS);
        setAuthStatus(EMPTY_AUTH_STATUS);
        setStep('setup');
        setError(null);
        return EMPTY_AUTH_STATUS;
    }, [applyStatus]);

    useEffect(() => {
        refreshStatus();
        return () => clearTimers();
    }, [clearTimers, refreshStatus]);

    useEffect(() => {
        if (step !== 'setup') {
            return;
        }
        resetSetupVisibility();
        loadStoredSetupValues();
    }, [loadStoredSetupValues, resetSetupVisibility, step]);

    function handleSetupChange(field, value) {
        setSetupData((prev) => ({ ...prev, [field]: value }));
    }

    function toggleSetupFieldVisibility(field) {
        setVisibleSetupFields((prev) => ({ ...prev, [field]: !prev[field] }));
    }

    function openSetupEditor() {
        setError(null);
        setStep('setup');
    }

    function renderMaskedSetupField(field, label, placeholder, options = {}) {
        const {
            required = false,
            hint = null,
            marginBottom = 14,
        } = options;
        const isVisible = visibleSetupFields[field];
        const isDisabled = loading || loadingStoredSetup;

        return (
            <div style={{ marginBottom }}>
                <label style={labelStyle}>{label}{required ? ' *' : ''}</label>
                <div style={inputWrapStyle}>
                    <input
                        style={hiddenFieldInputStyle}
                        type={isVisible ? 'text' : 'password'}
                        value={setupData[field]}
                        onChange={(e) => handleSetupChange(field, e.target.value)}
                        placeholder={placeholder}
                        autoComplete="off"
                        disabled={isDisabled}
                    />
                    <button
                        type="button"
                        onClick={() => toggleSetupFieldVisibility(field)}
                        disabled={isDisabled}
                        aria-label={isVisible ? `Ukryj ${label}` : `Pokaz ${label}`}
                        title={isVisible ? 'Ukryj wartosc' : 'Pokaz wartosc'}
                        style={{
                            ...eyeButtonStyle,
                            cursor: isDisabled ? 'default' : 'pointer',
                            opacity: isDisabled ? 0.45 : 1,
                        }}
                    >
                        {isVisible ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                </div>
                {hint && (
                    <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', marginTop: 4 }}>
                        {hint}
                    </p>
                )}
            </div>
        );
    }

    async function handleSetupSubmit(e) {
        e.preventDefault();
        if (loadingStoredSetup) {
            return;
        }
        if (!setupData.developer_token || !setupData.client_id || !setupData.client_secret) {
            setError('Wypelnij wszystkie wymagane pola.');
            return;
        }

        setLoading(true);
        setError(null);
        try {
            await saveSetup(setupData);
            await refreshStatus();
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
            const popup = window.open(data.auth_url, '_blank');
            if (!popup) {
                throw new Error('Przegladarka zablokowala okno logowania Google.');
            }
            startPolling();
        } catch (err) {
            setError(err.message || 'Nie udalo sie rozpoczac logowania.');
            setLoading(false);
        }
    }

    function startPolling() {
        clearTimers();

        intervalRef.current = setInterval(async () => {
            try {
                const data = await getAuthStatus();
                const nextAuthStatus = { ...EMPTY_AUTH_STATUS, ...data };
                setAuthStatus(nextAuthStatus);

                if (nextAuthStatus.ready) {
                    clearTimers();
                    setLoading(false);
                    setError(null);
                    onAuthComplete();
                    return;
                }

                if (nextAuthStatus.authenticated && !nextAuthStatus.ready) {
                    clearTimers();
                    setLoading(false);
                    setStep('ready-blocked');
                    setError(nextAuthStatus.reason || 'Logowanie zakonczone, ale API nadal nie jest gotowe.');
                }
            } catch {
                // keep polling
            }
        }, 2000);

        timeoutRef.current = setTimeout(() => {
            clearTimers();
            setLoading(false);
            setError('Timeout - nie zakonczono logowania w ciagu 5 minut. Sprobuj ponownie.');
        }, 300_000);
    }

    const setupComplete = step !== 'setup';
    const loginActive = step === 'oauth' || step === 'ready-blocked';

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

                <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                    margin: '16px 0 24px', fontSize: 11, color: 'rgba(255,255,255,0.35)',
                }}>
                    <span style={{
                        display: 'flex', alignItems: 'center', gap: 4,
                        color: setupComplete ? '#4ADE80' : '#4F8EF7',
                    }}>
                        {setupComplete ? <CheckCircle size={12} /> : <Key size={12} />}
                        Konfiguracja API
                    </span>
                    <ChevronRight size={12} style={{ color: 'rgba(255,255,255,0.15)' }} />
                    <span style={{
                        display: 'flex', alignItems: 'center', gap: 4,
                        color: loginActive ? '#4F8EF7' : 'rgba(255,255,255,0.25)',
                    }}>
                        <LogIn size={12} />
                        Logowanie Google
                    </span>
                </div>

                {step === 'ready-blocked' && (
                    <div style={{
                        marginBottom: 16,
                        padding: '12px 14px',
                        borderRadius: 8,
                        background: 'rgba(250,204,21,0.08)',
                        border: '1px solid rgba(250,204,21,0.2)',
                        color: '#FDE68A',
                        fontSize: 12,
                        textAlign: 'left',
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, fontWeight: 600 }}>
                            <AlertTriangle size={14} />
                            OAuth zakonczony, ale aplikacja nadal nie jest gotowa
                        </div>
                        <div>{authStatus.reason || 'Sprawdz zapisane credentials i sproboj ponownie.'}</div>
                    </div>
                )}

                {error && step !== 'ready-blocked' && (
                    <div style={{
                        marginBottom: 16, padding: '10px 14px', borderRadius: 8,
                        background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.2)',
                        color: '#F87171', fontSize: 12, textAlign: 'left',
                    }}>
                        {error}
                    </div>
                )}

                {step === 'setup' && (
                    <form onSubmit={handleSetupSubmit} style={{ textAlign: 'left' }}>
                        <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginBottom: 8, textAlign: 'center' }}>
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

                        <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', marginBottom: 20, textAlign: 'center' }}>
                            Dane sa zapisane lokalnie w Windows Credential Manager. Kliknij ikonke oka, aby sprawdzic wartosc.
                        </p>

                        {renderMaskedSetupField(
                            'developer_token',
                            'Developer Token',
                            'np. aBcDeFgHiJkLmNoPqRs',
                            { required: true }
                        )}

                        {renderMaskedSetupField(
                            'client_id',
                            'OAuth Client ID',
                            'np. 123456789-abc.apps.googleusercontent.com',
                            { required: true }
                        )}

                        {renderMaskedSetupField(
                            'client_secret',
                            'OAuth Client Secret',
                            'GOCSPX-...',
                            { required: true }
                        )}

                        {renderMaskedSetupField(
                            'login_customer_id',
                            'Login Customer ID (MCC)',
                            'np. 1234567890 (opcjonalne)',
                            {
                                marginBottom: 20,
                                hint: 'Wymagane, jesli korzystasz z konta MCC (menadzera).',
                            }
                        )}

                        <button
                            type="submit"
                            disabled={loading || loadingStoredSetup}
                            style={{
                                width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                                padding: '10px 20px', borderRadius: 10, fontSize: 13, fontWeight: 600,
                                background: 'rgba(79,142,247,0.15)', border: '1px solid rgba(79,142,247,0.3)',
                                color: '#4F8EF7', cursor: loading || loadingStoredSetup ? 'wait' : 'pointer',
                                opacity: loading || loadingStoredSetup ? 0.6 : 1,
                            }}
                        >
                            {loading || loadingStoredSetup ? <Loader2 size={16} className="animate-spin" /> : <Key size={16} />}
                            {loading ? 'Zapisywanie...' : loadingStoredSetup ? 'Wczytywanie...' : 'Zapisz i przejdz dalej'}
                        </button>
                    </form>
                )}

                {step === 'oauth' && (
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
                            onClick={openSetupEditor}
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

                {step === 'ready-blocked' && (
                    <div>
                        <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginBottom: 20 }}>
                            Logowanie OAuth jest zakonczone, ale backend nie moze jeszcze potwierdzic gotowosci Google Ads API.
                        </p>

                        <button
                            onClick={refreshStatus}
                            disabled={loading}
                            style={{
                                width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                                padding: '10px 20px', borderRadius: 10, fontSize: 13, fontWeight: 600,
                                background: 'rgba(79,142,247,0.15)', border: '1px solid rgba(79,142,247,0.3)',
                                color: '#4F8EF7', cursor: loading ? 'wait' : 'pointer',
                                opacity: loading ? 0.6 : 1,
                            }}
                        >
                            {loading ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
                            Sprawdz ponownie
                        </button>

                        <button
                            onClick={handleLogin}
                            disabled={loading}
                            style={{
                                width: '100%', marginTop: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                                padding: '10px 20px', borderRadius: 10, fontSize: 13, fontWeight: 600,
                                background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
                                color: '#E5E7EB', cursor: loading ? 'wait' : 'pointer',
                                opacity: loading ? 0.6 : 1,
                            }}
                        >
                            {loading ? <Loader2 size={16} className="animate-spin" /> : <LogIn size={16} />}
                            Zaloguj sie ponownie
                        </button>

                        <button
                            onClick={openSetupEditor}
                            style={{
                                marginTop: 16, background: 'none', border: 'none',
                                color: 'rgba(255,255,255,0.3)', fontSize: 11, cursor: 'pointer',
                                textDecoration: 'underline',
                            }}
                        >
                            Wroc do konfiguracji API
                        </button>

                        {!setupStatus.has_login_customer_id && (
                            <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', marginTop: 14 }}>
                                Brakuje Login Customer ID? Wroc do konfiguracji API i uzupelnij pole MCC.
                            </p>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
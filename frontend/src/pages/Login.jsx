import { useState, useRef, useEffect } from 'react';
import { getLoginUrl, getAuthStatus } from '../api';
import { Zap, LogIn, Loader2 } from 'lucide-react';

export default function Login({ onAuthComplete }) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const intervalRef = useRef(null);

    useEffect(() => {
        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
        };
    }, []);

    const handleLogin = async () => {
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
    };

    const startPolling = () => {
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

        // stop after 5 minutes
        setTimeout(() => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
                setLoading(false);
                setError('Timeout — nie zalogowano w ciagu 5 minut. Sprobuj ponownie.');
            }
        }, 300_000);
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-surface-900">
            <div className="max-w-md w-full p-8 bg-surface-800 rounded-2xl border border-surface-700/60 text-center">
                {/* Logo */}
                <div className="w-16 h-16 mx-auto mb-6 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
                    <Zap size={32} className="text-white" />
                </div>

                <h1 className="text-2xl font-bold text-white mb-2">Google Ads Helper</h1>
                <p className="text-surface-200/60 mb-8">
                    Polacz swoje konto Google Ads, aby rozpoczac.
                </p>

                {error && (
                    <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
                        {error}
                    </div>
                )}

                <button
                    onClick={handleLogin}
                    disabled={loading}
                    className="w-full flex items-center justify-center gap-3 px-6 py-3 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-medium rounded-lg transition-colors cursor-pointer disabled:cursor-wait"
                >
                    {loading ? (
                        <>
                            <Loader2 size={20} className="animate-spin" />
                            Czekam na logowanie...
                        </>
                    ) : (
                        <>
                            <LogIn size={20} />
                            Zaloguj sie przez Google
                        </>
                    )}
                </button>

                {loading && (
                    <p className="mt-4 text-xs text-surface-200/40">
                        Otworzylo sie okno przegladarki. Zaloguj sie tam na konto Google z dostepem do Google Ads.
                    </p>
                )}
            </div>
        </div>
    );
}

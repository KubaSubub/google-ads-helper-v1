import { useState, useEffect } from 'react';
import { getClients } from '../api';

export function useClients() {
    const [clients, setClients] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchClients = async () => {
        try {
            setLoading(true);
            const data = await getClients();
            setClients(Array.isArray(data) ? data : data.items || []);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchClients();
    }, []);

    return { clients, loading, error, refetch: fetchClients };
}

import { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../lib/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        checkAuth();
    }, []);

    async function checkAuth() {
        try {
            if (localStorage.getItem('token')) {
                const userData = await api.get('/api/users/me');
                setUser(userData);
            }
        } catch (err) {
            console.error("Auth check failed", err);
            localStorage.removeItem('token');
        } finally {
            setLoading(false);
        }
    }

    async function login(username, password) {
        // Standard OAuth2 password flow
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        const { access_token } = await api.post('/api/auth/token', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });

        localStorage.setItem('token', access_token);
        await checkAuth();
    }

    function logout() {
        localStorage.removeItem('token');
        setUser(null);
    }

    return (
        <AuthContext.Provider value={{ user, loading, login, logout, isAuthenticated: !!user }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    return useContext(AuthContext);
}

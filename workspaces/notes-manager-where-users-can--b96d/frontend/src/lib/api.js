import axios from 'axios';

// Get API URL from env or default to localhost
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

export const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor for Auth
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Response interceptor for Errors
api.interceptors.response.use(
    (response) => response.data, // Return data directly for cleaner call sites
    (error) => {
        const message = error.response?.data?.detail || error.message;
        console.error('API Error:', message);

        // Auto-logout on 401
        if (error.response?.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '/login';
        }

        return Promise.reject(new Error(message));
    }
);

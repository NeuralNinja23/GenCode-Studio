
import { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
// @ROUTE_IMPORTS - Integrator injects component imports here

function App() {
    return (
        <AuthProvider>
            <BrowserRouter>
                <Suspense fallback={<div className="h-screen w-full flex items-center justify-center">Loading...</div>}>
                    <Routes>
                        <Route path="/" element={<Navigate to="/dashboard" replace />} />

                        {/* @ROUTE_REGISTER - Integrator injects new routes here */}
                        {/* Example: <Route path="/dashboard" element={<Dashboard />} /> */}

                        <Route path="*" element={<div className="p-10">404 - Page Not Found</div>} />
                    </Routes>
                </Suspense>
            </BrowserRouter>
        </AuthProvider>
    );
}

export default App;

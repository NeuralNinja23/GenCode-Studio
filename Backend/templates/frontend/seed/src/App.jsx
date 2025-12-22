import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from "@/components/ui/sonner";

// @ROUTE_IMPORTS

function App() {
    return (
        <Router>
            <div className="min-h-screen bg-background text-foreground font-sans antialiased">
                <Routes>
                    <Route path="/" element={<Navigate to="/dashboard" replace />} />
                    {/* @ROUTE_REGISTER - Integrator injects new routes here */}
                </Routes>
                <Toaster />
            </div>
        </Router>
    );
}

export default App;

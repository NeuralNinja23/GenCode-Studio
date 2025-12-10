import React, { useEffect, useState } from 'react';
import { HashRouter, Routes, Route, useLocation } from 'react-router-dom';
import HomePage from './pages/HomePage';
import WorkspacePage from './pages/WorkspacePage';
import Header from './components/Header';
import MatrixBackground from './components/MatrixBackground';
import ErrorBoundary from './components/ErrorBoundary';

import './index.css';

// Component to conditionally render Header based on route
const ConditionalHeader: React.FC = () => {
  const location = useLocation();
  const isWorkspace = location.pathname.includes('/workspace');

  // Don't render main header on workspace pages - WorkspacePage has its own top bar
  if (isWorkspace) return null;

  return <Header />;
};

// ===================================================================
// SECTION 1: SERVICE WORKER REGISTRATION
// ===================================================================
// NOTE: Service worker registration is disabled until a proper sw.js is created.
// Uncomment the block below and create public/sw.js when PWA functionality is needed.
/*
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js')
    .then(registration => {
      console.log('[App.tsx] Service Worker registration initiated successfully.');
    })
    .catch(error => {
      console.error('[App.tsx] Service Worker registration failed:', error);
    });
}
*/

// ===================================================================
// SECTION 2: THE MAIN APP COMPONENT DEFINITION
// ===================================================================
const App: React.FC = () => {
  const [servicesReady, setServicesReady] = useState(false);

  useEffect(() => {
    // Service worker is currently disabled (no sw.js file)
    // Set servicesReady immediately since we're not waiting for a worker
    setServicesReady(true);
    console.log('[App.tsx] App initialized (service worker disabled).');
  }, []);

  return (
    <div className="relative min-h-screen w-full bg-[#0A0A0A] font-sans text-sm antialiased overflow-hidden">
      {/* Matrix Background - deepest layer */}
      <div className="fixed inset-0" style={{ zIndex: -100 }}>
        <MatrixBackground color="#8B5CF6" />
      </div>

      {/* Dark overlay to control matrix visibility */}
      <div className="fixed inset-0 bg-black/70" style={{ zIndex: -90 }} />

      {/* Animated Grid Background */}
      <div className="fixed inset-0" style={{ zIndex: -80 }}>
        <div className="absolute inset-0 bg-[radial-gradient(#1a1a2e_1px,transparent_1px)] [background-size:32px_32px] opacity-30" />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[#0A0A0A]" />
      </div>

      {/* Animated Gradient Orbs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none" style={{ zIndex: -70 }}>
        {/* Purple orb - top left */}
        <div
          className="absolute -top-[400px] -left-[200px] w-[800px] h-[800px] rounded-full bg-purple-600/30 blur-[150px] animate-pulse"
          style={{ animationDuration: '8s' }}
        />
        {/* Cyan orb - top right */}
        <div
          className="absolute -top-[200px] -right-[300px] w-[600px] h-[600px] rounded-full bg-cyan-500/20 blur-[120px] animate-pulse"
          style={{ animationDuration: '10s', animationDelay: '2s' }}
        />
        {/* Indigo orb - bottom center */}
        <div
          className="absolute -bottom-[300px] left-1/2 -translate-x-1/2 w-[1000px] h-[500px] rounded-full bg-indigo-600/20 blur-[150px] animate-pulse"
          style={{ animationDuration: '12s', animationDelay: '4s' }}
        />
      </div>

      {/* Noise Texture Overlay */}
      <div
        className="fixed inset-0 opacity-[0.02] pointer-events-none"
        style={{
          zIndex: -60,
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
        }}
      />

      <HashRouter>
        <div className="relative flex flex-col min-h-screen">
          <ConditionalHeader />
          <main className="flex-1">
            {!servicesReady ? (
              <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
                <div className="flex flex-col items-center gap-4">
                  <div className="relative">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600 animate-pulse" />
                    <div className="absolute inset-0 w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600 blur-lg opacity-50 animate-pulse" />
                  </div>
                  <p className="text-sm text-zinc-500 animate-pulse">Initializing GenCode Studio...</p>
                </div>
              </div>
            ) : (
              <ErrorBoundary>
                <Routes>
                  <Route path="/" element={<HomePage />} />
                  <Route path="/workspace/:id" element={<WorkspacePage />} />
                </Routes>
              </ErrorBoundary>
            )}
          </main>
        </div>
      </HashRouter>
    </div>
  );
};

// ===================================================================
// SECTION 3: EXPORT COMPONENT (Mounted by index.tsx)
// ===================================================================
// NOTE: The actual React root is created in index.tsx
// This file only exports the App component - no duplicate createRoot!
export default App;
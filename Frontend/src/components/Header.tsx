import React, { useState } from 'react';
import { NavLink, useLocation, useParams } from 'react-router-dom';
import { SparklesIcon, SettingsIcon, BellIcon } from './Icons';
import CostDashboard from './CostDashboard';

const Header: React.FC = () => {
  const location = useLocation();
  const params = useParams<{ projectId?: string }>();
  const isWorkspace = location.pathname.includes('/workspace');

  // Cost Dashboard state
  const [showCostDashboard, setShowCostDashboard] = useState(false);

  // Extract project ID from URL or path
  const projectId = params.projectId || (isWorkspace ? location.pathname.split('/').pop() : null);

  return (
    <>
      <header className="absolute top-0 left-0 right-0 z-50 w-full" role="banner">
        <div className="mx-auto flex h-16 max-w-screen-2xl items-center justify-between px-4 sm:px-6 lg:px-8">
          {/* Left: Logo */}
          <div className="flex items-center gap-8">
            {/* Logo */}
            <NavLink
              to="/"
              className="group flex items-center gap-3 focus:outline-none focus:ring-2 focus:ring-purple-500/40 rounded-lg"
              aria-label="GenCode Studio Home"
            >
              <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-purple-500 via-violet-500 to-indigo-600 shadow-lg shadow-purple-500/25 transition-all duration-300 group-hover:shadow-purple-500/40 group-hover:scale-105 group-focus:scale-105">
                <SparklesIcon className="h-5 w-5 text-white" aria-hidden="true" />
                <div className="absolute inset-0 rounded-xl bg-white/20 opacity-0 transition-opacity group-hover:opacity-100" />
              </div>
              <div className="flex flex-col">
                <span className="text-lg font-bold bg-gradient-to-r from-white via-purple-200 to-violet-200 bg-clip-text text-transparent">
                  GenCode
                </span>
                <span className="text-[10px] font-medium tracking-wider text-zinc-500 uppercase -mt-0.5">
                  Studio
                </span>
              </div>
            </NavLink>

            {/* Breadcrumb for workspace */}
            {isWorkspace && (
              <nav aria-label="Breadcrumb">
                <ol className="hidden md:flex items-center gap-2 text-sm text-zinc-500">
                  <li>
                    <span className="text-zinc-700" aria-hidden="true">/</span>
                  </li>
                  <li>
                    <span className="text-zinc-300 font-medium">Workspace</span>
                  </li>
                </ol>
              </nav>
            )}
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-2">
            {/* Notification Bell */}
            <button
              className="relative p-2.5 rounded-lg text-zinc-500 hover:text-white hover:bg-white/5 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-purple-500/40"
              aria-label="Notifications"
            >
              <BellIcon className="h-5 w-5" aria-hidden="true" />
              <span
                className="absolute top-2 right-2 h-1.5 w-1.5 rounded-full bg-purple-500 animate-pulse"
                aria-label="New notifications"
              />
            </button>

            {/* Settings - Opens Cost Dashboard */}
            <button
              onClick={() => setShowCostDashboard(true)}
              className="p-2.5 rounded-lg text-zinc-500 hover:text-white hover:bg-white/5 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-purple-500/40"
              aria-label="Settings - Cost Dashboard"
            >
              <SettingsIcon className="h-5 w-5" aria-hidden="true" />
            </button>

            {/* User Avatar */}
            <div className="relative group ml-2">
              <button
                className="h-9 w-9 rounded-full ring-2 ring-white/10 ring-offset-2 ring-offset-transparent overflow-hidden transition-all duration-300 group-hover:ring-purple-500/50 focus:outline-none focus:ring-2 focus:ring-purple-500"
                aria-label="User profile"
              >
                <img
                  src="https://api.dicebear.com/7.x/avataaars/svg?seed=gencode"
                  alt="User Avatar"
                  className="h-full w-full object-cover bg-zinc-800"
                />
              </button>
              <span
                className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full bg-emerald-500 ring-2 ring-black/50"
                aria-label="Online"
              />
            </div>
          </div>
        </div>
      </header>

      {/* Cost Dashboard Modal */}
      <CostDashboard
        isOpen={showCostDashboard}
        onClose={() => setShowCostDashboard(false)}
        projectId={projectId || null}
      />
    </>
  );
};

export default Header;

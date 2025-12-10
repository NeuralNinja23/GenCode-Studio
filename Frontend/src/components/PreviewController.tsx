// frontend/src/components/PreviewController.tsx
import React, { useEffect, useRef, useState } from "react";

interface PreviewControllerProps {
  previewUrl: string | null;
  projectId: string;
  onPreviewUrlChange: (url: string | null) => void;
}

// Device presets for responsive testing
const devicePresets = [
  { name: 'Desktop', width: '100%', height: '100%', icon: '🖥️' },
  { name: 'Tablet', width: '768px', height: '100%', icon: '📱' },
  { name: 'Mobile', width: '375px', height: '100%', icon: '📱' },
];

const PreviewController: React.FC<PreviewControllerProps> = ({
  previewUrl,
  projectId,
  onPreviewUrlChange,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDevice, setSelectedDevice] = useState(0);
  const [iframeKey, setIframeKey] = useState(0);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // guard for React Strict Mode double-mount
  const hasRequestedRef = useRef(false);

  const backendBase = (): string => {
    const anyImportMeta = import.meta as any;
    const env =
      anyImportMeta?.env?.VITE_BACKEND_URL ||
      anyImportMeta?.env?.REACT_APP_BACKEND_URL;

    return env || `${window.location.protocol}//${window.location.host}`;
  };

  const fetchPreviewUrl = async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(
        `${backendBase()}/api/sandbox/${projectId}/preview`
      );
      if (!res.ok) {
        const text = await res.text();
        throw new Error(
          `Backend returned ${res.status}: ${text || "Failed to get preview"}`
        );
      }

      const data = await res.json();

      // support both preview_url and previewUrl
      const url = data.preview_url || data.previewUrl || data.url;
      if (!url) {
        throw new Error("Preview URL missing in response");
      }

      onPreviewUrlChange(url);
    } catch (err: any) {
      console.error("[PREVIEW] Error fetching preview URL:", err);
      setError(err.message || "Unknown error while fetching preview URL");
      onPreviewUrlChange(null);
    } finally {
      setLoading(false);
    }
  };

  // ✅ Auto-fetch preview URL the first time this component is shown,
  //    if we don't already have one.
  useEffect(() => {
    if (!projectId) return;
    if (previewUrl) return;
    if (hasRequestedRef.current) return;

    hasRequestedRef.current = true;
    fetchPreviewUrl();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, previewUrl]);

  const handleOpenExternal = () => {
    if (previewUrl) {
      window.open(previewUrl, "_blank", "noopener,noreferrer");
    }
  };

  const handleReload = () => {
    if (previewUrl) {
      setIframeKey(prev => prev + 1);
    } else {
      hasRequestedRef.current = true;
      fetchPreviewUrl();
    }
  };

  const currentDevice = devicePresets[selectedDevice];

  return (
    <div className="flex flex-col h-full bg-zinc-950">
      {/* Top Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-zinc-900/80 border-b border-zinc-800/80">
        {/* Left side - Title & URL */}
        <div className="flex items-center gap-3">
          {/* Live indicator */}
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500"></span>
            </span>
            <span className="text-sm font-medium text-zinc-200">Live Preview</span>
          </div>

          {/* URL Bar */}
          {previewUrl && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800/60 rounded-lg border border-zinc-700/50">
              <svg className="w-3.5 h-3.5 text-green-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <span className="text-xs text-zinc-400 font-mono max-w-[200px] truncate">
                {previewUrl}
              </span>
              <button
                onClick={() => navigator.clipboard.writeText(previewUrl)}
                className="p-1 hover:bg-zinc-700 rounded transition-colors"
                title="Copy URL"
              >
                <svg className="w-3.5 h-3.5 text-zinc-500 hover:text-zinc-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
              </button>
            </div>
          )}
        </div>

        {/* Center - Device Toggles */}
        <div className="flex items-center gap-1 p-1 bg-zinc-800/60 rounded-lg border border-zinc-700/50">
          {devicePresets.map((device, index) => (
            <button
              key={device.name}
              onClick={() => setSelectedDevice(index)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200 ${selectedDevice === index
                  ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/20'
                  : 'text-zinc-400 hover:text-white hover:bg-zinc-700/50'
                }`}
              title={device.name}
            >
              <span className="mr-1.5">{device.icon}</span>
              {device.name}
            </button>
          ))}
        </div>

        {/* Right side - Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleReload}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                       bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white
                       border border-zinc-700/50 transition-all duration-200"
            title="Refresh preview"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
              <path d="M21 3v5h-5" />
              <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
              <path d="M3 21v-5h5" />
            </svg>
            <span>Refresh</span>
          </button>

          {previewUrl && (
            <button
              onClick={handleOpenExternal}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                         bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-500 hover:to-purple-400
                         text-white shadow-lg shadow-purple-500/20 transition-all duration-200"
              title="Open in new tab"
            >
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                <polyline points="15 3 21 3 21 9" />
                <line x1="10" y1="14" x2="21" y2="3" />
              </svg>
              <span>New Tab</span>
            </button>
          )}
        </div>
      </div>

      {/* Preview Content Area */}
      <div className="flex-1 flex items-center justify-center p-4 bg-gradient-to-br from-zinc-900 via-zinc-950 to-zinc-900 overflow-hidden">
        {/* Loading State */}
        {loading && (
          <div className="flex flex-col items-center gap-4">
            {/* Animated loader */}
            <div className="relative">
              <div className="w-16 h-16 rounded-full border-4 border-zinc-800"></div>
              <div className="absolute top-0 left-0 w-16 h-16 rounded-full border-4 border-transparent border-t-purple-500 animate-spin"></div>
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-zinc-300">Starting preview...</p>
              <p className="text-xs text-zinc-500 mt-1">Launching Docker sandbox</p>
            </div>
          </div>
        )}

        {/* Error State */}
        {!loading && error && (
          <div className="flex flex-col items-center gap-4 max-w-md text-center">
            <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20">
              <svg className="w-12 h-12 text-red-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <circle cx="12" cy="12" r="10" />
                <path d="m15 9-6 6M9 9l6 6" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-medium text-red-400">Preview Failed</h3>
              <p className="text-sm text-zinc-500 mt-2">{error}</p>
            </div>
            <button
              onClick={fetchPreviewUrl}
              className="px-4 py-2 rounded-lg text-sm font-medium
                         bg-zinc-800 hover:bg-zinc-700 text-zinc-300
                         border border-zinc-700 transition-all duration-200"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Empty State - No Preview URL */}
        {!loading && !error && !previewUrl && (
          <div className="flex flex-col items-center gap-6 max-w-md text-center">
            {/* Decorative illustration */}
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-purple-600/20 to-blue-600/20 blur-3xl rounded-full scale-150" />
              <div className="relative p-6 rounded-2xl bg-zinc-900/80 border border-zinc-800/80 shadow-2xl">
                <svg className="w-20 h-20 text-zinc-700" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <path d="M3 9h18" />
                  <path d="M9 21V9" />
                  <circle cx="6" cy="6" r="1" fill="currentColor" />
                  <circle cx="9" cy="6" r="1" fill="currentColor" />
                </svg>
              </div>
            </div>

            <div>
              <h3 className="text-xl font-semibold text-zinc-200">Launch Live Preview</h3>
              <p className="text-sm text-zinc-500 mt-2 max-w-xs">
                Start a Docker sandbox to preview your generated application with both frontend and backend running live.
              </p>
            </div>

            {/* Feature highlights */}
            <div className="flex gap-4 text-xs text-zinc-500">
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                Live reload
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                Full stack
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-purple-500"></span>
                Isolated
              </div>
            </div>

            <button
              onClick={fetchPreviewUrl}
              className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-medium
                         bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-500 hover:to-purple-400
                         text-white shadow-xl shadow-purple-500/25 transition-all duration-200 transform hover:scale-105"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="5 3 19 12 5 21 5 3" fill="currentColor" strokeLinejoin="round" />
              </svg>
              <span>Launch Preview</span>
            </button>
          </div>
        )}

        {/* Preview Iframe */}
        {!loading && !error && previewUrl && (
          <div
            className="relative bg-white rounded-lg shadow-2xl overflow-hidden transition-all duration-300"
            style={{
              width: currentDevice.width,
              height: currentDevice.height,
              maxWidth: '100%',
              maxHeight: '100%',
            }}
          >
            {/* Browser Chrome (optional styling) */}
            {selectedDevice !== 0 && (
              <div className="flex items-center gap-2 px-3 py-2 bg-zinc-200 border-b border-zinc-300">
                <div className="flex gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-red-400"></span>
                  <span className="w-3 h-3 rounded-full bg-yellow-400"></span>
                  <span className="w-3 h-3 rounded-full bg-green-400"></span>
                </div>
                <div className="flex-1 mx-8">
                  <div className="bg-white rounded-md px-3 py-1 text-xs text-zinc-500 text-center truncate">
                    {previewUrl}
                  </div>
                </div>
              </div>
            )}

            <iframe
              key={iframeKey}
              ref={iframeRef}
              src={previewUrl}
              title="Sandbox Preview"
              className="w-full border-0"
              style={{ height: selectedDevice !== 0 ? 'calc(100% - 36px)' : '100%' }}
              sandbox="allow-scripts allow-forms allow-same-origin allow-popups"
            />
          </div>
        )}
      </div>

      {/* Bottom Status Bar */}
      <div className="flex items-center justify-between px-4 py-1.5 bg-zinc-900/80 border-t border-zinc-800/80 text-xs text-zinc-500">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${previewUrl ? 'bg-green-500' : 'bg-zinc-600'}`}></span>
            {previewUrl ? 'Connected' : 'Disconnected'}
          </span>
          <span>Project: {projectId}</span>
        </div>
        <div className="flex items-center gap-4">
          <span>Viewport: {currentDevice.name}</span>
          {previewUrl && <span>Docker Sandbox</span>}
        </div>
      </div>
    </div>
  );
};

export default PreviewController;

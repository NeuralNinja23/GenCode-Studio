// frontend/src/components/PreviewView.tsx
import React, { useRef } from 'react';
import { Spinner } from './Spinner'; // Assuming you have a Spinner component

export type BundlerStatus = 'disconnected' | 'connecting' | 'connected' | 'bundling' | 'error';

interface PreviewViewProps {
  htmlContent: string; // Fallback HTML content
  status: BundlerStatus;
  error: string;
  previewUrl: string | null; // 👈 ADDED this prop
}

const PreviewView: React.FC<PreviewViewProps> = ({
  htmlContent,
  status,
  error,
  previewUrl, // 👈 GET this prop
}) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Display a loading spinner while connecting or bundling
  // 👇 UPDATED: Show loading while connecting OR bundling OR connected but waiting for URL
  if (status === 'connecting' || status === 'bundling' || (status === 'connected' && !previewUrl && !error)) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-zinc-950/80">
        <Spinner />
        <p className="ml-2 text-zinc-400">
          {status === 'connecting' ? 'Connecting to server...' : 'Initializing preview...'}
        </p>
      </div>
    );
  }

  // Display a clear, formatted error message if bundling fails
  if (status === 'error' && error) {
    return (
      <div className="h-full w-full bg-red-900/20 p-4 text-red-300">
          <h3 className="mb-2 text-lg font-semibold text-red-200">Preview Error</h3>
          <pre className="whitespace-pre-wrap rounded-md bg-zinc-900 p-4 font-mono text-sm">
              {error}
          </pre>
      </div>
    );
  }

  // Render the iframe pointing to the Vite server URL
  return (
    <iframe
      ref={iframeRef}
      title="Preview"
      className="h-full w-full rounded-md border border-zinc-700 bg-white"
      sandbox="allow-scripts allow-same-origin allow-forms" // Added allow-forms
      // 👇 UPDATED: Use previewUrl as the source
      src={previewUrl || 'about:blank'}
      // Fallback to srcDoc if previewUrl is null but legacy htmlContent exists
      srcDoc={!previewUrl ? htmlContent : undefined}
    />
  );
};

export default PreviewView;
import React, { useEffect, useState, useRef, useCallback } from 'react';
import { ChevronDown, Check, Loader2, AlertCircle } from 'lucide-react';

interface ProviderModel {
  id: string;
  name: string;
  models: string[];
  requiresApiKey: boolean;
  costPer1kTokens: number;
}

interface CurrentProviderResponse {
  provider: string;
  configured: boolean;
  model?: string;
}

const BACKEND_URL =
  (import.meta as any).env?.VITE_BACKEND_URL ||
  (import.meta as any).env?.REACT_APP_BACKEND_URL ||
  '';

const Providers: React.FC = () => {
  const [providers, setProviders] = useState<ProviderModel[]>([]);
  const [current, setCurrent] = useState<CurrentProviderResponse | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Fetch providers and current selection
  useEffect(() => {
    const fetchProviders = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/providers/available`);
        if (!res.ok) throw new Error('Failed to fetch providers');
        const data = await res.json();
        setProviders(data.providers || []);
      } catch (e) {
        console.error('Error loading providers', e);
        setError('Failed to load providers');
      }
    };

    const fetchCurrent = async () => {
      try {
        const res = await fetch(`${BACKEND_URL.replace(/\/$/, '')}/api/providers/current`);
        const data = await res.json();
        setCurrent(data);
        setSelectedProvider(data.provider);
        if (data.model) setSelectedModel(data.model);
      } catch (e) {
        console.error('Error loading current provider', e);
      }
    };

    fetchProviders();
    fetchCurrent();
  }, []);

  const handleSelect = useCallback(async (provider: string, model: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${BACKEND_URL.replace(/\/$/, '')}/api/providers/set`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, model }),
      });

      if (!response.ok) {
        throw new Error('Failed to set provider');
      }

      setSelectedProvider(provider);
      setSelectedModel(model);
      setCurrent({ provider, configured: true, model });
      setIsOpen(false);
    } catch (e) {
      console.error('Error saving provider', e);
      setError('Failed to save provider');
    } finally {
      setLoading(false);
    }
  }, []);

  const currentProvider = providers.find((p) => p.id === selectedProvider);
  const currentLabel = currentProvider?.name || "Select Model";

  return (
    <div ref={dropdownRef} className="relative inline-block text-left">
      {/* Dropdown Trigger */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setIsOpen(!isOpen);
          }
        }}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label="Select LLM Provider"
        disabled={loading}
        className="flex cursor-pointer items-center justify-between gap-2 rounded-lg border border-zinc-700/70 bg-zinc-900/70 px-3 py-1.5 text-sm font-medium text-zinc-200 shadow-sm backdrop-blur-md transition-all hover:bg-zinc-800/80 focus:outline-none focus:ring-2 focus:ring-purple-500/40 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-label="Loading" />
        ) : error ? (
          <AlertCircle className="h-4 w-4 text-red-400" aria-label="Error" />
        ) : (
          <span className="truncate">{currentLabel}</span>
        )}
        <ChevronDown
          className={`h-4 w-4 opacity-70 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
          aria-hidden="true"
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          role="listbox"
          aria-label="Available LLM Providers"
          className="absolute right-0 z-[99999] mt-2 w-64 rounded-xl border border-zinc-800 bg-zinc-900/95 shadow-2xl backdrop-blur-xl ring-1 ring-black/10 overflow-y-auto max-h-[300px] animate-in fade-in slide-in-from-top-2 duration-200"
        >
          {providers.length === 0 ? (
            <div className="px-4 py-3 text-sm text-zinc-400 text-center">
              No providers available
            </div>
          ) : (
            providers.map((prov, idx) => (
              <button
                key={prov.id}
                type="button"
                role="option"
                aria-selected={selectedProvider === prov.id}
                onClick={() => handleSelect(prov.id, prov.models[0])}
                className={`flex w-full items-center justify-between rounded-md px-4 py-3 text-sm transition-all ${selectedProvider === prov.id
                    ? 'bg-purple-500/10 text-purple-400 font-semibold'
                    : 'text-zinc-300 hover:bg-zinc-800/60 hover:text-zinc-100'
                  } ${idx !== providers.length - 1 ? 'border-b border-zinc-800/70' : ''}`}
              >
                <div className="flex flex-col items-start gap-0.5">
                  <span className="font-medium">{prov.name}</span>
                  {prov.costPer1kTokens > 0 && (
                    <span className="text-xs text-zinc-500">
                      ${prov.costPer1kTokens}/1k tokens
                    </span>
                  )}
                </div>
                {selectedProvider === prov.id && (
                  <Check className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
                )}
              </button>
            ))
          )}
        </div>
      )}

      {/* Error message */}
      {error && !isOpen && (
        <div className="absolute top-full mt-1 text-xs text-red-400" role="alert">
          {error}
        </div>
      )}
    </div>
  );
};

export default Providers;

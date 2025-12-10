import React, { useState, useEffect } from 'react';
import { X, TrendingDown, DollarSign, Zap, BarChart3, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react';

interface TokenUsage {
    input: number;
    output: number;
    calls: number;
    retries: number;
}

interface StepData {
    input: number;
    output: number;
    calls: number;
    retries: number;
    cost_usd?: number;
    cost_inr?: number;
    agents: Record<string, TokenUsage & { cost_usd?: number }>;
}

interface DetailedCall {
    timestamp: string;
    agent: string;
    step: string;
    input_tokens: number;
    output_tokens: number;
    is_retry: boolean;
}

interface CostData {
    total_input_tokens: number;
    total_output_tokens: number;
    total_tokens: number;
    total_estimated_cost: number;
    total_cost_inr?: number;
    max_budget_inr?: number;
    remaining_inr?: number;
    budget_status?: string;
    by_agent: Record<string, TokenUsage>;
    by_provider_cost: Record<string, number>;
    by_step: Record<string, StepData>;
    detailed_calls: DetailedCall[];
}

interface CostDashboardProps {
    isOpen: boolean;
    onClose: () => void;
    projectId: string | null;
}

const CostDashboard: React.FC<CostDashboardProps> = ({ isOpen, onClose, projectId: propProjectId }) => {
    const [costData, setCostData] = useState<CostData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

    // Project selection state - for when no projectId is passed (homepage)
    const [availableProjects, setAvailableProjects] = useState<string[]>([]);
    const [selectedProject, setSelectedProject] = useState<string | null>(propProjectId);
    const [loadingProjects, setLoadingProjects] = useState(false);

    // Use prop projectId if available, otherwise use selected project
    const activeProjectId = propProjectId || selectedProject;

    // Fetch available projects when opened without a projectId
    useEffect(() => {
        if (isOpen && !propProjectId) {
            fetchAvailableProjects();
        }
    }, [isOpen, propProjectId]);

    // Fetch cost data when project is selected
    useEffect(() => {
        if (isOpen && activeProjectId) {
            fetchCostData();
        }
    }, [isOpen, activeProjectId]);

    const fetchAvailableProjects = async () => {
        setLoadingProjects(true);
        try {
            const response = await fetch('http://localhost:8000/api/tracking/projects');
            if (!response.ok) throw new Error('Failed to fetch projects');
            const data = await response.json();
            setAvailableProjects(data.projects || []);
            // Auto-select first project if available and none selected
            if (data.projects?.length > 0 && !selectedProject) {
                setSelectedProject(data.projects[0]);
            }
        } catch (err) {
            console.error('Failed to fetch projects:', err);
        } finally {
            setLoadingProjects(false);
        }
    };

    const fetchCostData = async () => {
        if (!activeProjectId) return;

        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`http://localhost:8000/api/tracking/${activeProjectId}/costs`);
            if (!response.ok) throw new Error('Failed to fetch cost data');

            const data = await response.json();
            setCostData(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setLoading(false);
        }
    };

    const toggleStep = (stepName: string) => {
        const newExpanded = new Set(expandedSteps);
        if (newExpanded.has(stepName)) {
            newExpanded.delete(stepName);
        } else {
            newExpanded.add(stepName);
        }
        setExpandedSteps(newExpanded);
    };

    if (!isOpen) return null;

    const formatCost = (cost: number) => {
        const inr = cost * 83; // USD to INR
        return `₹${inr.toFixed(2)}`;
    };

    const formatTokens = (tokens: number) => {
        if (tokens >= 1000000) return `${(tokens / 1000000).toFixed(2)}M`;
        if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}K`;
        return tokens.toString();
    };

    const getAgentColor = (agent: string) => {
        const colors: Record<string, string> = {
            'Derek': 'from-blue-500 to-cyan-500',
            'Marcus': 'from-purple-500 to-violet-500',
            'Luna': 'from-pink-500 to-rose-500',
            'Victoria': 'from-emerald-500 to-green-500',
        };
        return colors[agent] || 'from-gray-500 to-gray-600';
    };

    const getAgentBadgeColor = (agent: string) => {
        const colors: Record<string, string> = {
            'Derek': 'bg-blue-500/20 text-blue-400',
            'Marcus': 'bg-purple-500/20 text-purple-400',
            'Luna': 'bg-pink-500/20 text-pink-400',
            'Victoria': 'bg-emerald-500/20 text-emerald-400',
        };
        return colors[agent] || 'bg-gray-500/20 text-gray-400';
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <div className="relative w-full max-w-5xl bg-zinc-900 rounded-2xl shadow-2xl border border-white/10 overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-white/10 bg-gradient-to-br from-purple-500/10 to-violet-500/10">
                    <div className="flex items-center gap-3">
                        <div className="p-2.5 rounded-lg bg-purple-500/20">
                            <BarChart3 className="h-6 w-6 text-purple-400" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white">Cost Optimization Dashboard</h2>
                            <p className="text-sm text-zinc-400">Step-by-step • Agent-by-agent • Retry tracking</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
                        aria-label="Close"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 max-h-[75vh] overflow-y-auto">
                    {loading && (
                        <div className="flex items-center justify-center py-12">
                            <RefreshCw className="h-8 w-8 text-purple-500 animate-spin" />
                        </div>
                    )}

                    {error && (
                        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
                            {error}
                        </div>
                    )}

                    {/* Project Selector - shown when no projectId passed (homepage) */}
                    {!propProjectId && availableProjects.length > 0 && (
                        <div className="mb-4 p-4 rounded-lg bg-zinc-800/50 border border-white/10">
                            <label className="block text-sm text-zinc-400 mb-2">Select Project</label>
                            <select
                                value={selectedProject || ''}
                                onChange={(e) => setSelectedProject(e.target.value)}
                                className="w-full px-4 py-2 rounded-lg bg-zinc-900 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-purple-500/40"
                            >
                                {availableProjects.map((proj) => (
                                    <option key={proj} value={proj}>
                                        {proj.slice(0, 20)}...
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}

                    {!loading && !error && !activeProjectId && (
                        <div className="text-center py-12 text-zinc-500">
                            {loadingProjects ? (
                                <div className="flex items-center justify-center gap-2">
                                    <RefreshCw className="h-5 w-5 animate-spin" />
                                    Loading projects...
                                </div>
                            ) : availableProjects.length === 0 ? (
                                <div>
                                    <p className="mb-2">No tracked projects found.</p>
                                    <p className="text-sm">Generate a project to see cost data here.</p>
                                </div>
                            ) : (
                                'Select a project to view costs'
                            )}
                        </div>
                    )}

                    {!loading && !error && costData && (
                        <div className="space-y-6">
                            {/* Summary Cards */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="p-4 rounded-xl bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border border-blue-500/20">
                                    <div className="flex items-center gap-2 text-blue-400 text-sm font-medium mb-2">
                                        <Zap className="h-4 w-4" />
                                        Total Tokens
                                    </div>
                                    <div className="text-3xl font-bold text-white">
                                        {formatTokens(costData.total_tokens)}
                                    </div>
                                    <div className="text-xs text-zinc-400 mt-1">
                                        <span className="text-cyan-400">{formatTokens(costData.total_input_tokens)} in</span>
                                        {' • '}
                                        <span className="text-purple-400">{formatTokens(costData.total_output_tokens)} out</span>
                                    </div>
                                </div>

                                <div className="p-4 rounded-xl bg-gradient-to-br from-purple-500/10 to-violet-500/10 border border-purple-500/20">
                                    <div className="flex items-center gap-2 text-purple-400 text-sm font-medium mb-2">
                                        <DollarSign className="h-4 w-4" />
                                        Total Cost
                                    </div>
                                    <div className="text-3xl font-bold text-white">
                                        ₹{(costData.total_cost_inr ?? costData.total_estimated_cost * 90).toFixed(2)}
                                    </div>
                                    <div className="text-xs text-zinc-400 mt-1">
                                        ${costData.total_estimated_cost.toFixed(4)} USD
                                    </div>
                                </div>

                                <div className="p-4 rounded-xl bg-gradient-to-br from-emerald-500/10 to-green-500/10 border border-emerald-500/20">
                                    <div className="flex items-center gap-2 text-emerald-400 text-sm font-medium mb-2">
                                        <TrendingDown className="h-4 w-4" />
                                        Budget Status
                                    </div>
                                    <div className="text-2xl font-bold text-white">
                                        {costData.budget_status ?? '🟢 HEALTHY'}
                                    </div>
                                    <div className="text-xs text-zinc-400 mt-1">
                                        ₹{(costData.remaining_inr ?? 30).toFixed(2)} / ₹{(costData.max_budget_inr ?? 30).toFixed(2)} remaining
                                    </div>
                                </div>
                            </div>

                            {/* Step Breakdown (if available) */}
                            {costData.by_step && Object.keys(costData.by_step).length > 0 && (
                                <div>
                                    <h3 className="text-lg font-semibold text-white mb-4">Tokens per Workflow Step</h3>
                                    <div className="space-y-2">
                                        {Object.entries(costData.by_step).map(([stepName, stepData]) => {
                                            const stepTokens = stepData.input + stepData.output;
                                            const isExpanded = expandedSteps.has(stepName);
                                            // Use backend-provided cost_inr, fallback to calculation
                                            const stepCostInr = stepData.cost_inr ?? (stepData.cost_usd ? stepData.cost_usd * 90 : 0);

                                            return (
                                                <div key={stepName} className="rounded-lg bg-white/5 border border-white/10 overflow-hidden">
                                                    {/* Step Header */}
                                                    <button
                                                        onClick={() => toggleStep(stepName)}
                                                        className="w-full p-4 flex items-center justify-between hover:bg-white/5 transition-colors"
                                                    >
                                                        <div className="flex items-center gap-3">
                                                            {isExpanded ? (
                                                                <ChevronDown className="h-4 w-4 text-zinc-400" />
                                                            ) : (
                                                                <ChevronRight className="h-4 w-4 text-zinc-400" />
                                                            )}
                                                            <div className="text-left">
                                                                <div className="font-medium text-white">{stepName.replace(/_/g, ' ').toUpperCase()}</div>
                                                                <div className="text-xs text-zinc-500">
                                                                    {stepData.calls} call{stepData.calls > 1 ? 's' : ''}
                                                                    {stepData.retries > 0 && ` (${stepData.retries} ${stepData.retries > 1 ? 'retries' : 'retry'})`}
                                                                    {' • '}
                                                                    <span className="text-cyan-400">{formatTokens(stepData.input)} in</span>
                                                                    {' • '}
                                                                    <span className="text-purple-400">{formatTokens(stepData.output)} out</span>
                                                                </div>
                                                            </div>
                                                        </div>
                                                        <div className="text-right">
                                                            <div className="text-white font-semibold">{formatTokens(stepTokens)}</div>
                                                            <div className="text-xs text-emerald-400">₹{stepCostInr.toFixed(2)}</div>
                                                        </div>
                                                    </button>

                                                    {/* Agents within Step */}
                                                    {isExpanded && (
                                                        <div className="px-4 pb-4 space-y-2 bg-black/20">
                                                            {Object.entries(stepData.agents).map(([agentName, agentData]) => {
                                                                const agentTokens = agentData.input + agentData.output;
                                                                const agentCost = (agentData.input / 1000 * 0.00015) + (agentData.output / 1000 * 0.00060);

                                                                return (
                                                                    <div key={agentName} className="p-3 rounded-lg bg-white/5 border border-white/5">
                                                                        <div className="flex items-center justify-between mb-2">
                                                                            <div className="flex items-center gap-2">
                                                                                <span className={`px-2 py-1 rounded text-xs font-medium ${getAgentBadgeColor(agentName)}`}>
                                                                                    {agentName}
                                                                                </span>
                                                                                <span className="text-xs text-zinc-500">
                                                                                    {agentData.calls} call{agentData.calls > 1 ? 's' : ''}
                                                                                    {agentData.retries > 0 && (
                                                                                        <span className="ml-1 text-orange-400">
                                                                                            ({agentData.retries} retry)
                                                                                        </span>
                                                                                    )}
                                                                                </span>
                                                                            </div>
                                                                            <div className="text-right">
                                                                                <div className="text-sm text-white font-medium">{formatTokens(agentTokens)}</div>
                                                                                <div className="text-xs text-zinc-500">{formatCost(agentCost)}</div>
                                                                            </div>
                                                                        </div>
                                                                        <div className="flex items-center gap-4 text-xs text-zinc-500">
                                                                            <span>↓ {formatTokens(agentData.input)} in</span>
                                                                            <span>↑ {formatTokens(agentData.output)} out</span>
                                                                        </div>
                                                                    </div>
                                                                );
                                                            })}
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}

                            {/* Agent Summary */}
                            <div>
                                <h3 className="text-lg font-semibold text-white mb-4">Total by Agent</h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    {Object.entries(costData.by_agent).map(([agent, usage]) => {
                                        const totalAgentTokens = usage.input + usage.output;
                                        const agentCost = costData.by_provider_cost[agent] || 0;
                                        const percentage = (totalAgentTokens / costData.total_tokens) * 100;

                                        return (
                                            <div key={agent} className="p-4 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">
                                                <div className="flex items-center justify-between mb-2">
                                                    <div className="flex items-center gap-3">
                                                        <div className={`px-3 py-1 rounded-md text-sm font-medium ${getAgentBadgeColor(agent)}`}>
                                                            {agent}
                                                        </div>
                                                    </div>
                                                    <div className="text-right">
                                                        <div className="text-white font-semibold">{formatCost(agentCost)}</div>
                                                        <div className="text-xs text-zinc-500">{percentage.toFixed(1)}%</div>
                                                    </div>
                                                </div>

                                                <div className="relative h-2 bg-zinc-800 rounded-full overflow-hidden mb-2">
                                                    <div
                                                        className={`absolute left-0 top-0 h-full transition-all bg-gradient-to-r ${getAgentColor(agent)}`}
                                                        style={{ width: `${percentage}%` }}
                                                    />
                                                </div>

                                                <div className="flex items-center justify-between text-xs text-zinc-500">
                                                    <div className="flex gap-4">
                                                        <span>↓ {formatTokens(usage.input)} in</span>
                                                        <span>↑ {formatTokens(usage.output)} out</span>
                                                    </div>
                                                    <div>
                                                        {usage.calls} calls
                                                        {usage.retries > 0 && (
                                                            <span className="ml-1 text-orange-400">({usage.retries} retries)</span>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* Optimization Info */}
                            <div className="p-4 rounded-lg bg-gradient-to-br from-purple-500/10 to-violet-500/10 border border-purple-500/20">
                                <h4 className="text-sm font-semibold text-purple-400 mb-2">Active Optimizations</h4>
                                <ul className="space-y-1 text-sm text-zinc-400">
                                    <li>✓ Core prompt caching (30-40% savings)</li>
                                    <li>✓ Progressive context building (25-30% savings)</li>
                                    <li>✓ Differential retry (5-10% savings)</li>
                                    <li>✓ Token limits reduced (5-10% savings)</li>
                                </ul>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-white/10 bg-zinc-900/50 flex items-center justify-between">
                    <p className="text-xs text-zinc-500">
                        Prices in INR (1 USD = ₹83) • Gemini 2.5 Flash rates
                    </p>
                    <button
                        onClick={fetchCostData}
                        disabled={!activeProjectId || loading}
                        className="px-4 py-2 rounded-lg bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium flex items-center gap-2"
                    >
                        <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                        Refresh
                    </button>
                </div>
            </div>
        </div>
    );
};

export default CostDashboard;

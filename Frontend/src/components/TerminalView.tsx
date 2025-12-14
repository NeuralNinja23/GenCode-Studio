import React, { useEffect, useRef } from "react";
import { BrainCircuit } from "lucide-react";

interface LogEntry {
    scope: string;
    message: string;
    timestamp: string | number;
    data?: {
        agent?: string;
        status?: string;
    };
}

interface TerminalViewProps {
    logs: LogEntry[];
}

// Agent-specific colors
const getAgentColor = (agent: string): string => {
    if (agent === "Marcus") return "text-yellow-400";
    if (agent === "Derek") return "text-cyan-400";
    if (agent === "Victoria") return "text-pink-400";
    if (agent === "Luna") return "text-purple-400";
    return "text-green-400";
};

const getAgentBorder = (agent: string): string => {
    if (agent === "Marcus") return "border-yellow-500/50";
    if (agent === "Derek") return "border-cyan-500/50";
    if (agent === "Victoria") return "border-pink-500/50";
    if (agent === "Luna") return "border-purple-500/50";
    return "border-green-500/50";
};

const formatTimestamp = (ts: string | number): string => {
    try {
        if (typeof ts === "number") {
            return new Date(ts * 1000).toLocaleTimeString();
        }
        return new Date(ts).toLocaleTimeString();
    } catch {
        return "";
    }
};

// Internal Typewriter component
const Typewriter = ({ text }: { text: string }) => {
    const [displayed, setDisplayed] = React.useState("");

    useEffect(() => {
        let current = "";
        let i = 0;
        const timer = setInterval(() => {
            if (i < text.length) {
                // Add chunks of characters for faster effect on long text
                const chunk = text.slice(i, i + 3);
                current += chunk;
                setDisplayed(current);
                i += 3;
            } else {
                clearInterval(timer);
                setDisplayed(text);
            }
        }, 10); // 10ms speed

        return () => clearInterval(timer);
    }, [text]);

    return <span>{displayed}{displayed.length < text.length && <span className="animate-pulse">|</span>}</span>;
};

const TerminalView: React.FC<TerminalViewProps> = ({ logs }) => {
    const containerRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when new logs arrive
    useEffect(() => {
        if (containerRef.current) {
            containerRef.current.scrollTop = containerRef.current.scrollHeight;
        }
    }, [logs]);

    // FILTER: Show agent logs with either "AGENT:*" prefix or direct agent names
    const validScopes = ["MARCUS", "DEREK", "VICTORIA", "LUNA"];
    const agentLogs = logs.filter((log) => {
        const isAgentPrefix = log.scope.startsWith("AGENT:");
        const isDirectAgent = validScopes.includes(log.scope.toUpperCase());
        return (isAgentPrefix || isDirectAgent) &&
            !log.message.includes("Processing request") &&
            !log.message.includes("thinking...");
    });

    return (
        <div className="flex flex-col h-full bg-zinc-950 overflow-hidden">
            {/* Header */}
            <div className="flex items-center gap-2 px-4 py-3 bg-zinc-900 border-b border-zinc-800 shrink-0">
                <BrainCircuit className="w-4 h-4 text-purple-400" />
                <span className="text-zinc-300 font-medium">Agent Thinking</span>
                <span className="ml-auto text-xs text-zinc-600">
                    {agentLogs.length} thoughts
                </span>
            </div>

            {/* Scrollable content area */}
            <div
                ref={containerRef}
                className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0"
            >
                {agentLogs.length === 0 && (
                    <div className="text-center py-12">
                        <BrainCircuit className="w-12 h-12 text-zinc-800 mx-auto mb-4" />
                        <p className="text-zinc-500">Waiting for agent thoughts...</p>
                    </div>
                )}

                {agentLogs.map((log, i) => {
                    // Handle both "AGENT:Derek" and "MARCUS" formats
                    const agentName = log.scope.startsWith("AGENT:")
                        ? log.scope.replace("AGENT:", "")
                        : log.scope.charAt(0) + log.scope.slice(1).toLowerCase(); // "MARCUS" -> "Marcus"
                    // Only animate the very last log to prevent re-animating old ones
                    const isLatest = i === agentLogs.length - 1;

                    return (
                        <div
                            key={i}
                            className={`rounded-lg border-l-4 ${getAgentBorder(agentName)} bg-zinc-900/50 p-4`}
                        >
                            {/* Agent header */}
                            <div className="flex items-center gap-2 mb-2">
                                <span className={`font-bold ${getAgentColor(agentName)}`}>
                                    {agentName}
                                </span>
                                <span className="ml-auto text-zinc-600 text-xs">
                                    {formatTimestamp(log.timestamp)}
                                </span>
                            </div>

                            {/* Thinking content */}
                            <div className="text-zinc-300 text-sm leading-relaxed whitespace-pre-wrap font-sans">
                                {isLatest ? <Typewriter text={log.message} /> : log.message}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default TerminalView;

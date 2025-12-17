// frontend/src/pages/WorkspacePage.tsx
import React, { useState, useEffect, useRef } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import {
  SendIcon,
  BotIcon,
  CodeIcon,
  EyeIcon,
  UploadCloudIcon,
  LoaderCircleIcon,
  TerminalIcon,
  SparklesIcon,
  UserIcon,
  BarChart3Icon,
} from "../components/Icons";

import CodeView from "../components/CodeView";
import TerminalView from "../components/TerminalView";
import PreviewController from "../components/PreviewController";
import CostDashboard from "../components/CostDashboard";
import {
  resumeWorkflow,
  startWorkflow,
  getWorkspaceFiles,
  getFileContent,
  getProjectProgress,
} from "../services/agentService";
import { startDeployment } from "../services/deploymentService";
import { ChatMessage, MessageSender, FileTreeNode } from "../types";
import { getWebSocketUrl } from "../config/env";

// BackendFileTreeEntry removed - using FileTreeNode from types

// 🔒 Guard to prevent duplicate workflow starts per projectId
// Note: Cleaned up on component unmount and on error to prevent memory leaks
const startedWorkspaces = new Set<string>();

// Workflow stages with agent names - Matches backend TaskGraph (11 steps)
// Marcus supervises all agents (3 retries each)
const WORKFLOW_STAGES = [
  { step: 1, agent: "Marcus", stage: "Analysis", description: "Understanding requirements" },
  { step: 2, agent: "Victoria ↔ Marcus", stage: "Architecture", description: "Design + Supervision" },
  { step: 3, agent: "Derek ↔ Marcus", stage: "Frontend Mock", description: "Frontend with mock data" },
  { step: 4, agent: "Marcus", stage: "Screenshot Verify", description: "Visual QA of frontend" },
  { step: 5, agent: "Marcus", stage: "Contracts", description: "Defining API contracts" },
  { step: 6, agent: "Derek ↔ Marcus", stage: "Backend Implementation", description: "Models + Routers + Wiring" },
  { step: 7, agent: "System", stage: "System Integration", description: "Wiring everything together" },
  { step: 8, agent: "Derek", stage: "Testing Backend", description: "Running pytest tests" },
  { step: 9, agent: "Derek ↔ Marcus", stage: "Frontend Integration", description: "Replace mock with API" },
  { step: 10, agent: "Luna ↔ Marcus", stage: "Testing Frontend", description: "Playwright E2E tests" },
  { step: 11, agent: "Marcus", stage: "Preview", description: "Final preview ready!" },
];

const WorkspacePage: React.FC = () => {
  const { id: projectId } = useParams<{ id: string }>();
  const location = useLocation();
  const initialPrompt: string | null = (location.state as any)?.prompt || null;

  // ---- State ----
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [userInput, setUserInput] = useState("");
  const [fileTree, setFileTree] = useState<FileTreeNode[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [selectedFileContent, setSelectedFileContent] = useState("");
  const [rightPanelView, setRightPanelView] = useState<"code" | "preview" | "terminal" | null>(null);
  const [agentLogs, setAgentLogs] = useState<any[]>([]);
  const [generationStatus, setGenerationStatus] = useState("Initiating workflow.");
  // Start as NOT running if loading existing project (no initialPrompt)
  const [isWorkflowRunning, setIsWorkflowRunning] = useState(!!initialPrompt);
  const [workflowStage, setWorkflowStage] = useState(0);
  const [currentStepName, setCurrentStepName] = useState(""); // Track semantic step name
  const [workflowTotalStages, setWorkflowTotalStages] = useState(WORKFLOW_STAGES.length);
  const [isDeploying, setIsDeploying] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const [paused, setPaused] = useState(false);
  const [pauseMessage, setPauseMessage] = useState("");
  const [showCostDashboard, setShowCostDashboard] = useState(false);

  const ws = useRef<WebSocket | null>(null);
  const hasStartedGeneration = useRef(false);
  const [isWsOpen, setIsWsOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ---- Helpers ----
  // backendBase removed in favor of agentService

  // ---- File tree fetch ----
  const fetchFileTree = async () => {
    if (!projectId) return;
    try {
      const data = await import("../services/agentService").then(m => m.getWorkspaceFiles(projectId));
      // Type compatibility check: backend returns items with 'children', frontend interface expects them too.
      // The types are effectively compatible even if named differently in this file.
      setFileTree(data as FileTreeNode[]);
    } catch (err) {
      console.error("File tree error:", err);
      setMessages((prev) => [
        ...prev,
        {
          id: `fs-error-${Date.now()}`,
          sender: MessageSender.Agent,
          content: "Error loading file tree.",
        },
      ]);
    }
  };

  const fetchFileContent = async (filePath: string) => {
    if (!projectId) return;
    try {
      const content = await import("../services/agentService").then(m => m.getFileContent(projectId, filePath));
      setSelectedFile(filePath);
      setSelectedFileContent(content);
      setRightPanelView("code");
    } catch (err) {
      console.error("File content error:", err);
    }
  };

  // ---- Initialization on Mount ----
  useEffect(() => {
    if (!projectId) return;

    // 1. Fetch file tree immediately
    fetchFileTree();

    // 2. If no initial prompt (opening existing project), just load it for editing
    if (!initialPrompt) {
      // Show the code view immediately
      setRightPanelView("code");

      // Show welcome message - user can now chat to refine
      setMessages([{
        id: `loaded-${Date.now()}`,
        sender: MessageSender.Agent,
        content: "📁 Project loaded. Send a message to make changes or refinements.",
      }]);

      // Check if a workflow is currently running
      getProjectProgress(projectId)
        .then(progress => {
          if (progress?.is_running) {
            setIsWorkflowRunning(true);
            setMessages(prev => [...prev, {
              id: `running-${Date.now()}`,
              sender: MessageSender.Agent,
              content: "⚙️ A workflow is currently running...",
            }]);
          }
        })
        .catch(err => console.error("Failed to check progress:", err));
    }
  }, [projectId, initialPrompt]);

  // ============================================================
  // CLEANUP ON UNMOUNT
  // ============================================================
  useEffect(() => {
    return () => {
      // Clean up started workspaces set to prevent memory leak
      if (projectId && startedWorkspaces.has(projectId)) {
        console.log(`[CLEANUP] Removing ${projectId} from startedWorkspaces`);
        startedWorkspaces.delete(projectId);
      }
    };
  }, [projectId]);

  // ============================================================
  // WEBSOCKET SETUP
  // ============================================================
  useEffect(() => {
    if (!projectId) return;

    // Robust WebSocket URL construction using centralized config
    const wsUrl = getWebSocketUrl(projectId);
    console.log(`[WS] Connecting to: ${wsUrl}`);

    // Create socket
    const socket = new WebSocket(wsUrl);
    ws.current = socket;

    socket.onopen = () => {
      console.log("[WS] Connected successfully");
      setIsWsOpen(true);
    };

    socket.onclose = (event) => {
      console.log(`[WS] Closed: Code ${event.code}, Reason: ${event.reason || "No reason provided"}`);
      setIsWsOpen(false);

      if (isWorkflowRunning) {
        setMessages((prev) => [
          ...prev,
          {
            id: `ws-disconnect-${Date.now()}`,
            sender: MessageSender.Agent,
            content: "⚠️ Connection to server lost. Attempting to reconnect...",
          },
        ]);
      }
    };

    socket.onerror = (error) => {
      console.error("[WS] Error:", error);
      setMessages((prev) => [
        ...prev,
        {
          id: `ws-error-${Date.now()}`,
          sender: MessageSender.Agent,
          content: "❌ WebSocket connection error. Please refresh the page.",
        },
      ]);
    };

    socket.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        console.log("[WS] Message received:", data);

        switch (data.type) {
          case "WORKFLOW_UPDATE":
            setIsWorkflowRunning(true);
            setWorkflowStage(data.currentTurn ?? data.turn ?? 0);
            setCurrentStepName(data.step || "");
            setWorkflowTotalStages(data.maxTurns ?? data.totalTurns ?? 12);
            setGenerationStatus(data.status || "Processing");

            // Refetch file tree when backend sends updates implying files changed
            if ((data.status || "").toLowerCase().includes("frontend_mock complete") ||
              data.step === "frontend_mock" ||
              data.step === "frontend_integration") {
              fetchFileTree();
            }
            break;

          case "WORKFLOW_PAUSED":
            setPaused(true);
            setPauseMessage(data.message || "Workflow paused. Continue?");
            setMessages((prev) => [
              ...prev,
              {
                id: `pause-${Date.now()}`,
                sender: MessageSender.Agent,
                content: `⏸️ ${data.message || "Workflow paused"}`,
              },
            ]);
            break;

          case "WORKFLOW_RESUMED":
            setPaused(false);
            setPauseMessage("");
            setMessages((prev) => [
              ...prev,
              {
                id: `resume-${Date.now()}`,
                sender: MessageSender.Agent,
                content: "▶️ Workflow resumed",
              },
            ]);
            break;

          case "WORKFLOW_COMPLETE":
            setIsWorkflowRunning(false);
            fetchFileTree();
            setRightPanelView("code");
            setMessages((prev) => [
              ...prev,
              {
                id: `complete-${Date.now()}`,
                sender: MessageSender.Agent,
                content: "✅ Workflow completed successfully!",
              },
            ]);
            break;

          case "WORKFLOW_FAILED":
            setIsWorkflowRunning(false);
            setMessages((prev) => [
              ...prev,
              {
                id: `fail-${Date.now()}`,
                sender: MessageSender.Agent,
                content: `❌ Workflow failed: ${data.error || "Unknown error"}`,
              },
            ]);
            break;

          case "PREVIEW_URL_READY":
            setPreviewUrl(data.url);
            setRightPanelView("preview");
            setMessages((prev) => [
              ...prev,
              {
                id: `preview-${Date.now()}`,
                sender: MessageSender.Agent,
                content: `🌐 Preview is ready at: ${data.url}`,
              },
            ]);
            break;

          case "AGENT_LOG":
            setAgentLogs((prev) => [...prev, data]);
            break;

          case "AGENT_MESSAGE":
            if (data.message) {
              setMessages((prev) => [
                ...prev,
                {
                  id: `agent-${Date.now()}`,
                  sender: MessageSender.Agent,
                  content: data.message,
                },
              ]);
            }
            break;

          case "QUALITY_GATE_BLOCKED":
            setPaused(true);
            setPauseMessage(data.message || "Quality gate blocked. Please review.");
            setMessages((prev) => [
              ...prev,
              {
                id: `quality-gate-${Date.now()}`,
                sender: MessageSender.Agent,
                content: `⚠️ Quality Gate Blocked: ${data.message || "Quality standards not met. Please review and continue."}`
              },
            ]);
            break;

          case "WORKSPACE_UPDATED":
            // Refresh file tree when workspace is updated
            console.log("[WS] Workspace updated, refreshing file tree");
            fetchFileTree();
            break;

          default:
            console.warn("[WS] Unknown message type:", data.type);
            break;
        }
      } catch (err) {
        console.error("[WS] Failed to parse message:", err);
      }
    };

    return () => {
      console.log("[WS] Cleaning up connection");
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close(1000, "Component unmounted");
      }
    };
  }, [projectId]);

  // ============================================================
  // START GENERATION
  // ============================================================
  const isRequestInFlight = useRef(false);

  useEffect(() => {
    if (!initialPrompt || !projectId || !isWsOpen) return;

    if (startedWorkspaces.has(projectId)) return;
    if (isRequestInFlight.current) return;

    startedWorkspaces.add(projectId);
    isRequestInFlight.current = true;
    hasStartedGeneration.current = true;

    setMessages([
      {
        id: `user-${Date.now()}`,
        sender: MessageSender.User,
        content: initialPrompt,
      },
      {
        id: `init-${Date.now()}`,
        sender: MessageSender.Agent,
        content: "Initiating autonomous workflow. This may take a few minutes.",
      },
    ]);

    // FIX: Use "fresh" mode for new projects from HomePage to ensure full scaffolding
    // This prevents accidentally resuming from stale MongoDB state
    startWorkflow(projectId, initialPrompt, "fresh")
      .then((response) => {
        setMessages((prev) => [
          ...prev,
          {
            id: `success-${Date.now()}`,
            sender: MessageSender.Agent,
            content: response?.message || "Workflow started successfully. Awaiting updates",
          },
        ]);
      })
      .catch((err) => {
        setIsWorkflowRunning(false);
        // Clean up to allow retry
        if (projectId) {
          startedWorkspaces.delete(projectId);
        }
        setMessages((prev) => [
          ...prev,
          {
            id: `err-${Date.now()}`,
            sender: MessageSender.Agent,
            content: `❌ Failed to start workflow: ${err?.message || "Unknown error"}. Please check backend logs.`,
          },
        ]);
      })
      .finally(() => {
        isRequestInFlight.current = false;
      });
  }, [initialPrompt, projectId, isWsOpen]);

  // ---- Resume workflow ----
  const handleResume = async () => {
    if (!projectId) return;
    try {
      await resumeWorkflow(projectId, "Yes, continue.");
      setPaused(false);
      setPauseMessage("");
      setMessages((prev) => [
        ...prev,
        {
          id: `resume-${Date.now()}`,
          sender: MessageSender.Agent,
          content: "✓ Workflow resumed successfully.",
        },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `resume-err-${Date.now()}`,
          sender: MessageSender.Agent,
          content: `Failed to resume: ${err.message}`,
        },
      ]);
    }
  };

  // ---- Deployment ----
  const handleDeploy = async () => {
    if (!projectId || isDeploying || isWorkflowRunning) return;
    setIsDeploying(true);
    await startDeployment({ projectId });
  };

  // ---- Chat send ----
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userInput.trim() || !projectId) return;

    const msg = userInput;
    setUserInput("");

    setMessages((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        sender: MessageSender.User,
        content: msg,
      },
    ]);

    if (isWorkflowRunning) return;

    try {
      setIsWorkflowRunning(true);
      setGenerationStatus("Refining codebase...");
      await resumeWorkflow(projectId, msg);
      setMessages((prev) => [
        ...prev,
        {
          id: `agent-ack-${Date.now()}`,
          sender: MessageSender.Agent,
          content: "Got it. Refining the codebase based on your feedback...",
        },
      ]);
    } catch (err: any) {
      setIsWorkflowRunning(false);
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          sender: MessageSender.Agent,
          content: `Failed to refine: ${err.message}`,
        },
      ]);
    }
  };

  // Get current workflow stage info
  const getCurrentStage = () => {
    // Special handling for Refine step
    if (currentStepName === "refine") {
      return {
        step: workflowStage,
        agent: "Agent",
        stage: "Refinement",
        description: "Refining codebase based on feedback"
      };
    }

    // Normal handling
    const stage = WORKFLOW_STAGES.find(s => s.step === workflowStage);
    return stage || { step: workflowStage, agent: "Agent", stage: "Processing", description: generationStatus };
  };

  const currentStage = getCurrentStage();
  const progressPercent = Math.min((workflowStage / WORKFLOW_STAGES.length) * 100, 100);

  // ---- Render ----
  return (
    <div className="flex flex-col h-screen bg-[#0A0A0A] text-white overflow-hidden">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-white/5 bg-zinc-900/50 backdrop-blur-sm">
        <div className="flex items-center gap-4">
          <Link to="/" className="flex items-center gap-3 group hover:opacity-80 transition-opacity">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-purple-500 to-indigo-600 group-hover:shadow-lg group-hover:shadow-purple-500/25 transition-shadow">
              <SparklesIcon className="h-4 w-4 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-semibold text-white truncate max-w-[200px]">
                {projectId?.slice(0, 20)}...
              </h1>
              <p className="text-xs text-zinc-500">Autonomous Generator</p>
            </div>
          </Link>
        </div>

        {/* Progress Bar */}
        {isWorkflowRunning && (
          <div className="flex-1 max-w-2xl mx-8 flex items-center gap-4">
            <div className="flex items-center gap-2 flex-shrink-0">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center">
                <LoaderCircleIcon className="animate-spin h-4 w-4 text-white" />
              </div>
              <div className="flex flex-col">
                <span className="text-xs font-semibold text-purple-400">{currentStage.agent}</span>
                <span className="text-[10px] text-zinc-500">{currentStage.stage}</span>
              </div>
            </div>

            <div className="flex-1">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-zinc-300">{currentStage.description}</span>
                <span className="text-xs text-zinc-600">{workflowStage}/{WORKFLOW_STAGES.length}</span>
              </div>
              <div className="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-purple-500 via-violet-500 to-indigo-500 rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>

              {/* Stage indicators */}
              <div className="flex justify-between mt-2">
                {WORKFLOW_STAGES.slice(0, 5).map((s) => (
                  <div
                    key={s.step}
                    className={`h-1.5 w-1.5 rounded-full transition-all ${s.step <= workflowStage
                      ? 'bg-purple-500'
                      : 'bg-zinc-700'
                      }`}
                    title={`${s.agent}: ${s.stage}`}
                  />
                ))}
                <div className="w-px" />
                {WORKFLOW_STAGES.slice(5).map((s) => (
                  <div
                    key={s.step}
                    className={`h-1.5 w-1.5 rounded-full transition-all ${s.step <= workflowStage
                      ? 'bg-purple-500'
                      : 'bg-zinc-700'
                      }`}
                    title={`${s.agent}: ${s.stage}`}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Cost Dashboard Button */}
        <button
          onClick={() => setShowCostDashboard(true)}
          className="p-2.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition-all duration-200"
          aria-label="Cost Dashboard"
          title="View token usage & costs"
        >
          <BarChart3Icon className="h-5 w-5" />
        </button>

        {/* Deploy Button */}
        <button
          onClick={handleDeploy}
          disabled={isDeploying || isWorkflowRunning || fileTree.length === 0}
          className="group relative flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium overflow-hidden transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-emerald-600 to-green-600 transition-opacity group-hover:opacity-90" />
          <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent group-hover:translate-x-full transition-transform duration-700" />
          {isDeploying ? (
            <LoaderCircleIcon className="relative animate-spin h-4 w-4 text-white" />
          ) : (
            <UploadCloudIcon className="relative h-4 w-4 text-white" />
          )}
          <span className="relative text-white">{isDeploying ? "Deploying..." : "Deploy"}</span>
        </button>
      </div>

      {/* Main Content - 40% Chat / 60% Code-Preview-Terminal */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Panel - Chat (40%) */}
        <div className="w-[40%] min-w-[320px] flex flex-col border-r border-white/5 bg-zinc-950">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex gap-3 ${m.sender === MessageSender.User ? "flex-row-reverse" : ""}`}
              >
                {/* Avatar */}
                <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${m.sender === MessageSender.User
                  ? "bg-purple-500/20"
                  : "bg-gradient-to-br from-violet-500 to-purple-600"
                  }`}>
                  {m.sender === MessageSender.User ? (
                    <UserIcon className="h-4 w-4 text-purple-400" />
                  ) : (
                    <BotIcon className="h-4 w-4 text-white" />
                  )}
                </div>

                {/* Message */}
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 ${m.sender === MessageSender.User
                    ? "bg-purple-600/20 border border-purple-500/20 rounded-tr-sm"
                    : "bg-zinc-800/50 border border-white/5 rounded-tl-sm"
                    }`}
                >
                  <p className="text-sm text-zinc-200 whitespace-pre-wrap leading-relaxed">
                    {m.content}
                  </p>
                </div>
              </div>
            ))}

            {/* Pause Banner */}
            {paused && (
              <div className="flex items-center justify-between bg-amber-900/20 border border-amber-500/30 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <div className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
                  <p className="text-sm text-amber-200">{pauseMessage || "Workflow paused."}</p>
                </div>
                <button
                  onClick={handleResume}
                  className="px-4 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-sm font-medium text-white transition-colors"
                >
                  Continue
                </button>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={handleSendMessage} className="p-4 border-t border-white/5">
            <div className="relative rounded-xl border border-white/10 bg-zinc-900 transition-all focus-within:border-purple-500/30 focus-within:bg-zinc-900/80">
              <textarea
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                placeholder={isWorkflowRunning ? "Waiting for workflow..." : "Send a message to refine..."}
                disabled={isWorkflowRunning || isDeploying}
                className="w-full resize-none bg-transparent rounded-xl p-4 pr-14 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none disabled:opacity-50"
                rows={2}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage(e);
                  }
                }}
              />
              <button
                type="submit"
                disabled={!userInput.trim() || isWorkflowRunning}
                className="absolute right-3 bottom-3 p-2 rounded-lg bg-purple-600 text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-purple-500 transition-colors"
              >
                <SendIcon className="h-4 w-4" />
              </button>
            </div>
          </form>
        </div>

        {/* Right Panel - Code/Preview/Terminal (60%) */}
        <div className="w-[60%] flex flex-col bg-zinc-900/30 overflow-hidden">
          {/* Tab Bar */}
          <div className="flex items-center gap-1 px-4 py-2 bg-zinc-900/80 border-b border-white/5">
            <button
              onClick={() => setRightPanelView("code")}
              disabled={fileTree.length === 0}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${rightPanelView === "code"
                ? "bg-white/10 text-white"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
                } disabled:opacity-40`}
            >
              <CodeIcon className="h-4 w-4" />
              Code
            </button>

            <button
              onClick={() => setRightPanelView("preview")}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${rightPanelView === "preview"
                ? "bg-white/10 text-white"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
                }`}
            >
              <EyeIcon className="h-4 w-4" />
              Preview
              {previewUrl && (
                <span className="ml-1 h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              )}
            </button>

            <button
              onClick={() => setRightPanelView("terminal")}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${rightPanelView === "terminal"
                ? "bg-white/10 text-white"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
                }`}
            >
              <TerminalIcon className="h-4 w-4" />
              Terminal
            </button>
          </div>

          {/* Content Area */}
          <div className="flex-1 overflow-hidden">
            {rightPanelView === "code" && (
              <CodeView
                fileTree={fileTree}
                selectedFile={selectedFile}
                fileContent={selectedFileContent}
                onContentChange={(newContent) => setSelectedFileContent(newContent)}
                onSelectFile={fetchFileContent}
              />
            )}

            {rightPanelView === "preview" && (
              <PreviewController
                previewUrl={previewUrl}
                projectId={projectId || ""}
                onPreviewUrlChange={setPreviewUrl}
              />
            )}

            {rightPanelView === "terminal" && (
              <TerminalView logs={agentLogs} />
            )}

            {!rightPanelView && (
              <div className="h-full flex flex-col items-center justify-center text-zinc-500">
                <div className="w-16 h-16 rounded-2xl bg-zinc-800/50 flex items-center justify-center mb-4">
                  {isWorkflowRunning ? (
                    <LoaderCircleIcon className="h-8 w-8 animate-spin text-purple-400" />
                  ) : (
                    <SparklesIcon className="h-8 w-8 text-zinc-600" />
                  )}
                </div>
                <p className="text-sm">
                  {isWorkflowRunning
                    ? "Generating your app..."
                    : fileTree.length > 0
                      ? "Select Code or Preview to view"
                      : "Waiting for generation..."}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Cost Dashboard Modal */}
      <CostDashboard
        isOpen={showCostDashboard}
        onClose={() => setShowCostDashboard(false)}
        projectId={projectId || null}
      />
    </div>
  );
};

export default WorkspacePage;

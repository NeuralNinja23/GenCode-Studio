
export interface Project {
  id: string;
  name: string;
  description: string;
  lastModified: string;
  imageUrl: string;
  provider?: string;
  model?: string;
  status?: string;
  createdAt?: string;
  exists?: boolean;
}

export enum MessageSender {
  User = 'user',
  Agent = 'agent',
  System = 'system',
}

export enum AgentStepStatus {
  Completed = 'completed',
  InProgress = 'in_progress',
  Failed = 'failed',
}

export interface AgentStep {
  title: string;
  status: AgentStepStatus;
  details?: string[];
}

export interface ChatMessage {
  id: string;
  sender: MessageSender;
  content: string;
  step?: AgentStep;
  timestamp?: string;
}

export interface FileTreeNode {
  path: string;
  name: string;
  type: 'file' | 'folder';
  children?: FileTreeNode[];
}

// ============================================================
// Workflow Types - Match backend app/core/types.py
// ============================================================

/**
 * Workflow status enum - matches backend WorkflowStatus
 */
export enum WorkflowStatus {
  Running = 'running',
  Paused = 'paused',
  Completed = 'completed',
  Failed = 'failed',
}

/**
 * Workflow step names - matches backend WorkflowStep in constants.py
 * Uses Emergent E1 Frontend-First pattern (12 steps)
 */
export enum WorkflowStepName {
  Architecture = 'architecture',
  FrontendMock = 'frontend_mock',
  BackendModels = 'backend_models',
  BackendRouters = 'backend_routers',
  SystemIntegration = 'system_integration',
  TestingBackend = 'testing_backend',
  FrontendIntegration = 'frontend_integration',
  TestingFrontend = 'testing_frontend',
  PreviewFinal = 'preview_final',
  Refine = 'refine',
  Complete = 'complete',
}

/**
 * Workflow stage info for UI display
 */
export interface WorkflowStage {
  step: number;
  agent: string;
  stage: string;
  description: string;
}

/**
 * WebSocket message types - matches backend WSMessageType
 */
export enum WSMessageType {
  WorkflowUpdate = 'WORKFLOW_UPDATE',
  WorkflowComplete = 'WORKFLOW_COMPLETE',
  WorkflowFailed = 'WORKFLOW_FAILED',
  WorkflowPaused = 'WORKFLOW_PAUSED',
  WorkflowResumed = 'WORKFLOW_RESUMED',
  AgentLog = 'AGENT_LOG',
  AgentMessage = 'AGENT_MESSAGE',
  PreviewUrlReady = 'PREVIEW_URL_READY',
  QualityGateBlocked = 'QUALITY_GATE_BLOCKED',
  WorkspaceUpdated = 'WORKSPACE_UPDATED',
}

/**
 * WebSocket message payload interface
 */
export interface WSMessage {
  type: WSMessageType;
  projectId?: string;
  step?: string;
  turn?: number;
  totalTurns?: number;
  status?: string;
  message?: string;
  error?: string;
  url?: string;
  backend_url?: string;
  data?: Record<string, unknown>;
}

/**
 * Agent output structure
 */
export interface AgentOutput {
  files: Array<{ path: string; content: string }>;
  thinking?: string;
  raw?: string;
}

/**
 * Cost tracking summary
 */
export interface CostSummary {
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  /** Estimated cost in USD - matches backend's total_estimated_cost */
  total_estimated_cost: number;
  /** Cost breakdown by agent */
  by_agent?: Record<string, { input: number; output: number }>;
  /** Cost breakdown by provider */
  by_provider_cost?: Record<string, number>;
  /** Legacy alias for total_estimated_cost */
  estimated_cost?: number;
  /** Legacy alias for API call count */
  calls?: number;
}


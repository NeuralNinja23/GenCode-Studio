// frontend/src/services/agentService.ts

import axios, { AxiosError } from "axios";
import { Project, FileTreeNode } from "../types";
import { TIMEOUTS } from "../config/constants";
import { getApiUrl, getBackendBaseUrl } from "../config/env";
import { withRetry, isNetworkError, RetryPresets } from "../utils/retry";
import { validateProjectId, validateFilePath, sanitizeInput } from "../utils/validation";

const API_BASE = getApiUrl('/api/workspace');

// ================================================================
// INTERFACES
// ================================================================

interface WorkflowResponse {
  success: boolean;
  message?: string;
  project_id?: string;
  already_running?: boolean;
  mode?: "fresh" | "resume";  // NEW: Resume mode indicator
  completed_steps?: string[]; // NEW: List of already completed steps
}

// NEW: Progress response from backend
interface ProgressResponse {
  project_id: string;
  project_exists: boolean;
  completed_steps: string[];
  current_step: string | null;
  is_running: boolean;
  is_paused: boolean;
  is_resumable: boolean;
  total_completed: number;
}

// FileTreeEntry removed - using FileTreeNode from types

interface FileContentResponse {
  content: string;
}

interface SaveFileResponse {
  success: boolean;
  filename: string;
}

// ================================================================
// ERROR HANDLING
// ================================================================

const handleAxiosError = (error: unknown, operation: string): never => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail: string }>;
    const detail = axiosError.response?.data?.detail || axiosError.message;
    const status = axiosError.response?.status;

    console.error(`[${operation}] Error ${status}:`, detail);
    throw new Error(`${operation} failed: ${detail}`);
  }

  console.error(`[${operation}] Unknown error:`, error);
  throw new Error(`${operation} failed: Unknown error`);
};

// ================================================================
// WORKFLOW FUNCTIONS
// ================================================================

/**
 * Starts the autonomous workflow for backend generation.
 * @param projectId - Project ID
 * @param prompt - User prompt describing the app
 * @param resumeMode - "auto" (default, auto-resume if progress exists), "resume" (force resume), "fresh" (clear progress and start new)
 * @throws Error if the request fails
 */
export const startWorkflow = async (
  projectId: string,
  prompt: string,
  resumeMode: "auto" | "resume" | "fresh" = "auto"
): Promise<WorkflowResponse> => {
  // Validate inputs
  if (!validateProjectId(projectId)) {
    throw new Error('Invalid project ID format');
  }

  const sanitizedPrompt = sanitizeInput(prompt);
  if (!sanitizedPrompt || sanitizedPrompt.length < 3) {
    throw new Error('Prompt must be at least 3 characters');
  }

  return withRetry(
    async () => {
      const response = await axios.post<WorkflowResponse>(
        `${API_BASE}/${projectId}/generate/backend`,
        {
          description: sanitizedPrompt,
          resume_mode: resumeMode  // NEW: Send resume mode to backend
        },
        { timeout: TIMEOUTS.WORKFLOW }
      );

      console.log(`[START WORKFLOW] Success for ${projectId}, mode: ${response.data.mode || resumeMode}`);
      return response.data;
    },
    {
      ...RetryPresets.STANDARD,
      shouldRetry: isNetworkError,
      onRetry: (attempt, error) => {
        console.warn(`[START WORKFLOW] Retry attempt ${attempt} for ${projectId}:`, error);
      },
    }
  );
};

/**
 * Resume the workflow after user message.
 * @throws Error if the request fails
 */
export const resumeWorkflow = async (
  projectId: string,
  message: string = "Continue"
): Promise<WorkflowResponse> => {
  // Validate inputs
  if (!validateProjectId(projectId)) {
    throw new Error('Invalid project ID format');
  }

  const sanitizedMessage = sanitizeInput(message);

  return withRetry(
    async () => {
      const response = await axios.post<WorkflowResponse>(
        `${API_BASE}/resume`,
        {
          project_id: projectId,
          user_message: sanitizedMessage,
        },
        { timeout: TIMEOUTS.WORKFLOW }
      );

      console.log(`[RESUME WORKFLOW] Success for ${projectId}`);
      return response.data;
    },
    {
      ...RetryPresets.STANDARD,
      shouldRetry: isNetworkError,
    }
  );
};

// ================================================================
// FILE OPERATIONS
// ================================================================

/**
 * Get file tree for a project.
 * @throws Error if the request fails
 */
export const getWorkspaceFiles = async (
  projectId: string
): Promise<FileTreeNode[]> => {
  // Validate project ID
  if (!validateProjectId(projectId)) {
    throw new Error('Invalid project ID format');
  }

  return withRetry(
    async () => {
      const res = await axios.get<FileTreeNode[]>(
        `${API_BASE}/${projectId}/files`,
        { timeout: TIMEOUTS.FILE_LIST }
      );

      return res.data ?? [];
    },
    {
      ...RetryPresets.QUICK,
      shouldRetry: isNetworkError,
    }
  );
};

/**
 * Get project details.
 * @throws Error if the request fails
 */
export const getProject = async (
  projectId: string
): Promise<Project> => {
  try {
    const API_PROJECTS = getApiUrl('/api/projects');
    const res = await axios.get<Project>(`${API_PROJECTS}/${projectId}`);
    return res.data;
  } catch (error) {
    // handleAxiosError always throws, but we need explicit throw for TS control flow
    throw handleAxiosError(error, "Get Project");
  }
};

/**
 * Get file content from a specific file.
 * @throws Error if the request fails
 */
export const getFileContent = async (
  projectId: string,
  filePath: string
): Promise<string> => {
  // Validate inputs
  if (!validateProjectId(projectId)) {
    throw new Error('Invalid project ID format');
  }

  if (!validateFilePath(filePath)) {
    throw new Error('Invalid file path');
  }

  return withRetry(
    async () => {
      const res = await axios.get<FileContentResponse>(
        `${API_BASE}/${projectId}/file?path=${encodeURIComponent(filePath)}`,
        { timeout: TIMEOUTS.FILE_READ }
      );

      return res.data?.content ?? "";
    },
    {
      ...RetryPresets.QUICK,
      shouldRetry: isNetworkError,
    }
  );
};

/**
 * Save file content to a specific file.
 * @throws Error if the request fails
 */
export const saveFile = async (
  projectId: string,
  filePath: string,
  content: string
): Promise<SaveFileResponse> => {
  try {
    const res = await axios.put<{ saved: boolean; path: string }>(
      `${API_BASE}/${projectId}/file`,
      {
        path: filePath,
        content,
      },
      { timeout: TIMEOUTS.FILE_SAVE }
    );

    console.log(`[SAVE FILE] Success: ${filePath}`);
    // Map backend response to interface expected by consumers
    return {
      success: res.data.saved,
      filename: res.data.path,
    };
  } catch (error) {
    // handleAxiosError always throws, but we need explicit throw for TS control flow
    throw handleAxiosError(error, "Save File");
  }
};

// ================================================================
// UTILITIES
// ================================================================

/**
 * Test connection to backend
 */
export const testConnection = async (): Promise<boolean> => {
  try {
    await axios.get(`${API_BASE}/list`, { timeout: TIMEOUTS.CONNECTION_TEST });
    console.log("[CONNECTION TEST] Backend is reachable");
    return true;
  } catch (error) {
    console.error("[CONNECTION TEST] Backend is unreachable:", error);
    return false;
  }
};

/**
 * Get workflow progress for a project.
 * Used to check if a project can be resumed.
 */
export const getProjectProgress = async (
  projectId: string
): Promise<ProgressResponse | null> => {
  if (!validateProjectId(projectId)) {
    throw new Error('Invalid project ID format');
  }

  try {
    const response = await axios.get<ProgressResponse>(
      `${API_BASE}/${projectId}/progress`,
      { timeout: TIMEOUTS.CONNECTION_TEST }
    );
    console.log(`[GET PROGRESS] ${projectId}:`, response.data);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      // Project doesn't exist yet, not an error
      return null;
    }
    console.error("[GET PROGRESS] Error:", error);
    return null;
  }
};

/**
 * Clear progress for a project (for fresh start).
 */
export const clearProgress = async (
  projectId: string
): Promise<boolean> => {
  if (!validateProjectId(projectId)) {
    throw new Error('Invalid project ID format');
  }

  try {
    await axios.post(`${API_BASE}/${projectId}/clear-progress`, {}, {
      timeout: TIMEOUTS.CONNECTION_TEST
    });
    console.log(`[CLEAR PROGRESS] Success for ${projectId}`);
    return true;
  } catch (error) {
    console.error("[CLEAR PROGRESS] Error:", error);
    return false;
  }
};

// Export ProgressResponse type for components
export type { ProgressResponse };

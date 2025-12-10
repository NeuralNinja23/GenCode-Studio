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
 * @throws Error if the request fails
 */
export const startWorkflow = async (
  projectId: string,
  prompt: string
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
        { description: sanitizedPrompt },
        { timeout: TIMEOUTS.WORKFLOW }
      );

      console.log(`[START WORKFLOW] Success for ${projectId}`);
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

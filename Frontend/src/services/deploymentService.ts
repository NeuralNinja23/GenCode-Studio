// frontend/src/services/deploymentService.ts
import axios from 'axios';
import { getApiUrl } from '../config/env';

interface DeploymentInitRequest {
  projectId: string;
  projectName: string;
  customDomain?: string;
  environmentVars?: Record<string, string>;
}

interface DeploymentRequest {
  projectId: string;
  customDomain?: string;
  environmentVars?: Record<string, string>;
}

interface DeploymentStatus {
  status: 'active' | 'deploying' | 'failed' | 'not_deployed';
  version?: string;
  url?: string;
  customDomain?: string;
  containerHealth?: string;
  deployedAt?: string;
  port?: number;
}

const API_BASE_URL = getApiUrl('/api/deployment');

/**
 * Initialize a new deployment
 */
export const initializeDeployment = async (data: DeploymentInitRequest) => {
  console.log(`[DEPLOYMENT SERVICE] Initializing deployment for project: ${data.projectId}...`);
  const response = await axios.post(`${API_BASE_URL}/initialize`, data);
  return response.data;
};

/**
 * Start one-click deployment
 */
export const startDeployment = async (data: DeploymentRequest) => {
  console.log(`[DEPLOYMENT SERVICE] Starting deployment for project: ${data.projectId}...`);
  const response = await axios.post(`${API_BASE_URL}/${data.projectId}`, data);
  return response.data;
};

/**
 * Get deployment status
 */
export const getDeploymentStatus = async (projectId: string): Promise<DeploymentStatus> => {
  console.log(`[DEPLOYMENT SERVICE] Fetching deployment status for: ${projectId}`);
  const response = await axios.get(`${API_BASE_URL}/status/${projectId}`);
  return response.data;
};

/**
 * Get deployment history
 */
export const getDeploymentHistory = async (projectId: string, limit = 10) => {
  console.log(`[DEPLOYMENT SERVICE] Fetching deployment history for: ${projectId}`);
  const response = await axios.get(`${API_BASE_URL}/history/${projectId}`, { params: { limit } });
  return response.data;
};

/**
 * Rollback to previous version
 */
export const rollbackDeployment = async (projectId: string) => {
  console.log(`[DEPLOYMENT SERVICE] Rolling back deployment for: ${projectId}`);
  const response = await axios.post(`${API_BASE_URL}/rollback/${projectId}`);
  return response.data;
};

/**
 * Update environment variables
 */
export const updateEnvironmentVariables = async (projectId: string, environmentVars: Record<string, string>) => {
  console.log(`[DEPLOYMENT SERVICE] Updating environment variables for: ${projectId}`);
  const response = await axios.post(`${API_BASE_URL}/config/env/${projectId}`, { environmentVars });
  return response.data;
};

/**
 * Get environment variables
 */
export const getEnvironmentVariables = async (projectId: string) => {
  console.log(`[DEPLOYMENT SERVICE] Fetching environment variables for: ${projectId}`);
  const response = await axios.get(`${API_BASE_URL}/config/env/${projectId}`);
  return response.data;
};

/**
 * Setup custom domain
 */
export const setupCustomDomain = async (projectId: string, customDomain: string) => {
  console.log(`[DEPLOYMENT SERVICE] Setting up custom domain ${customDomain} for: ${projectId}`);
  const response = await axios.post(`${API_BASE_URL}/config/domain/${projectId}`, { customDomain });
  return response.data;
};

/**
 * Get deployment logs
 */
export const getDeploymentLogs = async (projectId: string) => {
  console.log(`[DEPLOYMENT SERVICE] Fetching deployment logs for: ${projectId}`);
  const response = await axios.get(`${API_BASE_URL}/logs/${projectId}`);
  return response.data;
};

/**
 * Restart deployment
 */
export const restartDeployment = async (projectId: string) => {
  console.log(`[DEPLOYMENT SERVICE] Restarting deployment for: ${projectId}`);
  const response = await axios.post(`${API_BASE_URL}/restart/${projectId}`);
  return response.data;
};

/**
 * Get deployment metrics (CPU, memory, restart count)
 */
export const getDeploymentMetrics = async (projectId: string) => {
  console.log(`[DEPLOYMENT SERVICE] Fetching metrics for: ${projectId}`);
  const response = await axios.get(`${API_BASE_URL}/metrics/${projectId}`);
  return response.data;
};

/**
 * Get container health status
 */
export const getContainerHealth = async (projectId: string) => {
  console.log(`[DEPLOYMENT SERVICE] Fetching health status for: ${projectId}`);
  const response = await axios.get(`${API_BASE_URL}/health/${projectId}`);
  return response.data;
};

/**
 * Download deployment logs as file
 */
export const downloadLogs = async (projectId: string) => {
  console.log(`[DEPLOYMENT SERVICE] Downloading logs for: ${projectId}`);
  const response = await axios.get(`${API_BASE_URL}/logs/${projectId}/download`, {
    responseType: 'blob'
  });
  return response.data;
};

export default {
  initializeDeployment,
  startDeployment,
  getDeploymentStatus,
  getDeploymentHistory,
  rollbackDeployment,
  updateEnvironmentVariables,
  getEnvironmentVariables,
  setupCustomDomain,
  getDeploymentLogs,
  restartDeployment,
  getDeploymentMetrics,
  getContainerHealth,
  downloadLogs
};

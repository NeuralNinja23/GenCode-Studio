// frontend/src/components/DeploymentDashboard.tsx
import React, { useState, useEffect } from 'react';
import deploymentService from '../services/deploymentService';
import EnvironmentVariablesModal from './EnvironmentVariablesModal';
import LogsViewerModal from './LogsViewerModal';
import './DeploymentDashboard.css';

interface DeploymentDashboardProps {
  projectId: string;
  projectName: string;
  onDeployClick: () => void;
}

interface DeploymentStatus {
  status: string;
  version?: string;
  url?: string;
  customDomain?: string;
  containerHealth?: string;
  deployedAt?: string;
  port?: number;
}

interface HistoryItem {
  _id: string;
  action: string;
  version: string;
  timestamp: string;
}

interface Metrics {
  cpuPercent: number;
  memoryMB: number;
  timestamp: Date;
}

interface Health {
  status: 'healthy' | 'unhealthy' | 'unknown';
  lastCheck: Date;
  isHealthy: boolean;
}

export const DeploymentDashboard: React.FC<DeploymentDashboardProps> = ({
  projectId,
  projectName,
  onDeployClick
}) => {
  const [status, setStatus] = useState<DeploymentStatus | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionInProgress, setActionInProgress] = useState(false);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [showEnvModal, setShowEnvModal] = useState(false);
  const [showLogsModal, setShowLogsModal] = useState(false);

  useEffect(() => {
    fetchDeploymentStatus();
    fetchDeploymentHistory();
    fetchMetrics();
    fetchHealth();

    // Refresh status every 10 seconds
    const statusInterval = setInterval(() => {
      fetchDeploymentStatus();
    }, 10000);

    // Refresh metrics every 5 seconds (when deployed)
    const metricsInterval = setInterval(() => {
      if (status?.status === 'active') {
        fetchMetrics();
        fetchHealth();
      }
    }, 5000);

    return () => {
      clearInterval(statusInterval);
      clearInterval(metricsInterval);
    };
  }, [projectId, status?.status]);

  const fetchDeploymentStatus = async () => {
    try {
      const result = await deploymentService.getDeploymentStatus(projectId);
      setStatus(result);
    } catch (error) {
      console.error('Failed to fetch deployment status:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDeploymentHistory = async () => {
    try {
      const result = await deploymentService.getDeploymentHistory(projectId, 5);
      setHistory(result.history || []);
    } catch (error) {
      console.error('Failed to fetch deployment history:', error);
    }
  };

  const fetchMetrics = async () => {
    try {
      const result = await deploymentService.getDeploymentMetrics(projectId);
      if (result.metrics) {
        setMetrics(result.metrics);
      }
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
    }
  };

  const fetchHealth = async () => {
    try {
      const result = await deploymentService.getContainerHealth(projectId);
      if (result.health) {
        setHealth(result.health);
      }
    } catch (error) {
      console.error('Failed to fetch health:', error);
    }
  };

  const handleRollback = async () => {
    setActionInProgress(true);
    try {
      await deploymentService.rollbackDeployment(projectId);
      // Refresh status
      setTimeout(() => {
        fetchDeploymentStatus();
        fetchDeploymentHistory();
      }, 2000);
    } catch (error) {
      console.error('Rollback failed:', error);
    } finally {
      setActionInProgress(false);
    }
  };

  const handleRestart = async () => {
    setActionInProgress(true);
    try {
      await deploymentService.restartDeployment(projectId);
      // Refresh status
      setTimeout(() => {
        fetchDeploymentStatus();
      }, 2000);
    } catch (error) {
      console.error('Restart failed:', error);
    } finally {
      setActionInProgress(false);
    }
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'active':
        return 'green';
      case 'deploying':
        return 'orange';
      case 'failed':
        return 'red';
      default:
        return 'gray';
    }
  };

  const getHealthColor = (health?: string) => {
    switch (health) {
      case 'healthy':
        return 'green';
      case 'unhealthy':
        return 'red';
      default:
        return 'gray';
    }
  };

  if (loading) {
    return (
      <div className="deployment-dashboard">
        <div className="loading">Loading deployment status...</div>
      </div>
    );
  }

  const isDeployed = status?.status === 'active';

  return (
    <div className="deployment-dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <h2>🚀 Deployment Status</h2>
        <button
          className="btn-deploy"
          onClick={onDeployClick}
          disabled={status?.status === 'deploying'}
        >
          {status?.status === 'deploying' ? 'Deploying...' : 'Deploy Now'}
        </button>
      </div>

      {/* Status Card */}
      <div className="status-card">
        {isDeployed ? (
          <>
            <div className="status-content">
              <div className="status-item">
                <label>Status</label>
                <div className={`status-badge ${getStatusColor(status?.status)}`}>
                  ● {status?.status || 'Unknown'}
                </div>
              </div>

              <div className="status-item">
                <label>Version</label>
                <span className="version">{status?.version || 'N/A'}</span>
              </div>

              <div className="status-item">
                <label>Container Health</label>
                <div className={`health-badge ${getHealthColor(health?.status)}`}>
                  ● {health?.status || 'Unknown'}
                </div>
              </div>

              <div className="status-item">
                <label>Live URL</label>
                {status?.url ? (
                  <a href={status.url} target="_blank" rel="noopener noreferrer" className="url-link">
                    {status.url}
                  </a>
                ) : (
                  <span>Not deployed</span>
                )}
              </div>

              {status?.customDomain && (
                <div className="status-item">
                  <label>Custom Domain</label>
                  <span>{status.customDomain}</span>
                </div>
              )}

              <div className="status-item">
                <label>Deployed</label>
                <span>{status?.deployedAt ? new Date(status.deployedAt).toLocaleString() : 'N/A'}</span>
              </div>
            </div>

            {/* Metrics Panel */}
            {metrics && (
              <div className="metrics-panel">
                <h4>📊 Container Metrics</h4>
                <div className="metrics-grid">
                  <div className="metric-display">
                    <label>CPU Usage</label>
                    <div className="metric-bar-container">
                      <div className="metric-bar" style={{ width: `${Math.min(metrics.cpuPercent, 100)}%` }}></div>
                    </div>
                    <span>{metrics.cpuPercent.toFixed(1)}%</span>
                  </div>
                  <div className="metric-display">
                    <label>Memory Usage</label>
                    <div className="metric-bar-container">
                      <div className="metric-bar" style={{ width: `${Math.min((metrics.memoryMB / 512) * 100, 100)}%` }}></div>
                    </div>
                    <span>{metrics.memoryMB.toFixed(0)} MB / 512 MB</span>
                  </div>
                </div>
              </div>
            )}

            <div className="status-actions">
              <button
                className="btn-action btn-restart"
                onClick={handleRestart}
                disabled={actionInProgress}
              >
                🔄 Restart
              </button>
              <button
                className="btn-action btn-rollback"
                onClick={handleRollback}
                disabled={actionInProgress || history.length === 0}
              >
                ⏮ Rollback
              </button>
              <button
                className="btn-action btn-env"
                onClick={() => setShowEnvModal(true)}
              >
                🔐 Update Env
              </button>
              <button
                className="btn-action btn-logs"
                onClick={() => setShowLogsModal(true)}
              >
                📋 View Logs
              </button>
            </div>
          </>
        ) : (
          <div className="not-deployed">
            <p>No active deployment yet.</p>
            <p className="note">Click "Deploy Now" to deploy your application to production.</p>
          </div>
        )}
      </div>

      {/* Deployment History */}
      {history.length > 0 && (
        <div className="history-card">
          <h3>📋 Deployment History</h3>
          <div className="history-list">
            {history.map((item) => (
              <div key={item._id} className="history-item">
                <div className="history-action">{item.action.toUpperCase()}</div>
                <div className="history-version">v{item.version}</div>
                <div className="history-time">
                  {new Date(item.timestamp).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Features */}
      <div className="features-card">
        <h3>✨ Managed Infrastructure Features</h3>
        <div className="features-grid">
          <div className="feature-item">
            <span className="feature-icon">🔒</span>
            <span className="feature-name">Auto HTTPS</span>
            <span className="feature-desc">Let's Encrypt SSL</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">📈</span>
            <span className="feature-name">Auto-Scaling</span>
            <span className="feature-desc">Scale as needed</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">🏥</span>
            <span className="feature-name">Health Checks</span>
            <span className="feature-desc">24/7 monitoring</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">⏮</span>
            <span className="feature-name">Instant Rollback</span>
            <span className="feature-desc">One-click undo</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">🔄</span>
            <span className="feature-name">Auto Restart</span>
            <span className="feature-desc">Always online</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">📊</span>
            <span className="feature-name">Live Logs</span>
            <span className="feature-desc">Real-time insights</span>
          </div>
        </div>
      </div>

      {/* Modals */}
      <EnvironmentVariablesModal
        projectId={projectId}
        isOpen={showEnvModal}
        onClose={() => setShowEnvModal(false)}
        onSave={() => {
          fetchDeploymentStatus();
        }}
      />

      <LogsViewerModal
        projectId={projectId}
        isOpen={showLogsModal}
        onClose={() => setShowLogsModal(false)}
      />
    </div>
  );
};

export default DeploymentDashboard;

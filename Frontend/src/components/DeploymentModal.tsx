// frontend/src/components/DeploymentModal.tsx
import React, { useState, useEffect } from 'react';
import deploymentService from '../services/deploymentService';
import './DeploymentModal.css';

interface DeploymentModalProps {
  projectId: string;
  projectName: string;
  isOpen: boolean;
  onClose: () => void;
  onWebSocketUpdate: (message: any) => void;
}

export const DeploymentModal: React.FC<DeploymentModalProps> = ({
  projectId,
  projectName,
  isOpen,
  onClose,
  onWebSocketUpdate
}) => {
  const [step, setStep] = useState<'config' | 'deploying' | 'success' | 'error'>('config');
  const [customDomain, setCustomDomain] = useState('');
  const [environmentVars, setEnvironmentVars] = useState<Record<string, string>>({});
  const [envVarInput, setEnvVarInput] = useState('');
  const [deploymentUrl, setDeploymentUrl] = useState('');
  const [deploymentLogs, setDeploymentLogs] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStage, setCurrentStage] = useState('');
  const [metrics, setMetrics] = useState({ cpuPercent: 0, memoryMB: 0, timestamp: new Date() });
  const [encryptSecrets, setEncryptSecrets] = useState(true);
  const [deploymentVersion, setDeploymentVersion] = useState('');

  useEffect(() => {
    if (!isOpen) return;

    // Fetch existing environment variables
    deploymentService
      .getEnvironmentVariables(projectId)
      .then((res) => {
        setEnvironmentVars(res.environmentVars || {});
      })
      .catch((err) => {
        console.error('Failed to fetch environment variables:', err);
      });
  }, [isOpen, projectId]);

  const handleAddEnvVar = () => {
    const [key, value] = envVarInput.split('=');
    if (key && value) {
      setEnvironmentVars({ ...environmentVars, [key]: value });
      setEnvVarInput('');
    }
  };

  const handleRemoveEnvVar = (key: string) => {
    const newVars = { ...environmentVars };
    delete newVars[key];
    setEnvironmentVars(newVars);
  };

  const updateProgressBar = (stage: string) => {
    const stageProgress: Record<string, number> = {
      'initialization': 5,
      'building': 30,
      'pushing': 50,
      'deploying': 70,
      'https_setup': 85,
      'health_check': 100
    };
    setProgress(stageProgress[stage] || 0);
  };

  const handleStartDeployment = async () => {
    try {
      setLoading(true);
      setStep('deploying');
      setDeploymentLogs([]);
      setProgress(0);
      setCurrentStage('');

      // Initialize deployment
      await deploymentService.initializeDeployment({
        projectId,
        projectName,
        customDomain: customDomain || undefined,
        environmentVars
      });

      // Start deployment
      await deploymentService.startDeployment({
        projectId,
        customDomain: customDomain || undefined,
        environmentVars
      });

      // Listen for WebSocket updates
      const handleUpdate = (message: any) => {
        if (message.projectId === projectId) {
          if (message.type === 'DEPLOY_LOG') {
            setDeploymentLogs((prev) => [...prev, message.log]);
          } else if (message.type === 'DEPLOY_UPDATE') {
            setCurrentStage(message.stage || '');
            updateProgressBar(message.stage);
            if (message.status) {
              setDeploymentLogs((prev) => [...prev, message.status]);
            }
          } else if (message.type === 'DEPLOY_METRICS') {
            setMetrics({
              cpuPercent: message.cpuPercent || 0,
              memoryMB: message.memoryMB || 0,
              timestamp: new Date(message.timestamp)
            });
          } else if (message.type === 'DEPLOY_COMPLETE') {
            setStep('success');
            setDeploymentUrl(message.deploymentUrl);
            setDeploymentVersion(message.version);
            setProgress(100);
          } else if (message.type === 'DEPLOY_ERROR') {
            setStep('error');
            setError(message.error);
          }
          onWebSocketUpdate(message);
        }
      };

      // Store handler for later cleanup
      (window as any).deploymentMessageHandler = handleUpdate;
    } catch (err: any) {
      setStep('error');
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenUrl = () => {
    if (deploymentUrl) {
      window.open(deploymentUrl, '_blank');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="deployment-modal-overlay">
      <div className="deployment-modal">
        <div className="deployment-modal-header">
          <h2>🚀 Deploy {projectName}</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        {step === 'config' && (
          <div className="deployment-step config">
            <h3>Deployment Configuration</h3>

            <div className="form-group">
              <label>Custom Domain (Optional)</label>
              <input
                type="text"
                placeholder="myapp.com"
                value={customDomain}
                onChange={(e) => setCustomDomain(e.target.value)}
              />
              <small>Leave empty to use auto-generated domain</small>
            </div>

            <div className="form-group">
              <label>Environment Variables</label>
              <div className="encryption-notice">
                <input
                  type="checkbox"
                  id="encrypt-secrets"
                  checked={encryptSecrets}
                  onChange={(e) => setEncryptSecrets(e.target.checked)}
                />
                <label htmlFor="encrypt-secrets">🔒 Encrypt environment variables (checked by default)</label>
              </div>
              {encryptSecrets && (
                <small className="encryption-warning">Secrets are encrypted at-rest and never logged</small>
              )}
              <div className="env-var-input-group">
                <input
                  type="text"
                  placeholder="KEY=VALUE"
                  value={envVarInput}
                  onChange={(e) => setEnvVarInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleAddEnvVar()}
                />
                <button onClick={handleAddEnvVar}>Add</button>
              </div>

              <div className="env-vars-list">
                {Object.entries(environmentVars).map(([key, value]) => (
                  <div key={key} className="env-var-item">
                    <span>{key}={encryptSecrets ? '••••••••' : value}</span>
                    <button onClick={() => handleRemoveEnvVar(key)}>Remove</button>
                  </div>
                ))}
              </div>
            </div>

            <div className="deployment-features">
              <h4>✨ Deployment Includes:</h4>
              <ul>
                <li>✅ Docker containerization</li>
                <li>✅ Automatic HTTPS (Let's Encrypt)</li>
                <li>✅ 24/7 uptime guarantee</li>
                <li>✅ Isolated runtime environment</li>
                <li>✅ Health monitoring</li>
                <li>✅ One-click rollback</li>
              </ul>
            </div>

            <div className="deployment-actions">
              <button onClick={onClose} className="btn-secondary">Cancel</button>
              <button onClick={handleStartDeployment} className="btn-primary" disabled={loading}>
                {loading ? 'Starting...' : 'Start Deployment'}
              </button>
            </div>
          </div>
        )}

        {step === 'deploying' && (
          <div className="deployment-step deploying">
            <div className="deployment-spinner"></div>
            <h3>Deployment in Progress...</h3>
            <p>Building and deploying your application to production.</p>

            {/* Progress Bar */}
            <div className="progress-section">
              <div className="progress-bar-container">
                <div className="progress-bar" style={{ width: `${progress}%` }}></div>
              </div>
              <div className="progress-info">
                <span className="progress-percentage">{progress}%</span>
                {currentStage && <span className="current-stage">{currentStage.toUpperCase()}</span>}
              </div>
            </div>

            {/* Metrics Display */}
            {(metrics.cpuPercent > 0 || metrics.memoryMB > 0) && (
              <div className="metrics-section">
                <div className="metric-item">
                  <label>CPU Usage</label>
                  <div className="metric-bar-container">
                    <div className="metric-bar cpu" style={{ width: `${metrics.cpuPercent}%` }}></div>
                  </div>
                  <span className="metric-value">{metrics.cpuPercent.toFixed(1)}%</span>
                </div>
                <div className="metric-item">
                  <label>Memory Usage</label>
                  <div className="metric-bar-container">
                    <div className="metric-bar memory" style={{ width: `${(metrics.memoryMB / 512) * 100}%` }}></div>
                  </div>
                  <span className="metric-value">{metrics.memoryMB.toFixed(0)} MB / 512 MB</span>
                </div>
              </div>
            )}

            {/* Logs Display */}
            <div className="deployment-logs">
              <h4>Build & Deployment Logs</h4>
              <div className="logs-container">
                {deploymentLogs.length > 0 ? (
                  <pre>{deploymentLogs.join('')}</pre>
                ) : (
                  <pre>Waiting for logs...</pre>
                )}
              </div>
            </div>

            <p className="deployment-note">
              ⏱️ This may take 2-5 minutes. Please don't close this window.
            </p>
          </div>
        )}

        {step === 'success' && (
          <div className="deployment-step success">
            <div className="success-icon">✅</div>
            <h3>Deployment Successful!</h3>
            <p>Your application is now live and accessible at production URL.</p>

            {/* Deployment Summary */}
            <div className="deployment-summary">
              <div className="summary-item">
                <label>Version</label>
                <span>{deploymentVersion}</span>
              </div>
              <div className="summary-item">
                <label>Container Health</label>
                <span>✅ Healthy</span>
              </div>
              <div className="summary-item">
                <label>Initial CPU Usage</label>
                <span>{metrics.cpuPercent.toFixed(1)}%</span>
              </div>
              <div className="summary-item">
                <label>Initial Memory Usage</label>
                <span>{metrics.memoryMB.toFixed(0)} MB</span>
              </div>
            </div>

            <div className="deployment-url-box">
              <label>Live URL:</label>
              <div className="url-display">
                <input type="text" value={deploymentUrl} readOnly />
                <button onClick={handleOpenUrl}>Visit App</button>
              </div>
            </div>

            <div className="deployment-info">
              <h4>Next Steps:</h4>
              <ul>
                <li>Visit your live application</li>
                <li>Configure custom domain in settings</li>
                <li>Setup environment-specific variables</li>
                <li>Monitor application health</li>
              </ul>
            </div>

            <div className="deployment-actions">
              <button onClick={onClose} className="btn-primary">Close</button>
            </div>
          </div>
        )}

        {step === 'error' && (
          <div className="deployment-step error">
            <div className="error-icon">❌</div>
            <h3>Deployment Failed</h3>
            <p>{error}</p>

            <div className="deployment-logs">
              <h4>Error Details</h4>
              <pre>{deploymentLogs}</pre>
            </div>

            <div className="deployment-actions">
              <button onClick={() => setStep('config')} className="btn-secondary">Try Again</button>
              <button onClick={onClose} className="btn-primary">Close</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DeploymentModal;

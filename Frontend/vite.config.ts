import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { execSync } from 'child_process'
import net from 'net'

// Helper to check if a port is accessible
function checkPort(port: number, host: string): Promise<boolean> {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(400); // Fast timeout to not block startup
    socket.on('connect', () => {
      socket.destroy();
      resolve(true);
    });
    socket.on('timeout', () => {
      socket.destroy();
      resolve(false);
    });
    socket.on('error', () => {
      resolve(false);
    });
    socket.connect(port, host);
  });
}

// Logic to determine backend URL
async function getBackendConfig() {
  const customHost = process.env.VITE_BACKEND_HOST;
  if (customHost) {
    console.log(`🔌 Using custom backend host: ${customHost}`);
    return { host: customHost, source: 'env' };
  }

  // 1. Try localhost first (Safest default for Windows/Mac/Linux)
  // We check if the backend is already running on localhost
  const isLocalhostOpen = await checkPort(8000, 'localhost');
  if (isLocalhostOpen) {
    return { host: 'localhost', source: 'localhost (detected)' };
  }

  // 2. If localhost failed (backend might be in WSL without auto-forwarding, or not started yet)
  // We try to detect a WSL IP as a smart fallback for mixed environments.
  try {
    const wslIp = execSync('wsl hostname -I', { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'ignore'] }).trim().split(' ')[0];
    if (wslIp && wslIp.match(/^\d+\.\d+\.\d+\.\d+$/)) {
      return { host: wslIp, source: 'WSL IP (fallback)' };
    }
  } catch (e) {
    // Ignore wsl errors (e.g. not on windows, or wsl not installed)
  }

  // 3. Default to localhost
  return { host: 'localhost', source: 'default' };
}

// https://vitejs.dev/config/
export default defineConfig(async () => {
  const { host: backendHost, source } = await getBackendConfig();
  const backendUrl = `http://${backendHost}:8000`;
  const wsUrl = `ws://${backendHost}:8000`;

  console.log(`� Frontend connecting to Backend at: ${backendUrl} [${source}]`);

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: backendUrl,
          changeOrigin: true,
        },
        '/ws': {
          target: wsUrl,
          ws: true,
        }
      }
    }
  }
})

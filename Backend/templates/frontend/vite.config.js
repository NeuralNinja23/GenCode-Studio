import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from "path"

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    server: {
        host: true,
        port: 5174,
        strictPort: true,
        watch: {
            usePolling: true
        },
        proxy: {
            "/api": {
                target: "http://localhost:8001",
                changeOrigin: true,
                secure: false
            }
        }
    }
})

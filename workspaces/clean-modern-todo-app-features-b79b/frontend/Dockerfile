# frontend/Dockerfile
# syntax=docker/dockerfile:1

# Use Playwright image so e2e tests can run in the same container
FROM mcr.microsoft.com/playwright:v1.57.0-jammy

WORKDIR /app

# Copy package metadata first (better build caching)
COPY package.json package-lock.json* ./

# Install dependencies (including dev deps for Playwright + Vite)
RUN npm install --legacy-peer-deps --include=dev

# Copy the rest of the frontend source
COPY . .

# Vite dev server port
EXPOSE 5174

# Optional healthcheck for sandbox / monitoring
HEALTHCHECK --interval=5s --timeout=3s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5174/ || exit 1

# Run Vite dev server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5174"]

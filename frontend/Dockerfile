FROM node:22-alpine

WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy workspace config + lockfile (monorepo root)
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml* ./

# Copy frontend package.json separately
COPY frontend/package.json ./frontend/package.json

# Install dependencies (filter to frontend workspace only)
RUN pnpm install --frozen-lockfile --filter=frontend

# Copy frontend source
COPY frontend/ ./frontend/

WORKDIR /app/frontend

# Expose port
EXPOSE 3000

CMD ["pnpm", "dev"]
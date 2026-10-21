# Stage 1: build the React app into static files.
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime. Only the built static files come across from stage 1,
# so the final image has no Node or node_modules.
FROM python:3.12-slim
WORKDIR /app
COPY backend/pyproject.toml backend/
COPY backend/app backend/app
# Editable install keeps the repo layout (config.py finds paths relative to itself).
RUN pip install --no-cache-dir -e ./backend
COPY --from=web /web/dist frontend/dist
ENV FRONTEND_DIST=/app/frontend/dist
EXPOSE 8000
# Secrets (ESPN cookies, API key) are NOT baked in: pass them at runtime via env vars.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

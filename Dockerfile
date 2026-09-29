FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/main.py backend/start.py ./
COPY --from=frontend /frontend/dist /app/static
ENV FRONTEND_DIST=/app/static
EXPOSE 8000
CMD ["python", "start.py"]

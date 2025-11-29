# Multi-stage build pour frontend React
FROM node:20-alpine as builder

WORKDIR /app

# Copier fichiers de dépendances
COPY package.json package-lock.json ./

# Installer dépendances
RUN npm ci

# Copier code source
COPY . .

# Build application
RUN npm run build

# Stage runtime avec nginx
FROM nginx:alpine

# Copier build depuis builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copier config nginx pour SPA (fallback vers index.html)
RUN echo 'server { \
    listen 80; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    location /api { \
        proxy_pass http://syro-api:8000; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]


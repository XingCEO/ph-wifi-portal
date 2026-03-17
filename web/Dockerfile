FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=builder /app/out /usr/share/nginx/html
COPY <<'EOF' /etc/nginx/conf.d/default.conf
server {
    listen 3000;
    root /usr/share/nginx/html;
    index index.html;

    # SPA fallback — try file, then directory, then index.html
    location / {
        try_files $uri $uri/ $uri/index.html /index.html;
    }

    # Cache static assets
    location /_next/static/ {
        expires 365d;
        add_header Cache-Control "public, immutable";
    }
}
EOF
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]

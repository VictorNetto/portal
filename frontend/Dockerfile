# Frontend PRODUCTION image: build the Vue app, serve the static files with nginx.
# (The development image is Dockerfile.dev: Vite with hot reload.)

# ---- build ----
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# ---- serve ----
FROM nginx:alpine
COPY nginx.web.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

ARG NODE_BASE_IMAGE=node:22-alpine
ARG NGINX_BASE_IMAGE=nginx:1.29-alpine
FROM ${NODE_BASE_IMAGE} AS build
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL
WORKDIR /src
COPY package*.json ./
RUN if [ -f package-lock.json ]; then npm ci --ignore-scripts --no-audit --no-fund; else npm install --package-lock=false --ignore-scripts --no-audit --no-fund; fi
COPY . .
RUN npm run build
FROM ${NGINX_BASE_IMAGE}
COPY --from=build /src/dist /usr/share/nginx/html
EXPOSE 80

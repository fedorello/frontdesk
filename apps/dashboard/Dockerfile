# Frontdesk admin dashboard — Next.js standalone, multi-stage.
FROM node:24-slim AS build
RUN corepack enable
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
# NEXT_PUBLIC_* is inlined at build time — take it from Railway's build args.
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN pnpm build

FROM node:24-slim AS run
WORKDIR /app
# HOSTNAME=0.0.0.0 so Next's standalone server binds all interfaces (Docker otherwise sets
# HOSTNAME to the container id, which a proxy like Railway can't reach).
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0
COPY --from=build /app/public ./public
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]

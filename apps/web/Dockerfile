# Tovayo landing — Next.js standalone, multi-stage.
FROM node:24-slim AS build
RUN corepack enable
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
# NEXT_PUBLIC_* are inlined at build time — take them from Railway's build args.
ARG NEXT_PUBLIC_APP_URL
ARG NEXT_PUBLIC_GITHUB_URL
ENV NEXT_PUBLIC_APP_URL=$NEXT_PUBLIC_APP_URL \
    NEXT_PUBLIC_GITHUB_URL=$NEXT_PUBLIC_GITHUB_URL
RUN pnpm build

FROM node:24-slim AS run
WORKDIR /app
# Run as an unprivileged user so a process compromise doesn't start as root in the container.
RUN useradd --create-home --uid 10001 app
# HOSTNAME=0.0.0.0 so Next's standalone server binds all interfaces — Docker otherwise sets
# HOSTNAME to the container id and the server would bind there, unreachable behind a proxy.
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0
COPY --from=build --chown=app:app /app/public ./public
COPY --from=build --chown=app:app /app/.next/standalone ./
COPY --from=build --chown=app:app /app/.next/static ./.next/static
USER app
EXPOSE 3000
CMD ["node", "server.js"]

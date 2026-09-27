# ── Stage 1: build ─────────────────────────────────────────────────────────
# NEXT_PUBLIC_* variables are inlined by the Next.js compiler at build time,
# not at runtime.  They must be declared as build ARGs and forwarded to ENV so
# that "next build" can embed them.  Pass them when running:
#
#   docker build \
#     --build-arg NEXT_PUBLIC_API_BASE_URL=https://api.example.com/api/v1 \
#     --build-arg NEXT_PUBLIC_GOOGLE_CLIENT_ID=... \
#     -t syncshift-frontend ./app
#
# Or supply them through the "args:" section of compose.yaml (see below).
# Environment variables set only at "docker run" time are NOT visible to
# NEXT_PUBLIC_* – they must be known before the build finishes.

FROM node:20-alpine AS builder

# Receive public env vars as build arguments.
# Defaults are empty strings so the build completes without them; the app
# simply falls back to local-dev mode in that case.
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
ARG NEXT_PUBLIC_GOOGLE_CLIENT_ID=
ARG NEXT_PUBLIC_MICROSOFT_CLIENT_ID=
ARG NEXT_PUBLIC_MICROSOFT_REDIRECT_URI=http://localhost:3000/auth/microsoft/callback
ARG NEXT_PUBLIC_TURNSTILE_SITE_KEY=

# Forward ARGs to ENV so that Next.js picks them up during "next build".
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_GOOGLE_CLIENT_ID=$NEXT_PUBLIC_GOOGLE_CLIENT_ID
ENV NEXT_PUBLIC_MICROSOFT_CLIENT_ID=$NEXT_PUBLIC_MICROSOFT_CLIENT_ID
ENV NEXT_PUBLIC_MICROSOFT_REDIRECT_URI=$NEXT_PUBLIC_MICROSOFT_REDIRECT_URI
ENV NEXT_PUBLIC_TURNSTILE_SITE_KEY=$NEXT_PUBLIC_TURNSTILE_SITE_KEY

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Produce an optimised standalone build so the runtime image needs no dev deps.
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ── Stage 2: production runtime ─────────────────────────────────────────────
# Copies only the compiled output and the minimal node_modules required at
# runtime.  The result is a much smaller image than running "npm run dev".
FROM node:20-alpine AS runner

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

WORKDIR /app

# next.js standalone output bundles the server; public and static assets are
# kept separately for correct serving.
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

# "node server.js" is the production entrypoint emitted by Next.js standalone.
CMD ["node", "server.js"]

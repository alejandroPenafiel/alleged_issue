FROM node:20-bullseye AS builder

WORKDIR /app

RUN npm install -g bun@1.1.8
RUN git clone https://github.com/elizaOS/eliza.git . \
    && bun install --frozen-lockfile
RUN bun run build

FROM node:20-bullseye

ENV NODE_ENV=production
WORKDIR /app

RUN npm install -g bun@1.1.8
COPY --from=builder /app /app
COPY scripts/register-tools.mjs /app/scripts/register-tools.mjs
COPY entrypoint.sh /app/entrypoint.sh
RUN mkdir -p /app/config

RUN chmod +x /app/entrypoint.sh

EXPOSE 3000
ENTRYPOINT ["/app/entrypoint.sh"]

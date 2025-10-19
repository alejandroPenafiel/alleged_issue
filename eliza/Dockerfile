FROM node:20-bullseye AS builder

WORKDIR /app

RUN npm install -g bun@1.1.15

RUN git clone https://github.com/elizaOS/eliza.git . \
    && bun install

RUN bun run build || true

FROM node:20-bullseye

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app /app
COPY register-tools.mjs ./register-tools.mjs

EXPOSE 3000

CMD ["bun", "run", "start"]

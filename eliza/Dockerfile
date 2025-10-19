FROM node:20-bullseye AS builder

WORKDIR /app

RUN npm install -g bun@1.1.10

RUN git clone https://github.com/elizaOS/eliza.git . \
    && bun install

RUN bun run build

FROM node:20-slim

ENV NODE_ENV=production
WORKDIR /app

COPY --from=builder /app /app
COPY config ./config

RUN npm install -g bun@1.1.10

EXPOSE 3000

CMD ["bun", "run", "start"]

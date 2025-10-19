FROM node:20-bookworm as builder

WORKDIR /app

RUN npm install -g bun@1.1.20

ARG ELIZA_REPO=https://github.com/elizaOS/eliza.git
ARG ELIZA_REF=main

RUN git clone --depth=1 --branch="$ELIZA_REF" "$ELIZA_REPO" . \
    && bun install \
    && bun run build

FROM node:20-bookworm-slim

WORKDIR /app

COPY --from=builder /app /app

ENV NODE_ENV=production
EXPOSE 3000

CMD ["bun", "run", "start"]

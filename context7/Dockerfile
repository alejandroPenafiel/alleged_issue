FROM node:20-alpine

RUN apk add --no-cache curl

WORKDIR /app

RUN npm install -g @upstash/context7-mcp@latest

ENV CONTEXT7_HOME=/root/.context7

CMD ["context7-mcp", "--transport", "http", "--port", "7070"]

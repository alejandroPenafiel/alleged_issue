FROM node:20-alpine

RUN apk add --no-cache bash curl git

RUN npm install -g @upstash/context7-mcp@0.3.4

WORKDIR /workspace

ENTRYPOINT ["context7-mcp"]

FROM node:20-alpine

WORKDIR /workspace

RUN npm install -g @upstash/context7-mcp@0.4.0

EXPOSE 7070

CMD ["context7-mcp", "--transport", "http", "--port", "7070", "--host", "0.0.0.0"]

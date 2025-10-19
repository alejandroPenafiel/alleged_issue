import { readFile } from 'node:fs/promises';
import { setTimeout as sleep } from 'node:timers/promises';

const registryPath = process.env.MCP_ENDPOINTS_FILE ?? '/mcp/endpoints.json';
const apiUrl = process.env.ELIZA_API_URL ?? 'http://localhost:3000/api/tools';
const maxAttempts = Number(process.env.ELIZA_TOOL_ATTEMPTS ?? 10);
const attemptDelay = Number(process.env.ELIZA_TOOL_ATTEMPT_DELAY_MS ?? 3000);

async function loadRegistry() {
  const file = await readFile(registryPath, 'utf8');
  return JSON.parse(file);
}

async function registerTool(tool) {
  const body = {
    name: tool.name,
    displayName: tool.displayName ?? tool.name,
    endpoint: tool.endpoint,
    transport: tool.transport ?? 'http',
    metadata: {
      capabilities: tool.capabilities ?? [],
      health: tool.health ?? null,
    },
  };

  const response = await fetch(apiUrl, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`failed to register ${tool.name}: ${response.status} ${text}`);
  }
}

async function waitForEliza() {
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const response = await fetch(`${apiUrl}/health`);
      if (response.ok) {
        return;
      }
    } catch (error) {
      if (attempt === maxAttempts) {
        throw error;
      }
    }
    await sleep(attemptDelay);
  }
}

async function main() {
  const registry = await loadRegistry();
  if (!Array.isArray(registry) || registry.length === 0) {
    console.warn('No MCP tools discovered, skipping registration');
    return;
  }
  await waitForEliza();
  for (const tool of registry) {
    try {
      await registerTool(tool);
      console.log(`Registered MCP tool ${tool.name}`);
    } catch (error) {
      console.warn(error.message);
    }
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

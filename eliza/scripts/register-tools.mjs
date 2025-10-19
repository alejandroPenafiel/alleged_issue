import { writeFile } from "fs/promises";

const args = process.argv.slice(2);
if (args.length < 2) {
  console.error("Usage: register-tools.mjs <json-endpoints> <output-path>");
  process.exit(1);
}

const [rawEndpoints, outputPath] = args;

let endpoints;
try {
  endpoints = JSON.parse(rawEndpoints);
} catch (error) {
  console.error("Failed to parse MCP endpoint definition", error);
  process.exit(1);
}

const controller = new AbortController();
const timeout = setTimeout(() => controller.abort(), 4000);

async function probeEndpoint(endpoint) {
  try {
    const response = await fetch(endpoint.url, {
      method: "POST",
      signal: controller.signal,
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: "healthcheck",
        method: "capabilities/list",
        params: {},
      }),
    });
    if (!response.ok) {
      return { ...endpoint, status: "unreachable" };
    }
    const json = await response.json();
    return { ...endpoint, status: "ready", capabilities: json.result ?? {} };
  } catch (error) {
    return { ...endpoint, status: "unreachable", error: String(error) };
  }
}

const results = await Promise.all(endpoints.map(probeEndpoint));
clearTimeout(timeout);

const registry = {
  generatedAt: new Date().toISOString(),
  endpoints: results,
};

await writeFile(outputPath, JSON.stringify(registry, null, 2));
console.log(`[register-tools] Wrote registry to ${outputPath}`);

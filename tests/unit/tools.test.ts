/**
 * Tools Tests
 */

import { describe, it, expect } from "vitest";
import { tools, handleToolCall } from "../../src/tools/index.js";
import type { HighlightConfig } from "../../src/config.js";

const mockConfig: HighlightConfig = {
  domain: "test.casthighlight.com",
  clientId: "test-client-id",
  clientSecret: "test-secret",
  timeout: 30000,
  cacheTtl: 300,
  logLevel: "info",
};

describe("tools", () => {
  it("should export an array of tools", () => {
    expect(Array.isArray(tools)).toBe(true);
    expect(tools.length).toBeGreaterThan(0);
  });

  it("should have required properties for each tool", () => {
    for (const tool of tools) {
      expect(tool).toHaveProperty("name");
      expect(tool).toHaveProperty("description");
      expect(tool).toHaveProperty("inputSchema");
      expect(typeof tool.name).toBe("string");
      expect(typeof tool.description).toBe("string");
    }
  });

  it("should have tool names starting with highlight_", () => {
    for (const tool of tools) {
      expect(tool.name.startsWith("highlight_")).toBe(true);
    }
  });
});

describe("handleToolCall", () => {
  it("should return error for unknown tool", async () => {
    const result = await handleToolCall("unknown_tool", {}, mockConfig);

    expect(result.content).toHaveLength(1);
    expect(result.content[0]?.type).toBe("text");
    expect(result.content[0]?.text).toContain("Unknown tool");
  });
});

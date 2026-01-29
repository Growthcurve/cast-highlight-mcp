/**
 * Configuration Tests
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { loadConfig } from "../../src/config.js";

describe("loadConfig", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it("should load config from environment variables", () => {
    process.env.HIGHLIGHT_DOMAIN = "test.casthighlight.com";
    process.env.HIGHLIGHT_CLIENT_ID = "test-client-id";
    process.env.HIGHLIGHT_CLIENT_SECRET = "test-secret";

    const config = loadConfig();

    expect(config.domain).toBe("test.casthighlight.com");
    expect(config.clientId).toBe("test-client-id");
    expect(config.clientSecret).toBe("test-secret");
  });

  it("should throw error when HIGHLIGHT_DOMAIN is missing", () => {
    process.env.HIGHLIGHT_CLIENT_ID = "test-client-id";
    process.env.HIGHLIGHT_CLIENT_SECRET = "test-secret";
    delete process.env.HIGHLIGHT_DOMAIN;

    expect(() => loadConfig()).toThrow("HIGHLIGHT_DOMAIN environment variable is required");
  });

  it("should throw error when HIGHLIGHT_CLIENT_ID is missing", () => {
    process.env.HIGHLIGHT_DOMAIN = "test.casthighlight.com";
    process.env.HIGHLIGHT_CLIENT_SECRET = "test-secret";
    delete process.env.HIGHLIGHT_CLIENT_ID;

    expect(() => loadConfig()).toThrow("HIGHLIGHT_CLIENT_ID environment variable is required");
  });

  it("should throw error when HIGHLIGHT_CLIENT_SECRET is missing", () => {
    process.env.HIGHLIGHT_DOMAIN = "test.casthighlight.com";
    process.env.HIGHLIGHT_CLIENT_ID = "test-client-id";
    delete process.env.HIGHLIGHT_CLIENT_SECRET;

    expect(() => loadConfig()).toThrow("HIGHLIGHT_CLIENT_SECRET environment variable is required");
  });

  it("should use default values for optional settings", () => {
    process.env.HIGHLIGHT_DOMAIN = "test.casthighlight.com";
    process.env.HIGHLIGHT_CLIENT_ID = "test-client-id";
    process.env.HIGHLIGHT_CLIENT_SECRET = "test-secret";

    const config = loadConfig();

    expect(config.timeout).toBe(30000);
    expect(config.cacheTtl).toBe(300);
    expect(config.logLevel).toBe("info");
  });

  it("should use custom values for optional settings", () => {
    process.env.HIGHLIGHT_DOMAIN = "test.casthighlight.com";
    process.env.HIGHLIGHT_CLIENT_ID = "test-client-id";
    process.env.HIGHLIGHT_CLIENT_SECRET = "test-secret";
    process.env.HIGHLIGHT_TIMEOUT = "60000";
    process.env.HIGHLIGHT_CACHE_TTL = "600";
    process.env.LOG_LEVEL = "debug";

    const config = loadConfig();

    expect(config.timeout).toBe(60000);
    expect(config.cacheTtl).toBe(600);
    expect(config.logLevel).toBe("debug");
  });
});

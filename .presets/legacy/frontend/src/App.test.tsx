import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App", () => {
  it("renders the legacy frontend message", () => {
    const app = App();

    expect(JSON.stringify(app)).toContain("Legacy frontend bundle is mounted.");
  });
});

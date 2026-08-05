import { describe, expect, it } from "vitest";
import Home from "./page";

describe("Home", () => {
  it("renders the Next preset message", () => {
    const page = Home();

    expect(JSON.stringify(page)).toContain("Next preset is running");
  });
});

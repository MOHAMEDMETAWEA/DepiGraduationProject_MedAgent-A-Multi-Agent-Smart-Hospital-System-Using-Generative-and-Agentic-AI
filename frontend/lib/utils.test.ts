import { describe, expect, it } from "vitest";
import { cn } from "./utils";

describe("cn (className merger)", () => {
  it("merges plain class strings", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("filters out falsy values", () => {
    expect(cn("a", false, null, undefined, "b")).toBe("a b");
  });

  it("dedupes conflicting tailwind classes (last one wins)", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
    expect(cn("text-red-500", "text-blue-500")).toBe("text-blue-500");
  });

  it("preserves non-conflicting tailwind classes", () => {
    expect(cn("p-4", "m-2")).toBe("p-4 m-2");
  });

  it("supports conditional class objects via clsx", () => {
    expect(cn({ "is-active": true, "is-disabled": false })).toBe("is-active");
  });
});

import { describe, it, expect } from "vitest";
import { change, monthLabel, percent, periodLabel } from "@/lib/progress";

describe("progress helpers", () => {
  it("marks a drop as good when lower is better", () => {
    expect(change(1000, 750, true)).toEqual({
      delta: -250,
      percent: -0.25,
      tone: "good",
    });
    expect(change(4, 6, true).tone).toBe("bad");
    expect(change(100, 120, false).tone).toBe("good");
  });
  it("stays neutral without a direction or a change", () => {
    expect(change(100, 80, null).tone).toBe("neutral");
    expect(change(5, 5, true).tone).toBe("neutral");
  });
  it("has no percent from a zero starting point", () => {
    expect(change(0, 10, true).percent).toBeNull();
  });
  it("formats signed percentages", () => {
    expect(percent(0.126)).toBe("+13%");
    expect(percent(-0.25)).toBe("-25%");
  });
  it("labels periods and months without shifting dates", () => {
    expect(periodLabel("2026-08-21", "2026-09-19")).toBe(
      "Aug 21 – Sep 19, 2026",
    );
    expect(periodLabel("2025-12-20", "2026-01-18")).toBe(
      "Dec 20, 2025 – Jan 18, 2026",
    );
    expect(monthLabel("2026-09")).toBe("Sep 2026");
  });
});

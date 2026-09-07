import { describe, expect, it } from "vitest";

import {
  changeColorClass,
  formatChangeRate,
  formatKRW,
  formatSignedNumber,
  heatColor,
} from "./format";

describe("changeColorClass", () => {
  it("returns neutral color for null (N/A)", () => {
    expect(changeColorClass(null)).toBe("text-neutral-600");
  });

  it("returns red for a positive change", () => {
    expect(changeColorClass(1.5)).toBe("text-red-400");
  });

  it("returns blue for a negative change", () => {
    expect(changeColorClass(-1.5)).toBe("text-blue-400");
  });

  it("returns neutral for exactly zero", () => {
    expect(changeColorClass(0)).toBe("text-neutral-400");
  });
});

describe("formatChangeRate", () => {
  it("prefixes a plus sign for positive values", () => {
    expect(formatChangeRate(1.234)).toBe("+1.23%");
  });

  it("keeps the minus sign for negative values", () => {
    expect(formatChangeRate(-1.234)).toBe("-1.23%");
  });

  it("adds no sign for zero", () => {
    expect(formatChangeRate(0)).toBe("0.00%");
  });
});

describe("formatSignedNumber", () => {
  it("prefixes a plus sign and adds thousand separators", () => {
    expect(formatSignedNumber(1234567)).toBe("+1,234,567");
  });

  it("keeps the minus sign for negative values", () => {
    expect(formatSignedNumber(-1234567)).toBe("-1,234,567");
  });
});

describe("formatKRW", () => {
  it("returns N/A for null instead of inventing a value", () => {
    expect(formatKRW(null)).toBe("N/A");
  });

  it("formats amounts under 억 in plain won", () => {
    expect(formatKRW(5000)).toBe("5,000원");
  });

  it("formats amounts in 억 (hundred millions)", () => {
    expect(formatKRW(12_3456_7890)).toBe("12억원");
  });

  it("formats amounts in 조 (trillions)", () => {
    expect(formatKRW(1_2345_0000_0000)).toBe("1.2조원");
  });

  it("keeps the minus sign for negative amounts", () => {
    expect(formatKRW(-12_3456_7890)).toBe("-12억원");
  });
});

describe("heatColor", () => {
  it("returns a red tone for positive change rates", () => {
    expect(heatColor(2)).toMatch(/^rgba\(220, 38, 38,/);
  });

  it("returns a blue tone for negative change rates", () => {
    expect(heatColor(-2)).toMatch(/^rgba\(37, 99, 235,/);
  });

  it("returns a neutral gray for exactly zero", () => {
    expect(heatColor(0)).toBe("rgba(115, 115, 115, 0.25)");
  });

  it("caps intensity at the 5%+ change-rate ceiling", () => {
    expect(heatColor(5)).toBe(heatColor(50));
  });
});

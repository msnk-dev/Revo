import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Money } from "./Money";

describe("Money", () => {
  it("formats decimal strings without converting the amount to floating point", () => {
    render(<Money amount="123456789012345.67" currency="INR" locale="en-IN" />);
    expect(screen.getByText(/12,34,56,78,90,12,345\.67/)).toBeInTheDocument();
  });

  it("preserves the sign for negative decimal values", () => {
    render(<Money amount="-1234.50" currency="INR" locale="en-IN" />);
    expect(screen.getByText(/-.*1,234\.50/)).toBeInTheDocument();
  });
});

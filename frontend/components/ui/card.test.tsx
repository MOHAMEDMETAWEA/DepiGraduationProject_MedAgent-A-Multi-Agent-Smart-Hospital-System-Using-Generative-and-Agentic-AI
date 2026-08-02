import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Card, CardContent, CardHeader, CardTitle } from "./card";

describe("<Card />", () => {
  it("renders children inside the card slot", () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Triage result</CardTitle>
        </CardHeader>
        <CardContent>Routine</CardContent>
      </Card>,
    );
    expect(screen.getByText("Triage result")).toBeInTheDocument();
    expect(screen.getByText("Routine")).toBeInTheDocument();
  });

  it("applies size=sm variant via data attribute", () => {
    const { container } = render(
      <Card size="sm">
        <CardContent>Tight</CardContent>
      </Card>,
    );
    const card = container.querySelector('[data-slot="card"]');
    expect(card).toHaveAttribute("data-size", "sm");
  });

  it("forwards custom className alongside defaults", () => {
    const { container } = render(<Card className="custom-x">x</Card>);
    const card = container.querySelector('[data-slot="card"]');
    expect(card?.className).toMatch(/custom-x/);
    expect(card?.className).toMatch(/rounded-2xl/);
  });
});

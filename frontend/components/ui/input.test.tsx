import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Input } from "./input";

describe("<Input />", () => {
  it("accepts user typing and forwards onChange", async () => {
    const onChange = vi.fn();
    render(<Input placeholder="email" onChange={onChange} />);
    const input = screen.getByPlaceholderText("email");
    await userEvent.type(input, "abc");
    expect(onChange).toHaveBeenCalledTimes(3);
    expect((input as HTMLInputElement).value).toBe("abc");
  });

  it("respects disabled prop", () => {
    render(<Input placeholder="email" disabled />);
    expect(screen.getByPlaceholderText("email")).toBeDisabled();
  });

  it("supports type=password", () => {
    render(<Input placeholder="pw" type="password" />);
    expect(screen.getByPlaceholderText("pw")).toHaveAttribute("type", "password");
  });
});

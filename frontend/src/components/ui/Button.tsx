import { forwardRef, type ButtonHTMLAttributes } from "react";
import clsx from "clsx";
import "./Button.css";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, Props>(
  ({ variant = "primary", size = "md", loading, className, children, disabled, ...rest }, ref) => {
    return (
      <button
        ref={ref}
        className={clsx("btn", `btn-${variant}`, `btn-${size}`, loading && "btn-loading", className)}
        disabled={disabled || loading}
        {...rest}
      >
        {loading && <span className="btn-spinner" aria-hidden />}
        <span className="btn-label">{children}</span>
      </button>
    );
  },
);
Button.displayName = "Button";

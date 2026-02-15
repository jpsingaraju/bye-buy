"use client";

import { ButtonHTMLAttributes, forwardRef } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost" | "success";
  size?: "sm" | "md" | "lg";
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = "", variant = "primary", size = "md", ...props }, ref) => {
    const base =
      "inline-flex items-center justify-center font-bold neo-border neo-shadow neo-hover cursor-pointer select-none disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none";

    const variants: Record<string, string> = {
      primary: "bg-primary text-white",
      secondary: "bg-yellow text-ink",
      danger: "bg-orange text-ink",
      ghost: "bg-transparent text-ink",
      success: "bg-green text-ink",
    };

    const sizes: Record<string, string> = {
      sm: "px-3 py-1.5 text-sm",
      md: "px-5 py-2.5 text-sm",
      lg: "px-8 py-3.5 text-base",
    };

    return (
      <button
        ref={ref}
        className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
        {...props}
      />
    );
  }
);

Button.displayName = "Button";

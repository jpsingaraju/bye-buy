"use client";

import { InputHTMLAttributes, TextareaHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className = "", label, error, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="space-y-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-bold text-ink"
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={`block w-full neo-border bg-surface px-4 py-2.5 text-ink placeholder-muted focus:border-primary focus:shadow-[4px_4px_0px_var(--color-primary)] focus:outline-none transition-all ${
            error ? "border-orange" : ""
          } ${className}`}
          {...props}
        />
        {error && <p className="text-sm font-medium text-orange">{error}</p>}
      </div>
    );
  }
);
Input.displayName = "Input";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className = "", label, error, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="space-y-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-bold text-ink"
          >
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={inputId}
          className={`block w-full neo-border bg-surface px-4 py-2.5 text-ink placeholder-muted focus:border-primary focus:shadow-[4px_4px_0px_var(--color-primary)] focus:outline-none resize-none transition-all ${
            error ? "border-orange" : ""
          } ${className}`}
          {...props}
        />
        {error && <p className="text-sm font-medium text-orange">{error}</p>}
      </div>
    );
  }
);
Textarea.displayName = "Textarea";

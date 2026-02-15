"use client";

import { useEffect, useRef } from "react";
import { useInView, useMotionValue, useSpring, motion } from "framer-motion";

interface AnimatedCounterProps {
  value: number;
  format?: "currency" | "integer";
  className?: string;
  prefix?: string;
  duration?: number;
}

export function AnimatedCounter({
  value,
  format = "integer",
  className = "",
  prefix = "",
  duration = 1.5,
}: AnimatedCounterProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-50px" });

  const motionValue = useMotionValue(0);
  const springValue = useSpring(motionValue, {
    duration: duration * 1000,
    bounce: 0,
  });

  useEffect(() => {
    if (isInView) {
      motionValue.set(value);
    }
  }, [isInView, value, motionValue]);

  useEffect(() => {
    const unsubscribe = springValue.on("change", (latest) => {
      if (ref.current) {
        if (format === "currency") {
          ref.current.textContent =
            prefix + "$" + latest.toLocaleString("en-US", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            });
        } else {
          ref.current.textContent = prefix + Math.round(latest).toLocaleString();
        }
      }
    });
    return unsubscribe;
  }, [springValue, format, prefix]);

  const initial =
    format === "currency"
      ? prefix + "$0.00"
      : prefix + "0";

  return (
    <motion.span ref={ref} className={`tabular-nums ${className}`}>
      {initial}
    </motion.span>
  );
}

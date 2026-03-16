"use client";

import { useEffect, useRef, useState } from "react";
import { useInView } from "framer-motion";

interface CountUpProps {
  value: string;
  className?: string;
}

export default function CountUp({ value, className = "" }: CountUpProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-50px" });
  const [display, setDisplay] = useState("0");

  useEffect(() => {
    if (!isInView) return;

    // Extract numeric part and suffix
    const match = value.match(/^([\d.]+)(.*)$/);
    if (!match) {
      setDisplay(value);
      return;
    }

    const target = parseFloat(match[1]);
    const suffix = match[2];
    const isFloat = match[1].includes(".");
    const duration = 1500;
    const startTime = performance.now();

    const animate = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = target * eased;

      if (isFloat) {
        setDisplay(current.toFixed(1) + suffix);
      } else {
        setDisplay(Math.round(current) + suffix);
      }

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }, [isInView, value]);

  return (
    <span ref={ref} className={className}>
      {isInView ? display : "0"}
    </span>
  );
}

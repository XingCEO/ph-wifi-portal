"use client";

import { useCallback, useRef, useState } from "react";

interface CountUpProps {
  value: string;
  className?: string;
}

export default function CountUp({ value, className = "" }: CountUpProps) {
  const [display, setDisplay] = useState("0");
  const [inView, setInView] = useState(false);
  const animating = useRef(false);
  const observerRef = useRef<IntersectionObserver | null>(null);

  const callbackRef = useCallback(
    (node: HTMLSpanElement | null) => {
      if (observerRef.current) {
        observerRef.current.disconnect();
        observerRef.current = null;
      }

      if (!node) return;

      observerRef.current = new IntersectionObserver(
        ([entry]) => {
          if (!entry.isIntersecting || animating.current) return;
          animating.current = true;
          setInView(true);

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
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = target * eased;

            setDisplay(
              isFloat
                ? current.toFixed(1) + suffix
                : Math.round(current) + suffix
            );

            if (progress < 1) {
              requestAnimationFrame(animate);
            }
          };

          requestAnimationFrame(animate);
          observerRef.current?.disconnect();
        },
        { rootMargin: "-50px" }
      );

      observerRef.current.observe(node);
    },
    [value]
  );

  return (
    <span ref={callbackRef} className={className}>
      {inView ? display : "0"}
    </span>
  );
}

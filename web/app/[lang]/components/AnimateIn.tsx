"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

interface AnimateInProps {
  children: ReactNode;
  className?: string;
  delay?: number;
  direction?: "up" | "left" | "right" | "none";
  duration?: number;
}

export default function AnimateIn({
  children,
  className = "",
  delay = 0,
  direction = "up",
  duration = 0.6,
}: AnimateInProps) {
  const initial = {
    opacity: 0,
    ...(direction === "up" && { y: 30 }),
    ...(direction === "left" && { x: -30 }),
    ...(direction === "right" && { x: 30 }),
  };

  return (
    <motion.div
      initial={initial}
      whileInView={{ opacity: 1, x: 0, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{
        duration,
        delay,
        ease: [0.22, 1, 0.36, 1],
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

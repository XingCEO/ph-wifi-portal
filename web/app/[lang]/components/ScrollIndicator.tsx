"use client";

import { motion } from "framer-motion";

export default function ScrollIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 1.2, duration: 0.8 }}
      className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
    >
      <motion.div
        animate={{ y: [0, 8, 0] }}
        transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
      >
        <svg
          width="20"
          height="28"
          viewBox="0 0 20 28"
          fill="none"
          className="text-[var(--color-text-muted)]"
        >
          {/* Mouse outline */}
          <rect
            x="1"
            y="1"
            width="18"
            height="26"
            rx="9"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeOpacity="0.3"
          />
          {/* Scroll dot */}
          <motion.circle
            cx="10"
            cy="8"
            r="2"
            fill="currentColor"
            fillOpacity="0.4"
            animate={{ y: [0, 6, 0] }}
            transition={{
              duration: 1.8,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        </svg>
      </motion.div>
    </motion.div>
  );
}

import type { Variants } from "framer-motion";

export const springSmooth = {
  type: "spring",
  damping: 25,
  stiffness: 400,
} as const;

export const bounce = {
  type: "spring",
  damping: 15,
  stiffness: 300,
} as const;

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.3, ease: "easeOut" },
  },
};

export const pulseUrgent: Variants = {
  initial: { scale: 1, boxShadow: "0 0 0 0 rgba(229, 72, 77, 0.4)" },
  animate: {
    scale: [1, 1.05, 1],
    boxShadow: [
      "0 0 0 0 rgba(229, 72, 77, 0.4)",
      "0 0 0 12px rgba(229, 72, 77, 0)",
      "0 0 0 0 rgba(229, 72, 77, 0)",
    ],
    transition: {
      duration: 2,
      repeat: 2,
      repeatType: "loop" as const,
      ease: "easeInOut",
    },
  },
};

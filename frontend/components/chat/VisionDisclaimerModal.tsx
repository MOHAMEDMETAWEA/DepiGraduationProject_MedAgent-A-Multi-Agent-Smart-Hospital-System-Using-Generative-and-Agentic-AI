"use client";

import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, Shield } from "lucide-react";
import { useEffect, useState } from "react";
import { fadeUp } from "@/lib/motion";

interface Props {
  onAccept: () => void;
}

export function VisionDisclaimerModal({ onAccept }: Props) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const accepted = localStorage.getItem("medagent-vision-disclaimer");
    // Reading localStorage requires the client to be mounted; setting state
    // here is the canonical way to gate UI on a persistent client value.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (!accepted) setOpen(true);
  }, []);

  const handleAccept = () => {
    localStorage.setItem("medagent-vision-disclaimer", "true");
    setOpen(false);
    onAccept();
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
          />
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            exit="hidden"
            className="fixed inset-x-4 top-1/4 z-50 mx-auto max-w-md rounded-[2.5rem] border border-border bg-card p-6 shadow-2xl"
          >
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-urgent/10">
                <AlertTriangle className="h-5 w-5 text-urgent" />
              </div>
              <h2 className="text-lg font-bold text-foreground">Preliminary Only</h2>
            </div>

            <div className="space-y-3 text-sm leading-relaxed text-foreground">
              <p>
                <strong>This is NOT a radiology report.</strong> Image analysis is for
                preliminary triage only and does NOT replace a licensed radiologist or
                clinician review.
              </p>
              <div className="flex items-start gap-2 rounded-xl bg-muted p-3 text-xs">
                <Shield className="mt-0.5 h-4 w-4 flex-shrink-0 text-muted-foreground" />
                <span>
                  Images are processed securely. PII and faces are automatically blurred.
                  Images are deleted after analysis.
                </span>
              </div>
              <p className="font-semibold text-emergency">
                If you have a medical emergency, call 123 immediately. Do NOT wait for
                image analysis.
              </p>
            </div>

            <button
              type="button"
              onClick={handleAccept}
              className="btn-primary mt-5 w-full"
            >
              I Understand — Continue
            </button>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

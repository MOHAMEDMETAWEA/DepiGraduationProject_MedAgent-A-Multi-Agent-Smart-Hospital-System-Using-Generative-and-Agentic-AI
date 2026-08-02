"use client";

import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Ambulance, MapPin, Phone, X } from "lucide-react";
import { useEffect, useState } from "react";
import { fadeUp, pulseUrgent, springSmooth } from "@/lib/motion";

interface SOSButtonProps {
  autoOpen?: boolean;
}

const contacts = [
  { icon: Phone, label: "Emergency (Ambulance)", labelAr: "طوارئ (إسعاف)", number: "123", color: "text-emergency" },
  { icon: Ambulance, label: "Poison Control", labelAr: "مركز السموم", number: "0223651280", color: "text-urgent" },
  { icon: Phone, label: "Mental Health Crisis", labelAr: "الأزمة النفسية", number: "08008888800", color: "text-primary" },
];

export function SOSButton({ autoOpen = false }: SOSButtonProps) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    // Open the dialog when the parent toggles `autoOpen` (e.g. AI emergency).
    // External imperative trigger — must be applied through an effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (autoOpen) setOpen(true);
  }, [autoOpen]);

  const handleShareLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const url = `https://maps.google.com/?q=${pos.coords.latitude},${pos.coords.longitude}`;
          window.open(url, "_blank");
        },
        () => alert("Location access denied")
      );
    }
  };

  return (
    <>
      <motion.button
        type="button"
        onClick={() => setOpen(true)}
        variants={pulseUrgent}
        initial="initial"
        animate="animate"
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.95 }}
        className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-emergency text-white shadow-lg shadow-emergency/30"
        aria-label="Emergency SOS"
      >
        <AlertTriangle className="h-5 w-5" />
      </motion.button>

      <AnimatePresence>
        {open && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
              onClick={() => setOpen(false)}
            />
            <motion.div
              variants={fadeUp}
              initial="hidden"
              animate="visible"
              exit="hidden"
              className="fixed inset-x-4 bottom-24 z-50 mx-auto max-w-sm rounded-[2.5rem] border border-line bg-card p-6 shadow-2xl"
            >
              <div className="mb-5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-emergency" />
                  <h2 className="text-lg font-bold text-foreground">Emergency Contacts</h2>
                </div>
                <button type="button" onClick={() => setOpen(false)} className="rounded-full p-1.5 text-ink-4 hover:bg-muted">
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="space-y-3">
                {contacts.map((c) => (
                  <motion.a
                    key={c.number}
                    href={`tel:${c.number}`}
                    whileTap={{ scale: 0.97 }}
                    className="flex items-center gap-4 rounded-2xl border border-line bg-muted/50 p-3.5 transition-colors hover:border-primary/30 hover:bg-primary-tint/50"
                  >
                    <c.icon className={`h-5 w-5 ${c.color}`} />
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-foreground">{c.label}</p>
                      <p className="text-xs text-ink-3">{c.labelAr}</p>
                    </div>
                    <span className={`text-lg font-bold ${c.color} tabular-nums`}>{c.number}</span>
                  </motion.a>
                ))}
              </div>

              <motion.button
                type="button"
                onClick={handleShareLocation}
                whileTap={{ scale: 0.97 }}
                transition={springSmooth}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-2xl bg-primary-tint py-3 text-sm font-semibold text-primary transition-colors hover:bg-primary hover:text-white"
              >
                <MapPin className="h-4 w-4" />
                Share My Location
              </motion.button>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

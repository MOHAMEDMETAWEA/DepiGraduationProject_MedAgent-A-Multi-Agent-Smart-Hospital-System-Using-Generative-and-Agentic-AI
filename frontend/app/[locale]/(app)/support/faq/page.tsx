"use client";

import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, HelpCircle, MessageCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { supportApi, type FAQItem } from "@/lib/api/support";

export default function FAQPage() {
  const t = useTranslations("support");
  const [faq, setFaq] = useState<FAQItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  useEffect(() => {
    supportApi.getFAQ().then((res) => {
      if (res.data?.items) setFaq(res.data.items);
      setLoading(false);
    });
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="mx-auto max-w-3xl space-y-6 p-6"
    >
      <div>
        <h1 className="font-display text-2xl font-bold text-foreground sm:text-3xl">
          {t("faq")}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("faqSubtitle")}</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      ) : faq.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center py-16 text-center">
            <div className="grid h-16 w-16 place-items-center rounded-2xl bg-secondary">
              <HelpCircle className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="mt-5 font-semibold text-foreground">
              {t("noFaqTitle") || "No questions yet"}
            </h3>
            <p className="mt-2 max-w-xs text-sm text-muted-foreground">
              {t("noFaqDesc") || "Frequently asked questions will appear here once available."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {faq.map((item, i) => (
            <Card
              key={i}
              className="overflow-hidden transition-shadow hover:shadow-md"
            >
              <button
                onClick={() => setOpenIndex(openIndex === i ? null : i)}
                className="flex w-full items-center gap-3 p-5 text-left"
              >
                <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary/10">
                  <MessageCircle className="h-5 w-5 text-primary" />
                </div>
                <h3 className="flex-1 pr-2 text-base font-semibold text-foreground">
                  {item.q}
                </h3>
                <ChevronDown
                  className={`h-5 w-5 shrink-0 text-foreground/50 transition-transform duration-300 ${
                    openIndex === i ? "rotate-180" : ""
                  }`}
                />
              </button>
              <AnimatePresence initial={false}>
                {openIndex === i && (
                  <motion.div
                    key="answer"
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.25, ease: "easeInOut" }}
                    className="overflow-hidden"
                  >
                    <div className="border-t border-border px-5 pb-5 pt-4">
                      <div className="rounded-xl bg-muted p-4">
                        <p className="text-base leading-relaxed text-foreground">
                          {item.a}
                        </p>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </Card>
          ))}
        </div>
      )}
    </motion.div>
  );
}

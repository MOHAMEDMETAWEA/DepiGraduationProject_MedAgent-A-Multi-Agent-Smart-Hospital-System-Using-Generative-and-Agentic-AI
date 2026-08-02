"use client";

import { motion } from "framer-motion";
import { Mail, MessageSquare, Send } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { supportApi } from "@/lib/api/support";

export default function ContactPage() {
  const t = useTranslations("support");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !subject.trim() || !message.trim()) return;
    setSubmitting(true);
    setError("");
    const res = await supportApi.submitContact({ email, subject, message });
    if (res.data?.ticket_id) {
      setSubmitted(true);
    } else {
      setError(res.error || t("tryAgain"));
    }
    setSubmitting(false);
  };

  if (submitted) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex min-h-[60vh] items-center justify-center p-6"
      >
        <Card className="w-full max-w-md text-center">
          <CardContent className="py-12">
            <div className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-emerald-50 dark:bg-emerald-950">
              <Mail className="h-8 w-8 text-emerald-600" />
            </div>
            <h2 className="mt-6 font-display text-xl font-bold text-[#0a1530] dark:text-[#e7eef9]">{t("submitted")}</h2>
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6 p-6"
    >
      <div>
        <h1 className="font-display text-2xl font-bold text-[#0a1530] sm:text-3xl dark:text-[#e7eef9]">{t("contact")}</h1>
        <p className="mt-1 text-sm text-[#4a5878] dark:text-[#8b9bb6]">{t("contactSubtitle")}</p>
      </div>

      <Card className="max-w-lg">
        <CardContent className="p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-[#0a1530] dark:text-[#e7eef9]">{t("email")}</label>
              <div className="flex items-center gap-2 rounded-2xl border border-line bg-white px-4 py-2.5 dark:bg-slate-900">
                <Mail className="h-4 w-4 text-[#7c88a6] dark:text-[#5d6d8a]" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={t("emailPlaceholder")}
                  required
                  className="flex-1 bg-transparent text-sm text-[#0a1530] outline-none placeholder:text-[#7c88a6] dark:text-[#e7eef9] dark:placeholder:text-[#5d6d8a]"
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-[#0a1530] dark:text-[#e7eef9]">{t("subject")}</label>
              <div className="flex items-center gap-2 rounded-2xl border border-line bg-white px-4 py-2.5 dark:bg-slate-900">
                <MessageSquare className="h-4 w-4 text-[#7c88a6] dark:text-[#5d6d8a]" />
                <input
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder={t("subjectPlaceholder")}
                  required
                  className="flex-1 bg-transparent text-sm text-[#0a1530] outline-none placeholder:text-[#7c88a6] dark:text-[#e7eef9] dark:placeholder:text-[#5d6d8a]"
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-[#0a1530] dark:text-[#e7eef9]">{t("message")}</label>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder={t("messagePlaceholder")}
                rows={5}
                required
                className="w-full rounded-2xl border border-line bg-white p-4 text-sm text-[#0a1530] outline-none placeholder:text-[#7c88a6] focus:border-primary dark:bg-slate-900 dark:text-[#e7eef9] dark:placeholder:text-[#5d6d8a]"
              />
            </div>

            {error && (
              <p className="rounded-xl bg-red-50 p-3 text-sm font-medium text-red-700 dark:bg-red-950 dark:text-red-300">{error}</p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-60"
            >
              {submitting ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              {t("submit")}
            </button>
          </form>
        </CardContent>
      </Card>
    </motion.div>
  );
}

"use client";

import { handoffApi, doctorApi, type DoctorPublic } from "@/lib/api/handoff";
import { Check, Loader2, Search, Send, Stethoscope, X, Languages } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";

type Step = "idle" | "generating" | "searching" | "sending" | "sent" | "error";

type Props = {
  conversationId: string;
  open: boolean;
  onClose: () => void;
};

const SPECIALTIES = [
  "General Practice",
  "Cardiology",
  "Dermatology",
  "Neurology",
  "Orthopedics",
  "Pediatrics",
  "Psychiatry",
  "Obstetrics & Gynecology",
  "Ophthalmology",
  "ENT",
  "Gastroenterology",
  "Pulmonology",
  "Endocrinology",
  "Urology",
  "Rheumatology",
];

export function DoctorSearchDialog({ conversationId, open, onClose }: Props) {
  const t = useTranslations("handoff");
  const [step, setStep] = useState<Step>("idle");
  const [error, setError] = useState("");
  const [handoffId, setHandoffId] = useState<string | null>(null);
  const [doctors, setDoctors] = useState<DoctorPublic[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [specialty, setSpecialty] = useState("");
  const [selectedDoctor, setSelectedDoctor] = useState<DoctorPublic | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef(false);

  // Reset state when dialog opens.
  // The dialog's lifecycle is driven by the parent's `open` prop, so resetting
  // the internal multi-step state on each open requires an effect.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (open) {
      abortRef.current = false;
      setStep("generating");
      setError("");
      setHandoffId(null);
      setSelectedDoctor(null);
      setMessage("");
      setDoctors([]);
      setSearch("");
      setSpecialty("");
      setPage(1);
      handoffApi.generate(conversationId).then((res) => {
        if (abortRef.current) return;
        if (res.error) {
          setError(res.error);
          setStep("error");
          return;
        }
        setHandoffId(res.data!.id);
        setStep("searching");
      });
      setTimeout(() => searchInputRef.current?.focus(), 100);
    }
  }, [open, conversationId]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const loadDoctors = useCallback(
    async (searchTerm?: string, spec?: string, p = 1) => {
      setLoading(true);
      const res = await doctorApi.search(searchTerm || search, spec || specialty, p);
      if (abortRef.current) return;
      if (res.error) {
        setError(res.error);
        setStep("error");
        return;
      }
      setDoctors(res.data!.items);
      setTotal(res.data!.total);
      setLoading(false);
    },
    [search, specialty]
  );

  useEffect(() => {
    if (step === "searching") {
      const t = setTimeout(() => loadDoctors(search, specialty, page), 300);
      return () => clearTimeout(t);
    }
  }, [search, specialty, page, step, loadDoctors]);

  const handleSend = async () => {
    if (!selectedDoctor || !handoffId) return;
    setStep("sending");
    const res = await handoffApi.send(handoffId, selectedDoctor.user_id, message || undefined);
    if (abortRef.current) return;
    if (res.error) {
      setError(res.error);
      setStep("error");
      return;
    }
    setStep("sent");
  };

  const handleClose = () => {
    abortRef.current = true;
    onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-lg rounded-2xl bg-card border border-border shadow-xl p-6 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Stethoscope className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold text-foreground">{t("dialogTitle")}</h2>
          </div>
          <button onClick={handleClose} className="p-1 rounded-lg hover:bg-muted transition-colors">
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        </div>

        {/* Step: Generating */}
        {step === "generating" && (
          <div className="flex flex-col items-center justify-center py-12 gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">{t("generating")}</p>
          </div>
        )}

        {/* Step: Error */}
        {step === "error" && (
          <div className="flex flex-col items-center justify-center py-8 gap-3">
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            <button
              onClick={handleClose}
              className="btn-secondary text-xs px-4 py-2 rounded-lg"
            >
              {t("close")}
            </button>
          </div>
        )}

        {/* Step: Searching / Select doctor */}
        {(step === "searching" || step === "sending") && (
          <div className="flex-1 flex flex-col min-h-0">
            {/* Filters */}
            <div className="flex items-center gap-2 mb-3">
              <div className="relative flex-1">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                <input
                  ref={searchInputRef}
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                  placeholder={t("searchPlaceholder")}
                  className="w-full rounded-lg border border-border bg-muted/50 pl-8 pr-3 py-2 text-xs outline-none focus:border-primary/40"
                  disabled={step === "sending"}
                />
              </div>
              <select
                value={specialty}
                onChange={(e) => { setSpecialty(e.target.value); setPage(1); }}
                className="rounded-lg border border-border bg-muted/50 px-2 py-2 text-xs outline-none focus:border-primary/40"
                disabled={step === "sending"}
              >
                <option value="">{t("allSpecialties")}</option>
                {SPECIALTIES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            {/* Doctor list */}
            <div className="flex-1 overflow-y-auto -mx-1 px-1 min-h-0">
              {loading && doctors.length === 0 ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                </div>
              ) : doctors.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-8">
                  {t("noDoctors")}{search ? ` "${search}"` : ""}.
                </p>
              ) : (
                doctors.map((doc) => {
                  const isSelected = selectedDoctor?.user_id === doc.user_id;
                  return (
                    <button
                      key={doc.user_id}
                      onClick={() => setSelectedDoctor(doc)}
                      disabled={step === "sending"}
                      className={`flex items-center gap-3 w-full text-left px-3 py-2.5 rounded-xl transition-colors mb-1 ${
                        isSelected
                          ? "bg-primary/10 border border-primary/30"
                          : "hover:bg-muted/50 border border-transparent"
                      }`}
                    >
                      <div className="grid place-items-center w-5 h-5 rounded-full border flex-shrink-0 transition-colors"
                        style={isSelected ? { backgroundColor: "var(--color-primary)", borderColor: "var(--color-primary)" } : {}}>
                        {isSelected && <Check className="h-3 w-3 text-primary-foreground" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground truncate">{doc.full_name}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-xs text-muted-foreground">{doc.specialty}</span>
                          {doc.years_of_experience != null && (
                            <span className="text-[10px] text-muted-foreground/70">· {doc.years_of_experience}y exp</span>
                          )}
                          {doc.languages?.length > 0 && (
                            <span className="inline-flex items-center gap-0.5 text-[10px] text-muted-foreground/70">
                              <Languages className="h-2.5 w-2.5" />
                              {doc.languages.join(", ")}
                            </span>
                          )}
                        </div>
                      </div>
                    </button>
                  );
                })
              )}
            </div>

            {/* Pagination */}
            {total > 20 && (
              <div className="flex items-center justify-between mt-2 text-xs">
                <span className="text-muted-foreground">{t("doctors", { count: total })}</span>
                <div className="flex gap-1">
                  <button disabled={page <= 1 || step === "sending"} onClick={() => setPage(page - 1)}
                    className="px-2 py-1 rounded hover:bg-muted disabled:opacity-30">{t("prev")}</button>
                  <button disabled={page * 20 >= total || step === "sending"} onClick={() => setPage(page + 1)}
                    className="px-2 py-1 rounded hover:bg-muted disabled:opacity-30">{t("next")}</button>
                </div>
              </div>
            )}

            {/* Optional message */}
            {selectedDoctor && (
              <div className="mt-3">
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                      placeholder={t("messagePlaceholder")}
                  rows={2}
                  className="w-full rounded-lg border border-border bg-muted/50 px-3 py-2 text-xs outline-none focus:border-primary/40 resize-none"
                  disabled={step === "sending"}
                />
              </div>
            )}

            {/* Send button */}
            <button
              onClick={handleSend}
              disabled={!selectedDoctor || step === "sending"}
              className="flex items-center justify-center gap-2 w-full mt-3 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-medium disabled:opacity-30 hover:opacity-90 transition-all"
            >
              {step === "sending" ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t("sending")}
                </>
              ) : selectedDoctor ? (
                <>
                  <Send className="h-4 w-4" />
                  {t("sendTo", { name: selectedDoctor.full_name })}
                </>
              ) : (
                <>
                  <Send className="h-4 w-4" />
                  Select a doctor
                </>
              )}
            </button>
          </div>
        )}

        {/* Step: Sent */}
        {step === "sent" && (
          <div className="flex flex-col items-center justify-center py-10 gap-3">
            <div className="grid place-items-center w-14 h-14 rounded-full bg-emerald-100 dark:bg-emerald-950">
              <Check className="h-7 w-7 text-emerald-600 dark:text-emerald-400" />
            </div>
            <h3 className="text-base font-semibold text-foreground">{t("sent")}</h3>
            <p className="text-sm text-muted-foreground text-center max-w-xs">
              {t("sentMessage", { name: selectedDoctor?.full_name || "" })}
            </p>
            <button
              onClick={handleClose}
              className="btn-primary text-xs px-6 py-2 rounded-xl mt-2"
            >
              {t("done")}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

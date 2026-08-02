"use client";

import { chatApi, type Conversation } from "@/lib/api/chat";
import { useRouter } from "@/src/i18n/navigation";
import { MessageSquare, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

const triageColors: Record<string, string> = {
  emergency: "bg-red-100 text-red-700",
  urgent: "bg-orange-100 text-orange-700",
  routine: "bg-emerald-100 text-emerald-700",
};

const statusColors: Record<string, string> = {
  active: "bg-blue-100 text-blue-700",
  completed: "bg-emerald-100 text-emerald-700",
  flagged_for_review: "bg-red-100 text-red-700",
  deleted: "bg-slate-100 text-slate-500",
};

export default function HistoryPage() {
  const router = useRouter();
  const [convs, setConvs] = useState<Conversation[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("");

  const loadConvs = useCallback(async (p: number) => {
    setLoading(true);
    const res = await chatApi.listConversations(p, statusFilter || undefined);
    if (res.data) {
      setConvs(res.data.items);
      setTotal(res.data.total);
    }
    setLoading(false);
  }, [statusFilter]);

  // Data fetch on page change. `loadConvs` calls setLoading/setConvs/setError
  // internally; the rule flags any function call from an effect that mutates
  // state — but this is the canonical data-fetching pattern.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    loadConvs(page);
  }, [page, loadConvs]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this conversation?")) return;
    await chatApi.deleteConversation(id);
    loadConvs(page);
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl font-bold">Conversations</h1>
          <p className="text-sm text-ink-3 mt-1">{total} total</p>
        </div>
        <button
          onClick={() => router.push("/chat")}
          className="btn-primary inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white no-underline"
        >
          <MessageSquare className="h-4 w-4" />
          New Chat
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-6">
        {["", "active", "completed", "flagged_for_review"].map((s) => (
          <button
            key={s || "all"}
            onClick={() => { setStatusFilter(s); setPage(1); }}
            className={`px-3.5 py-1.5 rounded-full text-[13px] font-medium transition-colors ${
              statusFilter === s ? "bg-primary text-white" : "bg-base-2 text-ink-3 hover:bg-line"
            }`}
          >
            {s === "" ? "All" : s.replace(/_/g, " ")}
          </button>
        ))}
      </div>

      {/* List */}
      {loading ? (
        <div className="text-center py-20 text-ink-3">Loading...</div>
      ) : convs.length === 0 ? (
        <div className="text-center py-20">
          <MessageSquare className="h-12 w-12 text-ink-4 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-ink-2">No conversations</h3>
          <p className="text-sm text-ink-3 mt-1">Start a new chat to begin.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {convs.map((c) => (
            <div
              key={c.id}
              onClick={() => router.push(`/chat/${c.id}`)}
              className="flex items-center justify-between p-4 rounded-2xl bg-white border border-line hover:border-primary-3 hover:shadow-1 transition-all cursor-pointer"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-semibold text-ink-2 truncate">
                    {c.title || "New conversation"}
                  </h3>
                  {c.triage_level && (
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${triageColors[c.triage_level] || ""}`}>
                      {c.triage_level}
                    </span>
                  )}
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${statusColors[c.status] || ""}`}>
                    {c.status}
                  </span>
                </div>
                {c.last_message && (
                  <p className="text-sm text-ink-3 truncate">{c.last_message}</p>
                )}
                <p className="text-xs text-ink-4 mt-1">
                  {new Date(c.created_at).toLocaleDateString()} · {c.message_count} messages
                </p>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); handleDelete(c.id); }}
                className="p-2 rounded-lg hover:bg-red-50 text-ink-4 hover:text-red-600 transition-colors"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}

          {/* Pagination */}
          {total > 20 && (
            <div className="flex justify-center gap-2 pt-4">
              <button
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
                className="px-4 py-2 rounded-full text-sm font-medium bg-base-2 text-ink-3 disabled:opacity-40"
              >
                Previous
              </button>
              <button
                disabled={page * 20 >= total}
                onClick={() => setPage(page + 1)}
                className="px-4 py-2 rounded-full text-sm font-medium bg-base-2 text-ink-3 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

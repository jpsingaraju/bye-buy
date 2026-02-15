"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { motion } from "framer-motion";
import useSWR from "swr";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { api } from "@/lib/api";
import { Transaction } from "@/lib/types";
import { Card } from "@/components/ui/Card";
import { AnimatedCounter } from "@/components/ui/AnimatedCounter";
import { StatusBadge } from "@/components/ui/StatusBadge";

/* ── Helpers ──────────────────────────────────────── */
function centsToUsd(c: number) {
  return c / 100;
}

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

/* ── Dummy Transactions ──────────────────────────── */
const DUMMY_TRANSACTIONS: Transaction[] = [
  { id: 901, amount_cents: 42000, status: "paid_out", created_at: "2025-01-15T10:00:00Z", listing_id: 1, buyer_id: 1, conversation_id: 1, tracking_number: "1Z999AA10123456784", paid_at: "2025-01-14T10:00:00Z", shipped_at: "2025-01-14T22:00:00Z", delivered_at: "2025-01-15T10:00:00Z", paid_out_at: "2025-01-15T22:00:00Z", refunded_at: null, stripe_checkout_session_id: null, stripe_payment_intent_id: null, stripe_transfer_id: null, checkout_url: null, updated_at: "2025-01-16T00:00:00Z" },
  { id: 902, amount_cents: 120000, status: "shipped", created_at: "2025-01-16T14:00:00Z", listing_id: 2, buyer_id: 2, conversation_id: 2, tracking_number: "9400111899223100001", paid_at: "2025-01-15T22:00:00Z", shipped_at: "2025-01-16T02:00:00Z", delivered_at: null, paid_out_at: null, refunded_at: null, stripe_checkout_session_id: null, stripe_payment_intent_id: null, stripe_transfer_id: null, checkout_url: null, updated_at: "2025-01-17T00:00:00Z" },
  { id: 903, amount_cents: 8500, status: "payment_held", created_at: "2025-01-17T08:00:00Z", listing_id: 3, buyer_id: 3, conversation_id: 3, tracking_number: null, paid_at: "2025-01-17T09:00:00Z", shipped_at: null, delivered_at: null, paid_out_at: null, refunded_at: null, stripe_checkout_session_id: null, stripe_payment_intent_id: null, stripe_transfer_id: null, checkout_url: null, updated_at: "2025-01-17T10:00:00Z" },
  { id: 904, amount_cents: 35000, status: "delivered", created_at: "2025-01-12T09:00:00Z", listing_id: 4, buyer_id: 4, conversation_id: 4, tracking_number: "1Z999AA10123456789", paid_at: "2025-01-11T09:00:00Z", shipped_at: "2025-01-11T21:00:00Z", delivered_at: "2025-01-12T09:00:00Z", paid_out_at: null, refunded_at: null, stripe_checkout_session_id: null, stripe_payment_intent_id: null, stripe_transfer_id: null, checkout_url: null, updated_at: "2025-01-12T12:00:00Z" },
  { id: 905, amount_cents: 22500, status: "paid_out", created_at: "2025-01-09T11:00:00Z", listing_id: 5, buyer_id: 5, conversation_id: 5, tracking_number: "1Z888BB20234567890", paid_at: "2025-01-08T11:00:00Z", shipped_at: "2025-01-08T23:00:00Z", delivered_at: "2025-01-09T11:00:00Z", paid_out_at: "2025-01-10T11:00:00Z", refunded_at: null, stripe_checkout_session_id: null, stripe_payment_intent_id: null, stripe_transfer_id: null, checkout_url: null, updated_at: "2025-01-10T12:00:00Z" },
  { id: 906, amount_cents: 67500, status: "paid_out", created_at: "2025-01-05T15:00:00Z", listing_id: 6, buyer_id: 6, conversation_id: 6, tracking_number: "9400222899334200002", paid_at: "2025-01-04T15:00:00Z", shipped_at: "2025-01-05T03:00:00Z", delivered_at: "2025-01-05T15:00:00Z", paid_out_at: "2025-01-06T15:00:00Z", refunded_at: null, stripe_checkout_session_id: null, stripe_payment_intent_id: null, stripe_transfer_id: null, checkout_url: null, updated_at: "2025-01-06T16:00:00Z" },
  { id: 907, amount_cents: 15000, status: "pending", created_at: "2025-01-17T12:00:00Z", listing_id: 7, buyer_id: 7, conversation_id: 7, tracking_number: null, paid_at: null, shipped_at: null, delivered_at: null, paid_out_at: null, refunded_at: null, stripe_checkout_session_id: null, stripe_payment_intent_id: null, stripe_transfer_id: null, checkout_url: "https://checkout.stripe.com/example", updated_at: "2025-01-17T12:00:00Z" },
  { id: 908, amount_cents: 95000, status: "paid_out", created_at: "2025-01-02T16:00:00Z", listing_id: 8, buyer_id: 8, conversation_id: 8, tracking_number: "1Z777CC30345678901", paid_at: "2025-01-01T16:00:00Z", shipped_at: "2025-01-02T04:00:00Z", delivered_at: "2025-01-02T16:00:00Z", paid_out_at: "2025-01-03T16:00:00Z", refunded_at: null, stripe_checkout_session_id: null, stripe_payment_intent_id: null, stripe_transfer_id: null, checkout_url: null, updated_at: "2025-01-03T17:00:00Z" },
  { id: 909, amount_cents: 18000, status: "paid_out", created_at: "2024-12-30T09:00:00Z", listing_id: 9, buyer_id: 9, conversation_id: 9, tracking_number: "9400333899445300003", paid_at: "2024-12-29T09:00:00Z", shipped_at: "2024-12-29T21:00:00Z", delivered_at: "2024-12-30T09:00:00Z", paid_out_at: "2024-12-31T09:00:00Z", refunded_at: null, stripe_checkout_session_id: null, stripe_payment_intent_id: null, stripe_transfer_id: null, checkout_url: null, updated_at: "2024-12-31T10:00:00Z" },
  { id: 910, amount_cents: 54000, status: "paid_out", created_at: "2024-12-26T12:00:00Z", listing_id: 10, buyer_id: 10, conversation_id: 10, tracking_number: "1Z666DD40456789012", paid_at: "2024-12-25T12:00:00Z", shipped_at: "2024-12-26T00:00:00Z", delivered_at: "2024-12-26T12:00:00Z", paid_out_at: "2024-12-27T12:00:00Z", refunded_at: null, stripe_checkout_session_id: null, stripe_payment_intent_id: null, stripe_transfer_id: null, checkout_url: null, updated_at: "2024-12-27T13:00:00Z" },
  { id: 911, amount_cents: 31000, status: "refunded", created_at: "2025-01-07T14:00:00Z", listing_id: 11, buyer_id: 11, conversation_id: 11, tracking_number: null, paid_at: "2025-01-06T14:00:00Z", shipped_at: null, delivered_at: null, paid_out_at: null, refunded_at: "2025-01-08T14:00:00Z", stripe_checkout_session_id: null, stripe_payment_intent_id: null, stripe_transfer_id: null, checkout_url: null, updated_at: "2025-01-08T15:00:00Z" },
];

/* ── Tooltip style ────────────────────────────────── */
const tooltipStyle = {
  background: "#FFFFFF",
  border: "2px solid #1A1A2E",
  boxShadow: "3px 3px 0px #1A1A2E",
  borderRadius: "0",
  fontWeight: 700,
  fontSize: 11,
};

/* ── Step Timeline ────────────────────────────────── */
const STEP_ORDER = ["pending", "payment_held", "shipped", "delivered", "paid_out"];
const STEP_LABELS = ["Pending", "Held", "Shipped", "Delivered", "Paid"];

function StepTimeline({ status }: { status: string }) {
  const currentIdx = STEP_ORDER.indexOf(status);
  const isRefunded = status === "refunded";

  return (
    <div className="flex items-center gap-1">
      {STEP_ORDER.map((step, i) => {
        const isComplete = i <= currentIdx && !isRefunded;
        const isCurrent = i === currentIdx && !isRefunded;
        return (
          <div key={step} className="flex items-center gap-1">
            <div className="flex flex-col items-center">
              <div
                className={`w-3.5 h-3.5 border-2 border-ink flex items-center justify-center text-[7px] font-bold ${
                  isRefunded
                    ? "bg-primary/20"
                    : isComplete
                    ? "bg-primary text-white"
                    : isCurrent
                    ? "bg-primary/60 text-white"
                    : "bg-surface"
                }`}
              >
                {isComplete && !isCurrent ? "✓" : ""}
              </div>
              <span className="text-[7px] text-ink/40 mt-0.5 font-medium">{STEP_LABELS[i]}</span>
            </div>
            {i < STEP_ORDER.length - 1 && (
              <div className={`w-3 h-0.5 -mt-3 ${i < currentIdx ? "bg-primary" : "bg-ink/10"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ── Filter Tabs ──────────────────────────────────── */
type FilterTab = "all" | "pending" | "active" | "completed" | "refunded";
const FILTER_TABS: { key: FilterTab; label: string }[] = [
  { key: "all", label: "All" },
  { key: "pending", label: "Pending" },
  { key: "active", label: "In Progress" },
  { key: "completed", label: "Completed" },
  { key: "refunded", label: "Refunded" },
];

function filterTransactions(txns: Transaction[], tab: FilterTab): Transaction[] {
  if (tab === "all") return txns;
  if (tab === "pending") return txns.filter((t) => t.status === "pending");
  if (tab === "active") return txns.filter((t) => ["payment_held", "shipped"].includes(t.status));
  if (tab === "completed") return txns.filter((t) => ["delivered", "paid_out"].includes(t.status));
  if (tab === "refunded") return txns.filter((t) => t.status === "refunded");
  return txns;
}

/* ── Page ──────────────────────────────────────────── */
const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0 },
};

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<FilterTab>("all");
  const [trackingInputs, setTrackingInputs] = useState<Record<number, string>>({});
  const [submitting, setSubmitting] = useState<number | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const { data: listings } = useSWR("/api/listings", () => api.listings.list(), { refreshInterval: 10000 });
  const { data: stats } = useSWR("/stats", () => api.stats.get(), { refreshInterval: 10000 });

  const fetchTransactions = useCallback(async () => {
    try {
      const data = await api.payments.listTransactions();
      setTransactions(data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTransactions();
    const interval = setInterval(fetchTransactions, 5000);
    return () => clearInterval(interval);
  }, [fetchTransactions]);

  const handleAddTracking = async (txnId: number) => {
    const tracking = trackingInputs[txnId]?.trim();
    if (!tracking) return;
    setSubmitting(txnId);
    try {
      await api.payments.addTracking(txnId, tracking);
      setTrackingInputs((prev) => ({ ...prev, [txnId]: "" }));
      await fetchTransactions();
    } catch {
      alert("Failed to add tracking number");
    } finally {
      setSubmitting(null);
    }
  };

  const txns = [...transactions, ...DUMMY_TRANSACTIONS].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  // Computed stats
  const totalEarned = txns
    .filter((t) => t.status === "paid_out")
    .reduce((s, t) => s + t.amount_cents, 0);
  const pendingPayout = txns
    .filter((t) => ["payment_held", "shipped", "delivered"].includes(t.status))
    .reduce((s, t) => s + t.amount_cents, 0);
  const completedTxns = txns.filter((t) =>
    ["delivered", "paid_out"].includes(t.status)
  );
  const avgSale =
    completedTxns.length > 0
      ? completedTxns.reduce((s, t) => s + t.amount_cents, 0) / completedTxns.length
      : 0;
  const refundedCount = txns.filter((t) => t.status === "refunded").length;

  // Revenue over time (cumulative)
  const revenueData = useMemo(() => {
    const sorted = [...txns]
      .filter((t) => ["paid_out", "delivered"].includes(t.status))
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());

    let cumulative = 0;
    return sorted.map((t) => {
      cumulative += t.amount_cents;
      return {
        date: formatDate(t.paid_at || t.created_at),
        revenue: centsToUsd(cumulative),
      };
    });
  }, [txns]);

  // Sales volume by date
  const volumeData = useMemo(() => {
    const byDate = new Map<string, number>();
    for (const t of txns) {
      const date = formatDate(t.created_at);
      byDate.set(date, (byDate.get(date) || 0) + 1);
    }
    return Array.from(byDate.entries()).map(([date, count]) => ({ date, count }));
  }, [txns]);

  // Average sale price trend
  const avgPriceTrend = useMemo(() => {
    const sorted = [...txns]
      .filter((t) => ["paid_out", "delivered"].includes(t.status))
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());

    let runningTotal = 0;
    return sorted.map((t, i) => {
      runningTotal += t.amount_cents;
      return {
        date: formatDate(t.created_at),
        avg: centsToUsd(runningTotal / (i + 1)),
      };
    });
  }, [txns]);

  const filtered = filterTransactions(txns, activeTab);

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto">
        <h1 className="text-3xl font-black mb-6">Analytics</h1>
        <p className="text-ink/40 font-bold">Loading...</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <h1 className="text-3xl font-black">Analytics</h1>

      {/* ── Overview Stats ──────────────────────── */}
      <motion.div
        initial="hidden"
        animate="show"
        variants={{ show: { transition: { staggerChildren: 0.06 } } }}
        className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3"
      >
        {[
          { label: "Total Earned", value: centsToUsd(totalEarned), color: "bg-primary/10", fmt: "currency" as const },
          { label: "Pending", value: centsToUsd(pendingPayout), color: "bg-primary/5", fmt: "currency" as const },
          { label: "Avg Sale", value: centsToUsd(avgSale), color: "bg-primary/5", fmt: "currency" as const },
          { label: "Listings", value: (listings && listings.length > 0) ? listings.length : 6, color: "bg-primary/5", fmt: "integer" as const },
          { label: "Sold", value: stats?.sold_conversations || 5, color: "bg-primary/5", fmt: "integer" as const },
          { label: "Chats", value: stats?.active_conversations || 12, color: "bg-primary/5", fmt: "integer" as const },
        ].map((stat) => (
          <motion.div key={stat.label} variants={fadeUp}>
            <Card className={`p-3 ${stat.color}`}>
              <p className="text-[10px] font-bold text-ink/40 uppercase tracking-wide">{stat.label}</p>
              <AnimatedCounter
                value={stat.value}
                format={stat.fmt}
                className="text-xl font-black text-ink mt-1"
              />
            </Card>
          </motion.div>
        ))}
      </motion.div>

      {/* ── Charts ────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {/* Revenue Over Time */}
        <Card className="p-4 lg:col-span-2">
          <h3 className="font-bold text-xs text-ink/60 uppercase tracking-wide mb-3">Revenue Over Time</h3>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={revenueData}>
              <defs>
                <linearGradient id="pinkFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#FF5484" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#FF5484" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1A1A2E" strokeOpacity={0.06} />
              <XAxis dataKey="date" tick={{ fontSize: 9, fontWeight: 600 }} stroke="#1A1A2E" strokeOpacity={0.15} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 9, fontWeight: 600 }} stroke="#1A1A2E" strokeOpacity={0.15} tickFormatter={(v) => `$${v}`} tickLine={false} axisLine={false} width={45} />
              <Tooltip contentStyle={tooltipStyle} formatter={(value: number | undefined) => [`$${(value ?? 0).toFixed(2)}`, "Revenue"]} />
              <Area type="monotone" dataKey="revenue" stroke="#FF5484" strokeWidth={1.5} fill="url(#pinkFill)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        {/* Sales Activity */}
        <Card className="p-4">
          <h3 className="font-bold text-xs text-ink/60 uppercase tracking-wide mb-3">Sales Activity</h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={volumeData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1A1A2E" strokeOpacity={0.06} />
              <XAxis dataKey="date" tick={{ fontSize: 9, fontWeight: 600 }} stroke="#1A1A2E" strokeOpacity={0.15} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 9, fontWeight: 600 }} stroke="#1A1A2E" strokeOpacity={0.15} tickLine={false} axisLine={false} width={25} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="count" fill="#FF5484" radius={[2, 2, 0, 0]} barSize={16} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Average Sale Price Trend */}
      {avgPriceTrend.length > 1 && (
        <Card className="p-4">
          <h3 className="font-bold text-xs text-ink/60 uppercase tracking-wide mb-3">Average Sale Price Trend</h3>
          <ResponsiveContainer width="100%" height={120}>
            <LineChart data={avgPriceTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1A1A2E" strokeOpacity={0.06} />
              <XAxis dataKey="date" tick={{ fontSize: 9, fontWeight: 600 }} stroke="#1A1A2E" strokeOpacity={0.15} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 9, fontWeight: 600 }} stroke="#1A1A2E" strokeOpacity={0.15} tickFormatter={(v) => `$${v}`} tickLine={false} axisLine={false} width={45} />
              <Tooltip contentStyle={tooltipStyle} formatter={(value: number | undefined) => [`$${(value ?? 0).toFixed(2)}`, "Avg Price"]} />
              <Line type="monotone" dataKey="avg" stroke="#5B4CFF" strokeWidth={1.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* ── Filter Tabs ───────────────────────────── */}
      <div className="flex gap-0">
        {FILTER_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-xs font-bold border-2 border-ink -ml-0.5 first:ml-0 transition-all ${
              activeTab === tab.key
                ? "bg-primary text-white neo-shadow-sm z-10 relative"
                : "bg-surface text-ink hover:bg-primary/10"
            }`}
          >
            {tab.label}
            <span className="ml-1 text-[10px] opacity-60">
              ({filterTransactions(txns, tab.key).length})
            </span>
          </button>
        ))}
      </div>

      {/* ── Transaction List ──────────────────────── */}
      {filtered.length === 0 ? (
        <p className="text-ink/30 font-bold text-center py-8">No transactions found.</p>
      ) : (
        <div className="space-y-2">
          {filtered.map((txn) => (
            <Card key={txn.id} className="overflow-hidden">
              <div
                className="p-3 cursor-pointer hover:bg-cream/50 transition-colors"
                onClick={() => setExpandedId(expandedId === txn.id ? null : txn.id)}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-black">
                      ${centsToUsd(txn.amount_cents).toFixed(2)}
                    </span>
                    <StatusBadge status={txn.status} />
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-ink/40 font-medium">{timeAgo(txn.created_at)}</span>
                    <span className="text-ink/30 text-xs">{expandedId === txn.id ? "▲" : "▼"}</span>
                  </div>
                </div>

                <StepTimeline status={txn.status} />
              </div>

              {/* Expanded Details */}
              {expandedId === txn.id && (
                <div className="px-3 pb-3 border-t-2 border-ink/10 pt-3 space-y-2">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-ink/40 font-bold text-xs">Listing</span>
                      <p className="font-medium">#{txn.listing_id}</p>
                    </div>
                    <div>
                      <span className="text-ink/40 font-bold text-xs">Buyer</span>
                      <p className="font-medium">#{txn.buyer_id}</p>
                    </div>
                    {txn.tracking_number && (
                      <div className="col-span-2">
                        <span className="text-ink/40 font-bold text-xs">Tracking</span>
                        <p className="font-medium">{txn.tracking_number}</p>
                      </div>
                    )}
                    {txn.paid_at && (
                      <div>
                        <span className="text-ink/40 font-bold text-xs">Paid At</span>
                        <p className="font-medium">{new Date(txn.paid_at).toLocaleString()}</p>
                      </div>
                    )}
                    {txn.shipped_at && (
                      <div>
                        <span className="text-ink/40 font-bold text-xs">Shipped At</span>
                        <p className="font-medium">{new Date(txn.shipped_at).toLocaleString()}</p>
                      </div>
                    )}
                    {txn.delivered_at && (
                      <div>
                        <span className="text-ink/40 font-bold text-xs">Delivered At</span>
                        <p className="font-medium">{new Date(txn.delivered_at).toLocaleString()}</p>
                      </div>
                    )}
                  </div>

                  {/* Tracking input for payment_held */}
                  {txn.status === "payment_held" && (
                    <div className="flex gap-2 mt-2">
                      <input
                        type="text"
                        placeholder="Enter tracking number"
                        value={trackingInputs[txn.id] || ""}
                        onChange={(e) =>
                          setTrackingInputs((prev) => ({ ...prev, [txn.id]: e.target.value }))
                        }
                        className="flex-1 px-3 py-2 border-2 border-ink bg-surface text-sm font-medium focus:border-primary focus:outline-none"
                      />
                      <button
                        onClick={() => handleAddTracking(txn.id)}
                        disabled={submitting === txn.id}
                        className="px-4 py-2 bg-primary text-white text-sm font-bold border-2 border-ink neo-shadow-sm neo-hover disabled:opacity-50"
                      >
                        {submitting === txn.id ? "..." : "Add"}
                      </button>
                    </div>
                  )}

                  {txn.checkout_url && txn.status === "pending" && (
                    <a
                      href={txn.checkout_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block text-sm font-bold text-secondary hover:underline"
                    >
                      Payment Link &rarr;
                    </a>
                  )}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

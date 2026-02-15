"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Transaction } from "@/lib/types";

const STATUS_BADGES: Record<string, { label: string; color: string }> = {
  pending: { label: "Pending Payment", color: "bg-yellow-100 text-yellow-800" },
  payment_held: { label: "Payment Held", color: "bg-blue-100 text-blue-800" },
  shipped: { label: "Shipped", color: "bg-purple-100 text-purple-800" },
  delivered: { label: "Delivered", color: "bg-green-100 text-green-800" },
  paid_out: { label: "Paid Out", color: "bg-green-200 text-green-900" },
  refunded: { label: "Refunded", color: "bg-red-100 text-red-800" },
};

function formatCents(cents: number) {
  return `$${(cents / 100).toFixed(2)}`;
}

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [trackingInputs, setTrackingInputs] = useState<Record<number, string>>({});
  const [submitting, setSubmitting] = useState<number | null>(null);

  const fetchTransactions = useCallback(async () => {
    try {
      const data = await api.payments.listTransactions();
      setTransactions(data);
    } catch {
      // silent fail on poll
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

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <h1 className="text-2xl font-bold mb-6">Transactions</h1>
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Transactions</h1>

      {transactions.length === 0 ? (
        <p className="text-gray-500">No transactions yet.</p>
      ) : (
        <div className="space-y-4">
          {transactions.map((txn) => {
            const badge = STATUS_BADGES[txn.status] || {
              label: txn.status,
              color: "bg-gray-100 text-gray-800",
            };

            return (
              <div
                key={txn.id}
                className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-4"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <span className="font-semibold text-lg">
                      {formatCents(txn.amount_cents)}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${badge.color}`}
                    >
                      {badge.label}
                    </span>
                  </div>
                  <span className="text-sm text-gray-500">
                    {timeAgo(txn.created_at)}
                  </span>
                </div>

                <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                  <p>Conversation #{txn.conversation_id} &middot; Listing #{txn.listing_id}</p>
                  {txn.tracking_number && (
                    <p>Tracking: {txn.tracking_number}</p>
                  )}
                  {txn.checkout_url && txn.status === "pending" && (
                    <p>
                      <a
                        href={txn.checkout_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        Payment Link
                      </a>
                    </p>
                  )}
                </div>

                {/* Tracking input for payment_held status */}
                {txn.status === "payment_held" && (
                  <div className="mt-3 flex gap-2">
                    <input
                      type="text"
                      placeholder="Enter tracking number"
                      value={trackingInputs[txn.id] || ""}
                      onChange={(e) =>
                        setTrackingInputs((prev) => ({
                          ...prev,
                          [txn.id]: e.target.value,
                        }))
                      }
                      className="flex-1 px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded text-sm bg-white dark:bg-gray-800"
                    />
                    <button
                      onClick={() => handleAddTracking(txn.id)}
                      disabled={submitting === txn.id}
                      className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
                    >
                      {submitting === txn.id ? "Saving..." : "Add Tracking"}
                    </button>
                  </div>
                )}

                {/* Shipped: show delivery progress */}
                {txn.status === "shipped" && txn.shipped_at && (
                  <div className="mt-3">
                    <div className="flex items-center gap-2 text-sm text-purple-700 dark:text-purple-400">
                      <span className="inline-block w-3 h-3 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
                      Tracking delivery... (auto-confirms in ~30s)
                    </div>
                  </div>
                )}

                {/* Delivered / Paid Out */}
                {(txn.status === "delivered" || txn.status === "paid_out") && (
                  <div className="mt-3 text-sm text-green-700 dark:text-green-400">
                    {txn.status === "paid_out"
                      ? "Funds transferred to seller"
                      : "Item delivered, processing payout..."}
                  </div>
                )}

                {/* Refunded */}
                {txn.status === "refunded" && (
                  <div className="mt-3 text-sm text-red-700 dark:text-red-400">
                    Payment refunded to buyer
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

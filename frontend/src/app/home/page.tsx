"use client";

import { useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import { api } from "@/lib/api";
import { ListingGrid } from "@/components/listings/ListingGrid";
import { ListingForm } from "@/components/listings/ListingForm";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";

/* ── helpers ──────────────────────────────────────── */
function centsToUsd(c: number) { return c / 100; }
function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

/* ── Dummy data for empty states ──────────────────── */
const DUMMY_TRANSACTIONS = [
  { id: 901, amount_cents: 42000, status: "paid_out" as const, created_at: "2025-01-15T10:00:00Z", listing_id: 1, buyer_id: 1, conversation_id: 1, tracking_number: "1Z999AA10123456784", paid_at: "2025-01-14T10:00:00Z", shipped_at: "2025-01-14T22:00:00Z", delivered_at: "2025-01-15T10:00:00Z", paid_out_at: "2025-01-15T22:00:00Z", refunded_at: null, stripe_checkout_session_id: null, stripe_payment_intent_id: null, stripe_transfer_id: null, checkout_url: null, updated_at: "2025-01-16T00:00:00Z" },
  { id: 902, amount_cents: 120000, status: "shipped" as const, created_at: "2025-01-16T14:00:00Z", listing_id: 2, buyer_id: 2, conversation_id: 2, tracking_number: "9400111899223100001", paid_at: "2025-01-15T22:00:00Z", shipped_at: "2025-01-16T02:00:00Z", delivered_at: null, paid_out_at: null, refunded_at: null, stripe_checkout_session_id: null, stripe_payment_intent_id: null, stripe_transfer_id: null, checkout_url: null, updated_at: "2025-01-17T00:00:00Z" },
  { id: 903, amount_cents: 8500, status: "payment_held" as const, created_at: "2025-01-17T08:00:00Z", listing_id: 3, buyer_id: 3, conversation_id: 3, tracking_number: null, paid_at: "2025-01-17T09:00:00Z", shipped_at: null, delivered_at: null, paid_out_at: null, refunded_at: null, stripe_checkout_session_id: null, stripe_payment_intent_id: null, stripe_transfer_id: null, checkout_url: null, updated_at: "2025-01-17T10:00:00Z" },
  { id: 904, amount_cents: 35000, status: "delivered" as const, created_at: "2025-01-12T09:00:00Z", listing_id: 4, buyer_id: 4, conversation_id: 4, tracking_number: "1Z999AA10123456789", paid_at: "2025-01-11T09:00:00Z", shipped_at: "2025-01-11T21:00:00Z", delivered_at: "2025-01-12T09:00:00Z", paid_out_at: null, refunded_at: null, stripe_checkout_session_id: null, stripe_payment_intent_id: null, stripe_transfer_id: null, checkout_url: null, updated_at: "2025-01-12T12:00:00Z" },
  { id: 905, amount_cents: 22500, status: "paid_out" as const, created_at: "2025-01-09T11:00:00Z", listing_id: 5, buyer_id: 5, conversation_id: 5, tracking_number: "1Z888BB20234567890", paid_at: "2025-01-08T11:00:00Z", shipped_at: "2025-01-08T23:00:00Z", delivered_at: "2025-01-09T11:00:00Z", paid_out_at: "2025-01-10T11:00:00Z", refunded_at: null, stripe_checkout_session_id: null, stripe_payment_intent_id: null, stripe_transfer_id: null, checkout_url: null, updated_at: "2025-01-10T12:00:00Z" },
  { id: 906, amount_cents: 67500, status: "paid_out" as const, created_at: "2025-01-05T15:00:00Z", listing_id: 6, buyer_id: 6, conversation_id: 6, tracking_number: "9400222899334200002", paid_at: "2025-01-04T15:00:00Z", shipped_at: "2025-01-05T03:00:00Z", delivered_at: "2025-01-05T15:00:00Z", paid_out_at: "2025-01-06T15:00:00Z", refunded_at: null, stripe_checkout_session_id: null, stripe_payment_intent_id: null, stripe_transfer_id: null, checkout_url: null, updated_at: "2025-01-06T16:00:00Z" },
  { id: 907, amount_cents: 15000, status: "pending" as const, created_at: "2025-01-17T12:00:00Z", listing_id: 7, buyer_id: 7, conversation_id: 7, tracking_number: null, paid_at: null, shipped_at: null, delivered_at: null, paid_out_at: null, refunded_at: null, stripe_checkout_session_id: null, stripe_payment_intent_id: null, stripe_transfer_id: null, checkout_url: "https://checkout.stripe.com/example", updated_at: "2025-01-17T12:00:00Z" },
];

export default function HomePage() {
  const [newListingOpen, setNewListingOpen] = useState(false);
  const { data: listings } = useSWR("/api/listings", () => api.listings.list().catch(() => []), { fallbackData: [], revalidateOnFocus: false, shouldRetryOnError: false, refreshInterval: 10000 });
  const { data: jobs } = useSWR("/api/jobs", () => api.jobs.list().catch(() => []), { fallbackData: [], revalidateOnFocus: false, shouldRetryOnError: false, refreshInterval: 10000 });
  const { data: transactions } = useSWR("/payments/transactions", () => api.payments.listTransactions().catch(() => []), { fallbackData: [], revalidateOnFocus: false, shouldRetryOnError: false, refreshInterval: 10000 });

  const txns = [...(transactions || []), ...DUMMY_TRANSACTIONS].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  const allListings = listings || [];

  return (
    <div className="space-y-6">
      {/* ── Your Listings ─────────────────────────── */}
      <div>
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-xl font-bold">Your Listings</h2>
          <button
            type="button"
            onClick={() => setNewListingOpen(true)}
            className="px-4 py-1.5 bg-primary text-white text-sm font-bold border-2 border-ink neo-shadow-sm neo-hover"
          >
            + New Listing
          </button>
        </div>
        <ListingGrid listings={allListings} jobs={jobs || []} />
      </div>

      {/* ── Recent Transactions ───────────────────── */}
      <div>
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-xl font-bold">Recent Transactions</h2>
          <Link href="/transactions">
            <Button size="sm">View All</Button>
          </Link>
        </div>
        <div className="space-y-2">
          {txns.slice(0, 6).map((txn) => (
            <Card key={txn.id} className="p-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-lg font-black">${centsToUsd(txn.amount_cents).toFixed(2)}</span>
                <StatusBadge status={txn.status} />
              </div>
              <div className="text-right">
                {txn.tracking_number && <p className="text-[10px] text-ink/40 font-medium">{txn.tracking_number}</p>}
                <span className="text-xs text-ink/40 font-medium">{timeAgo(txn.created_at)}</span>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* New Listing Modal */}
      {newListingOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40"
          onClick={() => setNewListingOpen(false)}
        >
          <div
            className="bg-surface border-2 border-ink neo-shadow max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <ListingForm
              onSuccess={() => setNewListingOpen(false)}
              onCancel={() => setNewListingOpen(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

"use client";

import Link from "next/link";
import Image from "next/image";
import useSWR from "swr";
import { api } from "@/lib/api";

const DUMMY_EARNED = 132000; // $1,320.00 in cents

export function Header() {
  const { data: transactions } = useSWR("/payments/transactions/header", () => api.payments.listTransactions().catch(() => []), { fallbackData: [], revalidateOnFocus: false, shouldRetryOnError: false, refreshInterval: 10000 });

  const totalEarnedCents = transactions && transactions.length > 0
    ? transactions.filter((t) => t.status === "paid_out").reduce((s, t) => s + t.amount_cents, 0)
    : DUMMY_EARNED;

  const earned = (totalEarnedCents / 100).toLocaleString("en-US", { style: "currency", currency: "USD" });

  return (
    <header className="sticky top-0 z-50 bg-surface border-b-2 border-ink">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo + Wordmark */}
          <Link href="/home" className="flex items-center gap-2.5 shrink-0">
            <Image src="/logo.png" alt="bye! buy!" width={36} height={36} className="w-9 h-9" />
            <span className="font-wordmark text-xl font-bold text-primary tracking-tight">
              bye! buy!
            </span>
          </Link>

          {/* Right: Earnings + Profile */}
          <div className="flex items-center gap-3">
            <Link
              href="/transactions"
              className="px-3 py-1.5 border-2 border-ink bg-primary/5 flex items-center gap-2 neo-shadow-sm hover:bg-primary/10 transition-colors"
            >
              <span className="text-[10px] font-bold text-ink/40 uppercase">Earned</span>
              <span className="text-sm font-black text-ink">{earned}</span>
            </Link>

            <Link
              href="/home"
              className="w-10 h-10 border-2 border-ink bg-primary/10 flex items-center justify-center neo-shadow-sm neo-hover"
              aria-label="Profile"
            >
              <svg className="w-5 h-5 text-ink" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
}

"use client";

import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

export default function PaymentSuccessPage() {
  return (
    <div className="max-w-lg mx-auto mt-20">
      <Card className="p-8 text-center bg-green/10">
        {/* Confetti-like decorative elements */}
        <div className="relative">
          <div className="absolute -top-4 -left-4 w-6 h-6 bg-yellow border-2 border-ink rotate-12" />
          <div className="absolute -top-6 right-8 w-4 h-4 bg-primary border-2 border-ink -rotate-6" />
          <div className="absolute -top-2 right-0 w-5 h-5 bg-secondary border-2 border-ink rotate-45" />
        </div>

        <div className="text-6xl mb-4 font-black text-green">✓</div>
        <h1 className="text-2xl font-black mb-3">Payment Received!</h1>
        <p className="text-ink/60 mb-6 font-medium">
          Your money is held securely until the item is delivered. You&apos;ll be
          notified once the seller ships and the item arrives.
        </p>
        <Link href="/transactions">
          <Button variant="success">View Transactions</Button>
        </Link>
      </Card>
    </div>
  );
}

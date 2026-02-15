"use client";

import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

export default function PaymentCancelPage() {
  return (
    <div className="max-w-lg mx-auto mt-20">
      <Card className="p-8 text-center bg-orange/10">
        <div className="text-6xl mb-4 font-black text-orange">✕</div>
        <h1 className="text-2xl font-black mb-3">Payment Cancelled</h1>
        <p className="text-ink/60 mb-6 font-medium">
          Your payment was not completed. You can try again from the payment link
          if you change your mind.
        </p>
        <Link href="/home">
          <Button variant="secondary">Back to Dashboard</Button>
        </Link>
      </Card>
    </div>
  );
}

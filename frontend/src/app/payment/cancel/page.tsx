"use client";

import Link from "next/link";

export default function PaymentCancelPage() {
  return (
    <div className="max-w-lg mx-auto p-6 text-center mt-20">
      <div className="text-5xl mb-4">&#10005;</div>
      <h1 className="text-2xl font-bold mb-3">Payment Cancelled</h1>
      <p className="text-gray-600 dark:text-gray-400 mb-6">
        Your payment was not completed. You can try again from the payment link
        if you change your mind.
      </p>
      <Link
        href="/dashboard"
        className="inline-block px-6 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
      >
        Back to Dashboard
      </Link>
    </div>
  );
}

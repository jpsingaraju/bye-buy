"use client";

import Link from "next/link";

export default function PaymentSuccessPage() {
  return (
    <div className="max-w-lg mx-auto p-6 text-center mt-20">
      <div className="text-5xl mb-4">&#10003;</div>
      <h1 className="text-2xl font-bold mb-3">Payment Received!</h1>
      <p className="text-gray-600 dark:text-gray-400 mb-6">
        Your money is held securely until the item is delivered. You&apos;ll be
        notified once the seller ships and the item arrives.
      </p>
      <Link
        href="/transactions"
        className="inline-block px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        View Transactions
      </Link>
    </div>
  );
}

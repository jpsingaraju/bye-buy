interface StatusBadgeProps {
  status: string;
  className?: string;
}

const statusConfig: Record<string, { bg: string; label: string }> = {
  pending: { bg: "bg-yellow text-ink", label: "Pending" },
  posting: { bg: "bg-sky text-ink", label: "Posting" },
  posted: { bg: "bg-green text-ink", label: "Posted" },
  failed: { bg: "bg-primary text-white", label: "Failed" },
  active: { bg: "bg-sky text-ink", label: "Active" },
  sold: { bg: "bg-green text-ink", label: "Sold" },
  closed: { bg: "bg-muted text-white", label: "Closed" },
  payment_held: { bg: "bg-secondary text-white", label: "Payment Held" },
  shipped: { bg: "bg-orange text-ink", label: "Shipped" },
  delivered: { bg: "bg-green text-ink", label: "Delivered" },
  paid_out: { bg: "bg-green text-ink", label: "Paid Out" },
  refunded: { bg: "bg-primary text-white", label: "Refunded" },
  negotiating: { bg: "bg-sky text-ink", label: "Negotiating" },
  agreed: { bg: "bg-green text-ink", label: "Agreed" },
  waiting: { bg: "bg-orange text-ink", label: "Waiting" },
  confirmed: { bg: "bg-green text-ink", label: "Confirmed" },
};

export function StatusBadge({ status, className = "" }: StatusBadgeProps) {
  const config = statusConfig[status] || {
    bg: "bg-muted text-white",
    label: status,
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 text-xs font-bold border border-ink ${config.bg} ${className}`}
    >
      {config.label}
    </span>
  );
}

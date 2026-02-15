export interface ListingImage {
  id: number;
  listing_id: number;
  filename: string;
  filepath: string;
  position: number;
  created_at: string;
}

export type ListingCondition = "new" | "like_new" | "good" | "fair";

export interface Listing {
  id: number;
  title: string;
  description: string;
  price: number;
  condition: ListingCondition;
  location: string | null;
  created_at: string;
  updated_at: string;
  images: ListingImage[];
}

export interface JobLog {
  id: number;
  job_id: number;
  level: string;
  message: string;
  screenshot_path: string | null;
  created_at: string;
}

export interface PostingJob {
  id: number;
  listing_id: number;
  platform: string;
  status: "pending" | "posting" | "posted" | "failed";
  external_id: string | null;
  external_url: string | null;
  error_message: string | null;
  retry_count: number;
  scheduled_at: string;
  started_at: string | null;
  completed_at: string | null;
  logs?: JobLog[];
}

export type Platform = "facebook_marketplace" | "ebay" | "craigslist" | "mercari";

export type TransactionStatus =
  | "pending"
  | "payment_held"
  | "shipped"
  | "delivered"
  | "paid_out"
  | "refunded";

export interface Transaction {
  id: number;
  conversation_id: number;
  listing_id: number;
  buyer_id: number;
  amount_cents: number;
  stripe_checkout_session_id: string | null;
  stripe_payment_intent_id: string | null;
  stripe_transfer_id: string | null;
  checkout_url: string | null;
  tracking_number: string | null;
  status: TransactionStatus;
  paid_at: string | null;
  shipped_at: string | null;
  delivered_at: string | null;
  paid_out_at: string | null;
  refunded_at: string | null;
  created_at: string;
  updated_at: string;
}

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
  min_price: number | null;
  willing_to_negotiate: number;
  seller_notes: string | null;
  condition: ListingCondition;
  location: string | null;
  status: string;
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

/* ── Messaging / Conversations ───────────────────── */

export interface Buyer {
  id: number;
  fb_name: string;
  fb_profile_url: string | null;
  created_at: string;
}

export interface Message {
  id: number;
  conversation_id: number;
  role: string;
  content: string;
  sent_at: string;
  delivered: boolean;
}

export interface Conversation {
  id: number;
  buyer_id: number;
  listing_id: number | null;
  fb_thread_id: string | null;
  status: string;
  agreed_price: number | null;
  current_offer: number | null;
  delivery_address: string | null;
  last_message_at: string | null;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  buyer: Buyer;
  messages: Message[];
  listing?: {
    id: number;
    title: string;
    price: number;
    min_price: number | null;
    status: string;
  };
}

export interface DashboardStats {
  total_conversations: number;
  active_conversations: number;
  sold_conversations: number;
  total_messages: number;
  total_buyers: number;
}

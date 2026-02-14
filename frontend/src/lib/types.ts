export interface ListingImage {
  id: number;
  listing_id: number;
  filename: string;
  filepath: string;
  position: number;
  created_at: string;
}

export interface Listing {
  id: number;
  title: string;
  description: string;
  price: number;
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

export type Platform = "facebook_marketplace" | "ebay" | "craigslist";

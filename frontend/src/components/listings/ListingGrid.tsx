"use client";

import Link from "next/link";
import { Listing, PostingJob } from "@/lib/types";
import { ListingCard } from "./ListingCard";

interface ListingGridProps {
  listings: Listing[];
  jobs: PostingJob[];
}

const DUMMY_LISTINGS: Listing[] = [
  {
    id: -1,
    title: "Herman Miller Aeron Chair",
    description: "Ergonomic office chair in excellent condition. Size B, fully loaded with all adjustments. Barely used, works from home setup.",
    price: 850.00,
    min_price: 700.00,
    willing_to_negotiate: 1,
    seller_notes: "Firm on $700 minimum. Chair retails for $1,395 new.",
    condition: "like_new",
    location: "San Francisco, CA",
    status: "active",
    created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
    updated_at: new Date().toISOString(),
    images: [
      { id: -1, listing_id: -1, filename: "chair_1.jpg", filepath: "/chair_1.jpg", position: 0, created_at: new Date().toISOString() },
      { id: -2, listing_id: -1, filename: "chair_2.jpg", filepath: "/chair_2.jpg", position: 1, created_at: new Date().toISOString() },
      { id: -3, listing_id: -1, filename: "chair_3.jpg", filepath: "/chair_3.jpg", position: 2, created_at: new Date().toISOString() },
    ],
  },
  {
    id: -2,
    title: "AirPods Pro 2nd Gen",
    description: "Apple AirPods Pro with USB-C charging case. Active noise cancellation, transparency mode. Comes with all ear tips.",
    price: 180.00,
    min_price: 150.00,
    willing_to_negotiate: 1,
    seller_notes: "Can go as low as $150. Original retail $249.",
    condition: "good",
    location: "San Francisco, CA",
    status: "active",
    created_at: new Date(Date.now() - 86400000 * 1).toISOString(),
    updated_at: new Date().toISOString(),
    images: [
      { id: -4, listing_id: -2, filename: "airpods_1.jpg", filepath: "/airpods_1.jpg", position: 0, created_at: new Date().toISOString() },
      { id: -5, listing_id: -2, filename: "airpods_2.jpg", filepath: "/airpods_2.jpg", position: 1, created_at: new Date().toISOString() },
    ],
  },
];

export function ListingGrid({ listings, jobs }: ListingGridProps) {
  const getLatestJob = (listingId: number) => {
    return jobs
      .filter((job) => job.listing_id === listingId)
      .sort(
        (a, b) =>
          new Date(b.scheduled_at).getTime() -
          new Date(a.scheduled_at).getTime()
      )[0];
  };

  const displayListings = listings.length === 0 ? DUMMY_LISTINGS : listings;
  const isDemo = listings.length === 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {displayListings.map((listing) => (
        <ListingCard
          key={listing.id}
          listing={listing}
          latestJob={isDemo ? undefined : getLatestJob(listing.id)}
          isDemo={isDemo}
        />
      ))}
    </div>
  );
}

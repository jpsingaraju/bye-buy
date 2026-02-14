"use client";

import { Listing, PostingJob } from "@/lib/types";
import { ListingCard } from "./ListingCard";

interface ListingGridProps {
  listings: Listing[];
  jobs: PostingJob[];
}

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

  if (listings.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 dark:text-gray-400">
          No listings yet. Create your first listing to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {listings.map((listing) => (
        <ListingCard
          key={listing.id}
          listing={listing}
          latestJob={getLatestJob(listing.id)}
        />
      ))}
    </div>
  );
}

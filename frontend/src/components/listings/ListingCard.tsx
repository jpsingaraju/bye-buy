"use client";

import Link from "next/link";
import { Listing, PostingJob } from "@/lib/types";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";

interface ListingCardProps {
  listing: Listing;
  latestJob?: PostingJob;
}

export function ListingCard({ listing, latestJob }: ListingCardProps) {
  const thumbnail = listing.images[0];
  const thumbnailUrl = thumbnail ? api.getImageUrl(thumbnail.filepath) : null;

  return (
    <Link href={`/listings/${listing.id}`}>
      <Card className="overflow-hidden hover:shadow-md transition-shadow cursor-pointer">
        <div className="aspect-square bg-gray-100 dark:bg-gray-800 relative">
          {thumbnailUrl ? (
            <img
              src={thumbnailUrl}
              alt={listing.title}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-400">
              No Image
            </div>
          )}
          {latestJob && (
            <div className="absolute top-2 right-2">
              <StatusBadge status={latestJob.status} />
            </div>
          )}
        </div>
        <CardContent className="p-4">
          <h3 className="font-medium text-gray-900 dark:text-white truncate">
            {listing.title}
          </h3>
          <p className="text-lg font-semibold text-blue-600 dark:text-blue-400 mt-1">
            ${listing.price.toFixed(2)}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
            {listing.description}
          </p>
        </CardContent>
      </Card>
    </Link>
  );
}

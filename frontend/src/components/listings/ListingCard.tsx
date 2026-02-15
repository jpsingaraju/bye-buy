"use client";

import Link from "next/link";
import { Listing, PostingJob } from "@/lib/types";
import { api } from "@/lib/api";
import { TiltCard } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";

interface ListingCardProps {
  listing: Listing;
  latestJob?: PostingJob;
  isDemo?: boolean;
}

export function ListingCard({ listing, latestJob, isDemo }: ListingCardProps) {
  const thumbnail = listing.images[0];
  const thumbnailUrl = thumbnail
    ? isDemo
      ? thumbnail.filepath
      : api.getImageUrl(thumbnail.filepath)
    : null;

  const href = isDemo ? "/home" : `/listings/${listing.id}`;

  return (
    <Link href={href} className="block">
      <TiltCard className="overflow-hidden cursor-pointer group">
        {/* Image */}
        <div className="aspect-square bg-cream relative overflow-hidden border-b-2 border-ink">
          {thumbnailUrl ? (
            <img
              src={thumbnailUrl}
              alt={listing.title}
              className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-ink/30 font-bold text-lg">
              No Image
            </div>
          )}

          {/* Price badge */}
          <div className="absolute bottom-2 left-2 px-3 py-1 bg-primary text-white font-bold text-sm border-2 border-ink neo-shadow-sm">
            ${listing.price.toFixed(2)}
          </div>

          {/* Status badge */}
          {latestJob && (
            <div className="absolute top-2 right-2">
              <StatusBadge status={latestJob.status} />
            </div>
          )}
        </div>

        {/* Content */}
        <div className="p-4">
          <h3 className="font-bold text-ink truncate">{listing.title}</h3>
          <p className="text-sm text-ink/50 mt-1 line-clamp-2">
            {listing.description}
          </p>
        </div>
      </TiltCard>
    </Link>
  );
}

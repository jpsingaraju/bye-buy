"use client";

import useSWR from "swr";
import Link from "next/link";
import { api } from "@/lib/api";
import { ListingGrid } from "@/components/listings/ListingGrid";
import { Button } from "@/components/ui/Button";

export default function DashboardPage() {
  const { data: listings, error: listingsError, isLoading: listingsLoading } = useSWR(
    "/api/listings",
    () => api.listings.list(),
    { refreshInterval: 5000 }
  );

  const { data: jobs, error: jobsError } = useSWR(
    "/api/jobs",
    () => api.jobs.list(),
    { refreshInterval: 5000 }
  );

  if (listingsError || jobsError) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500">Failed to load data. Is the backend running?</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Your Listings
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Manage and post your listings to multiple platforms
          </p>
        </div>
        <Link href="/listings/new">
          <Button>Create Listing</Button>
        </Link>
      </div>

      {listingsLoading ? (
        <div className="text-center py-12">
          <p className="text-gray-500 dark:text-gray-400">Loading...</p>
        </div>
      ) : (
        <ListingGrid listings={listings || []} jobs={jobs || []} />
      )}
    </div>
  );
}

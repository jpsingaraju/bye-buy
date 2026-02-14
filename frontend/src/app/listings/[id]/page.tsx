"use client";

import { use, useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Platform } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { JobLogs } from "@/components/listings/JobLogs";

export default function ListingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const [posting, setPosting] = useState(false);
  const [selectedPlatform, setSelectedPlatform] = useState<Platform>("facebook_marketplace");

  const { data: listing, error: listingError, mutate: mutateListing } = useSWR(
    `/api/listings/${id}`,
    () => api.listings.get(parseInt(id))
  );

  const { data: jobs, mutate: mutateJobs } = useSWR(
    `/api/jobs?listing_id=${id}`,
    () => api.jobs.list({ listing_id: parseInt(id) }),
    { refreshInterval: 3000 }
  );

  if (listingError) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500">Listing not found</p>
        <Link href="/dashboard">
          <Button variant="secondary" className="mt-4">
            Back to Dashboard
          </Button>
        </Link>
      </div>
    );
  }

  if (!listing) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  const handlePost = async () => {
    setPosting(true);
    try {
      await api.listings.post(listing.id, selectedPlatform);
      mutateJobs();
    } catch (err) {
      console.error("Failed to post listing:", err);
    } finally {
      setPosting(false);
    }
  };

  const handleRetry = async (jobId: number) => {
    try {
      await api.jobs.retry(jobId);
      mutateJobs();
    } catch (err) {
      console.error("Failed to retry job:", err);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this listing?")) return;
    try {
      await api.listings.delete(listing.id);
      router.push("/dashboard");
    } catch (err) {
      console.error("Failed to delete listing:", err);
    }
  };

  const platformLabels: Record<Platform, string> = {
    facebook_marketplace: "Facebook Marketplace",
    ebay: "eBay",
    craigslist: "Craigslist",
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="flex justify-between items-start">
        <div>
          <Link
            href="/dashboard"
            className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
          >
            &larr; Back to Dashboard
          </Link>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
            {listing.title}
          </h1>
          <p className="text-2xl font-semibold text-blue-600 dark:text-blue-400 mt-1">
            ${listing.price.toFixed(2)}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="danger" onClick={handleDelete}>
            Delete
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card>
          <CardHeader>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Images
            </h2>
          </CardHeader>
          <CardContent>
            {listing.images.length > 0 ? (
              <div className="grid grid-cols-2 gap-4">
                {listing.images.map((image) => (
                  <img
                    key={image.id}
                    src={api.getImageUrl(image.filepath)}
                    alt={`${listing.title} image ${image.position + 1}`}
                    className="w-full aspect-square object-cover rounded-lg"
                  />
                ))}
              </div>
            ) : (
              <p className="text-gray-500 dark:text-gray-400">No images</p>
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Description
              </h2>
            </CardHeader>
            <CardContent>
              <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                {listing.description}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Post to Platform
              </h2>
            </CardHeader>
            <CardContent className="space-y-4">
              <select
                value={selectedPlatform}
                onChange={(e) => setSelectedPlatform(e.target.value as Platform)}
                className="block w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-2 text-gray-900 dark:text-gray-100"
              >
                <option value="facebook_marketplace">Facebook Marketplace</option>
                <option value="ebay">eBay</option>
                <option value="craigslist">Craigslist</option>
              </select>
              <Button onClick={handlePost} disabled={posting} className="w-full">
                {posting ? "Posting..." : "Post Listing"}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Posting History
          </h2>
        </CardHeader>
        <CardContent>
          {jobs && jobs.length > 0 ? (
            <div className="space-y-4">
              {jobs.map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg"
                >
                  <div className="flex items-center gap-4">
                    <StatusBadge status={job.status} />
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">
                        {platformLabels[job.platform as Platform]}
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {new Date(job.scheduled_at).toLocaleString()}
                      </p>
                      {job.error_message && (
                        <p className="text-sm text-red-500 mt-1">
                          {job.error_message}
                        </p>
                      )}
                      {job.external_url && (
                        <a
                          href={job.external_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                        >
                          View on {platformLabels[job.platform as Platform]}
                        </a>
                      )}
                      <JobLogs jobId={job.id} />
                    </div>
                  </div>
                  {job.status === "failed" && job.retry_count < 3 && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleRetry(job.id)}
                    >
                      Retry
                    </Button>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 dark:text-gray-400">
              No posting history yet
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

import { Listing, PostingJob, Platform } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new ApiError(res.status, error.detail || "Request failed");
  }

  return res.json();
}

export const api = {
  listings: {
    list: () => fetchApi<Listing[]>("/api/listings"),

    get: (id: number) => fetchApi<Listing>(`/api/listings/${id}`),

    create: async (data: {
      title: string;
      description: string;
      price: number;
      images: File[];
    }) => {
      const formData = new FormData();
      formData.append("title", data.title);
      formData.append("description", data.description);
      formData.append("price", data.price.toString());
      data.images.forEach((file) => formData.append("images", file));

      return fetchApi<Listing>("/api/listings", {
        method: "POST",
        body: formData,
      });
    },

    update: async (
      id: number,
      data: {
        title?: string;
        description?: string;
        price?: number;
        images?: File[];
      }
    ) => {
      const formData = new FormData();
      if (data.title) formData.append("title", data.title);
      if (data.description) formData.append("description", data.description);
      if (data.price) formData.append("price", data.price.toString());
      data.images?.forEach((file) => formData.append("images", file));

      return fetchApi<Listing>(`/api/listings/${id}`, {
        method: "PUT",
        body: formData,
      });
    },

    delete: (id: number) =>
      fetchApi<{ status: string }>(`/api/listings/${id}`, {
        method: "DELETE",
      }),

    post: (id: number, platform: Platform) =>
      fetchApi<PostingJob>(`/api/listings/${id}/post`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ platform }),
      }),
  },

  jobs: {
    list: (params?: { status?: string; listing_id?: number }) => {
      const searchParams = new URLSearchParams();
      if (params?.status) searchParams.append("status", params.status);
      if (params?.listing_id)
        searchParams.append("listing_id", params.listing_id.toString());
      const query = searchParams.toString();
      return fetchApi<PostingJob[]>(`/api/jobs${query ? `?${query}` : ""}`);
    },

    get: (id: number) => fetchApi<PostingJob>(`/api/jobs/${id}`),

    retry: (id: number) =>
      fetchApi<PostingJob>(`/api/jobs/${id}/retry`, { method: "POST" }),

    getLogs: (id: number) =>
      fetchApi<PostingJob>(`/api/jobs/${id}/logs`),
  },

  getImageUrl: (filepath: string) => {
    const filename = filepath.split("/").pop();
    return `${API_BASE}/uploads/${filename}`;
  },
};

import {
  Listing,
  ListingCondition,
  PostingJob,
  Platform,
  Transaction,
  Conversation,
  ConversationDetail,
  DashboardStats,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const MESSAGING_API_BASE =
  process.env.NEXT_PUBLIC_MESSAGING_API_URL || "http://localhost:8001";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit,
  baseUrl: string = API_BASE
): Promise<T> {
  const res = await fetch(`${baseUrl}${endpoint}`, {
    ...options,
    headers: {
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const error = await res
      .json()
      .catch(() => ({ detail: "Request failed" }));
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
      condition: ListingCondition;
      location?: string;
      min_price?: number;
      seller_notes?: string;
      images: File[];
    }) => {
      const formData = new FormData();
      formData.append("title", data.title);
      formData.append("description", data.description);
      formData.append("price", data.price.toString());
      formData.append("condition", data.condition);
      if (data.location) formData.append("location", data.location);
      if (data.min_price !== undefined)
        formData.append("min_price", data.min_price.toString());
      if (data.seller_notes) formData.append("seller_notes", data.seller_notes);
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
        condition?: ListingCondition;
        location?: string;
        min_price?: number;
        seller_notes?: string;
        images?: File[];
      }
    ) => {
      const formData = new FormData();
      if (data.title) formData.append("title", data.title);
      if (data.description) formData.append("description", data.description);
      if (data.price) formData.append("price", data.price.toString());
      if (data.condition) formData.append("condition", data.condition);
      if (data.location) formData.append("location", data.location);
      if (data.min_price !== undefined)
        formData.append("min_price", data.min_price.toString());
      if (data.seller_notes) formData.append("seller_notes", data.seller_notes);
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

    postBatch: (id: number, platforms: Platform[]) =>
      fetchApi<PostingJob[]>(`/api/listings/${id}/post-batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ platforms }),
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

    getLogs: (id: number) => fetchApi<PostingJob>(`/api/jobs/${id}/logs`),
  },

  getImageUrl: (filepath: string) => {
    const filename = filepath.split("/").pop();
    return `${API_BASE}/uploads/${filename}`;
  },

  payments: {
    listTransactions: () =>
      fetchApi<Transaction[]>(
        "/payments/transactions",
        undefined,
        MESSAGING_API_BASE
      ),

    getTransaction: (id: number) =>
      fetchApi<Transaction>(
        `/payments/transactions/${id}`,
        undefined,
        MESSAGING_API_BASE
      ),

    addTracking: (id: number, trackingNumber: string) =>
      fetchApi<Transaction>(
        `/payments/transactions/${id}/tracking`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ tracking_number: trackingNumber }),
        },
        MESSAGING_API_BASE
      ),

    createCheckout: (conversationId: number) =>
      fetchApi<{ checkout_url: string; transaction_id: number }>(
        `/payments/checkout/${conversationId}`,
        { method: "POST" },
        MESSAGING_API_BASE
      ),
  },

  conversations: {
    list: (params?: { listing_id?: number; status?: string }) => {
      const searchParams = new URLSearchParams();
      if (params?.listing_id)
        searchParams.append("listing_id", params.listing_id.toString());
      if (params?.status) searchParams.append("status", params.status);
      const query = searchParams.toString();
      return fetchApi<Conversation[]>(
        `/conversations${query ? `?${query}` : ""}`,
        undefined,
        MESSAGING_API_BASE
      );
    },

    get: (id: number) =>
      fetchApi<ConversationDetail>(
        `/conversations/${id}`,
        undefined,
        MESSAGING_API_BASE
      ),
  },

  stats: {
    get: () =>
      fetchApi<DashboardStats>("/stats", undefined, MESSAGING_API_BASE),
  },
};

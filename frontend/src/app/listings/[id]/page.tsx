"use client";

import { use, useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import { api } from "@/lib/api";
import { Platform, Conversation, ConversationDetail } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { AnimatedCounter } from "@/components/ui/AnimatedCounter";
import { JobLogs } from "@/components/listings/JobLogs";

/* ── helpers ──────────────────────────────────────── */
function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

/* ── Dummy conversations when no real data ────────── */
const DUMMY_CONVOS: { buyerName: string; status: string; offer: number; agreedPrice: number | null; messages: { role: string; content: string; time: string }[] }[] = [
  {
    buyerName: "Sarah M.",
    status: "active",
    offer: 420,
    agreedPrice: null,
    messages: [
      { role: "buyer", content: "Hey, is this still available?", time: "2m ago" },
      { role: "seller", content: "Yes! It's in great condition, barely used.", time: "1m ago" },
      { role: "buyer", content: "Would you take $400?", time: "45s ago" },
      { role: "seller", content: "I can do $420, that's the lowest I'll go.", time: "30s ago" },
      { role: "buyer", content: "Let me think about it...", time: "10s ago" },
    ],
  },
  {
    buyerName: "Mike R.",
    status: "active",
    offer: 380,
    agreedPrice: null,
    messages: [
      { role: "buyer", content: "Hi! What condition is this in?", time: "15m ago" },
      { role: "seller", content: "Like new, comes with original box and all accessories.", time: "14m ago" },
      { role: "buyer", content: "Can you do $350?", time: "10m ago" },
      { role: "seller", content: "The lowest I can go is $380. It's a great deal for the condition.", time: "8m ago" },
      { role: "buyer", content: "I'll do $380. Where can we meet?", time: "5m ago" },
      { role: "seller", content: "Great! I'll send you a payment link via Visa Direct.", time: "3m ago" },
    ],
  },
  {
    buyerName: "James K.",
    status: "agreed",
    offer: 450,
    agreedPrice: 430,
    messages: [
      { role: "buyer", content: "Interested! Full price?", time: "1h ago" },
      { role: "seller", content: "I can do $430 if you pay today.", time: "55m ago" },
      { role: "buyer", content: "Deal! Let's do it.", time: "50m ago" },
      { role: "seller", content: "Payment link sent! Once confirmed, we'll arrange pickup.", time: "45m ago" },
    ],
  },
  {
    buyerName: "Lisa T.",
    status: "closed",
    offer: 300,
    agreedPrice: null,
    messages: [
      { role: "buyer", content: "Would you take $300?", time: "2h ago" },
      { role: "seller", content: "Sorry, the lowest I can accept is $380.", time: "2h ago" },
      { role: "buyer", content: "That's too much for me. Thanks anyway!", time: "1h ago" },
    ],
  },
];

/* ── Photo Carousel ──────────────────────────────── */
function PhotoCarousel({ images, title }: { images: { id: number; filepath: string }[]; title: string }) {
  const [currentIndex, setCurrentIndex] = useState(0);

  if (images.length === 0) {
    return (
      <Card className="overflow-hidden">
        <div className="aspect-[4/3] bg-cream flex items-center justify-center">
          <span className="text-ink/30 font-bold">No Photos</span>
        </div>
      </Card>
    );
  }

  const prev = () => setCurrentIndex((i) => (i === 0 ? images.length - 1 : i - 1));
  const next = () => setCurrentIndex((i) => (i === images.length - 1 ? 0 : i + 1));

  return (
    <Card className="overflow-hidden">
      <div className="relative aspect-[4/3] bg-cream">
        <img
          src={api.getImageUrl(images[currentIndex].filepath)}
          alt={`${title} - ${currentIndex + 1}`}
          className="w-full h-full object-cover"
        />

        {images.length > 1 && (
          <>
            {/* Left arrow */}
            <button
              onClick={prev}
              className="absolute left-2 top-1/2 -translate-y-1/2 w-8 h-8 bg-surface/90 border-2 border-ink flex items-center justify-center hover:bg-surface transition-colors"
            >
              <span className="text-sm font-black text-ink">&larr;</span>
            </button>

            {/* Right arrow */}
            <button
              onClick={next}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 bg-surface/90 border-2 border-ink flex items-center justify-center hover:bg-surface transition-colors"
            >
              <span className="text-sm font-black text-ink">&rarr;</span>
            </button>

            {/* Dots */}
            <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1.5">
              {images.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentIndex(i)}
                  className={`w-2 h-2 border border-ink transition-colors ${
                    i === currentIndex ? "bg-primary" : "bg-surface/70"
                  }`}
                />
              ))}
            </div>

            {/* Counter */}
            <div className="absolute top-2 right-2 px-2 py-0.5 bg-ink/70 text-white text-[10px] font-bold">
              {currentIndex + 1} / {images.length}
            </div>
          </>
        )}
      </div>
    </Card>
  );
}

/* ── Chat Card Component (dummy conversations) ───── */
function ChatCard({ chat }: {
  chat: typeof DUMMY_CONVOS[0];
  isDemo: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const lastMsg = chat.messages[chat.messages.length - 1];

  return (
    <ChatCardShell
      buyerName={chat.buyerName}
      status={chat.agreedPrice ? "agreed" : chat.status}
      offer={chat.offer}
      lastMessage={lastMsg?.content}
      expanded={expanded}
      onToggle={() => setExpanded(!expanded)}
    >
      {chat.messages.map((msg, i) => (
        <div key={i} className={`flex ${msg.role === "seller" ? "justify-end" : "justify-start"}`}>
          <div className={`max-w-[75%] px-3 py-2 border-2 border-ink ${
            msg.role === "seller" ? "bg-primary/10" : "bg-surface"
          }`}>
            <span className={`text-[10px] font-bold block mb-0.5 ${
              msg.role === "seller" ? "text-primary" : "text-ink/40"
            }`}>
              {msg.role === "seller" ? "AI Agent" : chat.buyerName}
            </span>
            <p className="text-sm text-ink leading-snug">{msg.content}</p>
            <span className="block text-[9px] text-ink/30 mt-1">{msg.time}</span>
          </div>
        </div>
      ))}
    </ChatCardShell>
  );
}

/* ── Real Chat Card (fetches message history) ──────── */
function RealChatCard({ conversation }: { conversation: Conversation }) {
  const [expanded, setExpanded] = useState(false);
  const { data: detail } = useSWR(
    expanded ? `/conversations/${conversation.id}` : null,
    () => api.conversations.get(conversation.id),
  );

  const buyerName = detail?.buyer?.fb_name || `Buyer #${conversation.buyer_id}`;
  const offer = conversation.current_offer ?? conversation.agreed_price ?? 0;
  const messages = detail?.messages || [];
  const lastMsg = messages.length > 0
    ? messages[messages.length - 1].content
    : conversation.last_message_at ? `Last active ${timeAgo(conversation.last_message_at)}` : "No messages yet";

  return (
    <ChatCardShell
      buyerName={buyerName}
      status={conversation.agreed_price ? "agreed" : conversation.status}
      offer={offer}
      lastMessage={lastMsg}
      expanded={expanded}
      onToggle={() => setExpanded(!expanded)}
    >
      {messages.length === 0 && expanded ? (
        <p className="text-xs text-ink/40 font-medium py-2">Loading messages...</p>
      ) : (
        messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === "seller" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[75%] px-3 py-2 border-2 border-ink ${
              msg.role === "seller" ? "bg-primary/10" : "bg-surface"
            }`}>
              <span className={`text-[10px] font-bold block mb-0.5 ${
                msg.role === "seller" ? "text-primary" : "text-ink/40"
              }`}>
                {msg.role === "seller" ? "AI Agent" : buyerName}
              </span>
              <p className="text-sm text-ink leading-snug">{msg.content}</p>
              <span className="block text-[9px] text-ink/30 mt-1">{timeAgo(msg.sent_at)}</span>
            </div>
          </div>
        ))
      )}
    </ChatCardShell>
  );
}

/* ── Shared Chat Card Shell ───────────────────────── */
function ChatCardShell({ buyerName, status, offer, lastMessage, expanded, onToggle, children }: {
  buyerName: string; status: string; offer: number; lastMessage: string;
  expanded: boolean; onToggle: () => void; children: React.ReactNode;
}) {
  return (
    <Card className="overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full text-left px-4 py-3 flex items-center justify-between hover:bg-primary/5 transition-colors"
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 bg-primary/10 border-2 border-ink flex items-center justify-center shrink-0">
            <span className="text-xs font-black text-primary">{buyerName.charAt(0)}</span>
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <p className="font-bold text-sm text-ink">{buyerName}</p>
              <StatusBadge status={status} />
            </div>
            <p className="text-xs text-ink/40 font-medium truncate">
              {lastMessage}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-3">
          <span className="font-black text-sm text-primary">${offer}</span>
          <span className="text-ink/30 text-xs">{expanded ? "▲" : "▼"}</span>
        </div>
      </button>

      {expanded && (
        <div className="border-t-2 border-ink/10 px-4 py-3 space-y-2.5 max-h-72 overflow-y-auto bg-cream/30">
          {children}
        </div>
      )}
    </Card>
  );
}

/* ── Page ──────────────────────────────────────────── */
export default function ListingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [posting, setPosting] = useState(false);
  const [selectedPlatforms, setSelectedPlatforms] = useState<Set<Platform>>(
    new Set(["facebook_marketplace", "craigslist"])
  );

  const { data: listing, error: listingError } = useSWR(`/api/listings/${id}`, () => api.listings.get(parseInt(id)));
  const { data: jobs, mutate: mutateJobs } = useSWR(`/api/jobs?listing_id=${id}`, () => api.jobs.list({ listing_id: parseInt(id) }), { refreshInterval: 3000 });
  const { data: conversations } = useSWR(`/conversations?listing_id=${id}`, () => api.conversations.list({ listing_id: parseInt(id) }), { refreshInterval: 5000 });

  if (listingError) {
    return (
      <div className="text-center py-12">
        <p className="text-primary font-bold">Listing not found</p>
        <Link href="/home" className="inline-block mt-4 px-4 py-2 bg-primary text-white text-sm font-bold border-2 border-ink neo-shadow-sm neo-hover">Back to Home</Link>
      </div>
    );
  }

  if (!listing) {
    return <div className="text-center py-12"><p className="text-ink/40 font-bold">Loading...</p></div>;
  }

  const convos = conversations || [];
  const isDemo = convos.length === 0;

  const offers = isDemo
    ? DUMMY_CONVOS.map((c) => c.offer)
    : convos.filter((c) => c.current_offer || c.agreed_price).map((c) => c.current_offer ?? c.agreed_price ?? 0);
  const highestBid = offers.length > 0 ? Math.max(...offers) : 0;
  const avgOffer = offers.length > 0 ? offers.reduce((a, b) => a + b, 0) / offers.length : 0;
  const buyerCount = isDemo ? DUMMY_CONVOS.length : convos.length;

  const togglePlatform = (platform: Platform) => {
    setSelectedPlatforms((prev) => {
      const next = new Set(prev);
      next.has(platform) ? next.delete(platform) : next.add(platform);
      return next;
    });
  };

  const handlePost = async () => {
    if (selectedPlatforms.size === 0) return;
    setPosting(true);
    try {
      const platforms = Array.from(selectedPlatforms);
      platforms.length === 1
        ? await api.listings.post(listing.id, platforms[0])
        : await api.listings.postBatch(listing.id, platforms);
      mutateJobs();
    } catch (err) { console.error("Failed to post:", err); }
    finally { setPosting(false); }
  };

  const platformLabels: Record<Platform, string> = {
    facebook_marketplace: "Facebook Marketplace", ebay: "eBay", craigslist: "Craigslist", mercari: "Mercari",
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <Link href="/home" className="text-sm font-bold text-ink/40 hover:text-primary transition-colors">&larr; Back</Link>
        <h1 className="text-3xl font-black text-ink mt-2">{listing.title}</h1>
        <div className="flex items-center gap-3 mt-2">
          <span className="px-4 py-1 bg-primary text-white font-bold text-xl border-2 border-ink neo-shadow-sm">
            ${listing.price.toFixed(2)}
          </span>
          {listing.min_price && (
            <span className="text-sm text-ink/40 font-medium">Min: ${listing.min_price.toFixed(2)}</span>
          )}
          <StatusBadge status={listing.condition} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ── Left: Listing Info (2/3) ─────────────── */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          <Card>
            <CardHeader><h2 className="font-bold">Description</h2></CardHeader>
            <CardContent>
              <p className="text-ink/80 whitespace-pre-wrap">{listing.description}</p>
              {listing.seller_notes && (
                <div className="mt-4 p-3 bg-primary/5 border-2 border-ink">
                  <p className="text-xs font-bold text-primary mb-1">AI Negotiator Notes</p>
                  <p className="text-sm text-ink/70">{listing.seller_notes}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Conversations / Chats */}
          <div>
            <h2 className="font-bold text-lg mb-3">
              Conversations
            </h2>
            <div className="space-y-2">
              {isDemo
                ? DUMMY_CONVOS.map((chat, i) => (
                    <ChatCard key={i} chat={chat} isDemo={true} />
                  ))
                : convos.map((c) => (
                    <RealChatCard key={c.id} conversation={c} />
                  ))
              }
            </div>
          </div>
        </div>

        {/* ── Right: Photos + Stats + Actions (1/3) ─────────── */}
        <div className="space-y-4">
          {/* Photo Carousel */}
          <PhotoCarousel images={listing.images} title={listing.title} />

          {/* Buyer Stats */}
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: "Buyers", value: buyerCount },
              { label: "Highest Bid", value: highestBid, currency: true },
              { label: "Avg Offer", value: avgOffer, currency: true },
              { label: "Your Floor", value: listing.min_price ?? 0, currency: true },
            ].map((stat) => (
              <Card key={stat.label} className="p-3 bg-primary/5">
                <p className="text-[10px] font-bold text-ink/40 uppercase tracking-wide">{stat.label}</p>
                <AnimatedCounter value={stat.value} format={stat.currency ? "currency" : "integer"} className="text-lg font-black text-ink mt-0.5" />
              </Card>
            ))}
          </div>

          {/* Post to Platform */}
          <Card>
            <CardHeader><h2 className="font-bold text-sm">Cross-Post</h2></CardHeader>
            <CardContent className="space-y-3">
              {(
                [["facebook_marketplace", "Facebook Marketplace"], ["craigslist", "Craigslist"]] as const
              ).map(([value, label]) => (
                <label key={value} className="flex items-center gap-3 cursor-pointer group">
                  <div className={`w-5 h-5 border-2 border-ink flex items-center justify-center transition-colors ${
                    selectedPlatforms.has(value) ? "bg-primary" : "bg-surface"
                  }`}>
                    {selectedPlatforms.has(value) && <span className="text-white text-xs font-bold">✓</span>}
                  </div>
                  <input type="checkbox" checked={selectedPlatforms.has(value)} onChange={() => togglePlatform(value)} className="sr-only" />
                  <span className="font-medium text-sm group-hover:text-primary transition-colors">{label}</span>
                </label>
              ))}
              <Button onClick={handlePost} disabled={posting || selectedPlatforms.size === 0} className="w-full">
                {posting ? "Posting..." : `Post to ${selectedPlatforms.size} Platform${selectedPlatforms.size !== 1 ? "s" : ""}`}
              </Button>
            </CardContent>
          </Card>

          {/* Posting History */}
          {jobs && jobs.length > 0 && (
            <Card>
              <CardHeader><h2 className="font-bold text-sm">Posting History</h2></CardHeader>
              <CardContent className="space-y-2">
                {jobs.map((job) => (
                  <div key={job.id} className="p-2 bg-cream border border-ink">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <StatusBadge status={job.status} />
                        <span className="font-bold text-xs">{platformLabels[job.platform as Platform]}</span>
                      </div>
                      {job.status === "failed" && job.retry_count < 3 && (
                        <button onClick={() => api.jobs.retry(job.id).then(() => mutateJobs())}
                          className="text-[10px] font-bold text-primary hover:underline">Retry</button>
                      )}
                    </div>
                    <p className="text-[10px] text-ink/40 mt-1">{new Date(job.scheduled_at).toLocaleString()}</p>
                    {job.error_message && <p className="text-[10px] text-primary mt-0.5">{job.error_message}</p>}
                    {job.external_url && (
                      <a href={job.external_url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-primary font-bold hover:underline">View &rarr;</a>
                    )}
                    <JobLogs jobId={job.id} />
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
